#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy.obj.typedobject import TypedObject


class CollectionEntry(TypedObject):
    def __init__(self, **kwargs):
        super(CollectionEntry, self).__init__(**kwargs)

    def deserialize(self, message=None):
        super(CollectionEntry, self).deserialize(message)
        if self.isD6Serialization():
            self.readInt()