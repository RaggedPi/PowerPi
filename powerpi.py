################################################################
#  Ragged Jack Farm (RaggedPi)                                 #
#  Package: PowerPi                                            #
#  Author: David Durost <david.durost@gmail.com>               #
#  Url: http://ragedjackfarm.net                               #
#                                                              #
#  RaspberryPi powered communications bridge between various   #
#  modbus connections (TCP, RTS) and a MQTT broker.            #
################################################################

################################################################
# Imports                                                      #
################################################################
# Globals
import argparse
import json
import time
import uuid
import logging
from collections import OrderedDict
from datetime import datetime
# Magnum Energy
import paho.mqtt.client as mqtt
from magnum import magnum
from tzlocal import get_localzone
# Midnite Classic
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from Midnite.midnite import ClassicDevice

################################################################
# Variables                                                    #
################################################################
# UUID
uuidstr = str(uuid.uuid1())
# Saved Device List
saveddevices = {}
# Command-line Argument Parser
parser = argparse.ArgumentParser(description="PowerPi MQTT Publisher")
# Parser Groups
logger = parser.add_argument_group("MQTT publish")
reader = parser.add_argument_group("Magnum reader")
seldom = parser.add_argument_group("Seldom used")
# Logging
log = logging.getLogger(__name__)
file_hander = logging.FileHandler('powerpi.log')
file_hander.setFormatter(
    logging.Formatter('%(asctime)s :: %(loglevel)s :: %(message)s'))
log.addHandler(file_hander)


################################################################
# Callbacks                                                    #
################################################################
# OnConnect
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True
        log.info("Connected. [RC: {}]".format(rc))
    else:
        client.bad_connection_flag = True
        log.warning("Bad connection. [RC: {}]".format(rc))


# OnLog
def on_log(client, obj, mid):
    log.debug("Mid: {}".format(str(mid)))


# OnDisconnect
def on_disconnect(client, userdata, rc):
    log_data = "Disconnected. ReasonCode={}".format(rc)
    if rc != client.MQTT_ERR_SUCCESS:
        log.debug("on_disconnect: {}".format(log_data))

    log.info(log_data)


# OnPublish
def on_publish(client, obj, mid):
    log.info("Mid: {}".format(str(mid)))


################################################################
# Command Arguments                                            #
################################################################
# Magnum #######################################################
# Device
reader.add_argument(
    "-d",
    "--device",
    default="/dev/ttyUSB0",
    help="Serial device path (default: %(default)s)")

# Classic ######################################################
# Host
reader.add_argument(
    "-ch",
    "--classichost",
    default='localhost',
    help="Classic ip address (default: %(default)s)")
# Port
seldom.add_argument(
    "-cp",
    "--classicport",
    default=502,
    type=int,
    help="Classic port (default: %(default)s)")

# Broker #######################################################
# IP
logger.add_argument(
    "-b",
    "--broker",
    default='localhost',
    help="MQTT Broker ip address (default: %(default)s)")
# Port
seldom.add_argument(
    "-p",
    "--port",
    default=1883,
    type=int,
    help="MQTT Broker port (default: %(default)s)")
# MQTT Client ID
logger.add_argument(
    "-c",
    "--clientid",
    default=uuidstr,
    help="MQTT Client id (default: %(default)s)")
# MQTT User
logger.add_argument(
    "-u",
    "--username",
    default='mqtt_user',
    help="MQTT Username (default: %(default)s)")
# MQTT Password
logger.add_argument(
    "-P",
    "--password",
    default='mqtt',
    help="MQTT Client Password (default: %(default)s)")
# MQTT Topic
logger.add_argument(
    "-t",
    "--topic",
    default='powerpi/',
    help="Topic prefix (default: %(default)s)")

# Global #######################################################
# Interval
logger.add_argument(
    "-i",
    "--interval",
    default=60,
    type=int, dest='interval',
    help="Interval, in seconds, between publishing (default: %(default)s)")
# Allow Duplicates
logger.add_argument(
    "-D",
    "--duplicates",
    action="store_true",
    help="Log duplicate entries (default: %(default)s)",
    dest="allowduplicates")
# Packet Count
seldom.add_argument(
    "--packets",
    default=50,
    type=int,
    help="Number of packets to generate in reader (default: %(default)s)")
