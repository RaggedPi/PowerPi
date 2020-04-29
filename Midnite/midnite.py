#!/usr/bin/env python

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from collections import OrderedDict
import logging

# Logger
log = logging.getLogger('classic_mqtt')


# Get Registers
def getRegisters(theClient, addr, count):
    try:
        result = theClient.read_holding_registers(addr, count,  unit=10)
        if result.function_code >= 0x80:
            log.error("error getting {} for {} bytes".format(addr, count))
            return {}
    except Exception:
        log.error("Error getting {} for {} bytes".format(addr, count))
        return {}

    return result.registers


# Data Decoder
def getDataDecoder(registers):
    return BinaryPayloadDecoder.fromRegisters(
        registers,
        byteorder=Endian.Big,
        wordorder=Endian.Little)


# Decode Data
def doDecode(addr, decoder):
    if (addr == 4100):
        decoded = OrderedDict([
            ('pcb_revision', decoder.decode_8bit_uint()),                 # 4101 MSB
            ('unit_type', decoder.decode_8bit_uint()),                    # 4101 LSB
            ('build_year', decoder.decode_16bit_uint()),                  # 4102
            ('build_month', decoder.decode_8bit_uint()),                  # 4103 MSB
            ('build_day', decoder.decode_8bit_uint()),                    # 4103 LSB
            ('info_flag_bits_3', decoder.decode_16bit_uint()),            # 4104
            ('ignore', decoder.skip_bytes(2)),                            # 4105 Reserved
            ('mac_1', decoder.decode_8bit_uint()),                        # 4106 MSB  
            ('mac_0', decoder.decode_8bit_uint()),                        # 4106 LSB
            ('mac_3', decoder.decode_8bit_uint()),                        # 4107 MSB
            ('mac_2', decoder.decode_8bit_uint()),                        # 4107 LSB
            ('mac_5', decoder.decode_8bit_uint()),                        # 4108 MSB
            ('mac_4', decoder.decode_8bit_uint()),                        # 4108 LSB
            ('ignore_2', decoder.skip_bytes(4)),                          # 4109, 4110
            ('unit_id', decoder.decode_32bit_int()),                      # 4111
            ('status_roll', decoder.decode_16bit_uint()),                 # 4113
            ('restart_timer_ms', decoder.decode_16bit_uint()),            # 4114
            ('avg_battery_voltage', decoder.decode_16bit_int()/10.0),     # 4115
            ('avg_pv_voltage', decoder.decode_16bit_uint()/10.0),         # 4116
            ('avg_battery_current', decoder.decode_16bit_uint()/10.0),    # 4117
            ('avg_energy_today', decoder.decode_16bit_uint()/10.0),       # 4118
            ('avg_power', decoder.decode_16bit_uint()/1.0),               # 4119
            ('charge_stage', decoder.decode_8bit_uint()),                 # 4120 MSB
            ('charge_state', decoder.decode_8bit_uint()),                 # 4120 LSB
            ('avg_pv_current', decoder.decode_16bit_uint()/10.0),         # 4121
            ('last_voc', decoder.decode_16bit_uint()/10.0),               # 4122
            ('highest_pv_voltage_seen', decoder.decode_16bit_uint()),     # 4123
            ('match_point_shadow', decoder.decode_16bit_uint()),          # 4124
            ('amphours_today', decoder.decode_16bit_uint()),              # 4125
            ('lifetime_energy', decoder.decode_32bit_uint()/10.0),        # 4126, 4127
            ('lifetime_amphours', decoder.decode_32bit_uint()),           # 4128, 4129
            ('info_flags_bits', decoder.decode_32bit_int()),              # 4130, 31
            ('battery_temperature', decoder.decode_16bit_int()/10.0),     # 4132
            ('fet_temperature', decoder.decode_16bit_int()/10.0),         # 4133
            ('pcb_temperature', decoder.decode_16bit_int()/10.0),         # 4134
            ('no_power_timer', decoder.decode_16bit_uint()),              # 4135
            # in seconds, minimum: 1 minute
            ('log_interval', decoder.decode_16bit_uint()),                # 4136
            ('modbus_port_register', decoder.decode_16bit_uint()),        # 4137
            ('float_time_today', decoder.decode_16bit_uint()),            # 4138
            ('absorb_time', decoder.decode_16bit_uint()),                 # 4139
            ('reserved_1', decoder.decode_16bit_uint()),                  # 4140
            ('pwm_readonly', decoder.decode_16bit_uint()),                # 4141
            ('reason_for_reset', decoder.decode_16bit_uint()),            # 4142
            ('equalize_time', decoder.decode_16bit_uint()),               # 4143
        ])
        del decoded["ignore"]
        del decoded["ignore_2"]
        del decoded["reserved_1"]
    elif (addr == 4360):
        decoded = OrderedDict([
            ('wbjr_cmd_s', decoder.decode_16bit_uint()),                # 4361
            ('wbjr_raw_current', decoder.decode_16bit_int()),           # 4362
            ('skip', decoder.skip_bytes(4)),                            # 4363,4364
            ('wbjr_pos_amphour', decoder.decode_32bit_uint()),          # 4365,4366
            ('wbjr_neg_amphour', decoder.decode_32bit_int()),           # 4367,4368
            ('wbjr_net_amphour', decoder.decode_32bit_int()),           # 4369,4370
            ('wbjr_battery_current', decoder.decode_16bit_int()/10.0),  # 4371
            ('wbjr_crc', decoder.decode_8bit_int()),                    # 4372 MSB
            ('shunt_temperature', decoder.decode_8bit_int() - 50.0),    # 4372 LSB
            ('soc', decoder.decode_16bit_uint()),                       # 4373
            ('skip2', decoder.skip_bytes(6)),                           # 4374,4375, 4376
            ('remaining_amphours', decoder.decode_16bit_uint()),        # 4377
            ('skip3', decoder.skip_bytes(6)),                           # 4378,4379,4380
            ('total_amphours', decoder.decode_16bit_uint()),            # 4381
        ])
        del decoded["skip"]
        del decoded["skip2"]
        del decoded["skip3"]
    elif (addr == 4163):
        decoded = OrderedDict([
            ('mppt_mode', decoder.decode_16bit_uint()),                 # 4164
            ('aux1_and_2_function', decoder.decode_16bit_int()),        # 4165
        ])
    elif (addr == 4209):
        decoded = OrderedDict([
            ('name_0', decoder.decode_8bit_uint()),                     # 4210
            ('name_1', decoder.decode_8bit_uint()),                     # 4211
            ('name_2', decoder.decode_8bit_uint()),                     # 4212
            ('name_3', decoder.decode_8bit_uint()),                     # 4213
            ('name_4', decoder.decode_8bit_uint()),                     # 4214
            ('name_5', decoder.decode_8bit_uint()),                     # 4215
            ('name_6', decoder.decode_8bit_uint()),                     # 4216
            ('name_7', decoder.decode_8bit_uint()),                     # 4217
        ])
    elif (addr == 4243):
        decoded = OrderedDict([
            ('temp_regulated_battery_target_voltage',
             decoder.decode_16bit_int()/10.0),                          # 4244
            ('nominal_battery_voltage', decoder.decode_16bit_uint()),   # 4245
            ('ending_amps', decoder.decode_16bit_int()/10.0),           # 4246
            ('skip', decoder.skip_bytes(56)),                           # 4247-4274
            ('reason_for_resting', decoder.decode_16bit_uint()),        # 4275
        ])
        del decoded["skip"]
    elif (addr == 16386):
        decoded = OrderedDict([
            ('app_rev', decoder.decode_32bit_uint()),                     # 16387, 16388
            ('net_rev', decoder.decode_32bit_uint()),                     # 16387, 16388
        ])

    return decoded


