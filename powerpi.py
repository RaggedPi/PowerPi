#!/usr/bin/env python
# -*- coding: utf-8 -*-
__appname__ = "PowerPi"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.2.3"
__license__ = "Apache2"

import sys
import pendulum
from datetime import datetime
from collections import OrderedDict
import paho.mqtt.client as mqtt
import time
import json
from MidniteReader import MidniteReader
#from Magnum.magnum import Magnum as MagnumReader
from MagnumReader import MagnumReader
import os
from dotenv import load_dotenv, find_dotenv
import logging

logger = logging.getLogger(__appname__)
_ignoredReaders = {}
load_dotenv(find_dotenv())


class PowerPi:
    def __init__(self):
        self._configs = OrderedDict()
        # mqtt
        self._configs['mqtt'] = OrderedDict()
        self._configs['mqtt']['addr'] = os.getenv('broker', 'localhost')
        self._configs['mqtt']['port'] = int(os.getenv('port', 1883))
        self._configs['mqtt']['client'] = os.getenv('clientid', 'powerpi-client')
        self._configs['mqtt']['username'] = os.getenv('username', 'mqtt_user')
        self._configs['mqtt']['password'] = os.getenv('password', 'mqtt')
        self._configs['mqtt']['roottopic'] = os.getenv('roottopic')
        # global
        self._configs['interval'] = int(os.getenv('interval', 60))
        self._configs['timeout'] = float(os.getenv('timeout', 0.001))
        self._configs['roottopic'] = os.getenv('roottopic', 'powerpi/')
        self._configs['allow_duplicates'] = bool(os.getenv('allowduplicates', False))
        self.topic = None
        # magnum
        self._configs['magnum'] = OrderedDict()
        self._configs['magnum']['device'] = os.getenv('device', '/dev/ttyUSB0')
        self._configs['magnum']['packets'] = os.getenv('packets', 50)

        # readers
        self._readers = [
          #MidniteReader(),
          MagnumReader(
            device=self._configs['magnum']['device'],
            timeout=float(self._configs['timeout']),
            packets=int(self._configs['magnum']['packets'])),
          # TDAmeritradeReader()
        ]
        self._savedItems = OrderedDict()

        # Logging
        self._setupLogger()

        # Mqtt
        self.setup_mqtt()

    def publishItem(
      self,
      i: list,
      timestamp: datetime = pendulum.now()):
        """Publish item to mqtt broker.

        Args:
            item (list): OrderedDict of item data to publish
        """

        if 'device' in i.keys():
            i["item"] = i["device"]

        print(i["item"])

        data = OrderedDict()
        data["datetime"] = timestamp.replace(microsecond=0).isoformat()

        # Set a topic
        topic = self._configs['roottopic'] + i["item"].lower()
        
        # Defaults
        data["item"] = i["item"]
        savedKey = data["item"]
        duplicate = False

        # If NOT Checking For Duplicate items
        if not self._configs['allow_duplicates']:
            # If item Is Known
            if savedKey in self._savedItems:
                for key in ["remotetimehours", "remotetimemins"]:
                    if key in i["data"].keys():
                        self._savedItems[savedKey][key] = i["data"][key]

                # Duplicate Check
                if self._savedItems[savedKey] == i["data"]:
                    duplicate = True
        # If NOT A Duplicate item
        if not duplicate:
            # Mark As Known item
            self._savedItems[savedKey] = i["data"]

            # Copy Payload Data
            data["data"] = i["data"]

            # Generate JSON
            payload = json.dumps(
                data,
                indent=None,
                ensure_ascii=True,
                allow_nan=True,
                separators=(',', ':'))
            # Publish
            self.client.publish(topic, payload=payload)

    # Publish mqtt data
    def publish(self, items: list):
        """Publish device data."""

        print(f"publishing {len(items)} items")

        try:
            # Connect To MQTT Broker
            self.client.connect(
              self._configs['mqtt']['addr'],
              self._configs['mqtt']['port'])
            self.client.loop_start()
            while not self.client.connected_flag:
                time.sleep(1)

            # Publish Each item
            for item in items:
                self.publishItem(item)

            # Disconnect From MQTT Broker
            self.client.loop_stop()
            self.client.disconnect()
            self.client.connected_flag = False
            self.client.disconnected_flag = True

        except Exception as e:
            logging.error(f"Failed connect to MQTT broker: {e}")

    # Set up Logger
    def _setupLogger(self):
        """Setup the logger."""
        # Set default loglevel
        logger.setLevel(logging.DEBUG)

        # Create file handler
        # @todo: generate dated log files in a log directory
        self._configs['logging'] = OrderedDict()
        self._configs['logging']['filename'] = None
        fn = self._configs['logging']['filename'] or os.getenv('logging_filename', 'powerpi.log')
        fh = logging.FileHandler(fn)
        fh.setLevel(logging.DEBUG)

        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

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
        self.client = mqtt.Client(
          client_id=self._configs['mqtt']['client'],
          clean_session=False)
        self.client.username_pw_set(
          username=self._configs['mqtt']['username'],
          password=self._configs['mqtt']['password'])

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_log = self.on_log
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish

    # Callbacks #
    def on_connect(self, client, userdata, flags, rc):
        """OnConnect callback.

        Args:
            client: client
            userdata: userdata
            flags: flags
            rc: rc
        """

        if rc == 0:
            client.connected_flag = True
            client.disconnected_flag = False
            client.bad_connection_flag = False
            logger.info(f"Connected to MQTT broker. [RC: {rc}]")
        else:
            client.bad_connection_flag = True
            client.connected_flag = False
            logger.warning(f"Bad connection to MQTT broker. [RC: {rc}]")

    def on_log(self, client, obj, mid):
        """On_log callback."""
        logger.debug(f"{pendulum.now()} Mid: {str(mid)}")

    # OnDisconnect Callback
    def on_disconnect(self, client, userdata, rc):
        """On_disconnect callback."""
        log_data = "Disconnected from MQTT broker."
        if rc != client.MQTT_ERR_SUCCESS:
            logger.debug(f"{log_data} [RC: {rc}]")
            client.bad_connection_flag = True

        logger.info(log_data)
        client.connected_flag = False
        client.disconnected_flag = True

    # OnPublish Callback
    def on_publish(self, client, obj, mid):
            """On_publish callback."""
            logger.info(f"Mid: {str(mid)}")


