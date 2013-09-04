#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#


class AttrInfo(object):
    def __init__(self, **kwargs):
        self.__position = kwargs.pop('position', None)
        self.__name = kwargs.pop('name', None)
        self.__type = kwargs.pop('type', None)
        self.__repeating = kwargs.pop('repeating', None)
        self.__length = kwargs.pop('length', None)
        self.__restriction = kwargs.pop('restriction', None)

    def clone(self):
        return AttrInfo({
            'position': self.__position,
            'name': self.__name,
            'type': self.__type,
            'repeating': self.__repeating,
            'length': self.__length,
            'restriction': self.__restriction,
        })

    def name(self):
        return self.__name

    def position(self):
        return self.__position

    def repeating(self):
        return self.__repeating

    def type(self):
        return self.__type

    def length(self):
        return self.__length