# Get Modbus Data From Classic.
def getModbusData(modclient):
    try:
        # Test for succesful connect
        try:
            modclient.connect()
        except Exception as e:
            log.error("Modbus Client Connect Attempt Error: {}".format(e))

        result = modclient.read_holding_registers(4163, 2,  unit=10)
        if result.isError():
            # close the client
            log.error("Modbus result was an error")
            return {}

        data = {}
        # Read Registers
        data[4100] = getRegisters(theClient=modclient, addr=4100, count=44)
        data[4360] = getRegisters(theClient=modclient, addr=4360, count=22)
        data[4163] = getRegisters(theClient=modclient, addr=4163, count=2)
        data[4209] = getRegisters(theClient=modclient, addr=4209, count=4)
        data[4243] = getRegisters(theClient=modclient, addr=4243, count=32)
        data[16386] = getRegisters(theClient=modclient, addr=16386, count=4)
        modclient.close()

    except Exception as e:
        log.error(e)
        try:
            modclient.close()
        except Exception as ee:
            log.error("Modbus error on close: {}".format(ee))

        return {}

    log.debug("Obtained Classic data")

    # Iterate and decoded data
    decoded = OrderedDict()
    for index in data:
        decoded = {
            **dict(decoded),
            **dict(doDecode(index, getDataDecoder(data[index])))}

    return decoded


# Classic Device Class
class ClassicDevice:
    def __init__(self, mbc, trace=False):
        # Instances
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()

        # Device Attributes
        self.device["device"] = "Classic"
        self.device["client"] = mbc
        self.device["data"] = self.data

        # Default Register Value Data
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
        self.data["reason_for_resting"] = 0
        self.data["app_rev"] = 0
        self.data["net_rev"] = 0

    # Read From Classic
    def read(self):
        self.device["data"] = getModbusData(self.device["client"])

    # Get Device
    def getDevice(self):
        return self.device
