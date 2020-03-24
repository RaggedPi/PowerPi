import argparse
import json
import time
import traceback
import uuid
import logging
from collections import OrderedDict
from datetime import datetime

import paho.mqtt.client as mqtt
from magnum import magnum
from tzlocal import get_localzone

from midnite import getModbusData

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
    loggin.info("Mid: {}".format(str(mid)))


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
    # Read Classic data
    classic = ClassicDevice()
    classic.read()
    # Read Magnum data
    devices = magnumReader.getDevices()
    # Concat data
    devices.append(classic.getDevice)
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
            if not args.allowduplicates:
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
    except:
        traceback.print_exc()

    interval = time.time() - start
    sleep = args.interval - interval
    if sleep > 0:
        time.sleep(sleep)


class ClassicDevice:
    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()

        self.device["device"] = "Classic"
        self.device["data"] = self.data

        self.data["pcb_revision"] = 0
        self.data["unit_type"] = 0
        self.data["build_year"] = 0
        self.data["build_month"] = 0
        self.data["build_day"] = 0
        self.data["info_flag_bits_3"] = 0
        self.data["mac_1"] = 0
        self.data["mac_0"] = 0
        self.data["mac_3"] = 0
        self.data["mac_2"] = 0
        self.data["mac_5"] = 0
        self.data["mac_4"] = 0
        self.data["unit_id"] = 0
        self.data["status_roll"] = 0
        self.data["restart_timer_ms"] = 0
        self.data["avg_battery_voltage"] = 0
        self.data["avg_pv_voltage"] = 0
        self.data["avg_battery_current"] = 0
        self.data["avg_energy_today"] = 0
        self.data["avg_power"] = 0
        self.data["charge_stage"] = 0
        self.data["charge_state"] = 0
        self.data["avg_pv_current"] = 0
        self.data["last_voc"] = 0
        self.data["highest_pv_voltage_seen"] = 0
        self.data["match_point_shadow"] = 0
        self.data["amphours_today"] = 0
        self.data["lifetime_energy"] = 0
        self.data["lifetime_amphours"] = 0
        self.data["info_flags_bits"] = -0
        self.data["battery_temperature"] = 0
        self.data["fet_temperature"] = 0
        self.data["pcb_temperature"] = 0
        self.data["no_power_timer"] = 0
        self.data["log_interval"] = 0
        self.data["modbus_port_register"] = 0
        self.data["float_time_today"] = 0
        self.data["absorb_time"] = 0
        self.data["reserved_1"] = 0
        self.data["pwm_readonly"] = 0
        self.data["reason_for_reset"] = 0
        self.data["equalize_time"] = 0
        self.data["wbjr_cmd_s"] = 0
        self.data["wbjr_raw_current"] = 0
        self.data["wbjr_pos_amphour"] = 0
        self.data["wbjr_neg_amphour"] = 0
        self.data["wbjr_net_amphour"] = 0
        self.data["wbjr_battery_current"] = 0
        self.data["wbjr_crc"] = 0
        self.data["shunt_temperature"] = 0
        self.data["soc"] = 0
        self.data["remaining_amphours"] = 0
        self.data["total_amphours"] = 0
        self.data["mppt_mode"] = 0
        self.data["aux1_and_2_function"] = 0
        self.data["name_0"] = 0
        self.data["name_1"] = 0
        self.data["name_2"] = 0
        self.data["name_3"] = 0
        self.data["name_4"] = 0
        self.data["name_5"] = 0
        self.data["name_6"] = 0
        self.data["name_7"] = 0
        self.data["temperature_compensated_regulated_battery_voltage"] = 0
        self.data["nominal_battery_voltage"] = 0
        self.data["ending_amps"] = 0
        self.data["reason_for-_resting"] = 0
        self.data["app_rev"] = 0
        self.data["net_rev"] = 0

    def read(self):
        data = getModbusData(args.classichost, args.classicport)
        for k,v in enumerate(data):
            self.data[k] = v if v != self.data[k] else self.data[k]

    def getDevice(self):
        return self.device
