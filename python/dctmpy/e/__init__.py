#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#


class ParserException(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(ParserException, self).__init__(*args, **kwargs)


class ProtocolException(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(ProtocolException, self).__init__(*args, **kwargs)