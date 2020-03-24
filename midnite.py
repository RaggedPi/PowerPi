#!/usr/bin/env python

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
# from pymodbus.compat import iteritems
from collections import OrderedDict
import logging
import sys


log = logging.getLogger('classic_mqtt')


def getRegisters(theClient, addr, count):
    try:
        result = theClient.read_holding_registers(addr, count,  unit=10)
        if result.function_code >= 0x80:
            log.error("error getting {} for {} bytes".format(addr, count))
            return {}
    except:
        log.error("Error getting {} for {} bytes".format(addr, count))
        return {}

    return result.registers


def getDataDecoder(registers):
    return BinaryPayloadDecoder.fromRegisters(
        registers,
        byteorder=Endian.Big,
        wordorder=Endian.Little)

def doDecode(addr, decoder):
    if (addr == 4100 ):
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
    elif (addr == 4360):
        decoded = OrderedDict([
            ('wbjr_cmd_s', decoder.decode_16bit_uint()),                  # 4361
            ('wbjr_raw_current', decoder.decode_16bit_int()),             # 4362
            ('skip', decoder.skip_bytes(4)),                              # 4363,4364
            ('wbjr_pos_amphour', decoder.decode_32bit_uint()),            # 4365,4366
            ('wbjr_neg_amphour', decoder.decode_32bit_int()),             # 4367,4368
            ('wbjr_net_amphour', decoder.decode_32bit_int()),             # 4369,4370
            ('wbjr_battery_current', decoder.decode_16bit_int()/10.0),    # 4371
            ('wbjr_crc', decoder.decode_8bit_int()),                      # 4372 MSB
            ('shunt_temperature', decoder.decode_8bit_int() - 50.0),      # 4372 LSB
            ('soc', decoder.decode_16bit_uint()),                         # 4373
            ('skip2', decoder.skip_bytes(6)),                             # 4374,75, 76
            ('remaining_amphours', decoder.decode_16bit_uint()),          # 4377
            ('skip3', decoder.skip_bytes(6)),                             # 4378,79,80
            ('total_amphours', decoder.decode_16bit_uint()),              # 4381
        ])
    elif (addr == 4163):
        decoded = OrderedDict([
            ('mppt_mode', decoder.decode_16bit_uint()),                   # 4164
            ('aux1_and_2_function', decoder.decode_16bit_int()),          # 4165
        ])
    elif (addr == 4209):
        decoded = OrderedDict([
            ('name_0', decoder.decode_8bit_uint()),                       # 4210
            ('name_1', decoder.decode_8bit_uint()),                       # 4211
            ('name_2', decoder.decode_8bit_uint()),                       # 4212
            ('name_3', decoder.decode_8bit_uint()),                       # 4213
            ('name_4', decoder.decode_8bit_uint()),                       # 4214
            ('name_5', decoder.decode_8bit_uint()),                       # 4215
            ('name_6', decoder.decode_8bit_uint()),                       # 4216
            ('name_7', decoder.decode_8bit_uint()),                       # 4217
        ])
    elif (addr == 4243):
        decoded = OrderedDict([
            ('temp_regulated_battery_target_voltage', decoder.decode_16bit_int()/10.0),  # 4244
            ('nominal_battery_voltage', decoder.decode_16bit_uint()),     # 4245
            ('ending_amps', decoder.decode_16bit_int()/10.0),             # 4246
            ('skip', decoder.skip_bytes(56)),                             # 4247-4274
            ('reason_for-_resting', decoder.decode_16bit_uint()),         # 4275
        ])
    elif (addr == 16386):
        decoded = OrderedDict([
            ('app_rev', decoder.decode_32bit_uint()),                     # 16387, 16388
            ('net_rev', decoder.decode_32bit_uint()),                     # 16387, 16388
        ])

    return decoded


# --------------------------------------------------------------------------- # 
# Get the data from the Classic. 
# Open the cleint, read in the register, close the client, decode the data, 
# combine it and return it 
# --------------------------------------------------------------------------- # 
def getModbusData(classicHost, classicPort):
    try:
        modclient = ModbusClient(classicHost, port=classicPort)
        # Test for succesful connect, if not, log error and mark modbusConnected = False
        modclient.connect()

        result = modclient.read_holding_registers(4163, 2,  unit=10)
        if result.isError():
            # close the client
            log.error("MODBUS isError H:{} P:{}".format(classicHost, classicPort))
            modclient.close()
            return {}

        theData = {}
        # Read in all the registers at one time
        theData[4100] = getRegisters(theClient=modclient, addr=4100, count=44)
        theData[4360] = getRegisters(theClient=modclient, addr=4360, count=22)
        theData[4163] = getRegisters(theClient=modclient, addr=4163, count=2)
        theData[4209] = getRegisters(theClient=modclient, addr=4209, count=4)
        theData[4243] = getRegisters(theClient=modclient, addr=4243, count=32)
        theData[16386]= getRegisters(theClient=modclient, addr=16386, count=4)
        modclient.close()

    except:  # Catch all modbus excpetions
        e = sys.exc_info()[0]
        log.error("MODBUS Error H:{} P:{} e:{}".format(classicHost, classicPort, e))
        try:
            modclient.close()
        except:
            log.error("MODBUS Error on close H:{} P:{}".format(classicHost, classicPort))

        return {}

    log.debug("Got data from Classic at {}:{}".format(classicHost,classicPort))

    # Iterate over them and get the decoded data all into one dict
    decoded = {}
    for index in theData:
        decoded = {**dict(decoded), **dict(doDecode(index, getDataDecoder(theData[index])))}

    return decoded
