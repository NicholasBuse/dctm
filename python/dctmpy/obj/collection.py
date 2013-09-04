#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.collectionentry import CollectionEntry
from dctmpy.obj.typedobject import TypedObject


class Collection(TypedObject):
    def __init__(self, **kwargs):
        self.__collectionId = kwargs.pop('collection', None)
        self.__batchSize = kwargs.pop('batchSize', None)
        super(Collection, self).__init__(**kwargs)

    def shouldDeserializeType(self):
        return True

    def shouldDeserializeObject(self):
        return False

    def nextRecord(self):
        if isEmpty(self.rawdata()):
            self.rawdata(self.session().nextRecord(self.__collectionId, self.__batchSize))

        if not isEmpty(self.rawdata()):
            entry = CollectionEntry(session=self.session(), type=self.type(), rawdata=self.rawdata())
            self.rawdata(entry.rawdata())
            return entry

        return None

    def readAll(self):
        result = []
        r = self.nextRecord()
        while True:
            if r is None:
                break
            result.append(r)
            r = self.nextRecord()
        self.close()
        return result

    def collection(self, value=None):
        if value is not None:
            self.__collectionId = value
        return self.__collectionId

    def batchSize(self, value=None):
        if value is not None:
            self.__batchSize = value
        return self.__batchSize

    def close(self):
        if self.__collectionId is not None and self.__collectionId > 0:
            self.session().closeCollection(self.__collectionId)




