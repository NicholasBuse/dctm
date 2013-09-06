#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

import re
from dctmpy import *


class TypedObject(object):
    attrs = ['session', 'type', 'rawdata', 'd6serialization', 'serializationversion', 'iso8601time']

    def __init__(self, **kwargs):
        for attribute in TypedObject.attrs:
            self.__setattr__(ATTRIBUTE_PREFIX + attribute, kwargs.pop(attribute, None))
        self.__attrs = {}
        self.__hasExtendedAttrs = False

        if self.d6serialization is None:
            if self.serializationversion is None:
                self.serializationversion = self.session.serializationversion
            if self.serializationversion == 0:
                self.d6serialization = False
            else:
                self.d6serialization = True

        if self.iso8601time is None:
            if self.d6serialization:
                self.iso8601time = self.session.iso8601time
            else:
                self.iso8601time = False

        if not isEmpty(self.rawdata):
            self.deserialize()

    def deserialize(self, message=None):
        if isEmpty(message) and isEmpty(self.rawdata):
            raise ParserException("Empty data")
        elif not isEmpty(message):
            self.rawdata = message

        self.readHeader()

        if self.type is None and self.shouldDeserializeType():
            self.type = self.deserializeType()

        if self.shouldDeserializeObject():
            self.deserializeObject()

    def readHeader(self):
        if self.d6serialization:
            self.readInt()

    def deserializeType(self):
        header = self.nextToken()
        if header != "TYPE":
            raise ParserException("Invalid type header: %s" % header)

        typeInfo = self.deserializeTypeInfo()
        for i in xrange(0, self.readInt()):
            typeInfo.append(self.deserializeAttrInfo())

        return typeInfo

    def deserializeObject(self):
        header = self.nextToken()
        if "OBJ" != header:
            raise ParserException("Invalid header, expected OBJ, got: %s" % header)

        typename = self.nextToken()

        if typename is None or len(typename) == 0:
            raise ParserException("Wrong type name")

        if self.d6serialization:
            self.readInt()
            self.readInt()
            self.readInt()

        if self.type is None or typename != self.type.name:
            raise ParserException("No type info for %s" % typename)

        for i in xrange(0, self.readInt()):
            self.deserializeAttr(i)

        self.deserializeExtendedAttr()

    def deserializeAttr(self, index):
        position = {True: lambda: pseudoBase64ToInt(self.nextString(BASE64_PATTERN)),
                    False: lambda: index}[self.d6serialization]()

        if position is None:
            position = index

        repeating = self.type.get(position).repeating
        attrType = self.type.get(position).type
        attrName = self.type.get(position).name
        attrLength = self.type.get(position).length

        if attrType is None:
            raise ParserException("Unknown type")

        result = []

        if not repeating:
            result.append(self.readAttrValue(attrType))
        else:
            for i in xrange(0, self.readInt()):
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
        self.__attrs[attrValue.name] = attrValue

    def deserializeExtendedAttr(self):
        attrCount = self.readInt()
        if attrCount > 0:
            self.__hasExtendedAttrs = True
        else:
            return
        for i in xrange(0, attrCount):
            attrName = self.nextString(ATTRIBUTE_PATTERN)
            attrType = self.nextString(ATTRIBUTE_PATTERN)
            repeating = REPEATING == self.nextString()
            length = self.readInt()

            if isEmpty(attrType):
                raise ParserException("Unknown typedef: %s" % attrType)

            result = []

            if not repeating:
                result.append(self.readAttrValue(attrType))
            else:
                for i in xrange(1, self.readInt()):
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
            INT: lambda: self.readInt(),
            STRING: lambda: self.readString(),
            TIME: lambda: self.readTime(),
            BOOL: lambda: self.readBoolean(),
            ID: lambda: self.nextString(),
            DOUBLE: lambda: self.nextString(),
            UNDEFINED: lambda: self.nextString()
        }[attrType]()

    def deserializeTypeInfo(self):
        return TypeInfo(**{
            'name': self.nextString(ATTRIBUTE_PATTERN),
            'id': self.nextString(ATTRIBUTE_PATTERN),
            'vstamp': {True: lambda: self.readInt(),
                       False: lambda: None}[self.d6serialization](),
            'version': {True: lambda: self.readInt(),
                        False: lambda: None}[self.d6serialization](),
            'cache': {True: lambda: self.readInt(),
                      False: lambda: None}[self.d6serialization](),
            'super': self.nextString(ATTRIBUTE_PATTERN),
            'sharedparent': {True: lambda: self.nextString(ATTRIBUTE_PATTERN),
                             False: lambda: None}[self.d6serialization](),
            'aspectname': {True: lambda: self.nextString(ATTRIBUTE_PATTERN),
                           False: lambda: None}[self.d6serialization](),
            'aspectshareflag': {True: lambda: self.readBoolean(),
                                False: lambda: None}[self.d6serialization](),
            'd6serialization': self.d6serialization,
        })

    def deserializeAttrInfo(self):
        return AttrInfo(**{
            'position': {True: lambda: pseudoBase64ToInt(self.nextString(BASE64_PATTERN)),
                         False: lambda: None}[self.d6serialization](),
            'name': self.nextString(ATTRIBUTE_PATTERN),
            'type': self.nextString(TYPE_PATTERN),
            'repeating': REPEATING == self.nextString(),
            'length': self.readInt(),
            'restriction': {True: lambda: self.readInt(),
                            False: lambda: None}[self.d6serialization](),
        })

    def serialize(self):
        result = ""
        if self.d6serialization:
            result += "%d\n" % self.session.serializationversionhint
        result += "OBJ NULL 0 "
        if self.d6serialization:
            result += "0 0\n0\n"
        result += "%d\n" % len(self.__attrs)
        for attrValue in self.__attrs.values():
            result += "%s %s %s %d\n" % (
                attrValue.name, attrValue.type, [SINGLE, REPEATING][attrValue.repeating],
                attrValue.length)
            if attrValue.repeating:
                result += "%d\n" % len(attrValue.values)
            for value in attrValue.values:
                if STRING == attrValue.type:
                    result += "A %d %s\n" % (len(value), value)
                elif BOOL == attrValue.type:
                    result += "%s\n" % ["F", "T"][value]
                else:
                    result += "%s\n" % value
        return result

    def shouldDeserializeType(self):
        return True

    def shouldDeserializeObject(self):
        return True

    def read(self, length):
        data = self.rawdata
        self.rawdata = data[length:]
        return data[:length]

    def nextToken(self, separator=DEFAULT_SEPARATOR):
        self.rawdata = re.sub("^%s" % separator, "", self.rawdata)
        m = re.search(separator, self.rawdata)
        if m is not None:
            return self.read(m.start(0))
        else:
            return self.read(len(self.rawdata))

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
        timestr = self.nextToken(CRLF_PATTERN)
        if timestr.startswith(" "):
            timestr = timestr[1:]
        if timestr.startswith("xxx "):
            timestr = timestr[4:]
        return parseTime(timestr, self.iso8601time)

    def readBoolean(self):
        return bool(self.nextString(BOOLEAN_PATTERN))

    def getAttr(self, attrName):
        if attrName in self.__attrs:
            return self.__attrs[attrName]
        else:
            raise RuntimeError("No attribute %s" % attrName)

    def __getattr__(self, name):
        if name in self.__attrs:
            return self.__attrs[name]
        elif name in TypedObject.attrs:
            return self.__getattribute__(ATTRIBUTE_PREFIX + name)
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        if name in TypedObject.attrs:
            TypedObject.__setattr__(self, ATTRIBUTE_PREFIX + name, value)
        else:
            super(TypedObject, self).__setattr__(name, value)

    def __len__(self):
        return len(self.__attrs)

    def __contains__(self, key):
        return key in self.__attrs

    def __getitem__(self, key):
        if key in self.__attrs:
            attrValue = self.__attrs[key]
            if attrValue.repeating:
                return attrValue.values
            else:
                return attrValue[0]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        if key in self.__attrs:
            attrValue = self.__attrs[key]
            if attrValue.repeating:
                if value is None:
                    attrValue.values = []
                elif isinstance(value, list):
                    attrValue.values = value
                else:
                    attrValue.values = [value]
            else:
                if value is None:
                    attrValue.values = []
                elif isinstance(value, list):
                    if len(value) > 1:
                        raise RuntimeError("Single attribute %s does not accept arrays" % key)
                    elif len(value) == 0:
                        attrValue.values = []
                    else:
                        val = value[0]
                        if val is None:
                            attrValue.values = []
                        else:
                            attrValue.values = [val]
        else:
            raise KeyError

    def __iter__(self):
        return iter(self.__attrs.keys())
