#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.typedobject import TypedObject


class Persistent(TypedObject):
    def __init__(self, **kwargs):
        super(Persistent, self).__init__(**kwargs)

    def deserializeType(self):
        typeName = self.nextString(ATTRIBUTE_PATTERN)
        self.nextString(ATTRIBUTE_PATTERN)
        vstamp = 0
        if self.isD6Serialization():
            vstamp = self.readInt()
        return self.session().fetchType(typeName, vstamp)

    def deserializeObject(self):
        return super(Persistent, self).deserializeObject()





