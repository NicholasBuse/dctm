#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

import re
from dctmpy.netwise import Netwise
from dctmpy.obj.collection import Collection, PersistentCollection
from dctmpy.obj.entrypoints import EntryPoints
from dctmpy.obj.persistent import Persistent
from dctmpy.obj.type import TypeObject
from dctmpy.obj.typedobject import TypedObject
from dctmpy.req import *

NETWISE_VERSION = 3
NETWISE_RELEASE = 5
NETWISE_INUMBER = 769


class Docbase(Netwise):
    attrs = ['docbaseid', 'username', 'password', 'messages', 'entrypoints', 'serializationversion', 'iso8601time',
             'session', 'serializationversionhint']

    def __init__(self, **kwargs):
        for attribute in Docbase.attrs:
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

    def sendRpc(self, **kwargs):
        rpcId = kwargs.pop('rpcid', None)
        data = kwargs.pop('data', [])
        gettingErrors = kwargs.pop('gettingErrors', False)

        if self.session is not None:
            data.insert(0, self.session)

        (valid, odata, collection, persistent, maybemore, count) = (None, None, None, None, None, None)

        response = self.request(type=rpcId, data=data, immediate=True).receive()
        message = response.next()
        odata = response.last()
        if rpcId == RPC_APPLY_FOR_OBJECT:
            valid = int(response.next()) > 0
        elif rpcId == RPC_APPLY:
            collection = int(response.next())
            persistent = int(response.next()) > 0
            maybemore = int(response.next()) > 0
            valid = collection > 0
        elif rpcId == RPC_CLOSE_COLLECTION:
            pass
        elif rpcId == RPC_GET_NEXT_PIECE:
            pass
        elif rpcId == RPC_MULTI_NEXT:
            count = int(response.next())
            maybemore = int(response.next()) > 0
            valid = int(response.next()) > 0
        else:
            valid = int(response.next()) > 0

        if (odata & 0x02 != 0) and not gettingErrors:
            self.getMessages(gettingErrors=True)

        if valid is not None and not valid and (odata & 0x02 != 0) and len(self.messages) > 0:
            reason = ", ".join(
                "%s: %s" % (message['NAME'], message['1']) for message in
                ((lambda x: x.pop(0))(self.messages) for i in xrange(0, len(self.messages)))
                if message['SEVERITY'] == 3
            )
            if len(reason) > 0:
                raise RuntimeError(reason)

        if odata == 0x10 or (odata == 0x01 and rpcId == RPC_GET_NEXT_PIECE):
            message += self.sendRpc(RPC_GET_NEXT_PIECE).data

        return Response(data=message, odata=odata, persistent=persistent, collection=collection, maybemore=maybemore,
                        recordcount=count)

    def apply(self, **kwargs):
        request = kwargs.pop('request', None)
        rpcid = kwargs.pop('rpcid', None)
        method = kwargs.pop('method', None)
        cls = kwargs.pop('cls', Collection)
        objectId = kwargs.pop('objectId', NULL_ID)
        gettingErrors = kwargs.pop('gettingErrors', False)

        response = self.sendRpc(rpcid=rpcid, data=[self.resolveMethod(method), objectId, request],
                                gettingErrors=gettingErrors)
        data = response.data
        if response.persistent and cls == Collection:
            cls = PersistentCollection

        result = cls(session=self, rawdata=data)
        if response.collection is not None:
            result.collection = response.collection
            result.batchsize = DEFAULT_BATCH_SIZE
            result.persistent = response.persistent

        return result

    def getMessages(self, gettingErrors=False):
        self.messages = [x for x in self.applyForCollection(method="GET_ERRORS", request=requestGetErrors(self),
                                                            gettingErrors=gettingErrors)]

    def authenticate(self, username=None, password=None):
        if username is not None and password is not None:
            self.username = username
            self.password = password
        if self.username is None:
            raise RuntimeError("Empty username")
        if self.password is None:
            raise RuntimeError("Empty password")

        result = self.applyForObject(method="AUTHENTICATE_USER", cls=TypedObject, objectId=NULL_ID,
                                     request=requestAuthenticate(self, self.username,
                                                                 self.obfuscate(self.password)))
        if result['RETURN_VALUE'] != 1:
            raise RuntimeError("Unable to authenticate")

    def nextBatch(self, collection, batchHint=DEFAULT_BATCH_SIZE):
        return self.sendRpc(rpcid=RPC_MULTI_NEXT, data=[collection, batchHint])

    def closeCollection(self, collection):
        self.sendRpc(rpcid=RPC_CLOSE_COLLECTION, data=[collection])

    def fetchEntryPoints(self):
        self.entrypoints = self.applyForObject(method="ENTRY_POINTS", cls=EntryPoints, objectId=NULL_ID,
                                               request=requestEntryPoints(self)).methods()
        for name in self.entrypoints:
            self.addEntryPoint(name)

    def getServerConfig(self):
        return self.applyForObject(method="GET_SERVER_CONFIG", cls=Persistent, objectId=NULL_ID,
                                   request=requestServerConfig(self))

    def getDocbaseConfig(self):
        return self.applyForObject(method="GET_DOCBASE_CONFIG", cls=Persistent, objectId=NULL_ID,
                                   request=requestDocbaseConfig(self))

    def fetchObject(self, objectId):
        return self.applyForObject(method="FETCH", cls=Persistent, objectId=objectId)

    def fetchByQualification(self, qualification):
        collection = self.query("select r_object_id from %s" % qualification)
        record = collection.nextRecord()
        if record is not None:
            return self.fetchObject(record['r_object_id'])
        return None

    def fetchType(self, typename, vstamp):
        typeObj = getTypeFormCache(typename)
        if typeObj is not None:
            return typeObj
        if "FETCH_TYPE" in self.entrypoints:
            self.applyForString(method="FETCH_TYPE", cls=TypeObject, objectId=NULL_ID,
                                request=requestFetchType(self, typename, vstamp))
        else:
            response = self.sendRpc(rpcid=RPC_FETCH_TYPE, data=[typename])
            TypeObject(session=self, rawdata=response.data)
        return getTypeFormCache(typename)

    def query(self, query, forUpdate=False, batchHint=DEFAULT_BATCH_SIZE, bofDQL=False):
        try:
            collection = self.applyForCollection(method="EXEC", cls=Collection, objectId=NULL_ID,
                                                 request=requestQuery(self, query, forUpdate, batchHint, bofDQL))
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

    def applyForObject(self, **kwargs):
        cls = kwargs.pop('cls', TypedObject)
        return self.apply(**dict(kwargs, **{'cls': cls, 'rpcid': RPC_APPLY_FOR_OBJECT}))

    def applyForCollection(self, **kwargs):
        cls = kwargs.pop('cls', Collection)
        return self.apply(**dict(kwargs, **{'cls': cls, 'rpcid': RPC_APPLY}))

    def applyForString(self, **kwargs):
        return self.apply(**dict(kwargs, **{'rpcid': RPC_APPLY_FOR_STRING}))

    def resolveMethod(self, methodName):
        if methodName not in self.entrypoints:
            raise RuntimeError("Unknown method: %s" % methodName)
        return self.entrypoints[methodName]

    def __getattr__(self, name):
        if name in Docbase.attrs:
            return self.__getattribute__(ATTRIBUTE_PREFIX + name)
        else:
            return super(Docbase, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name in Docbase.attrs:
            Docbase.__setattr__(self, ATTRIBUTE_PREFIX + name, value)
        else:
            super(Docbase, self).__setattr__(name, value)


    def addEntryPoint(self, name):
        def inner(self, **kwargs):
            return self.applyForCollection(**dict(kwargs, **{'method': name}))

        inner.__name__ = name
        setattr(self.__class__, inner.__name__, inner)


class Response(object):
    attrs = ['data', 'odata', 'persistent', 'collection', 'recordsinbatch', 'maybemore']

    def __init__(self, **kwargs):
        for attribute in Response.attrs:
            self.__setattr__(ATTRIBUTE_PREFIX + attribute, kwargs.pop(attribute, None))

    def __getattr__(self, name):
        if name in Response.attrs:
            return self.__getattribute__(ATTRIBUTE_PREFIX + name)
        else:
            return AttributeError

    def __setattr__(self, name, value):
        if name in Response.attrs:
            Response.__setattr__(self, ATTRIBUTE_PREFIX + name, value)
        else:
            super(Response, self).__setattr__(name, value)
