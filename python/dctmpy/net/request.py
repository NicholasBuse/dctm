#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

import array
from dctmpy import *
from dctmpy.e import *
from dctmpy.net import *
from dctmpy.net.response import Response

HEADER_SIZE = 4


class Request(object):
    def __init__(self, **kwargs):
        self.__version = kwargs.pop('version', None)
        self.__release = kwargs.pop('release', None)
        self.__inumber = kwargs.pop('inumber', None)
        self.__sequence = kwargs.pop('sequence', None)
        self.__socket = kwargs.pop('socket', None)
        self.__immediate = kwargs.pop('immediate', False)
        self.__type = kwargs.pop('type', None)

        if self.__version is None or self.__release is None or self.__inumber is None:
            raise ProtocolException("Wrong protocol version info")

        if self.__type is None:
            raise ProtocolException("Invalid request type")

        data = kwargs.pop('data', None)

        if data is None:
            self.__data = None
        else:
            self.__data = serializeData(data)

        if self.__immediate:
            self.send()

    def send(self):
        self.__socket.sendall(
            self.buildRequest()
        )

    def receive(self):
        messagePayload = array.array('B')
        messagePayload.fromstring(self.__socket.recv(HEADER_SIZE))
        if len(messagePayload) == 0:
            raise ProtocolException("Unable to read header")

        messageLength = 0
        for i in range(0, HEADER_SIZE):
            messageLength = messageLength << 8 | messagePayload[i]

        headerPayload = stringToIntegerArray(self.__socket.recv(2))
        if headerPayload[0] != PROTOCOL_VERSION:
            raise ProtocolException("Wrong protocol 0x%X expected 0x%X" % (headerPayload[0], PROTOCOL_VERSION))
        headerLength = headerPayload[1]

        header = stringToIntegerArray(self.__socket.recv(headerLength))

        sequence = readInteger(header)
        if sequence != self.__sequence:
            raise ProtocolException("Invalid sequence %d expected %d" % (sequence, self.__sequence))

        status = readInteger(header)
        if status != 0:
            raise ProtocolException("Bad status: 0x%X" % status)

        bytesToRead = messageLength - len(headerPayload) - headerLength
        message = array.array('B')
        while True:
            chunk = stringToIntegerArray(self.__socket.recv(bytesToRead))
            message.extend(chunk)
            if len(chunk) == 0 or len(message) == bytesToRead:
                break

        return Response(**{
            'message': message
        })

    def buildRequest(self):
        data = self.buildHeader()
        if self.__data is not None:
            data.extend(self.__data)
        length = len(data)
        data.insert(0, length & 0x000000ff)
        data.insert(0, (length >> 8) & 0x000000ff)
        data.insert(0, (length >> 16) & 0x000000ff)
        data.insert(0, (length >> 24) & 0x000000ff)
        return data

    def buildHeader(self):
        header = array.array('B')
        header.extend(serializeInteger(self.__sequence))
        header.extend(serializeInteger(self.__type))
        header.extend(serializeInteger(self.__version))
        header.extend(serializeInteger(self.__release))
        header.extend(serializeInteger(self.__inumber))
        header.insert(0, len(header))
        header.insert(0, PROTOCOL_VERSION)
        return header




