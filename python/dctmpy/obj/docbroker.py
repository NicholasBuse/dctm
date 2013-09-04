#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.e import *
from dctmpy.obj.typedobject import TypedObject
from dctmpy.type.attrvalue import AttrValue


class DocbrokerObject(TypedObject):
    def __init__(self, **kwargs):
        super(DocbrokerObject, self).__init__(**dict(
            kwargs,
            **{'serializationVersion': 0}
        ))

    def deserializeType(self):
        pass

    def deserializeObject(self):
        header = self.nextToken()
        if "OBJ" != header:
            raise ParserException("Invalid header, expected OBJ, got: %s" % header)

        typename = self.nextToken()
        if isEmpty(typename):
            raise ParserException("Wrong type name")

        self.readInt()

        for i in range(0, self.readInt()):
            self.deserializeAttr(i)

    def deserializeAttr(self, index):
        attrName = self.nextString(ATTRIBUTE_PATTERN)
        attrType = self.nextString(ATTRIBUTE_PATTERN)
        repeating = self.nextString(REPEATING_PATTERN) == REPEATING
        attrLength = self.readInt()

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
            'type': attrType,
            'length': attrLength,
            'values': result,
            'repeating': repeating,
        }))

