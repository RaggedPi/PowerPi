#!/usr/bin/env python
# -*- coding: utf-8 -*-
__appname__ = "PowerPi"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.2.1"
__license__ = "Apache2"

import sys
from datetime import datetime
from collections import OrderedDict
import paho.mqtt.client as mqtt
from tzlocal import get_localzone
import time
import json
from . import MidniteReader
from magnum import Magnum as MagnumReader
import os
import logging
logger = logging.getLogger(__appname__)



def __init__(self):
    self._configs = OrderedDict()
    # mqtt
    self._configs['mqtt']['addr'] = os.getenv('broker', 'localhost')
    self._configs['mqtt']['port'] = os.getenv('port', 1883)
    self._configs['mqtt']['client'] = os.getenv('clientid', 'powerpi-client')
    self._configs['mqtt']['username'] = os.getenv('username', 'mqtt_user')
    self._configs['mqtt']['password'] = os.getenv('password', 'mqtt')
    self._configs['mqtt']['roottopic'] = os.getenv('roottopic')
    # global
    self._configs['interval'] = os.getenv('interval', 60)
    self._configs['timeout'] = os.getenv('timeout', 0.001)
    # readers
    self._readers = [
      MidniteReader(),
      MagnumReader(),
#      TDAmeritradeReader()
    ]

# Publish mqtt data
def publish(self, items: list):
    """Publish device data."""

    try:
        # Connect To MQTT Broker
        self.client.connect(self.broker['addr'], self.broker['port'])
        self.client.loop_start()
        while not self.client.connected_flag:
            time.sleep(1)

        # Build Payload Header Data
        data = OrderedDict()
        data["datetime"] = datetime.now(
            get_localzone()).replace(microsecond=0).isoformat()

        # Publish Each item
        for item in items:
            if self.topic is None:
                topic = self.root_topic + item["item"].lower()

            data["item"] = item["item"]
            savedkey = data["item"]
            duplicate = False

            # If NOT Data From Classic OR NOT Checking For Duplicate items
            if not self.allow_duplicates:
                # If item Is Known
                if savedkey in self.saved_items:
                    for key in ["remotetimehours", "remotetimemins"]:
                        self.saved_items[savedkey][key] = item["data"][key]
                    # Duplicate Check
                    if self.saved_items[savedkey] == item["data"]:
                        duplicate = True

            # If NOT A Duplicate item
            if not duplicate:
                # Mark As Known item
                self.saved_items[savedkey] = item["data"]
                # Copy Payload Data
                data["data"] = item["data"]
                # Generate JSON
                payload = json.dumps(
                    data,
                    indent=None,
                    ensure_ascii=True,
                    allow_nan=True,
                    separators=(',', ':'))
                # Publish
                self.client.publish(topic, payload=payload)

        # Disconnect From MQTT Broker
        self.client.loop_stop()
        self.client.disconnect()
        self.client.connected_flag = False
        self.client.disconnected_flag = True

    except Exception as e:
        logging.error(
            "Failed connect to MQTT broker: {}".format(e))


# Main loop
def main(self):
    """Main loop."""
    # Notify of start
    print("Publishing to broker:{} Every:{} seconds beginning at {}".format(
      self.broker['addr'], self.interval, datetime.now()))
    while(True):
        start = time.time()
        # Read items
        items = []
        for reader in self._readers:
            if reader not in self.ignored_readers:
                data = reader.getItems()
                if len(items) > 0:
                    items.append(data[0])
                else:
                    items = data

        # Nothing to do, exit.
        if len(self.readers) == len(self.ignored_readers) or len(self.readers) == 0:
            logger.info("No items to report, exiting.")
            sys.exit(0)
        # Publish Device Data
        publish(items)

        # Calculate Sleep Timer
        interval = time.time() - start
        sleep = self._configs['interval'] - interval
        if sleep > 0:
            time.sleep(sleep)


#########
# Inits #
#########
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


# Setup MQTT
def setup_mqtt(self):
    """Setup mqtt connection."""
    # Connection flags
    mqtt.Client.connected_flag = False
    mqtt.Client.bad_connection_flag = False

    # MQTT client
    self.client = mqtt.Client(client_id=self._configs['mqtt']['client'], clean_session=False)
    self.client.username_pw_set(username=self._configs['mqtt']['username'], password=self._configs['mqtt']['password'])

    # Set callbacks
    self.client.on_connect = on_connect
    self.client.on_log = on_log
    self.client.on_disconnect = on_disconnect
    self.client.on_publish = on_publish


#############
# Callbacks #
#############
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


if __name__ == '__main__':
    try:
        # start
        start_time = datetime.now()

        setup_logger()
        setup_mqtt()
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

    # everything else
    except Exception as e:
        logger.exception("Unknown exception occurred.")
        sys.exit(1)
