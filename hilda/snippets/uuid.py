from construct import *


class UUIDStructFactory(object):
    @staticmethod
    def uuid_t():
        return Struct(
            'time_low' / Int64ul,
            'time_mid' / Int32ul,
            'time_hi_and_version' / Int32ul,
            'clock_seq_hi_and_reserved' / Int8ul,
            'clock_seq_low' / Int8ul,
            'node' / Array(6, Int8ul)
        )
