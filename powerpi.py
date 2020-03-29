import argparse
import json
import time
import uuid
import logging
from collections import OrderedDict
from datetime import datetime

import paho.mqtt.client as mqtt
from magnum import magnum
from tzlocal import get_localzone

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from Midnite.midnite import ClassicDevice

################################################################
# Variables                                                    #
################################################################
uuidstr = str(uuid.uuid1())
parser = argparse.ArgumentParser(description="PowerPi MQTT Publisher")
logger = parser.add_argument_group("MQTT publish")
reader = parser.add_argument_group("Magnum reader")
seldom = parser.add_argument_group("Seldom used")


################################################################
# Callbacks                                                    #
################################################################
# OnConnect
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True
        print("Connected. [RC: {}]".format(rc))
    else:
        client.bad_connection_flag = True
        print("Bad connection. [RC: {}]".format(rc))


# OnLog
def on_log(client, obj, mid):
    print("[DEBUG] Mid: {}".format(str(mid)))


# OnDisconnect
def on_disconnect(client, userdata, rc):
    log_data = "Disconnected. ReasonCode={}".format(rc)
    if rc != client.MQTT_ERR_SUCCESS:
        logging.debug("on_disconnect: {}".format(log_data))

    logging.info(log_data)
    print(log_data)


# OnPublish
def on_publish(client, obj, mid):
    logging.info("Mid: {}".format(str(mid)))


################################################################
# Command Arguments                                            #
################################################################
# Magnum #######################################################
reader.add_argument(
    "-d",
    "--device",
    default="/dev/ttyUSB0",
    help="Serial device name (default: %(default)s)")

# Classic ######################################################
# Host
logger.add_argument(
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
    help="Broker port (default: %(default)s)")

# Broker #######################################################
# IP
logger.add_argument(
    "-b",
    "--broker",
    default='localhost',
    help="MQTT Broker address (default: %(default)s)")
# Port
seldom.add_argument(
    "-p",
    "--port",
    default=1883,
    type=int,
    help="Broker port (default: %(default)s)")
logger.add_argument(
    "-c",
    "--clientid",
    default=uuidstr,
    help="MQTT Client ID (default: %(default)s)")
logger.add_argument(
    "-u",
    "--username",
    default='mqtt_user',
    help="MQTT Username (default: %(default)s)")
logger.add_argument(
    "-P",
    "--password",
    default='mqtt',
    help="MQTT Client Password (default: %(default)s)")
logger.add_argument(
    "-t",
    "--topic",
    default='powerpi/',
    help="Topic prefix (default: %(default)s)")

# Global #######################################################g
logger.add_argument(
    "-i",
    "--interval",
    default=60,
    type=int, dest='interval',
    help="Interval, in seconds, between publishing (default: %(default)s)")
logger.add_argument(
    "-D",
    "--duplicates",
    action="store_true",
    help="Log duplicate entries (default: %(default)s)",
    dest="allowduplicates")
seldom.add_argument(
    "--packets",
    default=50,
    type=int,
    help="Number of packets to generate in reader (default: %(default)s)")
seldom.add_argument(
    "--timeout",
    default=0.005,
    type=float,
    help="Timeout for serial read (default: %(default)s)")
seldom.add_argument(
    "--trace",
    action="store_true",
    help="Add raw packet info to data (default: %(default)s)")
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
if args.topic[-1] != "/":
    args.topic += "/"
print(
    "Options:{}".format(str(args).replace("Namespace(", "").replace(")", "")))

print("Publishing to broker:{} Every:{} seconds".format(
    args.broker, args.interval))

# Magnum Reader
magnumReader = magnum.Magnum(
    device=args.device,
    packets=args.packets,
    timeout=args.timeout,
    cleanpackets=args.cleanpackets)

# Connect to mqtt broker
mqtt.Client.connected_flag = False
mqtt.Client.bad_connection_flag = False

client = mqtt.Client(client_id=args.clientid, clean_session=False)
client.on_connect = on_connect
client.on_log = on_log
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.username_pw_set(username=args.username, password=args.password)


saveddevices = {}

while True:
    start = time.time()
    # Read Magnum data
    devices = magnumReader.getDevices()

    # Read Classic data
    try:
        mbc = ModbusClient(args.classichost, args.classicport)
        classic = ClassicDevice(mbc)
        try:
            classic.read()
            # Remove data not be published
            print(classic.device)
            del classic.device["client"]
            print(classic.device)
            # Append data
            devices.append(classic.device)
        except Exception as e:
            logging.error(e)
    except Exception as e:
        logging.error(e)
    # publish
    try:
        client.connect(args.broker)
        client.loop_start()

        data = OrderedDict()
        now = int(time.time())
        data["datetime"] = datetime.now(
            get_localzone()).replace(microsecond=0).isoformat()
        for device in devices:
            topic = args.topic + device["device"].lower()
            data["device"] = device["device"]
            savedkey = data["device"]
            duplicate = False

            if not args.allowduplicates or device["device"].lower() != 'classic':
                if savedkey in saveddevices:
                    if device["device"] == magnum.REMOTE:
                        # normalize time of day in remote data for equal test
                        for key in ["remotetimehours", "remotetimemins"]:
                            saveddevices[savedkey][key] = device["data"][key]
                    if saveddevices[savedkey] == device["data"]:
                        duplicate = True
            if not duplicate:
                saveddevices[savedkey] = device["data"]
                data["data"] = device["data"]
                payload = json.dumps(
                    data,
                    indent=None,
                    ensure_ascii=True,
                    allow_nan=True,
                    separators=(',', ':'))
                client.publish(topic, payload=payload)
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        logging.error(e)

    interval = time.time() - start
    sleep = args.interval - interval
    if sleep > 0:
        time.sleep(sleep)
