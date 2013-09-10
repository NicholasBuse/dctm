#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#
from dctmpy import req, parseAddr
from dctmpy.netwise import Netwise
from dctmpy.obj.docbroker import DocbaseMap

NETWISE_VERSION = 1
NETWISE_RELEASE = 0
NETWISE_INUMBER = 1094

version = "0.0.1 python"
handle = "localhost"


class Docbroker(Netwise):
    def __init__(self, **kwargs):
        super(Docbroker, self).__init__(**dict(kwargs, **{
            'version': NETWISE_VERSION,
            'release': NETWISE_RELEASE,
            'inumber': NETWISE_INUMBER,
        }))

    def getDocbaseMap(self):
        return DocbaseMap(
            buffer=self.requestObject(req.docbaseMap(version, handle))
        )

    def getServerMap(self, docbase):
        servermap = DocbaseMap(buffer=self.requestObject(req.serverMap(version, handle, docbase)))
        if not 'r_host_name' in servermap:
            raise RuntimeError("No servers for docbase %s on %s" % (docbase, parseAddr(servermap['i_host_addr'])))
        return servermap

    def requestObject(self, data):
        try:
            result = self.request(type=1, data=[data], immediate=True).receive().next()
        finally:
            self.disconnect()
        return result
