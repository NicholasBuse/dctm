#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.typedobject import TypedObject


class Collection(TypedObject):
    def __init__(self, **kwargs):
        self.__collectionId = kwargs.pop('collection', None)
        self.__batchsize = kwargs.pop('batchsize', None)
        self.__recordsInBatch = None
        self.__mayBeMore = None
        super(Collection, self).__init__(**kwargs)

    def shouldDeserializeType(self):
        return True

    def shouldDeserializeObject(self):
        return False

    def nextRecord(self):
        firstinbatch = False
        if isEmpty(self.rawdata()) and (self.mayBeMore() is None or self.mayBeMore()):
            response = self.session().nextBatch(self.collection(), self.batchsize())
            self.rawdata(response.data())
            self.recordsInBatch(response.recordsInBatch())
            self.mayBeMore(response.mayBeMore())
            firstinbatch = True

        if not isEmpty(self.rawdata()) and (self.recordsInBatch() is None or self.recordsInBatch() > 0):
            try:
                entry = CollectionEntry(session=self.session(), type=self.type(), rawdata=self.rawdata(),
                                        first=firstinbatch)
                self.rawdata(entry.rawdata())
                return entry
            finally:
                if self.recordsInBatch() is not None:
                    self.recordsInBatch(self.recordsInBatch() - 1)

        self.close()
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

    def batchsize(self, value=None):
        if value is not None:
            self.__batchsize = value
        return self.__batchsize

    def recordsInBatch(self, value=None):
        if value is not None:
            self.__recordsInBatch = value
        return self.__recordsInBatch

    def mayBeMore(self, value=None):
        if value is not None:
            self.__mayBeMore = value
        return self.__mayBeMore

    def close(self):
        try:
            if self.collection() is not None and self.collection() > 0:
                self.session().closeCollection(self.collection())
        finally:
            self.collection(None)

    def __del__(self):
        self.close()


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


class CollectionEntry(TypedObject):
    def __init__(self, **kwargs):
        self.__firstInBatch = kwargs.pop('first', False)
        super(CollectionEntry, self).__init__(**kwargs)

    def readHeader(self):
        if self.__firstInBatch:
            super(CollectionEntry, self).readHeader()

    def deserialize(self, message=None):
        super(CollectionEntry, self).deserialize(message)
        if self.isD6Serialization():
            self.readInt()
