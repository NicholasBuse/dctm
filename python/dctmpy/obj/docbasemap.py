#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy.obj.docbroker import DocbrokerObject


class DocbaseMap(DocbrokerObject):
    def __init__(self, **kwargs):
        super(DocbaseMap, self).__init__(**kwargs)

    def getRecords(self):
        if 'r_docbase_name' in self.getAttrs():
            return [self.getRecord(index) for index in range(0, len(self.r_docbase_name))]
        return []

    def getRecord(self, index):
        return {
            'name': self.r_docbase_name[index],
            'id': self.r_docbase_id[index],
            'description': self.r_docbase_description[index],
            'version': self.r_server_version[index],
        }
