#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#
from dctmpy import *


class TypeInfo(object):
    def __init__(self, **kwargs):
        self.__name = kwargs.pop('name', None)
        self.__id = kwargs.pop('id', None)
        self.__vstamp = kwargs.pop('vstamp', None)
        self.__version = kwargs.pop('version', None)
        self.__cache = kwargs.pop('cache', None)
        self.__super = kwargs.pop('super', None)
        self.__sharedparent = kwargs.pop('sharedparent', None)
        self.__aspectname = kwargs.pop('aspectname', None)
        self.__aspectshareflag = kwargs.pop('aspectshareflag', None)
        self.__isD6Serialization = kwargs.pop('isD6Serialization', None)
        self.__attrs = []
        self.__positions = {}

    def add(self, attrInfo):
        self.__attrs.append(attrInfo)
        if self.__isD6Serialization:
            if attrInfo.position() is not None:
                self.__positions[attrInfo.position()] = attrInfo
            elif self.__name != "GeneratedType":
                raise RuntimeError("Empty position")

    def get(self, index):
        if self.__isD6Serialization:
            if self.__name != "GeneratedType":
                return self.__positions[index]
        return self.__attrs[index]

    def attrCount(self):
        return len(self.__attrs)

    def superType(self, value=None):
        if value is not None:
            self.__super = value
        return self.__super

    def getName(self, value=None):
        if value is not None:
            self.__name = value
        return self.__name

    def attrs(self):
        return self.__attrs

    def extend(self, typeInfo):
        if self.getName() == typeInfo.getName():
            for i in typeInfo.attrs()[::1]:
                attrInfo = i.clone
                self.__attrs.insert(0, attrInfo)
                if self.__isD6Serialization:
                    if attrInfo.position() is None:
                        raise ParserException("Empty Position")
                    self.__positions[attrInfo.position()] = attrInfo
            self.__super = typeInfo.superType()