if __name__ == '__main__':
    try:
        # start
        start_time = pendulum.now()

        logger.debug(f"PowerPi started at {start_time}")

        # Main loop
        pp = PowerPi()

        # Notify of start
        startup = f"Publishing to broker: {pp._configs['mqtt']['addr']} "
        startup += f"Every:{pp._configs['interval']} seconds "
        startup += f"beginning at {pendulum.now().to_datetime_string()}"
        print(startup)

        while(True):
            start = pendulum.now()

            # Read items
            items = []
            print(len(items))
            for reader in pp._readers:
                if reader not in _ignoredReaders:
                    data = reader.getItems()
                    print(f"data: {len(data)}")
                    if len(items) > 0:
                        items.append(data[0])
                    else:
                        items = data
                    print(f"items: {len(items)}")

            # Nothing to do, exit.
            if len(pp._readers) == len(_ignoredReaders) or len(pp._readers) == 0:
                logger.info("No items to report, exiting.")
                sys.exit(0)

            # Publish Device Data
            pp.publish(items)

            # Calculate Sleep Timer
            interval = pendulum.period(start, pendulum.now())
            if interval.remaining_seconds > 0:
                time.sleep(interval.remaining_seconds)

        # end
        finish_time = pendulum.now()
        logger.debug(finish_time)
        logger.debug(f'Execution time: {finish_time.subtract(start_time)}')
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
        logger.exception(f"Unknown exception occurred: {e}")
        sys.exit(1)
