#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy.net.request import Request
import socket


class Netwise(object):
    def __init__(self, **kwargs):
        self.__version = kwargs.pop('version', None)
        self.__release = kwargs.pop('release', None)
        self.__inumber = kwargs.pop('inumber', None)
        self.__sockopts = kwargs
        self.__socket = None
        self.__sequence = 0

    def connected(self):
        if self.__socket is None:
            return False
        return True

    def socket(self):
        if not self.connected():
            try:
                host = self.__sockopts.get('host', None)
                port = self.__sockopts.get('port', None)

                if host is None or port is None:
                    raise RuntimeError("Invalid host or port")

                self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.__socket.connect((host, port))
            except:
                self.__socket = None
                raise
        return self.__socket

    def disconnect(self):
        try:
            if self.connected():
                self.__socket.close()
        finally:
            self.__socket = None

    def __del__(self):
        self.disconnect()


    def request(self, **kwargs):
        return Request(**dict(kwargs, **{
            'socket': self.socket(),
            'sequence': ++self.__sequence,
            'version': self.__version,
            'release': self.__release,
            'inumber': self.__inumber,
        }))

