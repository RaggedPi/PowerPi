#!/usr/bin/env python
# -*- coding: utf-8 -*-

__appname__ = "MagnumReader"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.1.1"
__license__ = "Apache2"

# from pymagnum.magnum import Magnum
from Magnum.magnum import Magnum


class MagnumReader(Magnum):

    def getItems(self):
        d = super().getDevices()
        return d

    def getName(self):
        return 'magnum'
