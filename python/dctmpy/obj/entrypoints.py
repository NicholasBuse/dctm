#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#

from dctmpy.obj.typedobject import TypedObject


class EntryPoints(TypedObject):
    def __init__(self, **kwargs):
        self.__methods = None
        super(EntryPoints, self).__init__(**dict(
            kwargs,
            **{'serializationversion': 0}
        ))

    def map(self):
        if self.__methods is None:
            if len(self) == 0:
                return {}
            names = self['name']
            poss = self['pos']
            self.__methods = dict((names[i], poss[i]) for i in range(0, len(names)))
        return self.__methods

    def __getattr__(self, name):
        if name in self.map():
            return self.map()[name]
        else:
            return super(EntryPoints, self).__getattr__(name)


