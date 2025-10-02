from utils import *
from enum import IntEnum
import logging

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
    node2node = 0x6C

class FunctionalAddress(IntEnum):
    request_legislated = 0x6A
    response_legislated = 0x6B

class PhysicalAddress(IntEnum):
    scantool = 0xF1
    pcm = 0x10

class Mode(IntEnum):
    read_block = 0x3C
    unlock = 0x27
    get_pid = 0x22
    get_address = 0x23
    dpid_config = 0x2C
    dpid_request = 0x2A
    download_request = 0x34
    data_transfer = 0x36

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

class VPWMessage:
    '''
    SAE J1850-VPW message
    '''
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

    # todo: this should return something to indicate what went wrong
    def validate_response(self, message) -> bool:
        logger.debug(f'validating response: {message.hexstr}')

        if message.priority != self.priority:
            logger.warning('unexpected priority')
            # response priority doesn't have to match request

        if message.target_address != self.source_address:
            logger.error('unexpected target address')
            return False

        if message.source_address != self.target_address:
            logger.error('unexpected source address')
            return False
        
        if message.mode != self.mode + 0x40:
            logger.error('unexpected mode')
            return False

        if message.request != self.request:
            logger.error('unexpected request')
            return False

        return True

class Parameter():
    '''
    Diagnostic data parameter defined by PID (2 bytes) or Memory Address (3 bytes)
    '''
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
        priority = kwargs.pop('priority', Priority.node2node)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)
        rate = kwargs.pop('rate', DataRate.single_response)

        if len(self.bytes) == 2:
            mode = Mode.get_pid

        elif len(self.bytes) == 3:
            mode = Mode.get_address

        message = VPWMessage(
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
    '''
    Diagnostic Data Packet
    '''
    def __init__(self, dpid: int, parameters: list[Parameter, ...]):
        self.id = dpid
        self.parameters = parameters
        self.request = self.get_request()

    def __index__(self):
        return self.id

    def __bytes__(self):
        return bytes([self.id])

    def get_request(self, **kwargs):
        '''
        Generate request message
        '''
        priority = kwargs.pop('priority', Priority.node2node)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)
        rate = kwargs.pop('rate', DataRate.single_response)

        request = VPWMessage(
            priority,
            target_address,
            source_address,
            Mode.dpid_request,
            self.id,
            rate
        )

        return request

    def get_config(self, **kwargs) -> list[VPWMessage]:
        '''
        Generate list of configuration messages
        See SAE J2190 5.19.3
        '''
        priority = kwargs.pop('priority', Priority.node2node)
        target_address = kwargs.pop('target_address', PhysicalAddress.pcm)
        source_address = kwargs.pop('source_address', PhysicalAddress.scantool)

        config_messages = []
        start_byte = 0b001 # starting byte for data, where 001 is the first byte after the DPID #

        for param in self.parameters:
            # define by PID (2 bytes)
            if len(param) == 2:
                byte3 = 0b01 << 6 | start_byte << 3 | param.n_bytes

            # define by memory address (3 bytes)
            elif len(param) == 3:
                byte3 = 0b10 << 6 | start_byte << 3 | param.n_bytes
            
            start_byte += param.n_bytes

            data = bytes((byte3, *param.bytes))
            config_messages.append(
                VPWMessage(
                    priority,
                    target_address,
                    source_address,
                    Mode.dpid_config,
                    self.id,
                    data
                ))

        return config_messages

    def read_parameters(self, message) -> list[int]:
        if not self.request.validate_response(message):
            raise Exception('invalid response message')

        values = []
        read_byte = 0
        for param in self.parameters:
            data = message.data[read_byte: read_byte + param.n_bytes]
            values.append(param.decode(data))
            read_byte += param.n_bytes
            logger.debug(f'parameter={param.name} value={data.hex()}')

        return values

    def read_parameter(self, message, search_parameter):
        values = self.read_parameters(message)
        for i, value in enumerate(values):
            if self.parameters[i] == search_parameter:
                return value