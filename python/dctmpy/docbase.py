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
    def __init__(self, **kwargs):
        self.__docbaseId = kwargs.pop("docbaseId", None)
        self.__username = kwargs.pop("username", None)
        self.__password = kwargs.pop("password", None)
        self.__messages = None
        self.__entryPoints = None

        super(Docbase, self).__init__(**dict(kwargs, **{
            'version': NETWISE_VERSION,
            'release': NETWISE_RELEASE,
            'inumber': NETWISE_INUMBER,
        }))

        self.__serializationVersion = 0
        self.__iso8601Time = False
        self.__session = NULL_ID

        if self.__docbaseId is None:
            self.resolveDocbaseId()

        self.connect()
        self.getEntryPoints()

        if self.__password is not None and self.__username is not None:
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
            self.__docbaseId = int(m.group(1))
        self.disconnect()

    def disconnect(self):
        try:
            if self.__session is not None and self.__session != NULL_ID:
                self.request(
                    type=RPC_CLOSE_SESSION,
                    data=[
                        self.__session,
                    ],
                    immediate=True,
                ).receive()
            super(Docbase, self).disconnect()
        finally:
            self.__session = None

    def connect(self):
        response = self.request(
            type=RPC_NEW_SESSION_BY_ADDR,
            data=[
                self.__docbaseId,
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
                self.__serializationVersion = 1
            else:
                self.__serializationVersion = 0
        else:
            self.__serializationVersion = 0

        if self.__serializationVersion == 0:
            self.__iso8601Time = False
        else:
            if serverVersion[9] & 0x01 == 1:
                self.__iso8601Time = True
            else:
                self.__iso8601Time = False

        session = response.next()

        if session == NULL_ID:
            raise RuntimeError(reason)

        self.__session = session

    def sendRpc(self, **kwargs):
        rpcId = kwargs.pop('rpcid', None)
        data = kwargs.pop('data', [])
        gettingErrors = kwargs.pop('gettingErrors', False)

        if self.__session is not None:
            data.insert(0, self.__session)

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

        if valid is not None and not valid and (odata & 0x02 != 0) and len(self.__messages) > 0:
            reason = ""
            while len(self.__messages) > 0:
                message = self.__messages.pop(0)
                if message.get("SEVERITY") != 3:
                    continue
                if len(reason) > 0:
                    reason += ", "
                reason += "%s:%s" % (message.get("NAME"), message.get("1"))
            if len(reason) > 0:
                raise RuntimeError(reason)

        if odata == 0x10 or (odata == 0x01 and rpcId == RPC_GET_NEXT_PIECE):
            message += self.sendRpc(RPC_GET_NEXT_PIECE).data()

        return Response(data=message, odata=odata, persistent=persistent, collection=collection, maybemore=maybemore,
                        recordcount=count)

    def apply(self, **kwargs):
        request = kwargs.pop('request', None)
        rpcid = kwargs.pop('rpcid', None)
        method = kwargs.pop('method', None)
        clazz = kwargs.pop('clazz', Collection)
        objectId = kwargs.pop('objectId', NULL_ID)
        gettingErrors = kwargs.pop('gettingErrors', False)

        response = self.sendRpc(rpcid=rpcid, data=[self.resolveMethod(method), objectId, request],
                                gettingErrors=gettingErrors)
        data = response.data()
        if response.persistent() and clazz == Collection:
            clazz = PersistentCollection

        result = clazz(session=self, rawdata=data)
        if response.collection() is not None:
            result.collection(response.collection())
            result.batchsize(DEFAULT_BATCH_SIZE)

        return result

    def getMessages(self, gettingErrors=False):
        self.messages(
            self.applyForCollection(method="GET_ERRORS", request=requestGetErrors(self),
                                    gettingErrors=gettingErrors).readAll())

    def messages(self, value=None):
        if value is not None:
            self.__messages = value
        return self.__messages

    def authenticate(self, username=None, password=None):
        if username is not None and password is not None:
            self.__username = username
            self.__password = password
        if self.__username is None:
            raise RuntimeError("Empty username")
        if self.__password is None:
            raise RuntimeError("Empty password")

        result = self.applyForObject(method="AUTHENTICATE_USER", clazz=TypedObject, objectId=NULL_ID,
                                     request=requestAuthenticate(self, self.__username,
                                                                 self.obfuscate(self.__password)))
        if result.RETURN_VALUE != 1:
            raise RuntimeError("Unable to authenticate")

    def nextBatch(self, collection, batchHint=DEFAULT_BATCH_SIZE):
        return self.sendRpc(rpcid=RPC_MULTI_NEXT, data=[collection, batchHint])

    def closeCollection(self, collection):
        self.sendRpc(rpcid=RPC_CLOSE_COLLECTION, data=[collection])

    def entryPoints(self, value=None):
        if value is not None:
            self.__entryPoints = value
        if self.__entryPoints is None:
            return {
                'ENTRY_POINTS': 0,
                'GET_ERRORS': 558,
            }
        return self.__entryPoints

    def getEntryPoints(self):
        self.entryPoints(
            self.applyForObject(method="ENTRY_POINTS", clazz=EntryPoints, objectId=NULL_ID,
                                request=requestEntryPoints(self)).map()
        )

    def getServerConfig(self):
        return self.applyForObject(method="GET_SERVER_CONFIG", clazz=Persistent, objectId=NULL_ID,
                                   request=requestServerConfig(self))

    def getDocbaseConfig(self):
        return self.applyForObject(method="GET_DOCBASE_CONFIG", clazz=Persistent, objectId=NULL_ID,
                                   request=requestDocbaseConfig(self))

    def fetchObject(self, objectId):
        return self.applyForObject(method="FETCH", clazz=Persistent, objectId=objectId)

    def fetchByQualification(self, qualification):
        collection = self.query("select r_object_id from %s" % qualification)
        record = collection.nextBatch()
        if record is not None:
            return self.fetchObject(record.r_object_id)
        return None

    def fetchType(self, typename, vstamp):
        typeObj = getTypeFormCache(typename)
        if typeObj is not None:
            return typeObj
        if "FETCH_TYPE" in self.entryPoints():
            self.applyForString(method="FETCH_TYPE", clazz=TypeObject, objectId=NULL_ID,
                                request=requestFetchType(self, typename, vstamp))
        else:
            response = self.sendRpc(rpcid=RPC_FETCH_TYPE, data=[typename])
            TypeObject(session=self, rawdata=response.data())
        return getTypeFormCache(typename)

    def query(self, query, forUpdate=False, batchHint=DEFAULT_BATCH_SIZE, bofDQL=False):
        try:
            collection = self.applyForCollection(method="EXEC", clazz=Collection, objectId=NULL_ID,
                                                 request=requestQuery(self, query, forUpdate, batchHint, bofDQL))
        except Exception, e:
            raise RuntimeError("Error occured while executing query: %s\nError was: %s" % (query, str(e)))
        return collection

    def obfuscate(self, password):
        if self.isObfuscated(password):
            return password
        return "".join(
            ["%02x" % x for x in [
                [x ^ 0xB6, 0xB6][x == 0xB6] for x in [
                    ord(x) for x in [x for x in password][::-1]]
            ]]
        )

    def isObfuscated(self, password):
        if re.match("^([0-9a-f]{2})+$", password) is None:
            return False
        for x in re.findall("[0-9a-f]{2}", password):
            if int(x, 16) != 0xB6 and (int(x, 16) ^ 0xB6) > 127:
                return False
        return True

    def applyForObject(self, **kwargs):
        clazz = kwargs.pop('clazz', TypedObject)
        return self.apply(**dict(kwargs, **{'clazz': clazz, 'rpcid': RPC_APPLY_FOR_OBJECT}))

    def applyForCollection(self, **kwargs):
        clazz = kwargs.pop('clazz', Collection)
        return self.apply(**dict(kwargs, **{'clazz': clazz, 'rpcid': RPC_APPLY}))

    def applyForString(self, **kwargs):
        return self.apply(**dict(kwargs, **{'rpcid': RPC_APPLY_FOR_STRING}))

    def resolveMethod(self, methodName):
        if methodName not in self.entryPoints():
            raise RuntimeError("Unknown method: %s" % methodName)
        return self.entryPoints()[methodName]

    def docbaseId(self, value=None):
        if value is not None:
            self.__docbaseId = value
        return self.__docbaseId

    def session(self, value=None):
        if value is not None:
            self.__session = value
        return self.__session

    def serializationVersion(self, value=None):
        if value is not None:
            self.__serializationVersion = value
        return self.__serializationVersion

    def iso8601Time(self, value=None):
        if value is not None:
            self.__iso8601Time = value
        return self.__iso8601Time

    def serializationVersionHint(self):
        return CLIENT_VERSION_ARRAY[3]


class Response(object):
    def __init__(self, **kwargs):
        self.__data = kwargs.pop('data', None)
        self.__odata = kwargs.pop('odata', None)
        self.__persistent = kwargs.pop('persistent', None)
        self.__collection = kwargs.pop('collection', None)
        self.__recordsInBatch = kwargs.get('recordsinbacth', None)
        self.__mayBeMore = kwargs.get('maybemore', None)

    def data(self, value=None):
        if value is not None:
            self.__data = value
        return self.__data

    def odata(self, value=None):
        if value is not None:
            self.__odata = value
        return self.__odata

    def persistent(self, value=None):
        if value is not None:
            self.__persistent = value
        return self.__persistent

    def collection(self, value=None):
        if value is not None:
            self.__collection = value
        return self.__collection

    def mayBeMore(self, value=None):
        if value is not None:
            self.__mayBeMore = value
        return self.__mayBeMore

    def recordsInBatch(self, value=None):
        if value is not None:
            self.__recordsInBatch = value
        return self.__recordsInBatch
