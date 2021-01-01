#!/usr/bin/env python
# -*- coding: utf-8 -*-

__appname__ = "ReaderManager"
__author__ = "David Durost <david.durost@gmail.com>"
__version__ = "0.0.2"
__license__ = "Apache2"

from collections import OrderedDict
import pendulum
from copy import deepcopy
import logging
logger = logging.getLogger(__name__)


class Item:
    """ Reader Item Class. """  

    def __init__(self):
        """ Constructor. """

        self.data = OrderedDict()
        self.item = OrderedDict()
        self.item["item"] = f"item {pendulum.now().int_timestamp}"
        self.item["data"] = self.data

    def parse(self, data):
        """ Parse Data.

        Args:
            data (mixed): data to pass to be parsed
        """

        pass

    def getItem(self) -> OrderedDict:
        """ Get Item.

        Returns:
            OrderedDict: Dict of item
        """

        return self.item


class Device(Item):
    """ Device Class.

    Args:
        Item (Item): Item parent class
    """

    def __init__(self):
        """ Constructor. """

        super().__init__()

    def parse(self, data):
        """ Parse Data.

        Args:
            data (mixed): Data to be parsed.
        """

        return super.parse(data)

    def getDevice(self) -> OrderedDict:
        """ Get Device.

        Returns:
            OrderedDict: Device class.
        """

        return super.getItem()

    def getItem(self):
        """ Get Item.

        Returns:
            OrderedDict: Item class
        """

        return super.getItem()


class Reader:
    """ Reader class. """

    def __init__(self, name: str = __name__):
        """ Constructor

        Args:
            name (str, optional): Reader name. Defaults to class name.
        """

        self.name = name
        self.items = OrderedDict()
        self.lastread = None
        self._configs = OrderedDict()

    def getName(self) -> str:
        """ Get Reader Name.

        Returns:
            str: Reader name
        """

        return self.name

    def getItems(self) -> OrderedDict:
        """ Get Reader Items.

        Returns:
            OrderedDict: List of items.
        """

        return deepcopy(self.items)


class ReaderManager:
    def __init__(self,
                 name: str = __name__,
                 readers: OrderedDict = None,
                 ignored: OrderedDict = None):
        """ Constructor.

        Args:
            name (str, optional): Reader manager name. Defaults to class name.
            readers (OrderedDict, optional): List of readers. Defaults to None.
            ignored (OrderedDict, optional): List of readers to ignore. Defaults to None.
        """

        self.name = name
        self._setupLogger()
        self._readers = readers or OrderedDict()
        self.ignored = ignored or OrderedDict()
        self._updateIgnored()

    def _setupLogger(self):
        """ Setup the logger. """

        # Set default loglevel
        logger.setLevel(logging.DEBUG)

        # Create file handler
        # @todo: generate dated log files in a log directory
        fn = f"{__name__}.log"
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

    def _updateIgnored(self):
        """ Update Lists Based On Ignore List. """

        self.readers = OrderedDict()
        for r in self._readers:
            if r not in self.ignored:
                self.readers.append(r)
        logging.debug(f"Active readers list regenerated. {len(self.readers)} out of {len(self._readers)} readers found.")

    def getName(self) -> str:
        """ Get Reader Manager Name.

        Returns:
            str: Reader manager name
        """

        return self.name

    def getReaders(self, activeOnly: bool = True) -> OrderedDict:
        """ Get Readers List

        Args:
            activeOnly (bool, optional): If true, only returns active readers, otherwise returns ALL readers. Defaults to True.

        Returns:
            OrderedDict: List of readers.
        """

        return self.readers if activeOnly else self._readers

    def addReader(self, reader: Reader):
        """ Add/ Reactivate A Reader

        Args:
            reader (Reader): Reader to add/ reactivate
        """

        if reader not in self._readers:
            logging.debug(f"Adding {reader} to readers.")
            self.readers[reader.name] = reader
        elif reader in self.ignored:
            logging.debug(f"Removing {reader} from ignore list.")
            self.ignored.remove(reader)
            self._updateIgnored()
        else:
            logging.debug(f"{reader.getName()} already in found in readers.")

    def addIgnore(self, reader: Reader):
        """ Add A Reader To Ignore List

        Args:
            reader (Reader): Reader to ignore
        """

        if reader in self._readers:
            if reader not in self.ignored:
                logging.debug(f"{reader.getName()} not found in ignore list, adding.")
                self.ignored[reader.getName()].append(reader)
                self._updateIgnored()
        else:
            logging.warning(f"{reader.getName()} was not found in readers.")
