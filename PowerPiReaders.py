#!/usr/bin/env python
# -*- coding: utf-8 -*-

__appname__ = "MidniteReader"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.2.0"
__license__ = "Apache2"

from ReaderManager import Reader, Device
from collections import OrderedDict
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
import pymodbus.exceptions
#from Magnum.magnum import Magnum
import os
import pendulum
from tzlocal import get_localzone
import logging
from time import sleep
from copy import deepcopy
from struct import error as unpack_error
from struct import unpack
import serial
logger = logging.getLogger(__appname__)

UNKNOWN = "UNKNOWN"
INVERTER = "INVERTER"
AGS = "AGS"
REMOTE = "REMOTE"
BMK = "BMK"
PT100 = "PT100"
RTR = "RTR"


class MidniteReader(Reader):
    def __init__(self, name='MidniteReader'):
        """ Constructor

        Args:
            name (str, optional): Reader name. Defaults to 'MidniteReader'.
        """

        super().__init__(name=name)

        self.classic = None
        self._configs['midnite'] = OrderedDict()
        self._configs['midnite']['timeout'] = os.getenv('timeout', 0.001)
        self._configs['midnite']['host'] = os.getenv('classichost', 'localhost')
        self._configs['midnite']['port'] = os.getenv('classicport', 502)
        self._configs['midnite']['unit'] = os.getenv('unit', 10)
        self._configs['midnite']['read_interval'] = os.getenv('readinterval', 60)

        try:
            self.client = ModbusClient(
              self._configs['midnite']['host'],
              self._configs['midnite']['port'])
        except exception as e:
            logger.error('could not connect to modbus client.')

    def getName(self):
        return super().getName()

    def getItems(self):
        now = pendulum.now(get_localzone())
        if (not self.lastread
           or not self.classic
           or (now.diff(self.lastread).in_seconds() >= self._configs['midnite']['read_interval'])):
            self.classic = Classic()
            self.classic.parse(self.getModbusData())

            logger.info(f"{self.classic.data}")

        self.items = []
        for item in [self.classic]:
            if item:
                iteminfo = item.getItem()
                if iteminfo:
                    self.items.append(iteminfo)
        return deepcopy(self.items)

    # Get Registers
    def getRegisters(self, addr: int, count: int = 1) -> list:
        """Return supplied register values.

        Args:
            addr (int): Register address to start reading from
            count (int): Number of registers to return.  Defaults to 1.

        Returns:
            list: Collection of register values
        """
        err = f"Error getting {addr} for {count} bytes"
        logging.info(f"Trying to get data from registers starting at {addr} for {count} bytes.")
        try:
            result = self.client.read_holding_registers(
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
                ('temp_regulated_battery_target_voltage',
                 decoder.decode_16bit_int()/10.0),
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
        now = pendulum.now(get_localzone())
        print(f"reading registers")
        print(f"last read: {self.lastread or 'none'}")
        self.lastread = now
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
        except pymodbus.exceptions.ParameterException as e:
            logger.info(e)
            return OrderedDict()
        except pymodbus.exceptions.ConnectionException as e:
            logger.error("Modbus Client Connect Attempt Error: {}".format(e))
            # sys.exit(1)
            return OrderedDict()

        except Exception as e:
            logger.error("Could not get modbus data: {}".format(e))
            try:
                self.client.close()
            except Exception as ee:
                logger.error("Modbus error on close: {}".format(ee))
            # sys.exit(1)
            return OrderedDict()

        # Decode data
        decoded = OrderedDict()
        for index in data:
            decoded = {
                **dict(decoded),
                **dict(self.doDecode(index, self.getDataDecoder(data[index])))}

        return decoded


class Classic(Device):
    def __init__(self):
        """Constructor."""

        super().__init__()
        self.item["item"] = "Classic"

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

        self.data = {**self.data, **data}

    def parse(self, data: list):
        self.setData(data)

    # Get Device
    def getItem(self) -> OrderedDict:
        """Return item data.

        Returns:
            OrderedDict: Collection containing device info and data
        """

        return self.item


class MagnumReader(Reader):

    # Names of all the packet types
    AGS_A1 = "AGS_A1"
    AGS_A2 = "AGS_A2"
    BMK_81 = "BMK_81"
    INV = "INVERTER"
    PT_C1 = "PT_C1"
    PT_C2 = "PT_C2"
    PT_C3 = "PT_C3"
    PT_C4 = "PT_C4"
    REMOTE_00 = "REMOTE_00"
    REMOTE_11 = "REMOTE_11"
    REMOTE_80 = "REMOTE_80"
    REMOTE_A0 = "REMOTE_A0"
    REMOTE_A1 = "REMOTE_A1"
    REMOTE_A2 = "REMOTE_A2"
    REMOTE_A3 = "REMOTE_A3"
    REMOTE_A4 = "REMOTE_A4"
    REMOTE_C0 = "REMOTE_C0"
    REMOTE_C1 = "REMOTE_C1"
    REMOTE_C2 = "REMOTE_C2"
    REMOTE_C3 = "REMOTE_C3"
    REMOTE_D0 = "REMOTE_D0"
    RTR_91 = "RTR_91"
    sevenzeros = bytes([0, 0, 0, 0, 0, 0, 0])
    
    # refer to struct.unpack for format description
    default_remote = 'BBBBBbBBBBBBBB'
    unpackFormats = {
        AGS_A1: 'BbBbBB',
        AGS_A2: 'BBBHB',
        BMK_81:  'BbHhHHhHHBB',
        INV: 'BBhhBBbbBBBBBBBBhb',
        PT_C1: 'BbBBHhhbbbbbb',
        PT_C2: 'BbBHBbBBBB',
        PT_C3: 'BH11B',
        PT_C4: '7B',
        REMOTE_00: default_remote + '7B',
        REMOTE_11: default_remote + '7B',  # just the first 2 bytes count
        REMOTE_80: default_remote + 'bbbb3B',
        REMOTE_A0: default_remote + 'BBBbBBB',
        REMOTE_A1: default_remote + '7B',
        REMOTE_A2: default_remote + 'bb5B',
        REMOTE_A3: default_remote + '7B',
        REMOTE_A4: default_remote + '7B',
        REMOTE_C0: default_remote + 'bbbbHB',
        REMOTE_C1: default_remote + 'BBbbbbB',
        REMOTE_C2: default_remote + 'BBbbBbB',
        REMOTE_C3: default_remote + 'BBBBBbB',
        REMOTE_D0: default_remote + '7B',
        RTR_91: 'BB',
        UNKNOWN: ''
    }

    multiplier = 1

    def __init__(self, name='MagnumReader'):
        super().__init__(name=name)

        self._configs['magnum'] = OrderedDict()
        self._configs['magnum']['device'] = os.getenv('device', '/dev/ttyUSB0')
        self._configs['magnum']['packets'] = os.getenv('packets', 50)
        self._configs['magnum']['timeout'] = os.getenv('timeout', 0.001)
        self._configs['magnum']['cleanpackets'] = os.getenv('cleanpackets', True)
        self._configs['magnum']['trace'] = os.getenv('trace', False)

        self.packetcount = int(self._configs['magnum']['packets'])
        self.timeout = float(self._configs['magnum']['timeout'])
        self.cleanpackets = self._configs['magnum']['cleanpackets']
        self.trace = self._configs['magnum']['trace']
        self.device = self._configs['magnum']['device']
        self._reader = None
        self.inverter = None
        self.remote = None
        self.bmk = None
        self.ags = None
        self.rtr = None
        self.pt100 = None
        self.inverter_revision = -1
        self.inverter_model = -1

    def getPackets(self):
        """ Retrieves the raw packets.

        Returns:
            list: List of tupple objects

        **tupple contents**:

          - name of packet
          - bytes of packet
          - tupple of unpacked values - Bassed on ME documentation
        """

        packets = self.readPackets()
        messages = []
        unknown = 0
        for packet in packets:
            message = self.parsePacket(packet)
            if message[0] == UNKNOWN:
                unknown += 1
            messages.append(message)
        # if atleast 2 UNKNOWN packets attempt to clean them up
        if unknown > 1 and self.cleanpackets:
            messages = self.cleanup(messages)

        return messages

    def parsePacket(self, packet):
        """ Attempt to build a known packet and unpack its data into values
        

        Args:
            packet ([type]): [description]

        Raises:
            unpack_error: [description]
        """

        if len(packet) == 22:
            packet = packet[:21]
        packetType = UNKNOWN

        if len(packet) > 0:
            packetLen = len(packet)
            firstbyte = packet[0]
            lastbyte = packet[-1]

            if packetLen == 2:
                if firstbyte == 0x91:
                    packetType = MagnumReader.RTR_91
            elif packetLen == 6:
                if firstbyte == 0xa1:
                    packetType = MagnumReader.AGS_A1
                elif firstbyte == 0xa2:
                    packetType = MagnumReader.AGS_A2
            elif packetLen == 8:
                if firstbyte == 0xC4:
                    packetType = MagnumReader.PT_C4
            elif packetLen == 13:
                if firstbyte == 0xC2:
                    packetType = MagnumReader.PT_C2
            elif packetLen == 14:
                if firstbyte == 0xC3:
                    packetType = MagnumReader.PT_C3
            elif packetLen == 16:
                if firstbyte == 0xC1:
                    packetType = MagnumReader.PT_C1
            elif packetLen == 18:
                if firstbyte == 0x81:
                    packetType = MagnumReader.BMK_81
            elif packetLen == 21:
                version = packet[10]
                model = packet[14]

                if lastbyte == 0 and firstbyte == 0:
                    # There is an undocumented Remote message generated with 
                    # seven 0x00 bytes a the end. This code distinguishes it
                    # from a Inverter record with status byte 0 = 0x0
                    # Also the ME-ARC sends a spurious record with a zero end byte
                    if packet[-7:] == MagnumReader.sevenzeros:
                        packetType = MagnumReader.REMOTE_00
                    else:
                        if version == (self.inverter_revision and model == self.inverter_model) or self.inverter_revision == -1:
                            packetType = MagnumReader.INV
                        else:
                            packetType = MagnumReader.REMOTE_00
                else:
                    if lastbyte == 0:
                        if (version == self.inverter_revision and model == self.inverter_model) or self.inverter_revision == -1:
                            packetType = MagnumReader.INV
                            if self.inverter_revision == -1:
                                self.inverter_revision = version
                                self.inverter_model = model
                        else:
                            packetType = MagnumReader.REMOTE_00
                    elif lastbyte == 0xa0:
                        packetType = MagnumReader.REMOTE_A0
                    elif lastbyte == 0xa1:
                        packetType = MagnumReader.REMOTE_A1
                    elif lastbyte == 0xa2:
                        packetType = MagnumReader.REMOTE_A2
                    elif lastbyte == 0xa3:
                        packetType = MagnumReader.REMOTE_A3
                    elif lastbyte == 0xa4:
                        packetType = MagnumReader.REMOTE_A4
                    elif lastbyte == 0x80:
                        packetType = MagnumReader.REMOTE_80
                    elif lastbyte == 0xC0:
                        packetType = MagnumReader.REMOTE_C0
                    elif lastbyte == 0xC1:
                        packetType = MagnumReader.REMOTE_C1
                    elif lastbyte == 0xC2:
                        packetType = MagnumReader.REMOTE_C2
                    elif lastbyte == 0xC3:
                        packetType = MagnumReader.REMOTE_C3
                    elif lastbyte == 0x11:
                        packetType = MagnumReader.REMOTE_11
                    elif lastbyte == 0xD0:
                        packetType = MagnumReader.REMOTE_D0

            # Unpack as big endian. (Refer to unpackFormats)
            mask = ">" + MagnumReader.unpackFormats[packetType]
            if len(mask) > 1:
                try:
                    fields = unpack(mask, packet)
                except Exception as e:
                    msg = "{0} Converting {1} - {2} bytes".format(
                        e.args[0], packetType, len(packet))
                    raise unpack_error(msg) from e
            else:
                fields = {}

            return([packetType, packet, fields])

    def readPackets(self):
        """Raw read of packets to bytes.

        Raises:
            ConnectionError: [description]

        Returns:
            [type]: [description]
        """

        if not self._reader:
            self._reader = serial.serial_for_url(self.device,
                                                 baudrate=19200,
                                                 bytesize=8,
                                                 timeout=self.timeout,
                                                 stopbits=serial.STOPBITS_ONE,
                                                 dsrdtr=False,
                                                 parity=serial.PARITY_NONE)
            self._reader.close()
        packet = bytearray()
        packets = []

        # open port every time
        self._reader.open()

        # wait to see if there is any traffic on the device
        sleep(0.25)
        if self._reader.inWaiting() == 0:
            raise ConnectionError("There doesn't seem to be a network")

        packetsleft = self.packetcount
        self._reader.flushInput()

        # Start of packet reads into a list of bytearray()
        while packetsleft > 0:
            readbytes = self._reader.read(self._reader.in_waiting or 1)
            packet += readbytes

            # assumes an empty read is an inter packet gap
            if len(readbytes) == 0 and len(packet) != 0:
                packets.append(packet)
                packetsleft -= 1
                packet = bytearray()

        self._reader.close()

        return packets

    def cleanup(self, messages):
        """ Cleanup looks for consecutive UNKNOWN packet pairs
            and concatenates the pair and attempts to parse the result.

        Args:
            messages (list): List of Tupple

        Returns:
            list: List
        """

        cleaned = []
        lastone = len(messages) - 2
        ignoreit = False
        for index, message in enumerate(messages):
            if ignoreit:
                ignoreit = False
            elif index > lastone or message[0] != UNKNOWN:
                ignoreit = False
                cleaned.append(message)
            else:
                nextmessage = messages[index + 1]
                if nextmessage[0] == UNKNOWN:
                    # we may have a match
                    newmessage = self.parsePacket(message[1] + nextmessage[1])
                    ignoreit = True
                    cleaned.append(newmessage)
        return cleaned

    def getDevices(self):
        """ Get a list of connected devices.

            Each class is instantiated only once per run time execution
            This allows an oblect to reflect the latest CUMULATIVE value 
            for the packets.  This is useful for PT100 and AGS packets 
            which are not too numerous.

        Returns:
            list: deepcopy of the device data collections

        Each dictionary has two items:

        - **device**  One of INVERTER, REMOTE, AGS, BMK or PT100  
        - **data** A dictionary of name/value pairs for the device.

        pass each the packets to the correct object

        each packet is a tupple of: 
            type(string) name of packet
            raw packet (bytes) the raw binary bytes of the packet
            unpacked data (tupple int) integers of data deconstructed to macth ME definition
        """

        for packet in self.getPackets():
            packetType = packet[0]
            if packetType == MagnumReader.INV:
                if not self.inverter:
                    self.inverter = InverterDevice(trace=self.trace)
                self.inverter.parse(packet)
            elif packetType in (MagnumReader.REMOTE_00,
                                MagnumReader.REMOTE_11,
                                MagnumReader.REMOTE_80,
                                MagnumReader.REMOTE_A0,
                                MagnumReader.REMOTE_A1,
                                MagnumReader.REMOTE_A2,
                                MagnumReader.REMOTE_A3,
                                MagnumReader.REMOTE_A4,
                                MagnumReader.REMOTE_C0,
                                MagnumReader.REMOTE_C1,
                                MagnumReader.REMOTE_C2,
                                MagnumReader.REMOTE_C3,
                                MagnumReader.REMOTE_D0):
                if not self.remote:
                    self.remote = RemoteDevice(trace=self.trace)
                self.remote.parse(packet)
            elif packetType == MagnumReader.BMK_81:
                if not self.bmk:
                    self.bmk = BMKDevice(trace=self.trace)
                self.bmk.parse(packet)
            elif packetType in (MagnumReader.AGS_A1, MagnumReader.AGS_A2):
                if not self.ags:
                    self.ags = AGSDevice(trace=self.trace)
                self.ags.parse(packet)
            elif packetType == MagnumReader.RTR_91:
                if not self.rtr:
                    self.rtr = RTRDevice(trace=self.trace)
                self.rtr.parse(packet)
            elif packetType in (MagnumReader.PT_C1, MagnumReader.PT_C2, MagnumReader.PT_C3, MagnumReader.PT_C4):
                if not self.pt100:
                    self.pt100 = PT100Device(trace=self.trace)
                self.pt100.parse(packet)
        if self.remote:
            # remove extraneous fields if corresponding device is not present
            if not self.bmk:
                self.remote.removeBMK()
            if not self.ags:
                self.remote.removeAGS()
            if not self.pt100:
                self.remote.removePT100()
        devices = []
        for device in [self.inverter, self.remote, self.bmk, self.ags, self.rtr, self.pt100]:
            if device:
                deviceinfo = device.getDevice()
                if deviceinfo:
                    devices.append(deviceinfo)
        return deepcopy(devices)

    def getItems(self):
        """ Alias to getDevices method.

        Returns:
            list: list of devices
        """

        return self.getDevices()


class AGSDevice:

    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = AGS
        self.device["data"] = self.data
        self.data["revision"] = '0.0'
        self.data["status"] = 0
        self.data["status_text"] = ""
        self.data["running"] = False
        self.data["temp"] = 0.0
        self.data["runtime"] = 0.0
        self.data["gen_last_run"] = 0
        self.data["last_full_soc"] = 0
        self.data["gen_total_run"] = 0
        self.data["vdc"] = 0.0

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.AGS_A1:
            self.data["status"] = unpacked[1]
            self.data["revision"] = str(round(unpacked[2] / 10, 1))
            self.data["temp"] = unpacked[3]
            if self.data["temp"] < 105:
                self.data["temp"] = round((self.data["temp"] - 32) * 5 / 9, 1)
            self.data["runtime"] = round(unpacked[4] / 10, 2)
            self.setStatusText()
            self.data["vdc"] = round(unpacked[5] / 10 * MagnumReader.multiplier, 2)
            self.setRunning()
        elif packetType == MagnumReader.AGS_A2:
            self.data["gen_last_run"] = unpacked[1]
            self.data["last_full_soc"] = unpacked[2]
            self.data["gen_total_run"] = unpacked[3]

    def setRunning(self):
        if self.data["status"] in (3, 6, 7, 8, 12, 13, 14, 18, 19, 26, 2):
            self.data["running"] = True
        else:
            self.data["running"] = False

    def setStatusText(self):
        status = {
            0: "Not Connected",
            1: "Off",
            2: "Ready",
            3: "Manual Run",
            4: "AC In",
            5: "In quiet time",
            6: "Start in test mode",
            7: "Start on temperature",
            8: "Start on voltage",
            9: "Fault start on test",
            10: "Fault start on temp",
            11: "Fault start on voltage",
            12: "Start TOD",
            13: "Start SOC",
            14: "Start Exercise",
            15: "Fault start TOD",
            16: "Fault start SOC",
            17: "Fault start Exercise",
            18: "Start on Amp",
            19: "Start on Topoff",
            20: "Not used",
            21: "Fault start on Amp",
            22: "Fault on Topoff",
            23: "Not used",
            24: "Fault max run",
            25: "Gen Run Fault",
            26: "Gen in Warm up",
            27: "Gen in Cool down"
        }
        if self.data["status"] in status:
            self.data["status_text"] = status[self.data["status"]]

    def getDevice(self):
        return self.device


class BMKDevice:
    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = BMK
        self.device["data"] = self.data
        self.data["revision"] = ""
        self.data["soc"] = 0
        self.data["vdc"] = 0.0
        self.data["adc"] = 0.0
        self.data["vmin"] = 0.0
        self.data["vmax"] = 0.0
        self.data["amph"] = 0
        self.data["amphtrip"] = 0.0
        self.data["amphout"] = 0.0
        self.data["Fault"] = 0
        self.data["Fault_Text"] = ""

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.BMK_81:
            self.data["soc"] = unpacked[1]
            self.data["vdc"] = round(unpacked[2] / 100, 2)
            self.data["adc"] = round(unpacked[3] / 10, 2)
            self.data["vmin"] = round(unpacked[4] / 100, 2)
            self.data["vmax"] = round(unpacked[5] / 100, 2)
            self.data["amph"] = unpacked[6]
            self.data["amphtrip"] = round(unpacked[7] / 10, 2)
            self.data["amphout"] = round(unpacked[8] * 100, 2)
            self.data["revision"] = str(round(unpacked[9] / 10, 2))
            self.data["Fault"] = unpacked[10]
            if self.data["Fault"] == 0:
                self.data["Fault_Text"] = "Reserved"
            elif self.data["Fault"] == 1:
                self.data["Fault_Text"] = "Normal"
            elif self.data["Fault"] == 2:
                self.data["Fault_Text"] = "Fault Start"

    def getDevice(self):
        return self.device

class InverterDevice:
    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = INVERTER
        self.device["data"] = self.data
        self.data["revision"] = str(0.0)
        self.data["mode"] = 0
        self.data["mode_text"] = ""
        self.data["fault"] = 0
        self.data["fault_text"] = ""
        self.data["vdc"] = 0
        self.data["adc"] = 0
        self.data["VACout"] = 0
        self.data["VACin"] = 0
        self.data["invled"] = 0
        self.data["invled_text"] = ""
        self.data["chgled"] = 0
        self.data["chgled_text"] = ""
        self.data["bat"] = 0
        self.data["tfmr"] = 0
        self.data["fet"] = 0
        self.data["model"] = 0
        self.data["model_text"] = ""
        self.data["stackmode"] = 0
        self.data["stackmode_text"] = ""
        self.data["AACin"] = 0
        self.data["AACout"] = 0
        self.data["Hz"] = 0.0

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.INV:
            self.data["mode"] = unpacked[0]
            self.data["fault"] = unpacked[1]
            self.data["vdc"] = unpacked[2] / 10
            self.data["adc"] = unpacked[3]
            self.data["VACout"] = unpacked[4]
            self.data["VACin"] = unpacked[5]
            self.data["invled"] = unpacked[6]
            self.data["chgled"] = unpacked[7]
            self.data["revision"] = str(round(unpacked[8] / 10, 2))
            self.data["bat"] = unpacked[9]
            self.data["tfmr"] = unpacked[10]
            self.data["fet"] = unpacked[11]
            self.data["model"] = unpacked[12]
            self.data["stackmode"] = unpacked[13]
            self.data["AACin"] = unpacked[14]
            self.data["AACout"] = unpacked[15]
            self.data["Hz"] = round(unpacked[16] / 10, 2)
        #
        #    (Model <= 50) means 12V inverter
        #    (Model <= 107) means 24V inverter
        # 	 (Model < 150) means 48V inverter
        #
            if self.data["model"] <= 50:
                # voltage = 12
                MagnumReader.multiplier = 1
            elif self.data["model"] <= 107:
                # voltage = 24
                MagnumReader.multiplier = 2
            elif self.data["model"] <= 150:
                # voltage = 48
                MagnumReader.multiplier = 4
            self.set_fault_text()
            self.set_chgled_text()
            self.set_invled_text()
            self.set_mode_text()
            self.set_model_text()
            self.set_stackmode_text()

    def set_fault_text(self):
        faults = {
            0x00: "None",
            0x01: "STUCK RELAY",
            0x02: "DC OVERLOAD",
            0x03: "AC OVERLOAD",
            0x04: "DEAD BAT",
            0x05: "BACKFEED",
            0x08: "LOW BAT",
            0x09: "HIGH BAT",
            0x0A: "HIGH AC VOLTS",
            0x10: "BAD_BRIDGE",
            0x12: "NTC_FAULT",
            0x13: "FET_OVERLOAD",
            0x14: "INTERNAL_FAULT4",
            0x16: "STACKER MODE FAULT",
            0x18: "STACKER CLK PH FAULT",
            0x17: "STACKER NO CLK FAULT",
            0x19: "STACKER PH LOSS FAULT",
            0x20: "OVER TEMP",
            0x21: "RELAY FAULT",
            0x80: "CHARGER_FAULT",
            0x81: "High Battery Temp",
            0x90: "OPEN SELCO TCO",
            0x91: "CB3 OPEN FAULT"
        }
        if self.data["fault"] in faults:
            self.data["fault_text"] = faults[self.data["fault"]]

    def set_chgled_text(self):
        self.data["chgled_text"] = "Off" if self.data["chgled"] == 0 else "On"

    def set_invled_text(self):
        self.data["invled_text"] = "Off" if self.data["invled"] == 0 else "On"

    def set_mode_text(self):
        modes = {
            0x00:   "Standby",
            0x01:   "EQ",
            0x02:   "FLOAT",
            0x04:   "ABSORB",
            0x08:   "BULK",
            0x09:   "BATSAVER",
            0x10:   "CHARGE",
            0x20:   "Off",
            0x40:   "INVERT",
            0x50:   "Inverter_Standby",
            0x80:   "SEARCH"
        }
        if self.data["mode"] in modes:
            self.data["mode_text"] = modes[self.data["mode"]]
        else:
            self.data["mode_text"] = "??"

    def set_model_text(self):
        models = {
            6: "MM612",
            7: "MM612-AE",
            8: "MM1212",
            9: "MMS1012",
            10: "MM1012E",
            11: "MM1512",
            12: "MMS912E",
            15: "ME1512",
            20: "ME2012",
            21: "RD2212",
            25: "ME2512",
            30: "ME3112",
            35: "MS2012",
            36: "MS1512E",
            40: "MS2012E",
            44: "MSH3012M",
            45: "MS2812",
            47: "MS2712E",
            53: "MM1324E",
            54: "MM1524",
            55: "RD1824",
            59: "RD2624E",
            63: "RD2824",
            69: "RD4024E",
            74: "RD3924",
            90: "MS4124E",
            91: "MS2024",
            103: "MSH4024M",
            104: "MSH4024RE",
            105: "MS4024",
            106: "MS4024AE",
            107: "MS4024PAE",
            111: "MS4448AE",
            112: "MS3748AEJ",
            114: "MS4048",
            115: "MS4448PAE",
            116: "MS3748PAEJ",
            117: "MS4348PE"
        }
        if self.data["model"] in models:
            self.data["model_text"] = models[self.data["model"]]
        else:
            self.data["model_text"] = "Unknown"

    def set_stackmode_text(self):
        modes = {
            0x00:  "Stand Alone",
            0x01:  "Parallel stack - master",
            0x02:  "Parallel stack - slave",
            0x04:  "Series stack - master",
            0x08:  "Series stack - slave"
        }
        if self.data["stackmode"] in modes:
            self.data["stackmode_text"] = modes[self.data["stackmode"]]
        else:
            self.data["stackmode_text"] = "Unknown"

    def getDevice(self):
        return self.device

class PT100Device:
    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = PT100
        self.device["data"] = self.data
        self.data["address"] = 0
        self.data["on_off"] = 0
        self.data["mode"] = 0
        self.data["mode_text"] = ''
        self.data["regulation"] = 0
        self.data["regulation_text"] = ''
        self.data["fault"] = 0
        self.data["fault_text"] = ''
        self.data["battery"] = 0
        self.data["battery_amps"] = 0
        self.data["pv_voltage"] = 0
        self.data["charge_time"] = 0
        self.data["target_battery_voltage"] = 0.0
        self.data["relay_state"] = 0
        self.data["alarm_state"] = 0
        self.data["battery_temperature"] = 0.0
        self.data["inductor_temperature"] = 0
        self.data["fet_temperature"] = 0
        self.data["lifetime_kwhrs"] = 0
        self.data["resettable_kwhrs"] = 0
        self.data["ground_fault_current"] = 0
        self.data["nominal_battery_voltage"] = 0
        self.data["stacker_info"] = 0
        self.data["model"] = ''
        self.data["output_current_rating"] = 0
        self.data["input_voltage_rating"] = 0
        self.data["record"] = 0
        self.data["daily_kwh"] = 0
        self.data["max_daily_pv_volts"] = 0
        self.data["max_daily_pv_volts_time"] = 0
        self.data["max_daily_battery_volts"] = 0
        self.data["max_daily_battery_volts_time"] = 0
        self.data["minimum_daily_battery_volts"] = 0
        self.data["minimum_daily_battery_volts_time"] = 0
        self.data["daily_time_operational"] = 0
        self.data["daily_amp_hours"] = 0
        self.data["peak_daily_power"] = 0
        self.data["peak_daily_power_time"] = 0
        self.data["fault_number"] = 0
        self.data["max_battery_volts"] = 0
        self.data["max_pv_to_battery_vdc"] = 0
        self.data["max_battery_temperature"] = 0
        self.data["max_fet_temperature"] = 0
        self.data["max_inductor_temperature"] = 0

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.PT_C1:
            #  skip header
            self.data['address'] = unpacked[1] >> 5
            byte_value = unpacked[2]
            #  byte 2
            self.data['on_off'] = True if (
                byte_value & 0x80) >> 7 != 0 else False
            self.data['mode'] = (byte_value & 0x70) >> 4
            self.data['regulation'] = byte_value & 0x0F
            #  byte 3
            byte_value = unpacked[3]
            self.data['fault'] = byte_value >> 3
            self.data['battery'] = unpacked[4] / 10
            self.data['battery_amps'] = unpacked[5] / 10
            self.data['pv_voltage'] = unpacked[6] / 10
            self.data['charge_time'] = unpacked[7] / 10
            byte_value = unpacked[8]
            self.data['target_battery_voltage'] = (
                byte_value / 10) * MagnumReader.multiplier
            byte_value = unpacked[9]
            self.data['relay_state'] = True if (
                (byte_value & 0x80) >> 7) != 0 else False
            self.data['alarm_state'] = True if (
                (byte_value & 0x70) >> 6) != 0 else False
            byte_value = unpacked[10]
            self.data['battery_temperature'] = byte_value / 10
            byte_value = unpacked[11]
            self.data['inductor_temperature'] = byte_value
            byte_value = unpacked[12]
            self.data['fet_temperature'] = byte_value
            modes = {
                2: "Sleep",
                3: "Float",
                4: "Bulk",
                5: "Absorb",
                6: "EQ"
            }
            if self.data['mode'] in modes:
                self.data['mode_text'] = modes[self.data['mode']]
            else:
                self.data['mode_text'] = "Unknown"
            regulations = {
                0: "Off",
                1: "Voltage",
                2: "Current",
                3: "Temperature",
                4: "Hardware",
                5: "Voltage Off Limit",
                6: "PPT Limit",
                7: "Fault Limit",
                }
            if self.data['regulation']  in regulations:
                self.data['regulation_text'] = regulations[self.data['regulation']]
            else:
                self.data['regulation_text'] = "Unknown"
            faults =   {
                0: "No Fault",
                1: "Input er Fault",
                2: "Output er Fault",
                3: "PV High Fault",
                4: "Battery High Fault",
                5: "BTS Shorted Fault",
                6: "FET Overtemp Fault",
                7: "Inductor Overtemp Fault",
                8: "Over Current Fault",
                9: "Internal Phase Fault",
                10: "Repeated Internal Phase Fault",
                11: "Internal Fault 1",
                12: "GFP Fault",
                13: "ARC Fault",
                14: "NTC Fault",
                15: "FET Overload Fault",
                16: "Stack Fault 1",
                17: "Stack Fault 2",
                18: "Stack Fault 3",
                19: "High Battery Temp Fault"
                }
            if self.data['fault'] in faults:
                self.data['fault_text'] = faults[self.data['fault']]
            else:
                self.data['fault_text'] = "unknown"
        elif packetType == MagnumReader.PT_C2:
            self.data['address'] = unpacked[1] >> 5
            self.data['lifetime_kwhrs'] = unpacked[2] * 10
            self.data['resettable_kwhrs'] = unpacked[3] / 10
            self.data['ground_fault_current'] = unpacked[4]
            byte_value = unpacked[5]
            self.data['nominal_battery_voltage'] = byte_value >> 2
            self.data['stacker_info'] = byte_value & 0x03
            self.data['revision'] = str(unpacked[6] / 10)
            self.data['model'] = unpacked[7]
            self.data['output_current_rating'] = unpacked[8]
            self.data['input_voltage_rating'] = unpacked[9]
        elif packetType == MagnumReader.PT_C3:
            short_value = unpacked[1]
            self.data['address'] = ((short_value & 0xE000) >> 13)
            self.data['record'] = (short_value & 0x1ffffff)
            self.data['daily_kwh'] = unpacked[2] / 10
            self.data['max_daily_pv_volts'] = unpacked[3]
            self.data['max_daily_pv_volts_time'] = unpacked[4] / 10
            self.data['max_daily_battery_volts'] = unpacked[5]
            self.data['max_daily_battery_volts_time'] = unpacked[6] / 10
            self.data['minimum_daily_battery_volts'] = unpacked[7]
            self.data['minimum_daily_battery_volts_time'] = unpacked[8] / 10
            self.data['daily_time_operational'] = unpacked[7] / 10
            self.data['daily_amp_hours'] = unpacked[10]
            self.data['peak_daily_power'] = unpacked[11]
            self.data['peak_daily_power_time'] = unpacked[12] / 10
        elif packetType == MagnumReader.PT_C4:
            byte_value = unpacked[1]
            self.data['address'] = ((byte_value & 0xE0) >> 5)
            self.data['fault_number'] = (byte_value & 0x1f)
            self.data['max_battery_volts'] = unpacked[2]
            self.data['max_pv_to_battery_vdc'] = unpacked[3]
            self.data['max_battery_temperature'] = unpacked[4]
            self.data['max_fet_temperature'] = unpacked[5]
            self.data['max_inductor_temperature'] = unpacked[6]

    def getDevice(self):
        return self.device

class RemoteDevice:

    noAGS = ["genstart", "runtime", "starttemp", "startvdc", "quiettime",
             "begintime", "stoptime", "vdcstop", "voltstartdelay", "voltstopdelay", "maxrun",
             "socstart", "socstop", "ampstart", "ampsstartdelay", "ampstop", "ampsstopdelay",
             "quietbegintime", "quietendtime", "exercisedays", "exercisestart",
             "exerciseruntime", "topoff", "warmup", "cool"]

    noBMK = ["batteryefficiency", "resetbmk"]
    noMSH = ["mshinputamps", "mshcutoutvoltage"]
    noPT100 = ["forcechgode", "relayonoff", "buzzeronoff", "resetpt100", "address",
               "packet", "lognumber", "relayonvdc", "relayoffvdc", "relayondelayseconds",
               "relaydelayoffseconds", "batterytempcomp", "powersavetime", "alarmonvdc",
               "alarmoffvdc", "alarmdondelay", "alarmoffdelay", "eqdonetimer", "chargerate",
               "rebulkonsunup", "AbsorbVoltage", "FloatVoltage", "EqualizeVoltage", "AbsorbTime",
               "RebulkVoltage", "BatteryTemperatureCompensation"]

    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = REMOTE
        self.device["data"] = self.data
        self.data["revision"] = "0.0"
        self.data["action"] = 0
        self.data["searchwatts"] = 0
        self.data["batterysize"] = 0
        # see extract method for a note
        self.data["battype"] = 0
        self.data["absorb"] = 0
        self.data["chargeramps"] = 0
        self.data["ainput"] = 0
        self.data["parallel"] = 0
        self.data["force_charge"] = 0
        self.data["genstart"] = 0
        self.data["lbco"] = 0
        self.data["vaccutout"] = 0
        self.data["vsfloat"] = 0
        self.data["vEQ"] = 0
        self.data["absorbtime"] = 0
        # end of core info
        # A0
        self.data["remotetimehours"] = 0
        self.data["remotetimemins"] = 0
        self.data["runtime"] = 0
        self.data["starttemp"] = 0
        self.data["startvdc"] = 0
        self.data["quiettime"] = 0
        # A1
        self.data["begintime"] = 0
        self.data["stoptime"] = 0
        self.data["vdcstop"] = 0
        self.data["voltstartdelay"] = 0
        self.data["voltstopdelay"] = 0
        self.data["maxrun"] = 0
        # A2
        self.data["socstart"] = 0
        self.data["socstop"] = 0
        self.data["ampstart"] = 0
        self.data["ampsstartdelay"] = 0
        self.data["ampstop"] = 0
        self.data["ampsstopdelay"] = 0
        # A3
        self.data["quietbegintime"] = 0
        self.data["quietendtime"] = 0
        self.data["exercisedays"] = 0
        self.data["exercisestart"] = 0
        self.data["exerciseruntime"] = 0
        self.data["topoff"] = 0
        # A4
        self.data["warmup"] = 0
        self.data["cool"] = 0
        # 80
        self.data["batteryefficiency"] = 0
        self.data["resetbmk"] = 0
        # 11 MSH - not supported
        self.data["mshinputamps"] = 0
        self.data["mshcutoutvoltage"] = 0
        # C0
        self.data["forcechgode"] = 0
        self.data["relayonoff"] = 0
        self.data["buzzeronoff"] = 0
        self.data["resetpt100"] = 0
        self.data["address"] = 0
        self.data["packet"] = 0
        self.data["lognumber"] = 0
        # C1
        self.data["relayonvdc"] = 0
        self.data["relayoffvdc"] = 0
        self.data["relayondelayseconds"] = 0
        self.data["relaydelayoffseconds"] = 0
        self.data["batterytempcomp"] = 0
        self.data["powersavetime"] = 0
        # C2
        self.data["alarmonvdc"] = 0
        self.data["alarmoffvdc"] = 0
        self.data["alarmdondelay"] = 0
        self.data["alarmoffdelay"] = 0
        self.data["eqdonetimer"] = 0
        self.data["chargerate"] = 0
        self.data["rebulkonsunup"] = 0
        # C3
        self.data["AbsorbVoltage"] = 0
        self.data["FloatVoltage"] = 0
        self.data["EqualizeVoltage"] = 0
        self.data["RebulkVoltage"] = 0
        self.data["BatteryTemperatureCompensation"] = 0

    def setBaseValues(self, unpacked):
        self.data["action"] = unpacked[0]
        self.data["searchwatts"] = unpacked[1]
        #
        # The documentation is very weird on this value
        #
        self.data["batterysize"] = (unpacked[2] * 2) + 200
        value = unpacked[3]
        if(value > 100):
            self.data["absorb"] = value * MagnumReader.multiplier / 10
            self.data["battype"] = 0
        else:
            self.data["absorb"] = 0
            self.data["battype"] = value
        self.data["chargeramps"] = unpacked[4]
        self.data["ainput"] = unpacked[5]
        self.data["revision"] = unpacked[6] / 10
        value = unpacked[7]
        self.data["parallel"] = value & 0x0f
        self.data["parallel"] = self.data["parallel"] * 10
        self.data["force_charge"] = value & 0xf0
        self.data["force_charge"] = self.data["force_charge"] >> 4
        self.data["genstart"] = unpacked[8]
        self.data["lbco"] = unpacked[9] / 10
        self.data["vaccutout"] = unpacked[10]
        self.data["vsfloat"] = unpacked[11] * MagnumReader.multiplier / 10
        self.data["vEQ"] = self.data["absorb"] + (unpacked[12] / 10)
        self.data["absorbtime"] = unpacked[13] / 10

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.REMOTE_00:
            self.setBaseValues(unpacked)
        elif packetType == MagnumReader.REMOTE_11:
            self.setBaseValues(unpacked)
            self.data["mshinputamps"] = unpacked[14]
            self.data["mshcutoutvoltage"] = unpacked[15]
        elif packetType == MagnumReader.REMOTE_80:
            self.setBaseValues(unpacked)
            self.data["remotetimehours"] = unpacked[14]
            self.data["remotetimemins"] = unpacked[15]
            self.data["batteryefficiency"] = unpacked[16]
            self.data["resetbmk"] = unpacked[17]
        elif packetType == MagnumReader.REMOTE_A0:
            self.setBaseValues(unpacked)
            self.data["remotetimehours"] = unpacked[14]
            self.data["remotetimemins"] = unpacked[15]
            self.data["runtime"] = unpacked[16] / 10
            self.data["starttemp"] = unpacked[17]
            self.data["starttemp"] = round(
                (self.data["starttemp"] - 32) * 5 / 9, 1)
            value = unpacked[18] * MagnumReader.multiplier
            self.data["startvdc"] = value / 10
            self.data["quiettime"] = unpacked[19]
        elif packetType == MagnumReader.REMOTE_A1:
            self.setBaseValues(unpacked)
            minutes = unpacked[14] * 15
            self.data["begintime"] = ((minutes // 60) * 100) + (minutes % 60)
            minutes = unpacked[15] * 15
            self.data["stoptime"] = ((minutes // 60) * 100) + (minutes % 60)
            value = unpacked[16]
            self.data["vdcstop"] = value * MagnumReader.multiplier / 10
            self.data["voltstartdelay"] = unpacked[17]
            if self.data["voltstartdelay"] > 127:
                self.data["voltstartdelay"] = (
                    self.data["voltstartdelay"] & 0x0f) * 60
            self.data["voltstopdelay"] = unpacked[18]
            if self.data["voltstopdelay"] > 127:
                self.data["voltstopdelay"] = (
                    self.data["voltstopdelay"] & 0x0f) * 60
            self.data["maxrun"] = unpacked[19] / 10
        elif packetType == MagnumReader.REMOTE_A2:
            self.setBaseValues(unpacked)
            self.data["socstart"] = unpacked[14]
            self.data["socstop"] = unpacked[15]
            self.data["ampstart"] = unpacked[16]
            self.data["ampsstartdelay"] = unpacked[17]
            if self.data["ampsstartdelay"] > 127:
                self.data["ampsstartdelay"] = (
                    self.data["ampsstartdelay"] & 0x0f) * 60
            self.data["ampstop"] = unpacked[18]
            self.data["ampsstopdelay"] = unpacked[19]
            if self.data["ampsstopdelay"] > 127:
                self.data["ampsstopdelay"] = (
                    self.data["ampsstopdelay"] & 0x0f) * 60
        elif packetType == MagnumReader.REMOTE_A3:
            self.setBaseValues(unpacked)
            minutes = unpacked[14] * 15
            self.data["quietbegintime"] = (
                (minutes // 60) * 100) + (minutes % 60)
            minutes = unpacked[15] * 15
            self.data["quietendtime"] = (
                (minutes // 60) * 100) + (minutes % 60)
            minutes = unpacked[16] * 15
            self.data["exercisestart"] = (
                (minutes // 60) * 100) + (minutes % 60)
            self.data["runtime"] = unpacked[17] / 10
            self.data["topoff"] = unpacked[18]
        elif packetType == MagnumReader.REMOTE_A4:
            self.setBaseValues(unpacked)
            self.data["warmup"] = unpacked[14]
            if self.data["warmup"] > 127:
                self.data["warmup"] = (self.data["warmup"] & 0x0f) * 60
            self.data["cool"] = unpacked[15]
            if self.data["cool"] > 127:
                self.data["cool"] = (self.data["cool"] & 0x0f) * 60
        elif packetType == MagnumReader.REMOTE_C0:
            self.setBaseValues(unpacked)
            self.data["forcechgode"] = unpacked[14] & 0x03
            byte_value = unpacked[15]
            self.data["relayonoff"] = (byte_value & 0x60) >> 6
            self.data["buzzeronoff"] = (byte_value & 0x30) >> 4
            self.data["resetpt100"] = unpacked[16]
            byte_value = unpacked[17]
            self.data["address"] = byte_value >> 5
            self.data["packet"] = byte_value & 0x1f
            self.data["lognumber"] = unpacked[18]
        elif packetType == MagnumReader.REMOTE_C1:
            self.setBaseValues(unpacked)
            self.data["relayonvdc"] = unpacked[14] / 10 * MagnumReader.multiplier
            self.data["relayoffvdc"] = unpacked[15] / 10 * MagnumReader.multiplier
            self.data["relayondelayseconds"] = unpacked[16]
            if self.data["relayondelayseconds"] < 0:
                self.data["relayondelayseconds"] = (
                    60 * (0 - self.data["relayondelayseconds"]))
            self.data["relaydelayoffseconds"] = unpacked[17]
            if self.data["relaydelayoffseconds"] < 0:
                self.data["relaydelayoffseconds"] = (
                    60 * (0 - self.data["relaydelayoffseconds"]))
            self.data["batterytempcomp"] = unpacked[18]
            self.data["powersavetime"] = unpacked[19] >> 2
        elif packetType == MagnumReader.REMOTE_C2:
            self.setBaseValues(unpacked)
            self.data["alarmonvdc"] = unpacked[14] / 10 * MagnumReader.multiplier
            self.data["alarmoffvdc"] = unpacked[15] / 10 * MagnumReader.multiplier
            self.data["alarmdondelay"] = unpacked[16]
            if self.data["alarmdondelay"] < 0:
                self.data["alarmdondelay"] = 60 * \
                    (0 - self.data["alarmdondelay"])
            self.data["alarmoffdelay"] = unpacked[17]
            if self.data["alarmoffdelay"] < 0:
                self.data["alarmoffdelay"] = 60 * \
                    (0 - self.data["alarmoffdelay"])
            self.data["eqdonetimer"] = unpacked[18] / 10
            byte_value = unpacked[19]
            self.data["chargerate"] = (byte_value & 0xFE) >> 1
            self.data["rebulkonsunup"] = byte_value & 0x01
        elif packetType == MagnumReader.REMOTE_C3:
            self.setBaseValues(unpacked)
            self.data["AbsorbVoltage"] = unpacked[14] / 10 * MagnumReader.multiplier
            self.data["FloatVoltage"] = unpacked[15] / 10 * MagnumReader.multiplier
            self.data["EqualizeVoltage"] = unpacked[16] / \
                10 * MagnumReader.multiplier
            self.data["AbsorbTime"] = unpacked[17] / 10
            # akip a  byte"]
            self.data["RebulkVoltage"] = unpacked[19] / 10 * MagnumReader.multiplier
            self.data["BatteryTemperatureCompensation"] = unpacked[20]
        elif packetType == MagnumReader.REMOTE_D0:
            self.setBaseValues(unpacked)
            # I have no idea what a D0 is

    def removeBMK(self):
        for item in RemoteDevice.noBMK:
            if item in self.data:
                self.data.pop(item)

    def removeAGS(self):
        for item in RemoteDevice.noAGS:
            if item in self.data:
                self.data.pop(item)

    def removePT100(self):
        for item in RemoteDevice.noPT100:
            if item in self.data:
                self.data.pop(item)

    def getDevice(self):
        # remove MSH as it's not supported - yet
        for item in RemoteDevice.noMSH:
            if item in self.data:
                self.data.pop(item)
        return self.device

class RTRDevice:
    def __init__(self, trace=False):
        self.trace = trace
        self.data = OrderedDict()
        self.device = OrderedDict()
        self.device["device"] = RTR
        self.device["data"] = self.data
        self.data["revision"] = "0.0"

    def parse(self, packet):
        packetType = packet[0]
        unpacked = packet[2]
        if self.trace:
            self.data[packetType] = packet[1].hex().upper()
        if packetType == MagnumReader.RTR_91:
            self.data["revision"] = str(round(unpacked[1] / 10))

    def getDevice(self):
        return self.device

