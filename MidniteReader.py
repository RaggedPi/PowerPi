#!/usr/bin/env python
# -*- coding: utf-8 -*-

__appname__ = "MidniteReader"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.1.1"
__license__ = "Apache2"

from copy import deepcopy
import sys
import os
import pymodbus.exceptions
from collections import OrderedDict
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import logging
logger = logging.getLogger(__appname__)


class MidniteReader:
    def __init__(self):
        """Constructor."""

        self._configs = OrderedDict()
        self.items = []

        # Logging
        self._setupLogger()

        # Midnite Classic
        self.classic = None
        self._configs['midnite']['timeout'] = os.getenv('timeout', 0.001)
        self._configs['midnite']['host'] = os.getenv('classichost', 'localhost')
        self._configs['midnite']['port'] = os.getenv('classicport', 502)
        self._configs['midnite']['unit'] = os.getenv('unit', 10)

        try:
            self.client = ModbusClient(self.host, self.port)
        except Exception as e:
            logger.warning("Failed to connect to the Classic. {}".format(e))
            self.client = None

    def getItems(self):
        """Return associated items."""
        self.items.append(Classic(data=self.getModbusData()))

        items = []
        for item in self.items:
            if item:
                info = item.getItem()
                if info:
                    items.append(info)

        return deepcopy(items)

    # Set up Logger
    def _setupLogger(self):
        """Setup the logger."""
        # Set default loglevel
        logger.setLevel(logging.DEBUG)

        # Create file handler
        # @todo: generate dated log files in a log directory
        fn = self._configs['logging']['filename'] or os.getenv('logging_filename', 'midnite.log')
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

    # Get Registers
    async def getRegisters(self, addr: int, count: int = 1) -> list:
        """Return supplied register values.

        Args:
            addr (int): Register address to start reading from
            count (int): Number of registers to return.  Defaults to 1.

        Returns:
            list: Collection of register values
        """
        err = f"Error getting {addr} for {count} bytes"

        try:
            result = await self.client.read_holding_registers(
              addr,
              count,
              unit=self._configs['midnite']['unit'])

            if result.function_code >= 0x80:
                logging.error(err)
                return {}
        except Exception as e:
            logging.error(err)
            return {}

        return result.registers

    # Data Decoder
    def getDataDecoder(self, registers):
        """Return payload decoder."""
        return BinaryPayloadDecoder.fromRegisters(
            registers,
            byteorder=Endian.Big,
            wordorder=Endian.Little)

    # Decode Data
    def doDecode(self, addr, decoder):
        if (addr == 4100):
            decoded = OrderedDict([
                # 4101 MSB
                ('pcb_revision', decoder.decode_8bit_uint()),
                # 4101 LSB
                ('unit_type', decoder.decode_8bit_uint()),
                # 4102
                ('build_year', decoder.decode_16bit_uint()),
                # 4103 MSB
                ('build_month', decoder.decode_8bit_uint()),
                # 4103 LSB
                ('build_day', decoder.decode_8bit_uint()),
                # 4104
                ('info_flag_bits_3', decoder.decode_16bit_uint()),
                # 4105 Reserved
                ('ignore', decoder.skip_bytes(2)),
                # 4106 MSB
                ('mac_1', decoder.decode_8bit_uint()),
                # 4106 LSB
                ('mac_0', decoder.decode_8bit_uint()),
                # 4107 MSB
                ('mac_3', decoder.decode_8bit_uint()),
                # 4107 LSB
                ('mac_2', decoder.decode_8bit_uint()),
                # 4108 MSB
                ('mac_5', decoder.decode_8bit_uint()),
                # 4108 LSB
                ('mac_4', decoder.decode_8bit_uint()),
                # 4109, 4110
                ('ignore_2', decoder.skip_bytes(4)),
                # 4111
                ('unit_id', decoder.decode_32bit_int()),
                # 4113
                ('status_roll', decoder.decode_16bit_uint()),
                # 4114
                ('restart_timer_ms', decoder.decode_16bit_uint()),
                # 4115
                ('avg_battery_voltage', decoder.decode_16bit_int()/10.0),
                # 4116
                ('avg_pv_voltage', decoder.decode_16bit_uint()/10.0),
                # 4117
                ('avg_battery_current', decoder.decode_16bit_uint()/10.0),
                # 4118
                ('avg_energy_today', decoder.decode_16bit_uint()/10.0),
                # 4119
                ('avg_power', decoder.decode_16bit_uint()/1.0),
                # 4120 MSB
                ('charge_stage', decoder.decode_8bit_uint()),
                # 4120 LSB
                ('charge_state', decoder.decode_8bit_uint()),
                # 4121
                ('avg_pv_current', decoder.decode_16bit_uint()/10.0),
                # 4122
                ('last_voc', decoder.decode_16bit_uint()/10.0),
                # 4123
                ('highest_pv_voltage_seen', decoder.decode_16bit_uint()),
                # 4124
                ('match_point_shadow', decoder.decode_16bit_uint()),
                # 4125
                ('amphours_today', decoder.decode_16bit_uint()),
                # 4126, 4127
                ('lifetime_energy', decoder.decode_32bit_uint()/10.0),
                # 4128, 4129
                ('lifetime_amphours', decoder.decode_32bit_uint()),
                # 4130, 4131
                ('info_flags_bits', decoder.decode_32bit_int()),
                # 4132
                ('battery_temperature', decoder.decode_16bit_int()/10.0),
                # 4133
                ('fet_temperature', decoder.decode_16bit_int()/10.0),
                # 4134
                ('pcb_temperature', decoder.decode_16bit_int()/10.0),
                # 4135
                ('no_power_timer', decoder.decode_16bit_uint()),
                # 4136 (in seconds, minimum: 1 minute)
                ('log_interval', decoder.decode_16bit_uint()),
                # 4137
                ('modbus_port_register', decoder.decode_16bit_uint()),
                # 4138
                ('float_time_today', decoder.decode_16bit_uint()),
                # 4139
                ('absorb_time', decoder.decode_16bit_uint()),
                # 4140
                ('reserved_1', decoder.decode_16bit_uint()),
                # 4141
                ('pwm_readonly', decoder.decode_16bit_uint()),
                # 4142
                ('reason_for_reset', decoder.decode_16bit_uint()),
                # 4143
                ('equalize_time', decoder.decode_16bit_uint())
            ])
            # Removed reserved register data
            del decoded["ignore"]
            del decoded["ignore_2"]
            del decoded["reserved_1"]
        elif (addr == 4360):
            decoded = OrderedDict([
                # 4361
                ('wbjr_cmd_s', decoder.decode_16bit_uint()),
                # 4362
                ('wbjr_raw_current', decoder.decode_16bit_int()),
                # 4363, 4364
                ('skip', decoder.skip_bytes(4)),
                # 4365, 4366
                ('wbjr_pos_amphour', decoder.decode_32bit_uint()),
                # 4367, 4368
                ('wbjr_neg_amphour', decoder.decode_32bit_int()),
                # 4369, 4370
                ('wbjr_net_amphour', decoder.decode_32bit_int()),
                # 4371
                ('wbjr_battery_current', decoder.decode_16bit_int()/10.0),
                # 4372 MSB
                ('wbjr_crc', decoder.decode_8bit_int()),
                # 4372 LSB
                ('shunt_temperature', decoder.decode_8bit_int() - 50.0),
                # 4373
                ('soc', decoder.decode_16bit_uint()),
                # 4374 - 4376 Reserved
                ('skip2', decoder.skip_bytes(6)),
                # 4377
                ('remaining_amphours', decoder.decode_16bit_uint()),
                # 4378 - 4380 Reserved
                ('skip3', decoder.skip_bytes(6)),
                # 4381
                ('total_amphours', decoder.decode_16bit_uint()),
            ])
            # Removed reserved register data
            del decoded["skip"]
            del decoded["skip2"]
            del decoded["skip3"]
        elif (addr == 4163):
            decoded = OrderedDict([
                # 4164
                ('mppt_mode', decoder.decode_16bit_uint()),
                # 4165
                ('aux1_and_2_function', decoder.decode_16bit_int()),
            ])
        elif (addr == 4209):
            decoded = OrderedDict([
                # 4210
                ('name_0', decoder.decode_8bit_uint()),
                # 4211
                ('name_1', decoder.decode_8bit_uint()),
                # 4212
                ('name_2', decoder.decode_8bit_uint()),
                # 4213
                ('name_3', decoder.decode_8bit_uint()),
                # 4214
                ('name_4', decoder.decode_8bit_uint()),
                # 4215
                ('name_5', decoder.decode_8bit_uint()),
                # 4216
                ('name_6', decoder.decode_8bit_uint()),
                # 4217
                ('name_7', decoder.decode_8bit_uint()),
            ])
        elif (addr == 4243):
            decoded = OrderedDict([
                # 4244
                ('temp_regulated_battery_target_voltage', decoder.decode_16bit_int()/10.0),
                # 4245
                ('nominal_battery_voltage', decoder.decode_16bit_uint()),
                # 4246
                ('ending_amps', decoder.decode_16bit_int()/10.0),
                # 4247-4274 Reserved
                ('skip', decoder.skip_bytes(56)),
                # 4275
                ('reason_for_resting', decoder.decode_16bit_uint())
            ])
            # Removed reserved register data
            del decoded["skip"]
        elif (addr == 16386):
            decoded = OrderedDict([
                # 16387, 16388
                ('app_rev', decoder.decode_32bit_uint()),
                # 16387, 16388
                ('net_rev', decoder.decode_32bit_uint())
            ])

        return decoded

    # Get modbus data from classic.
    def getModbusData(self):
        try:
            # Open modbus connection
            self.client.connect()

            data = OrderedDict()
            # Read registers
            data[4100] = self.getRegisters(addr=4100, count=44)
            data[4360] = self.getRegisters(addr=4360, count=22)
            data[4163] = self.getRegisters(addr=4163, count=2)
            data[4209] = self.getRegisters(addr=4209, count=4)
            data[4243] = self.getRegisters(addr=4243, count=32)
            data[16386] = self.getRegisters(addr=16386, count=4)

            # Close modbus connection
            self.client.close()

        except pymodbus.exceptions.ConnectionException as e:
            logger.error("Modbus Client Connect Attempt Error: {}".format(e))
            sys.exit(1)
            return OrderedDict()

        except Exception as e:
            logger.error("Could not get modbus data: {}".format(e))
            try:
                self.client.close()
            except Exception as ee:
                logger.error("Modbus error on close: {}".format(ee))
            sys.exit(1)
            return OrderedDict()

        # Decode data
        decoded = OrderedDict()
        for index in data:
            decoded = {
                **dict(decoded),
                **dict(self.doDecode(index, self.getDataDecoder(data[index])))}

        return decoded


class Classic:
    def __init__(self):
        """Constructor."""

        # Attributes
        self.data = OrderedDict()
        self.item = OrderedDict()

        # Default attribute values
        self.item['item'] = "Classic"
        self.item['data'] = self.data

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
        self.data["avg_pv_current"] = 0

        self.data["charge_stage"] = 0
        self.data["charge_state"] = 0

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

    def setData(self, data: list):
        """Set read in Classic data.

        Args:
            data (list): Data from Midnite Classic device
        """

        self.data.update(data)

    # Get Device
    def getItem(self) -> OrderedDict:
        """Return item data.

        Returns:
            OrderedDict: Collection containing device info and data
        """

        return self.item
