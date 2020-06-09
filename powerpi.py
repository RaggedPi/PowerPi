#!/usr/bin/env python
# -*- coding: utf-8 -*-
__appname__ = "PowerPi"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.2.1"
__license__ = "Apache2"

import sys
from datetime import datetime
import uuid
from collections import OrderedDict
import paho.mqtt.client as mqtt
from tzlocal import get_localzone
import time
import json

import configargparse
parser = configargparse.ArgParser(default_config_files=['powerpi.conf'])

import logging
logger = logging.getLogger(__appname__)

# Magnum Energy
from magnum import magnum

# Midnite Classic
from Midnite import Midnite
from pymodbus.exceptions import ConnectionException
from pymodbus.exceptions import ParameterException

# UUID
uuidstr = str(uuid.uuid1())
# Saved Device List
saveddevices = {}
# Arguments
args = {}
# Readers
magnumReader = None
midniteReader = None


# OnConnect Callback
def on_connect(client, userdata, flags, rc):
    """On_connect callback."""
    if rc == 0:
        client.connected_flag = True
        client.disconnected_flag = False
        client.bad_connection_flag = False
        logger.info("Connected to MQTT broker. [RC: {}]".format(rc))
    else:
        client.bad_connection_flag = True
        client.connected_flag = False
        logger.warning("Bad connection to MQTT broker. [RC: {}]".format(rc))


# OnLog Callback
def on_log(client, obj, mid):
    """On_log callback."""
    logger.debug("{} Mid: {}".format(datetime.now(), str(mid)))


# OnDisconnect Callback
def on_disconnect(client, userdata, rc):
    """On_disconnect callback."""
    log_data = "Disconnected from MQTT broker."
    if rc != client.MQTT_ERR_SUCCESS:
        logger.debug("{} [RC: {}]".format(log_data, rc))
        client.bad_connection_flag = True

    logger.info(log_data)
    client.connected_flag = False
    client.disconnected_flag = True

# OnPublish Callback
def on_publish(client, obj, mid):
    """On_publish callback."""
    logger.info("Mid: {}".format(str(mid)))


# Set up Logger
def setup_logger(args):
    """Setup the logger."""
    # Set default loglevel
    logger.setLevel(logging.DEBUG)

    # Create file handler
    # @todo: generate dated log files in a log directory
    fh = logging.FileHandler(__appname__ + ".log")
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
    # Classic Unit ID
    parser.add(
      "-cu",
      "--classicunit",
      help="Classic unit id (default: %(default)s)",
      default=10,
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
    # Ignore Classic
    parser.add(
      "--ignoreclassic",
      help="Disables reading and reporting of classic stats (default: %(default)s",
      action="store_true",
      default=False)
    # Ignore Magnum
    parser.add(
      "--ignoremagnum",
      help="Disables reading and reporting of magnum devices (defaults: %(default)s",
      action="store_true",
      default=False)

    # Parse Args
    args = parser.parse_args()
    if args.interval < 10 or args.interval > (60*60):
        parser.error(
          "argument -i/--interval: must be between 10 seconds and 3600 (1 hour)")

    # Ensure proper topic formatting
    if args.topic[-1] != "/":
        args.topic += "/"

    # Log options
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


# Setup readers
def setup_readers(args):
    """Setup reader."""
    global magnumReader, midniteReader

    if not args.ignoremagnum:
        magnumReader = magnum.Magnum(
          device=args.device,
          packets=args.packets,
          timeout=args.timeout,
          cleanpackets=args.cleanpackets)

    if not args.ignoreclassic:
        midniteReader = Midnite.Midnite(
          host=args.classichost,
          port=args.classicport,
          unit=args.classicunit,
          timeout=args.timeout)


# Publish device data
def publish(devices):
    """Publish device data."""
    global args
    try:
        # Connect To MQTT Broker
        client.connect(args.broker)
        client.loop_start()
        while not client.connected_flag:
            time.sleep(1)

        # Build Payload Header Data
        data = OrderedDict()
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
        client.loop_stop()
        client.disconnect()
        client.connected_flag = False
        client.disconnected_flag = True

    except Exception as e:
        logging.error(
            "Failed connect to MQTT broker: {}".format(e))


# Main loop
def main(args):
    """Main loop."""
    # Notify of start
    print("Publishing to broker:{} Every:{} seconds beginning at {}".format(
      args.broker, args.interval, datetime.now()))
    while(True):
        start = time.time()
        # Read devices
        devices = []
        if not args.ignoremagnum:
            devices.append(magnumReader.getDevices()[0])
        print(devices)
        if not args.ignoreclassic:
            devices.append(midniteReader.getDevices()[0])
        print(devices)
        # Nothing to do, exit.
        if args.ignoremagnum and args.ignoreclassic:
            logger.info("No devices to report, exiting.")
            sys.exit(0)
        # Publish Device Data
        publish(devices)

        # Calculate Sleep Timer
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
        setup_readers(args)
        logger.debug("PowerPi started at {}".format(start_time))

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
        sys.exit(0)
    # sys.exit()
    except SystemExit as e:
        raise e
        sys.exit(0)

    except ParameterException as e:
        raise e
        sys.exit(1)

    # Connection fail
    except ConnectionException as e:
        raise e
        sys.exit(1)

    # everything else
    except Exception as e:
        logger.exception("Unknown exception occurred.")
        sys.exit(1)
