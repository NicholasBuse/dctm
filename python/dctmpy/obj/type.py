#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.typedobject import TypedObject


class TypeObject(TypedObject):
    def __init__(self, **kwargs):
        self.__typeCont = None
        super(TypeObject, self).__init__(**kwargs)

    def deserialize(self, message=None):
        if self.__typeCont is not None:
            for i in range(1, self.__typeCont):
                self.deserializeChildType()
        else:
            while not isEmpty(self.rawdata()):
                self.deserializeChildType()

    def deserializeChildType(self):
        childType = self.deserializeType()
        if childType is not None:
            addTypeToCache(childType)

    def readHeader(self):
        self.__typeCont = self.readInt()

    def shouldDeserializeType(self):
        return False

    def shouldDeserializeObject(self):
        return False
