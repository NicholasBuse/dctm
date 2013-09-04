#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

import re
from dctmpy import *
from dctmpy.e import *
from dctmpy.type import *
from dctmpy.type.attrinfo import AttrInfo
from dctmpy.type.attrvalue import AttrValue
from dctmpy.type.typeinfo import TypeInfo


class TypedObject(object):
    def __init__(self, **kwargs):
        self.__session = kwargs.pop('session', None)
        self.__serializationVersion = kwargs.pop('serializationVersion', None)
        self.__type = kwargs.pop('type', None)
        self.__rawdata = kwargs.pop('rawdata', None)
        self.__attrs = {}

        if self.__serializationVersion is None:
            self.__serializationVersion = self.__session.serializationVersion()

        if self.__serializationVersion == 0:
            self.__isD6Serialisation = False
        else:
            self.__isD6Serialisation = True

        if not isEmpty(self.__rawdata):
            self.deserialize()

    def isD6Serialization(self, value=None):
        if value is not None:
            self.__isD6Serialisation = value
        return self.__isD6Serialisation

    def iso8601Time(self):
        if self.isD6Serialization():
            return self.__session.iso8601Time()
        return False

    def deserialize(self, message=None):
        if isEmpty(message) and isEmpty(self.__rawdata):
            raise ParserException("Empty data")
        elif not isEmpty(message):
            self.__rawdata = message

        self.readHeader()

        if self.isD6Serialization():
            if self.readInt() != self.__session.serializationVersionHint():
                raise ParserException("Invalid serialization algorithm")

        if self.__type is None and self.shouldDeserializeType():
            self.__type = self.deserializeType()

        if self.shouldDeserializeObject():
            self.deserializeObject()

    def readHeader(self):
        pass

    def deserializeType(self):
        header = self.nextToken()
        if header != "TYPE":
            raise ParserException("Invalid type header: %s" % header)

        typeInfo = self.deserializeTypeInfo()
        for i in range(0, self.readInt()):
            typeInfo.add(self.deserializeAttrInfo())

        return typeInfo

    def deserializeObject(self):
        header = self.nextToken()
        if "OBJ" != header:
            raise ParserException("Invalid header, expected OBJ, got: %s" % header)

        typename = self.nextToken()

        if typename is None or len(typename) == 0:
            raise ParserException("Wrong type name")

        if self.isD6Serialization():
            self.readInt()
            self.readInt()
            self.readInt()

        if self.__type is None or typename != self.__type.getName():
            raise ParserException("No type info for %s" % typename)

        for i in range(0, self.readInt()):
            self.deserializeAttr(i)

        self.deserializeExtendedAttr()

    def deserializeAttr(self, index):
        position = {True: lambda: base64ToInt(self.nextString(BASE64_PATTERN)),
                    False: lambda: index}[self.isD6Serialization()]()

        if position is None:
            position = index

        repeating = self.__type.get(position).repeating()
        attrType = self.__type.get(position).type()
        attrName = self.__type.get(position).name()
        attrLength = self.__type.get(position).length()

        if attrType is None:
            raise ParserException("Unknown type")

        result = []

        if not repeating:
            result.append(self.readAttrValue(attrType))
        else:
            for i in range(0, self.readInt()):
                result.append(self.readAttrValue(attrType))

        self.add(AttrValue(**{
            'name': attrName,
            'position': position,
            'type': attrType,
            'length': attrLength,
            'values': result,
            'repeating': repeating,
        }))

    def add(self, attrValue):
        self.__attrs[attrValue.getName()] = attrValue

    def deserializeExtendedAttr(self):
        for i in range(0, self.readInt()):
            attrName = self.nextString(ATTRIBUTE_PATTERN)
            attrType = self.nextString(ATTRIBUTE_PATTERN)
            repeating = REPEATING == self.nextString()
            length = self.readInt()

            if isEmpty(attrType):
                raise ParserException("Unknown type: %s" % attrType)

            result = []

            if not repeating:
                result.append(self.readAttrValue(attrType))
            else:
                for i in range(1, self.readInt()):
                    result.append(self.readAttrValue(attrType))

            self.__attrs[attrName] = AttrValue(**{
                'name': attrName,
                'type': attrType,
                'length': length,
                'values': result,
                'repeating': repeating,
            })

    def readAttrValue(self, attrType):
        return {
            "INT": lambda: self.readInt(),
            "STRING": lambda: self.readString(),
            "TIME": lambda: self.readTime(),
            "BOOL": lambda: self.readBoolean(),
            "ID": lambda: self.nextString(),
            "DOUBLE": lambda: self.nextString(),
            "UNDEFINED": lambda: self.nextString()
        }[attrType]()

    def deserializeTypeInfo(self):
        return TypeInfo(**{
            'name': self.nextString(ATTRIBUTE_PATTERN),
            'id': self.nextString(ATTRIBUTE_PATTERN),
            'vstamp': {True: lambda: self.readInt(),
                       False: lambda: None}[self.isD6Serialization()](),
            'version': {True: lambda: self.readInt(),
                        False: lambda: None}[self.isD6Serialization()](),
            'cache': {True: lambda: self.readInt(),
                      False: lambda: None}[self.isD6Serialization()](),
            'super': self.nextString(ATTRIBUTE_PATTERN),
            'sharedparent': {True: lambda: self.nextString(ATTRIBUTE_PATTERN),
                             False: lambda: None}[self.isD6Serialization()](),
            'aspectname': {True: lambda: self.nextString(ATTRIBUTE_PATTERN),
                           False: lambda: None}[self.isD6Serialization()](),
            'aspectshareflag': {True: lambda: self.readBoolean(),
                                False: lambda: None}[self.isD6Serialization()](),
            'isD6Serialization': self.isD6Serialization(),
        })

    def deserializeAttrInfo(self):
        return AttrInfo(**{
            'position': {True: lambda: base64ToInt(self.nextString(BASE64_PATTERN)),
                         False: lambda: None}[self.isD6Serialization()](),
            'name': self.nextString(ATTRIBUTE_PATTERN),
            'type': self.nextString(TYPE_PATTERN),
            'repeating': REPEATING == self.nextString(),
            'length': self.readInt(),
            'restriction': {True: lambda: self.readInt(),
                            False: lambda: None}[self.isD6Serialization()](),
        })

    def serialize(self):
        result = ""
        if self.isD6Serialization():
            result += "%d\n" % self.__session.serializationVersionHint()
        result += "OBJ NULL 0 "
        if self.isD6Serialization():
            result += "0 0\n0\n"
        result += "%d\n" % len(self.__attrs)
        for attrValue in self.__attrs.values():
            result += "%s %s %s %d\n" % (
                attrValue.getName(), attrValue.getType(), [SINGLE, REPEATING][attrValue.isRepeating()],
                attrValue.getLength())
            if attrValue.isRepeating():
                result += "%d\n" % len(attrValue.getValues())
            for value in attrValue.getValues():
                if STRING == attrValue.getType():
                    result += "A %d %s\n" % (len(value), value)
                elif BOOL == attrValue.getType():
                    result += "%s\n" % ["F", "T"][value]
                else:
                    result += "%s\n" % value
        return result

    def shouldDeserializeType(self):
        return True

    def shouldDeserializeObject(self):
        return True

    def read(self, length):
        data = self.__rawdata
        self.__rawdata = data[length:]
        return data[:length]

    def nextToken(self, separator=DEFAULT_SEPARATOR):
        self.__rawdata = re.sub("^%s" % separator, "", self.__rawdata)
        m = re.search(separator, self.__rawdata)
        if m is not None:
            return self.read(m.start(0))
        else:
            return self.read(len(self.__rawdata))

    def nextString(self, pattern=None, separator=DEFAULT_SEPARATOR):
        value = self.nextToken(separator)
        if pattern is not None:
            if re.match(pattern, value) is None:
                raise ParserException("Invalid string: %s for regexp %s" % (value, pattern))
        return value

    def readInt(self):
        return int(self.nextString(INTEGER_PATTERN))

    def readString(self):
        self.nextString(ENCODING_PATTERN)
        return self.read(self.readInt() + 1)[1:]

    def readTime(self):
        return self.nextToken(CRLF_PATTERN)

    def readBoolean(self):
        return bool(self.nextString(BOOLEAN_PATTERN))

    def rawdata(self, value=None):
        if value is not None:
            self.__rawdata = value
        return self.__rawdata

    def getAttrs(self):
        return self.__attrs

    def session(self, value=None):
        if value is not None:
            self.__session = value
        return self.__session

    def type(self, value=None):
        if value is not None:
            self.__type = value
        return self.__type

    def __getattr__(self, name):
        if name in self.__attrs:
            attrValue = self.__attrs[name]
            if attrValue.isRepeating():
                return attrValue.getValues()
            else:
                if len(attrValue.getValues()) == 0:
                    return None
                return attrValue.getValues()[0]
        else:
            raise AttributeError


def parseAddr(value):
    if re.match("INET_ADDR", value) is None:
        raise ParserException("Invalid address: %s" % value)


