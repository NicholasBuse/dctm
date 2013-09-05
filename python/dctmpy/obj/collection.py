#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy import *
from dctmpy.obj.typedobject import TypedObject


class Collection(TypedObject):
    attrs = ['collection', 'batchsize', 'recordsinbatch', 'maybemore']

    def __init__(self, **kwargs):
        for attribute in Collection.attrs:
            self.__setattr__("__" + attribute, kwargs.pop(attribute, None))
        super(Collection, self).__init__(**kwargs)

    def shouldDeserializeType(self):
        return True

    def shouldDeserializeObject(self):
        return False

    def nextRecord(self):
        firstinbatch = False
        if isEmpty(self.rawdata) and (self.maybemore is None or self.maybemore):
            response = self.session.nextBatch(self.collection, self.batchsize)
            self.rawdata = response.data
            self.recordsinbatch = response.recordsinbatch
            self.maybemore = response.maybemore
            firstinbatch = True

        if not isEmpty(self.rawdata) and (self.recordsinbatch is None or self.recordsinbatch > 0):
            try:
                entry = CollectionEntry(session=self.session, type=self.type, rawdata=self.rawdata,
                                        firstinbatch=firstinbatch)
                self.rawdata = entry.rawdata
                return entry
            finally:
                if self.recordsinbatch is not None:
                    self.recordsinbatch -= 1

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

    def __getattr__(self, name):
        if name in Collection.attrs:
            return self.__getattribute__("__" + name)
        else:
            return super(Collection, self).__getattr__(name)

    def close(self):
        try:
            if self.collection > 0:
                self.session.closeCollection(self.collection)
        finally:
            self.collection = None

    def __del__(self):
        self.close()


class PersistentCollection(TypedObject):
    def __init__(self, **kwargs):
        super(PersistentCollection, self).__init__(**kwargs)

    def deserialize(self, message=None):
        if isEmpty(message) and isEmpty(self.rawdata):
            raise ParserException("Empty data")
        if not isEmpty(message):
            self.rawdata = message
        self.type = self.session.fetchType(message, 0)

    def shouldDeserializeType(self):
        return False


class CollectionEntry(TypedObject):
    attrs = ['firstinbatch']

    def __init__(self, **kwargs):
        for attribute in CollectionEntry.attrs:
            self.__setattr__("__" + attribute, kwargs.pop(attribute, None))
        super(CollectionEntry, self).__init__(**kwargs)

    def readHeader(self):
        if self.firstinbatch:
            super(CollectionEntry, self).readHeader()

    def deserialize(self, message=None):
        super(CollectionEntry, self).deserialize(message)
        if self.d6serialization:
            self.readInt()

    def __getattr__(self, name):
        if name in CollectionEntry.attrs:
            return self.__getattribute__("__" + name)
        else:
            return super(CollectionEntry, self).__getattr__(name)

