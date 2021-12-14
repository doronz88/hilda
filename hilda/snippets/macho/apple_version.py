from construct import BitStruct, Octet, BitsInteger

version_t = BitStruct(
    'major' / BitsInteger(16),
    'minor' / Octet,
    'bug' / Octet
)
