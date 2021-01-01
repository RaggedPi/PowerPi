#!/usr/bin/env python
# -*- coding: utf-8 -*-
__appname__ = "PowerPi"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "1.0.0"
__license__ = "Apache2"

from ReaderManager import ReaderManager
from PowerPiReaders import MidniteReader, MagnumReader
from collections import OrderedDict
import pendulum
from tzlocal import get_localzone
from datetime import datetime
from time import sleep
import logging
import paho.mqtt.client as mqtt
import os
from dotenv import load_dotenv, find_dotenv
import sys
import json

logger = logging.getLogger(__appname__)
load_dotenv(find_dotenv())


class PowerPi(ReaderManager):
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

        super().__init__(name='PowerPi')
        self._setupLogger()
        self._setupMqtt()

        self._savedItems = OrderedDict()

        self.addReader(MidniteReader())
        self.addReader(MagnumReader())
        self.items = []

    def _publishItem(self,
                     item: OrderedDict,
                     timestamp: datetime = None):
        """ Publish item to mqtt broker.

        Args:
            item (list): OrderedDict of item data to publish
        """
        #item = item[0]
        # Magnum workaround
        if 'device' in item:
            item["item"] = item["device"]

        # Create data dict
        data = OrderedDict()
        timestamp = timestamp or pendulum.now(get_localzone())
        data["datetime"] = timestamp.replace(microsecond=0).isoformat()

        # Set a topic
        topic = self._configs['roottopic'] + item["item"].lower()

        # Defaults
        data["item"] = item["item"]
        savedKey = data["item"]
        duplicate = False

        # If Checking For Duplicate items
        if self._configs['allow_duplicates']:
            # If item Is Known
            if savedKey in self._savedItems:
                # Unify timestamps
                for key in ["remotetimehours", "remotetimemins"]:
                    if key in item["data"].keys():
                        self._savedItems[savedKey][key] = item["data"][key]

                # Duplicate Check
                if self._savedItems[savedKey] == item["data"]:
                    duplicate = True
                    logger.debug('device is duplicate')

        # If NOT A Duplicate item
        if not duplicate:
            # Mark As Known item
            self._savedItems[savedKey] = item["data"]

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

    def publish(self, items: list, timestamp: datetime = None):
        try:
            if not self.client.connected_flag or self.client.disconnected_flag:
                logger.info(f"connecting to {self._configs['mqtt']['addr']}...")
                self.client.connect(
                  self._configs['mqtt']['addr'],
                  self._configs['mqtt']['port'])
                self.client.loop_start()
                while not self.client.connected_flag:
                    sleep(1)

            logger.info("connected.")
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
            exit(1)

        # Publish Each item
        logger.info(f"publishing {len(items)} item{'s' if len(items) > 1 else ''}.")
        for item in items:
            self._publishItem(item, timestamp)

        # Disconnect From MQTT Broker
        logger.info('disconnecting...')
        self.client.loop_stop()
        self.client.disconnect()
        self.client.connected_flag = False
        self.client.disconnected_flag = True

        

    # Set up Logger
    def _setupLogger(self):
        """Setup the logger."""
        # Set default loglevel
        logger.setLevel(logging.INFO)

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
    def _setupMqtt(self):
        """Setup mqtt connection."""
        # Connection flags
        mqtt.Client.connected_flag = False
        mqtt.Client.bad_connection_flag = False

        # MQTT client
        self.client = mqtt.Client(
          client_id=self._configs['mqtt']['client'],
          clean_session=True)
        self.client.username_pw_set(
          username=self._configs['mqtt']['username'],
          password=self._configs['mqtt']['password'])

        # Set callbacks
        self.client.on_connect = self._onConnect
        self.client.on_log = self._onLog
        self.client.on_disconnect = self._onDisconnect
        self.client.on_publish = self._onPublish

    # Callbacks #
    def _onConnect(self, client, userdata, flags, rc):
        """ On Connect Callback.

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
            logger.info(f"Connected to MQTT broker at {pendulum.now()}. [RC: {rc}]")
        else:
            client.bad_connection_flag = True
            client.connected_flag = False
            logger.warning(f"Bad connection to MQTT broker at {pendulum.now()}. [RC: {rc}]")

    def _onLog(self, client, obj, mid):
        """ On Log Callback. """

        #logger.debug(f"{pendulum.now()} Mid: {str(mid)}")

    def _onDisconnect(self, client, userdata, rc):
        """ On Disconnect Callback. """

        log_data = "Disconnected from MQTT broker at {pendulum.now()}."
        if rc != client.MQTT_ERR_SUCCESS:
            logger.debug(f"{log_data} [RC: {rc}]")
            client.bad_connection_flag = True

        logger.info(log_data)
        client.connected_flag = False
        client.disconnected_flag = True

    def _onPublish(self, client, obj, mid):
        """ On Publish Callback. """

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
            pp.items = []

            logger.debug("Reading readers.")
            readers = pp.getReaders()
            for reader in readers:
                logger.info(f"Reading from {reader}")
                data = readers[reader].getItems()
                print('=======================')
                print(data)
                print('=======================')
                logger.info(f"Read in {len(data)} item{'s' if len(data) > 1 else ''} from {reader}.")
                if len(pp.items) > 0:
                    logger.info(f"Appending to existing {len(pp.items)} items.")
                    pp.items.extend(data)
                    logger.info(f"there is now {len(pp.items)} items.")
                else:
                    logger.info("setting items.")
                    pp.items.append(data)
            # Nothing to do, exit.
            if len(pp.getReaders()) == 0:
                logger.info("No items to report, exiting.")
                sys.exit(0)

            # Publish Device Data
            logger.info('publishing items')
            pp.publish(pp.items)

            # Calculate Sleep Timer
            interval = pendulum.period(start, pendulum.now())
            if interval.remaining_seconds < pp._configs['interval']:
                sleep(pp._configs['interval'] - interval.remaining_seconds)

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