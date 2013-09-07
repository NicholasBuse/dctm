#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

import re
from dctmpy import *
from dctmpy.netwise import Netwise
from dctmpy.obj.collection import Collection, PersistentCollection
from dctmpy.obj.entrypoints import EntryPoints
from dctmpy.obj.persistent import Persistent
from dctmpy.obj.type import TypeObject
from dctmpy.obj.typedobject import TypedObject
from dctmpy import req

NETWISE_VERSION = 3
NETWISE_RELEASE = 5
NETWISE_INUMBER = 769


class Docbase(Netwise):
    fields = ['docbaseid', 'username', 'password', 'messages', 'entrypoints', 'serializationversion', 'iso8601time',
              'session', 'serializationversionhint', 'docbaseconfig', 'serverconfg']

    def __init__(self, **kwargs):
        for attribute in Docbase.fields:
            self.__setattr__(ATTRIBUTE_PREFIX + attribute, kwargs.pop(attribute, None))
        super(Docbase, self).__init__(**dict(kwargs, **{
            'version': NETWISE_VERSION,
            'release': NETWISE_RELEASE,
            'inumber': NETWISE_INUMBER,
        }))

        if self.serializationversion is None:
            self.serializationversion = 0
        if self.iso8601time is None:
            self.iso8601time = False
        if self.session is None:
            self.session = NULL_ID
        if self.docbaseid is None:
            self.resolveDocbaseId()
        if self.messages is None:
            self.messages = []
        if self.entrypoints is None:
            self.entrypoints = {
                'ENTRY_POINTS': 0,
                'GET_ERRORS': 558,
            }
        for name in self.entrypoints.keys():
            self.addEntryPoint(name)
        if self.serializationversionhint is None:
            self.serializationversionhint = CLIENT_VERSION_ARRAY[3]

        self.connect()
        self.fetchEntryPoints()

        if self.password is not None and self.username is not None:
            self.authenticate()

    def resolveDocbaseId(self):
        response = self.request(
            type=RPC_NEW_SESSION_BY_ADDR,
            data=[
                -1,
                EMPTY_STRING,
                CLIENT_VERSION_STRING,
                EMPTY_STRING,
                CLIENT_VERSION_ARRAY,
                NULL_ID,
            ],
            immediate=True,
        ).receive()

        reason = response.next()
        m = re.search('Wrong docbase id: \(-1\) expecting: \((\d+)\)', reason)
        if m is not None:
            self.docbaseid = int(m.group(1))
        self.disconnect()

    def disconnect(self):
        try:
            if self.session is not None and self.session != NULL_ID:
                self.request(
                    type=RPC_CLOSE_SESSION,
                    data=[
                        self.session,
                    ],
                    immediate=True,
                ).receive()
            super(Docbase, self).disconnect()
        finally:
            self.session = None

    def connect(self):
        response = self.request(
            type=RPC_NEW_SESSION_BY_ADDR,
            data=[
                self.docbaseid,
                EMPTY_STRING,
                CLIENT_VERSION_STRING,
                EMPTY_STRING,
                CLIENT_VERSION_ARRAY,
                NULL_ID,
            ],
            immediate=True,
        ).receive()

        reason = response.next()
        serverVersion = response.next()
        if serverVersion[7] == DM_CLIENT_SERIALIZATION_VERSION_HINT:
            if DM_CLIENT_SERIALIZATION_VERSION_HINT > 0:
                self.serializationversion = 1
            else:
                self.serializationversion = 0
        else:
            self.serializationversion = 0

        if self.serializationversion == 0:
            self.iso8601time = False
        else:
            if serverVersion[9] & 0x01 == 1:
                self.iso8601time = True
            else:
                self.iso8601time = False

        session = response.next()

        if session == NULL_ID:
            raise RuntimeError(reason)

        self.session = session

    def rpc(self, rpcid, data=None, faulted=False):
        if not data:
            data = []
        if self.session is not None:
            if len(data) == 0 or data[0] != self.session:
                data.insert(0, self.session)

        (valid, odata, collection, persistent, more, records) = (None, None, None, None, None, None)

        response = self.request(type=rpcid, data=data, immediate=True).receive()
        message = response.next()
        odata = response.last()
        if rpcid == RPC_APPLY_FOR_OBJECT:
            valid = int(response.next()) > 0
            persistent = int(response.next()) > 0
        elif rpcid == RPC_APPLY:
            collection = int(response.next())
            persistent = int(response.next()) > 0
            more = int(response.next()) > 0
            valid = collection > 0
        elif rpcid == RPC_CLOSE_COLLECTION:
            pass
        elif rpcid == RPC_GET_NEXT_PIECE:
            pass
        elif rpcid == RPC_MULTI_NEXT:
            records = int(response.next())
            more = int(response.next()) > 0
            valid = int(response.next()) > 0
        else:
            valid = int(response.next()) > 0

        if (odata & 0x02 != 0) and not faulted:
            self.getMessages(faulted=True)

        if valid is not None and not valid and (odata & 0x02 != 0) and len(self.messages) > 0:
            reason = ", ".join(
                "%s: %s" % (message['NAME'], message['1']) for message in
                ((lambda x: x.pop(0))(self.messages) for i in xrange(0, len(self.messages)))
                if message['SEVERITY'] == 3
            )
            if len(reason) > 0:
                raise RuntimeError(reason)

        if odata == 0x10 or (odata == 0x01 and rpcid == RPC_GET_NEXT_PIECE):
            message += self.rpc(RPC_GET_NEXT_PIECE).data

        return Response(data=message, odata=odata, persistent=persistent, collection=collection, more=more,
                        records=records)

    def apply(self, rpcid, objectid, method, request=None, cls=Collection, faulted=False):
        if rpcid is None:
            rpcid = RPC_APPLY

        if objectid is None:
            objectid = NULL_ID

        response = self.rpc(rpcid, [self.getMethod(method), objectid, request], faulted)
        data = response.data

        if rpcid == RPC_APPLY_FOR_STRING:
            return data
        elif rpcid == RPC_APPLY_FOR_ID:
            return data
        elif rpcid == RPC_APPLY_FOR_DOUBLE:
            return data
        elif rpcid == RPC_APPLY_FOR_BOOL:
            return data
        elif rpcid == RPC_APPLY_FOR_LONG:
            return data
        elif rpcid == RPC_APPLY_FOR_TIME:
            return data

        if cls is None:
            if rpcid == RPC_APPLY:
                cls = Collection
            elif rpcid == RPC_APPLY_FOR_OBJECT:
                cls = TypedObject

        if response.persistent:
            if cls == Collection:
                cls = PersistentCollection
            elif cls == TypedObject:
                cls = Persistent

        result = cls(session=self, buffer=data)
        if response.collecton is not None and isinstance(result, Collection):
            result.collection = response.collection
            result.persistent = response.persistent
            result.records = response.records
            if isinstance(request, TypedObject) and 'BATCH_HINT' in request:
                result.batchsize = request['BATCH_HINT']
            else:
                result.batchsize = DEFAULT_BATCH_SIZE

        return result

    def getMessages(self, faulted=False):
        self.messages = [x for x in self.GET_ERRORS(NULL_ID, req.getErrors(self), Collection, faulted)]

    def authenticate(self, username=None, password=None):
        if username is not None and password is not None:
            self.username = username
            self.password = password
        if self.username is None:
            raise RuntimeError("Empty username")
        if self.password is None:
            raise RuntimeError("Empty password")

        result = self.AUTHENTICATE_USER(NULL_ID, req.authenticate(self, self.username, self.obfuscate(self.password)))
        if result['RETURN_VALUE'] != 1:
            raise RuntimeError("Unable to authenticate")

        self.docbaseconfig = self.GET_DOCBASE_CONFIG()
        self.serverconfig = self.GET_SERVER_CONFIG()

    def nextBatch(self, collection, batchHint=DEFAULT_BATCH_SIZE):
        return self.rpc(RPC_MULTI_NEXT, [collection, batchHint])

    def closeCollection(self, collection):
        self.rpc(RPC_CLOSE_COLLECTION, [collection])

    def fetchEntryPoints(self):
        self.entrypoints = self.ENTRY_POINTS().methods()
        for name in self.entrypoints:
            self.addEntryPoint(name)

    def getServerConfig(self):
        return self.GET_SERVER_CONFIG()

    def getDocbaseConfig(self):
        return self.GET_DOCBASE_CONFIG()

    def fetch(self, objectid):
        return self.FETCH(objectid)

    def qualification(self, qualification):
        collection = self.query("select r_object_id from %s" % qualification)
        record = collection.nextRecord()
        if record is not None:
            return self.fetch(record['r_object_id'])
        return None

    def fetchType(self, name, vstamp=0):
        typeObj = getTypeFormCache(name)
        if typeObj is not None:
            return typeObj
        data = None
        if "FETCH_TYPE" in self.entrypoints:
            data = self.FETCH_TYPE(NULL_ID, req.fetchType(self, name, vstamp))['result']
        else:
            data = self.rpc(RPC_FETCH_TYPE, [name]).data
        return TypeObject(session=self, buffer=data).type

    def query(self, query, forUpdate=False, batchHint=DEFAULT_BATCH_SIZE, bofDQL=False):
        try:
            collection = self.EXEC(NULL_ID, req.query(self, query, forUpdate, batchHint, bofDQL))
        except Exception, e:
            raise RuntimeError("Error occurred while executing query: %s" % query, e)
        return collection

    def obfuscate(self, password):
        if self.isObfuscated(password):
            return password
        return "".join(
            "%02x" % [x ^ 0xB6, 0xB6][x == 0xB6] for x in (ord(x) for x in password[::-1])
        )

    def isObfuscated(self, password):
        if re.match("^([0-9a-f]{2})+$", password) is None:
            return False
        for x in re.findall("[0-9a-f]{2}", password):
            if int(x, 16) != 0xB6 and (int(x, 16) ^ 0xB6) > 127:
                return False
        return True

    def asObject(self, objectid, method, request=None, cls=TypedObject, faulted=False):
        if objectid is None:
            objectid = NULL_ID
        return self.apply(RPC_APPLY_FOR_OBJECT, objectid, method, request, cls, faulted)

    def asCollection(self, objectid, method, request=None, cls=Collection, faulted=False):
        if objectid is None:
            objectid = NULL_ID
        return self.apply(RPC_APPLY, objectid, method, request, cls, faulted)

    def asString(self, objectid, method, request=None, cls=None, faulted=False):
        if objectid is None:
            objectid = NULL_ID
        return self.apply(RPC_APPLY_FOR_STRING, objectid, method, request, cls, faulted)

    def asId(self, objectid, method, request=None, cls=None, faulted=False):
        if objectid is None:
            objectid = NULL_ID
        return self.apply(RPC_APPLY_FOR_ID, objectid, method, request, cls, faulted)

    def getMethod(self, name):
        if name not in self.entrypoints:
            raise RuntimeError("Unknown method: %s" % name)
        return self.entrypoints[name]

    def __getattr__(self, name):
        if name in Docbase.fields:
            return self.__getattribute__(ATTRIBUTE_PREFIX + name)
        else:
            return super(Docbase, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name in Docbase.fields:
            Docbase.__setattr__(self, ATTRIBUTE_PREFIX + name, value)
        else:
            super(Docbase, self).__setattr__(name, value)

    def addEntryPoint(self, name):
        if getattr(Docbase, name, None) is not None:
            return
        elif name in KNOWN_ENTRY_POINTS:
            def inner(self, objectid=NULL_ID, request=None, cls=KNOWN_ENTRY_POINTS[name][1], faulted=False):
                return KNOWN_ENTRY_POINTS[name][0](self, objectid, name, request, cls, faulted)

            inner.__name__ = name
            setattr(self.__class__, inner.__name__, inner)
        else:
            def inner(self, objectid=NULL_ID, request=None, cls=Collection, faulted=False):
                return self.asCollection(objectid, name, request, cls, faulted)

            inner.__name__ = name
            setattr(self.__class__, inner.__name__, inner)


class Response(object):
    fields = ['data', 'odata', 'persistent', 'collection', 'records', 'more']

    def __init__(self, **kwargs):
        for attribute in Response.fields:
            self.__setattr__(ATTRIBUTE_PREFIX + attribute, kwargs.pop(attribute, None))

    def __getattr__(self, name):
        if name in Response.fields:
            return self.__getattribute__(ATTRIBUTE_PREFIX + name)
        else:
            return AttributeError

    def __setattr__(self, name, value):
        if name in Response.fields:
            Response.__setattr__(self, ATTRIBUTE_PREFIX + name, value)
        else:
            super(Response, self).__setattr__(name, value)


KNOWN_ENTRY_POINTS = {
    'GET_SERVER_CONFIG': (Docbase.asObject, TypedObject),
    'GET_DOCBASE_CONFIG': (Docbase.asObject, TypedObject),
    'ENTRY_POINTS': (Docbase.asObject, EntryPoints),
    'FETCH': (Docbase.asObject, Persistent),
    'AUTHENTICATE_USER': (Docbase.asObject, TypedObject),
    'GET_ERRORS': (Docbase.asCollection, Collection),
    'FETCH_TYPE': (Docbase.asObject, TypedObject),
    'EXEC': (Docbase.asCollection, Collection),
}
