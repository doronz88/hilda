from construct import BitsInteger, BitStruct, Octet

version_t = BitStruct(
    'major' / BitsInteger(16),
    'minor' / Octet,
    'bug' / Octet
)
