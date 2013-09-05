#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy.netwise import Netwise
from dctmpy.obj.docbroker import DocbaseMap
from dctmpy.req import *

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
            rawdata=self.requestObject(requestDocbaseMap(version, handle))
        )

    def getServerMap(self, docbase):
        return DocbaseMap(
            rawdata=self.requestObject(requestServerMap(version, handle, docbase))
        )

    def requestObject(self, data):
        try:
            result = self.request(type=1, data=[data], immediate=True).receive().next()
        finally:
            self.disconnect()
        return result
