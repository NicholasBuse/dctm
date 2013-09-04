#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.e import *
from dctmpy.obj.typedobject import TypedObject


class PersistentCollection(TypedObject):
    def __init__(self, **kwargs):
        super(PersistentCollection, self).__init__(**kwargs)

    def deserialize(self, message=None):
        if isEmpty(message) and isEmpty(self.rawdata()):
            raise ParserException("Empty data")
        if not isEmpty(message):
            self.rawdata(message)
        self.type(self.session().fetchType(message, 0))

    def shouldDeserializeType(self):
        return False

