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
            **{'serializationVersion': 0}
        ))

    def map(self):
        if self.__methods is None:
            names = self.getAttrs()['name'].getValues()
            poss = self.getAttrs()['pos'].getValues()
            self.__methods = dict((names[i], poss[i]) for i in range(0, len(names)))
        return self.__methods



