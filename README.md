PowerPi
=======

PowerPi is a python3 interfacing bridge between modbus connections and a MQTT broker.

This project is based of the amazing work of `Charles Godwin <magnum@godwin.ca>`'s `pymagnum <https://github.com/CharlesGodwin/pymagnum>` software and `Graham22 <https://github.com/graham22>`'s `work <https://github.com/graham22/ClassicMQTT>` communicating with Midnite's classic MPPT charge controller.  

To fit my use case, I needed a single project to talk to Magnum Energy's device's via Modbus (RS485) connection as well as to Midnite Solar's Classic 150 charge controller that could combine the data and transmit a universal payload back to my Home Automation System.

This allows remote monitoring and control of my off grid home remotely.

This implementation is for personal use and uploaded for educational purposes only.  See each originating project's licenses where approprate.