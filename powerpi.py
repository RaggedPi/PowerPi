#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################
#  Ragged Jack Farm (RaggedPi)                                 #
#  Package: PowerPi                                            #
#  Author: David Durost <david.durost@gmail.com>               #
#  Url: http://ragedjackfarm.net                               #
#                                                              #
#  RaspberryPi powered communications bridge between various   #
#  modbus connections (TCP, RTS) and a MQTT broker.            #
################################################################
__appname__ = "PowerPi"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.2.0a"
__license__ = "Apache2"

# Misc Imports                                                      #
import json
import uuid
from collections import OrderedDict
# Parsing Imports
import configargparse
parser = configargparse.ArgParser(default_config_files=['powerpi.conf'])
# Logging Imports
import logging
logger = logging.getLogger(__appname__)
# Datetime Imports
import time
from datetime import datetime
from tzlocal import get_localzone
# Readers Imports
from magnum import magnum
from Midnite.midnite import ClassicDevice
# Connections Imports
import paho.mqtt.client as mqtt
from pymodbus.client.asynchronous.tcp import AsynchronousModbusTcpClient as ModbusClient
from pymodbus.client.asynchronous import schedulers
from threading import thread


# Set up Logger
def setup_logger(args):
    """Setup the logger."""
    # Set default loglevel
    logger.setLevel(logging.DEBUG)
    
    # Create file handler
    # @todo: generate dated log files in a log directory
    fh = logging.FileHandler("powerpi.log")
    fh.setLevel(logging.DEBUG)
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler()

    # Check for verbose argument
    if args.verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)

    # Create formatter and add it to handlers
    fh.setFormatter(logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    ch.setFormatter(logging.Formatter('%(message)s'))
    
    # Add handlers to logger
    logger.addHandler(fh)
    logger.addHandler(ch)


# Get Arguments
def get_arguments():
    """Get parser arguments."""
    # Config File
    parser.add(
      '-cfg',
      '--config',
      help='config file path',
      default='powerpi.conf',
      is_config_file=True)
    # Verbose Mode
    parser.add(
      '-v',
      help='verbose',
      default=False,
      action='store_true',
      dest="verbose")
    # Timeout
    parser.add(
      "--timeout",
      help="Timeout for serial read",
      default=0.005,
      type=float)
    # Allow Duplicates
    parser.add(
      "-D",
      "--duplicates",
      help="Log duplicate entries (default: %(default)s)",
      action="store_true",
      dest="allowduplicates")
    # Interval
    parser.add(
      "-i",
      "--interval",
      help="Interval, in seconds, between publishing (default: %(default)s)",
      default=60,
      type=int,
      dest='interval')
    # Device
    parser.add(
      "-d",
      "--device",
      help="Serial device path (default: %(default)s)",
      default="/dev/ttyUSB0")
    # Classic Host
    parser.add(
      "-ch",
      "--classichost",
      help="Classic ip address (default: %(default)s)",
      default='localhost')
    # Classic Port
    parser.add(
      "-cp",
      "--classicport",
      help="Classic port (default: %(default)s)",
      default=502,
      type=int)
    # Broker
    parser.add("-b",
      "--broker",
      help="MQTT Broker ip address (default: %(default)s)",
      default='localhost')
    # Broker Port
    parser.add(
      "-p",
      "--port",
      help="MQTT Broker port (default: %(default)s)",
      default=1883,
      type=int)
    # MQTT Client ID
    parser.add(
      "-c",
      "--clientid",
      help="MQTT Client id (default: %(default)s)",
      default=uuidstr)
    # MQTT User
    parser.add(
      "-u",
      "--username",
      help="MQTT Username (default: %(default)s)",
      default='mqtt_user')
    # MQTT Password
    parser.add(
      "-P",
      "--password",
      help="MQTT Client Password (default: %(default)s)",
      default='mqtt')
    # MQTT Topic
    parser.add(
      "-t",
      "--topic",
      default='powerpi/',
      help="Topic prefix (default: %(default)s)")
    # Packets
    parser.add(
      "--packets",
      help="Number of packets to generate in reader (default: %(default)s)",
      default=50,
      type=int)
    # Trace
    parser.add(
      "--trace",
      help="Add raw packet info to data (default: %(default)s)",
      action="store_true")
    # Packet Cleanup
    parser.add(
      "-nc",
      "--nocleanup",
      help="Suppress clean up of unknown packets (default: %(default)s)",
      action="store_false",
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
    logger.debug(
      "Options:{}".format(str(args).replace("Namespace(", "").replace(")", "")))

    return args


# Setup MQTT
def setup_mqtt(args):
    """Setup mqtt connection."""
    # Connection flags
    mqtt.Client.connected_flag = False
    mqtt.Client.bad_connection_flag = False
    
    # MQTT client
    global client
    client = mqtt.Client(client_id=args.clientid, clean_session=False)
    client.username_pw_set(username=args.username, password=args.password)

    # Set callbacks
    client.on_connect = on_connect
    client.on_log = on_log
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

# Setup Readers
def setup_readers(args):
    """Setup reader."""
    global magnumReader
    global midniteReader

    magnumReader = magnum.Magnum(
      device=args.device,
      packets=args.packets,
      timeout=args.timeout,
      cleanpackets=args.cleanpackets)

    midniteReader = midnite.Midnite(
      schedulers.ASYNC_IO,
      port=args.classicport,
      timeout=args.timeout)
    )

def start_async_connection(client):
    global args
    res await client.



# Main loop
def main(args):
    """Main loop."""
    # Notify of start
    print("Publishing to broker:{} Every:{} seconds beginning at {}".format(
      args.broker, args.interval, datetime.now()))

    # Read Magnum devices
    devices = magnumReader.getDevices()

    # Read Midnite devices asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    new_loop, client = ModbusClient(schedulers.ASYNC_IO, port=args.classicport, loop=loop)
    loop.run_until_complete(start_async_connection(client.protocol))
    devices.append(midniteReader.getDevices())

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
        logging.error(
            "Error connecting to MQTT broker: {}".format(e))

    # Claculate Sleep Timer
    interval = time.time() - start
    sleep = args.interval - interval
    if sleep > 0:
        time.sleep(sleep)


if __name__ == '__main__':
    try:
        # start
        start_time = datetime.now()

        args = get_arguments()
        setup_logger(args)
        setup_mqtt(args)
        setup_reader(args)
        logger.debug("PowePi Starting at {}".format(start_time))

        # loop
        main(args)

        # end
        finish_time = datetime.now()
        logger.debug(finish_time)
        logger.debug(
          'Execution time: {time}'.format(
            time=(finish_time - start_time)))
        logger.debug("#"*20 + " END EXECUTION " + "#"*20)

        # bye
        sys.exit(0)
    
    # Ctrl-C
    except KeyboardInterrupt as e: 
        raise e
    # sys.exit()
    except SystemExit as e: 
        raise e
    # everything else
    except Exception as e:
        logger.exception("Unknown exception occurred.")
        sys.exit(1)


# OnConnect Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.connected_flag = True
        msg = "Connected to broker."
        logger.info(msg)
        logger.debug("{} [RC: {}]".format(msg, rc))
    else:
        client.bad_connection_flag = True
        logger.warning("Bad connection. [RC: {}]".format(rc))


# OnLog Callback
def on_log(client, obj, mid):
    # logger.debug("Mid: {}".format(str(mid)))
    pass

# OnDisconnect Callback
def on_disconnect(client, userdata, rc):
    msg = "Disconnected from broker."
    if rc != client.MQTT_ERR_SUCCESS:
        logger.debug("{} [RC: {}]".format(msg, rc))
    else:
      logger.info(msg)


# OnPublish
def on_publish(client, obj, mid):
    global payload
    msg = "Payload published.
    logger.info(msg)
    logger.debug("{} Mid: {} | payload: {}".format(msg, str(mid), dumps(payload)))




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
