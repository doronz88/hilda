from construct import Struct, Int64ul, Int32ul, Int8ul, Array

uuid_t = Struct(
    'time_low' / Int64ul,
    'time_mid' / Int32ul,
    'time_hi_and_version' / Int32ul,
    'clock_seq_hi_and_reserved' / Int8ul,
    'clock_seq_low' / Int8ul,
    'node' / Array(6, Int8ul)
)
