#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#


class AttrValue(object):
    def __init__(self, **kwargs):
        self.__name = kwargs.pop('name', None)
        self.__type = kwargs.pop('type', None)
        self.__length = kwargs.pop('length', None)
        if self.__length is None:
            self.__length = 0
        self.__values = kwargs.pop('values', None)
        if self.__values is None:
            self.__values = []
        elif type([]) != type(self.__values):
            self.__values = [self.__values]
        self.__repeating = kwargs.pop('repeating', None)
        if self.__repeating is None:
            self.__repeating = False

    def getName(self):
        return self.__name

    def getType(self):
        return self.__type

    def isRepeating(self):
        return self.__repeating

    def getLength(self):
        return self.__length

    def getValues(self):
        return self.__values
