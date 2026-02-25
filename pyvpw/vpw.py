from .utils import *
from enum import IntEnum

class Priority(IntEnum):
    '''
    First byte of 3 byte header defines message priority and type
    See SAE J2178-1 section 7.2

    bits 7,6,5:  priority (0-7)
    bit 4:       0 = 3 byte header
    bit 3:       IFR: 1=not allowed (GM), 0=required
    bit 2:       addressing mode: 1=physical, 0=functional
    bit 1,0:     message type
    '''
    functional0 = 0x68 # priority 3, GM, functional, Type: Function Command/Status
    physical0 = 0x6C # priority 3, GM, physical, Type: Node-to-Node

class DataRate(IntEnum):
    '''
    1 byte value representing how data should be returned
    See SAE J2190 section 5.10
    Applies to modes $21-$23, $2A, and probably others
    '''
    single_response = 0x01 # this is the only one used for elm327
    repeat_slow = 0x02
    repeat_medium = 0x03
    repeat_fast = 0x04
    stop_transmission = 0x00

class PhysicalAddress(IntEnum):
    scantool = 0xF0
    pcm = 0x10
    broadcast = 0xFE

class FunctionalAddress(IntEnum):
    obd_request = 0x6A
    obd_response = 0x6B

class Mode(IntEnum):
    # SAE J1979 legislated modes
    get_pid = 0x01
    get_freeze_frame = 0x02
    get_dtc = 0x03
    clear_dtc = 0x04
    get_test_results = 0x06
    get_pending_dtcs = 0x07
    get_vehicle_info = 0x09

    # SAE J2190 modes
    read_block = 0x3C
    write_block = 0x3B
    unlock = 0x27
    get_pid_ext = 0x22
    define_dpid = 0x2C
    request_dpid = 0x2A
    download_request = 0x34
    data_transfer = 0x36
    test_device_present = 0x3F
    general_response = 0x7F

class VpwMessage:
    '''SAE J1850 VPW message'''

    def __init__(self, priority, target_address, source_address, mode, submode, data=b''):
        assert priority in range(0xFF)
        assert target_address in range(0xFF)
        assert source_address in range(0xFF)
        assert mode in range(0xFF)

        self.priority = priority
        self.target_address = target_address
        self.source_address = source_address
        self.mode = mode
        self.submode = get_bytes(submode) # submode is typically echoed in response
        self.data = get_bytes(data)

    def get_header(self) -> bytes:
        '''return message header'''
        return bytes((self.priority, self.target_address, self.source_address))

    def __bytes__(self):
        '''return message bytes'''
        return bytes((self.mode, *self.submode, *self.data))

    def __repr__(self):
        '''return hex string'''
        return bytes(self).hex()

    def __getitem__(self, index):
        return bytes(self)[index]

    def __eq__(self, other):
        return (self.get_header(), bytes(self)) == (other.get_header(), bytes(other))

class Pid:
    def __init__(self, name: str, pid: int, size: int, decoder=lambda x: x):
        self.name = name
        self.id = pid
        self.size = size # number of data bytes returned
        self.decoder = decoder
        assert pid in range(0xFFFF)

    def __bytes__(self):
        return get_bytes(self.id)

    def __eq__(self, other):
        if isinstance(other, Pid):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        elif isinstance(other, bytes):
            return bytes(self) == other
        else:
            raise NotImplementedError

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.name

class Dpid:
    def __init__(self, dpid: int, pids: list[Pid]):
        self.id = dpid
        self.pids = set(pids)
        assert dpid in range(0xFF)

    def __bytes__(self):
        return self.id.to_bytes()

    def __eq__(self, other):
        if isinstance(other, Dpid):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        elif isinstance(other, bytes):
            return bytes(self) == other
        else:
            raise NotImplementedError

    def __hash__(self):
        return hash(self.id)

    def __contains__(self, key):
        if isinstance(key, Pid):
            return key in self.pids
        elif isinstance(key, int):
            return key in [pid.id for pid in self.pids]
        elif isinstance(key, bytes):
            return key in [bytes(pid) for pid in self.pids]
        else:
            raise NotImplementedError

    def unpack(self, data: bytes) -> dict[Pid, bytes]: # should this go here?
        '''return dict of PIDs and values'''

        values = dict.fromkeys(self.pids, None)
        read_byte = 0
        for pid in values:
            values[pid] = data[read_byte: read_byte + pid.size]
            read_byte += pid.size

        return values