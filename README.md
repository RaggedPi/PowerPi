PowerPi
=======

**PowerPi** is a python3 interfacing bridge between modbus connections and a MQTT broker.

>This project is based of the amazing work of [Charles Godwin](mailto:magnum@godwin.ca)'s [pymagnum software](https://github.com/CharlesGodwin/pymagnum) as well as [Graham22](https://github.com/graham22)'s work [communicating with Midnite's classic MPPT charge controller](https://github.com/graham22/ClassicMQTT).  

To fit my use case, I needed a single project to talk to Magnum Energy's device's via Modbus (RS485) connection as well as to Midnite Solar's Classic 150 charge controller that could combine the data and transmit a universal payload back to my Home Automation System.

This allows remote monitoring and control of my off grid home remotely and easily through a single contact node.

This implementation is for personal use and uploaded for educational purposes only.  See each originating project's licenses where approprate.

## Configuration

`PowerPi` can be configured via a `config.env` file or via command-line arguments upon launch.  An example configuration file is supplied. 

Config | Section | Flag | Default | Notes
---|---|---|---|---
interval | **Config** | --interval | 60 | (s) interval between data publishing
timeout | **Config** | --timeout | 0.005 | (s) mqtt timeout
root_topic | **Config** | --topic | powerpi/ | root topic to publish to. [TOPIC]/[DEVICE]
allow_duplicates | **Config** | --duplicates | True | allow duplicate entries
packet_count | **Config** | --packets | 50 | number of packets to scan at a time
trace | **Config** | --trace | False | trace packets
clean_packets | **Config** | --nocleanup | True | clean up packets.
broker | **Mqtt** | --broker | localhost | ip address of mqtt broker
port | **Mqtt** | --brokerport | 1883 | mqtt broker port
username | **Mqtt** | --username | mqtt_user | username to the mqtt broker
mqtt_password | **Secret** | --password | mqtt | password to the mqtt broker
client | **Mqtt** | --clientid | `uuid` | mqtt client id
classic | **Classic** | --classic | 10.10.0.2 | ip address of the Midnite Classic
port | **Classic** | --classicport | 502 | port of the Midnite Classic
device | **Magnum** | --device | /dev/ttyUSB0 | path to modbus device

Any command-line arguments supplied upon execusion will override any settings within the `config.env` file.  Any values neglected from command-line or a config file will hold the default value shown above.

## Usage
`PowerPi` can be run from a bash shell or added to a startup script or routine.

### Launching
Basic:
`python3 powerpi.py`

Custom broker:
` python3 powerpi.py --broker 192.168.0.100`

Classic:
`python3 powerpi.py --classic 192.168.0.101`

Advanced:
`python3 powerpi.py --broker 192.168.0.100 --classic 192.168.0.101 --username classic_user --interval 3600 --duplicates --nocleanup`

## ToDo

* Add configs/ flags to enabled/ disabled classic and/or magnum communications if needed.

[![GitHub License](https://img.shields.io/github/license/RaggedPi/PowerPi?style=plastic&logo=github)](https://github.com/RaggedPi/PowerPi/LICENSE)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/RaggedPi/PowerPi?include_prereleases&style=plastic&logo=github)](https://github.com/RaggedPi/PowerPi/releases)
[![GitHub issues](https://img.shields.io/github/issues/RaggedPi/PowerPi?style=plastic&logo=github)](https://github.com/RaggedPi/PowerPi/issues)
[![https://www.buymeacoffee.com/ner0tic](https://img.shields.io/badge/Donate-Buy%20Me%20a%20coffee-orange?style=plastic&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/ner0tic)

## Setup And Usage
[PowerPi Wiki](https://github.com/RaggedPi/PowerPi/wiki)

## License
```

 Copyright (c) 2019

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

```


