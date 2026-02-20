from utils import *
from enum import IntEnum
import logging
import warnings

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='debug.log',
    filemode='w',
    level=logging.DEBUG
)

class Priority(IntEnum):
    '''
    First byte of 3 byte header defines message priority and type
    See SAE J2178-1 section 7.2

    bits 7,6,5:  priority (0-7)
    bit 4:       H=0 (3 byte header)
    bit 3:       IFR (1=not allowed 0=required)
    bit 2:       addressing Mode (1=physical 0=functional)
    bit 1,0:     Message Type

    high nibble (prioriry) = $0=0 $2=1 $4=2 $6=3 $8=4 $A=5 $C=6 $E=7
    low nibble defines 16 message types (SAE J1278/1 7.2.1.5)
    IFR required:           $0-3=functional, $4-7=physical
    IFR not allowed (GM):   $8-B=functional, $C-F=physical
    '''
    functional0 = 0x68
    physical0 = 0x6C

class FunctionalAddress(IntEnum):
    request_legislated = 0x6A
    response_legislated = 0x6B

class PhysicalAddress(IntEnum):
    scantool = 0xF1
    pcm = 0x10
    broadcast = 0xFE

class Mode(IntEnum):
    read_block = 0x3C
    write_block = 0x3B
    unlock = 0x27
    get_pid = 0x22
    get_address = 0x23
    dpid_config = 0x2C
    dpid_request = 0x2A
    download_request = 0x34
    data_transfer = 0x36
    test_device_present = 0x3F
    general_response = 0x7F

class DataRate(IntEnum):
    '''
    1 byte value representing how data should be returned
    See SAE J2190 section 5.10
    Applies to modes $21-$23, $2A, and probably others
    '''
    single_response = 0x01
    repeat_slow = 0x02
    repeat_medium = 0x03
    repeat_fast = 0x04
    stop_transmission = 0x00

class VpwException(Exception):
    '''Base exception for VPW message errors'''

class SecurityException(VpwException):
    '''Raised when secure mode is requested while PCM is locked'''

class VpwMessage:
    '''SAE J1850-VPW message'''

    def __init__(self, priority: int, target_address: int, source_address: int, mode: int, request: bytes | int, data=b'', **kwargs):
        self.priority = priority
        self.target_address = target_address
        self.source_address = source_address
        self.mode = mode
        self.request = get_bytes(request) # request bytes expected in response
        self.data = get_bytes(data) # data bytes or bytes that won't be in response

        # 3 byte header SAE J1278/1 section 5.4
        self.header = bytes((self.priority, self.target_address, self.source_address))

        # construct message
        self.bytes = bytes((self.mode, *self.request, *self.data))
        self.hexstr = self.bytes.hex()
    
    def __repr__(self):
        return self.hexstr

    def validate_response(self, response):
        '''Raise exception for invalid responses'''

        logger.debug(f'validating response: {message.hexstr}')

        # response priority should probably match request priority
        if response.priority != self.priority:
            warnings.warn('unexpected priority')

        if response.target_address != self.source_address:
            raise VpwException('invalid target address')

        if response.source_address != self.target_address:
            raise VpwException('invalid source address')
        
        # valid response modes are 0x33 or 0x40 + request mode
        if response.mode != self.mode + 0x40 and response.mode != Mode.general_response:
            raise VpwException('invalid mode')

        # secure access mode requested while PCM is locked
        if response.mode == Mode.general_response and response.data[-1] == 0x33:
            raise SecurityException('access denied')

        # PCM should echo request
        if response.request != self.request:
            raise VpwException('invalid request')

class Parameter():
    '''Diagnostic data parameter defined by PID (2 bytes) or Memory Address (3 bytes)'''

    def __init__(self, name, parameter: int | tuple[int, ...] | bytes, n_bytes: int, **kwargs):
        self.bytes = get_bytes(parameter)
        self.n_bytes = n_bytes # number of response data bytes
        self.name = name # display name
        self.decoder = kwargs.pop('decoder', None) # function to parse response

        if not 2 <= len(parameter) <= 3: raise ValueError('invalid parameter')

    def __bytes__(self):
        return self.bytes

    def __len__(self):
        return len(self.bytes)

    def decode(self, data):
        if self.decoder is None:
            return data.hex()
        
        return self.decoder(data)

    def get_request(self, **kwargs):
        '''Generate parameter request message'''

        priority = kwargs.pop('priority', Priority.physical0)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)
        rate = kwargs.pop('rate', DataRate.single_response)

        if len(self.bytes) == 2:
            mode = Mode.get_pid

        elif len(self.bytes) == 3:
            mode = Mode.get_address

        message = VpwMessage(
            priority,
            target_address,
            source_address,
            mode,
            self.bytes,
            rate
        )

        return message

    def __eq__(self, other):
        return self.bytes == other.bytes

class Dpid():
    '''Diagnostic Data Packet'''

    def __init__(self, dpid: int, parameters: list[Parameter, ...]):
        self.id = dpid
        self.parameters = parameters

        if 0 > dpid > 255: raise ValueError('invalid DPID')

        self.request = self.get_request()

    def __index__(self):
        return self.id

    def __bytes__(self):
        return bytes([self.id])

    def get_request(self, **kwargs):
        '''Generate DPID request message'''

        priority = kwargs.pop('priority', Priority.physical0)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)
        rate = kwargs.pop('rate', DataRate.single_response)

        request = VpwMessage(
            priority,
            target_address,
            source_address,
            Mode.dpid_request,
            self.id,
            rate
        )

        return request

    def get_config(self, **kwargs) -> list[VpwMessage]:
        '''
        Generate list of VPW messages to configure the data packet. Each message adds one parameter.
        See SAE J2190 5.19
        '''

        priority = kwargs.pop('priority', Priority.physical0)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)

        config_messages = []

        # SAE J2190 5.19.2: starting byte for data, where 001 is the first byte after DPID number
        # In other words, the index for each parameter in response packet
        start_byte = 0b001

        for param in self.parameters:
            # define by PID (2 bytes)
            if len(param) == 2:
                byte3 = 0b01 << 6 | start_byte << 3 | param.n_bytes

            # define by memory address (3 bytes)
            elif len(param) == 3:
                byte3 = 0b10 << 6 | start_byte << 3 | param.n_bytes
            
            # add size of parameter to start_byte
            start_byte += param.n_bytes

            # generate message for adding parameter to DPID
            data = bytes((byte3, *param.bytes))
            config_messages.append(
                VpwMessage(
                    priority,
                    target_address,
                    source_address,
                    Mode.dpid_config,
                    self.id,
                    data
                ))

        return config_messages

    def read_parameters(self, message):
        '''Read parameters from a DPID response. Returns dict of parameters with values'''

        values = dict.fromkeys(self.parameters, None)
        read_byte = 0
        for param in values:
            data = message.data[read_byte: read_byte + param.n_bytes]
            values[param] = param.decode(data)
            read_byte += param.n_bytes

            logger.debug(f'parameter={param.name} value={data.hex()}')

        return values

class Dtc():
    '''Diagnostic Trouble Code'''