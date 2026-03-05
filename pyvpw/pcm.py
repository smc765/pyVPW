from enum import Enum, IntEnum, auto

class PcmType(Enum):
    p01 = auto(), (36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40)
    p04 = auto(), (4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203)

    @property
    def seedkey_algorithm(self):
        return SEEDKEY_ALGORITHM[self]

    @classmethod
    def from_osid(cls, osid):
        return OSID_LOOKUP[osid]

class BlockId(IntEnum):
    vin1 = 0x01 # 0x00, first 5 bytes
    vin2 = 0x02
    vin3 = 0x03
    osid = 0x0A

SEEDKEY_ALGORITHM = {
    PcmType.p01: (36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40),
    PcmType.p04: (4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203),
}

OSID = {
    PcmType.p01: {
        12212156,
    },
    PcmType.p04: {
        9384022,
    },
}

OSID_LOOKUP = {key: value for value, keys in OSID.items() for key in keys}