# Timeout
seldom.add_argument(
    "--timeout",
    default=0.005,
    type=float,
    help="Timeout for serial read (default: %(default)s)")
# Trace
seldom.add_argument(
    "--trace",
    action="store_true",
    help="Add raw packet info to data (default: %(default)s)")
# Cleanup
seldom.add_argument(
    "-nc",
    "--nocleanup",
    action="store_false",
    help="Suppress clean up of unknown packets (default: %(default)s)",
    dest='cleanpackets')

# Parse Args
args = parser.parse_args()
if args.interval < 10 or args.interval > (60*60):
    parser.error(
        "argument -i/--interval: must be between 10 seconds and 3600 (1 hour)")
# Ensure Proper Topic Formatting
if args.topic[-1] != "/":
    args.topic += "/"
# Log Options
log.debug(
    "Options:{}".format(str(args).replace("Namespace(", "").replace(")", "")))

# Notify
print("Publishing to broker:{} Every:{} seconds".format(
    args.broker, args.interval))

################################################################
# MQTT Configuration                                           #
################################################################
# Set MQTT Flags
mqtt.Client.connected_flag = False
mqtt.Client.bad_connection_flag = False
# MQTT Client
client = mqtt.Client(client_id=args.clientid, clean_session=False)
client.username_pw_set(username=args.username, password=args.password)

################################################################
# Readers                                                      #
################################################################
# Magnum Reader
magnumReader = magnum.Magnum(
    device=args.device,
    packets=args.packets,
    timeout=args.timeout,
    cleanpackets=args.cleanpackets)

################################################################
# Set Callbacks                                                #
################################################################
client.on_connect = on_connect
client.on_log = on_log
client.on_disconnect = on_disconnect
client.on_publish = on_publish

################################################################
# Main Loop                                                    #
################################################################
while True:
    # Start Time
    start = time.time()

    # Read Magnum data
    devices = magnumReader.getDevices()

    # Read Classic Data
    try:
        # Create Instance
        classic = ClassicDevice(
            ModbusClient(args.classichost, args.classicport))
        try:
            # Read Device
            classic.read()
            # Remove Non-Published Device Attributes
            del classic.device["client"]

            # Append Classic Device Data To Device List Data
            devices.append(classic.device)
        except Exception as e:
            log.error(
                "Error encountered reading Classic device: {}".format(e))
    except Exception as e:
        log.error(
            "Error encountered creating Classic connection: {}".format(e))

    # Publish Device Data
    try:
        # Connect To MQTT Broker
        client.connect(args.broker)
        client.loop_start()

        # Build Payload Data
        data = OrderedDict()
        now = int(time.time())
        data["datetime"] = datetime.now(
            get_localzone()).replace(microsecond=0).isoformat()

        # Publish Each Device
        for device in devices:
            topic = args.topic + device["device"].lower()
            data["device"] = device["device"]
            savedkey = data["device"]
            duplicate = False

            # If NOT Data From Classic OR NOT Checking For Duplicate Devices
            if not args.allowduplicates or device["device"].lower() != 'classic':
                # If Device Is Known
                if savedkey in saveddevices:
                    # If Magnum Remote
                    if device["device"] == magnum.REMOTE:
                        # Normalize Timestamps
                        for key in ["remotetimehours", "remotetimemins"]:
                            saveddevices[savedkey][key] = device["data"][key]
                    # Duplicate Check
                    if saveddevices[savedkey] == device["data"]:
                        duplicate = True
            # If NOT A Duplicate Device
            if not duplicate:
                # Mark As Known Device
                saveddevices[savedkey] = device["data"]
                # Copy Payload Data
                data["data"] = device["data"]
                # Generate JSON
                payload = json.dumps(
                    data,
                    indent=None,
                    ensure_ascii=True,
                    allow_nan=True,
                    separators=(',', ':'))
                # Publish
                client.publish(topic, payload=payload)
        # Disconnect From MQTT Broker
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        log.error(
            "Error connecting to MQTT broker: {}".format(e))
    
    # Claculate Sleep Timer
    interval = time.time() - start
    sleep = args.interval - interval
    if sleep > 0:
        time.sleep(sleep)
