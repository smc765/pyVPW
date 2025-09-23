from enum import IntEnum
import logging
from utils import get_bytes

class Priority(IntEnum):
    '''
    First byte of 3 byte header defines message priority and type
    See SAE J2178-1 section 7.2

    bits 7,6,5:  priority (0-7)
    bit 4:       H=0 (3 byte header)
    bit 3:       IFR (1=not allowed 0=required)
    bit 2:       Addressing Mode (1=physical 0=functional)
    bit 1,0:     Message Type

    high nibble (prioriry) = $0=0 $2=1 $4=2 $6=3 $8=4 $A=5 $C=6 $E=7
    low nibble defines 16 message types (SAE J1278/1 7.2.1.5)
    IFR required:           $0-3=functional, $4-7=physical
    IFR not allowed (GM):   $8-B=functional, $C-F=physical
    '''
    functional0 =  0x68 # used for mode $01 (and maybe $02-0A) requests
    node2node  =  0x6C

class Rate(IntEnum):
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


class Parameter():
    '''
    Diagnostic data parameter defined by:
     - Offset:         1 byte
     - PID:            2 bytes
     - Memory Address: 3 bytes
    '''
    def __init__(self, name, parameter: int | tuple[int, int] | tuple[int, int, int] | bytes, n_bytes: int, **kwargs):
        self.bytes = get_bytes(parameter)
        self.n_bytes = n_bytes # number of response data bytes
        self.name = name # display name
        self.decoder = kwargs.pop('decoder', None) # function to parse response

        if len(self.bytes) > 3:
            raise ValueError('Parameter too long')

    def __bytes__(self):
        return self.bytes

    def __len__(self):
        return len(self.bytes)

    def get_request(self, **kwargs):
        priority = kwargs.pop('priority', Priority.node2node)
        target_addr = kwargs.pop('target_addr', 0x10) # physical address of PCM
        rate = kwargs.pop('rate', Rate.single_response)

        if len(self.bytes) == 1:
            mode = 0x21

        elif len(self.bytes) == 2:
            mode = 0x22

        elif len(self.bytes) == 3:
            mode = 0x23

        data = bytes((*self.bytes, rate))

        request = VPWMessage(
            priority,
            target_addr,
            mode,
            data
        )

        return request


class VPWMessage:
    '''
    base class for SAE J1850 VPW messages
    '''
    def __init__(self, priority: int, target_addr: int, mode: int, data: bytes, **kwargs):
        self.priority = priority
        self.target_addr = target_addr
        self.mode = mode
        self.data = data

        # physical address of scan tool. shouldn't need to change this
        self.source_addr = kwargs.pop('source_addr', 0xF1)

        # 3 byte header SAE J1278/1 section 5.4
        self.header = get_bytes(kwargs.pop(
            'header', (self.priority, self.target_addr, self.source_addr)))

        # construct message
        self.bytes = bytes((self.mode, *self.data))
        self.hexstr = self.bytes.hex()
    
    def __repr__(self):
        '''
        return request as hex string
        '''
        return self.hexstr

    def __bytes__(self):
        '''
        return request bytes
        '''
        return self.bytes


class Dpid():
    '''
    Diagnostic Data Packet (DPID)
    '''
    def __init__(self, id: int, parameters: list[Parameter, ...]):
        self.id = id
        self.parameters = parameters

    def __index__(self):
        return self.id

    def __bytes__(self):
        return bytes([self.id])

    def get_request(self, **kwargs):
        '''
        Generate request message
        '''
        priority = kwargs.pop('priority', Priority.node2node)
        target_addr = kwargs.pop('target_addr', 0x10) # physical address of PCM
        rate = kwargs.pop('rate', Rate.single_response)

        data = bytes((self.id, rate))

        request = VPWMessage(
            priority,
            target_addr,
            0x2A, # mode $2A
            data
        )

        return request

    def get_config(self, **kwargs):
        '''
        Generate list of configuration messages
        See SAE J2190 5.19.3
        '''
        priority = kwargs.pop('priority', Priority.node2node)
        target_addr = kwargs.pop('target_addr', 0x10)

        config = []
        start_byte = 0b001 # starting byte for data, where 001 is the first byte after the DPID #

        for param in self.parameters:
            # define by offset (1 byte)
            if len(param) == 1:
                byte3 = 0b00 << 6 | start_byte << 3 | param.n_bytes # [bits 7,6,5=param type][bits 4,3,2=start_byte][bits 2,1,0=n_bytes]

            # define by PID (2 bytes)
            elif len(param) == 2:
                byte3 = 0b01 << 6 | start_byte << 3 | param.n_bytes

            # define by memory address (3 bytes)
            elif len(param) == 3:
                byte3 = 0b10 << 6 | start_byte << 3 | param.n_bytes
            
            start_byte += param.n_bytes

            data = bytes((self.id, byte3, *param.bytes))
            config.append(
                VPWMessage(
                    priority,
                    target_addr,
                    0x2C, # mode $2C
                    data
                ))

        return config

    def get_param(self, data: bytes, parameter) -> int:
        '''
        extract a parameter from response
        '''
        if data[0] != self.id: raise Exception('this aint me')

        read_byte = 1 # first data byte to read
        for p in self.parameters:
            if p == parameter: 
                return data[read_byte:read_byte + p.n_bytes]

            read_byte += p.n_bytes


def main():
    pass
    p1 = Parameter((0x01,0x04), 1) # pid
    p2 = Parameter(0x32, 2) # offset
    p3 = Parameter((0x24,0x81,0x70), 2) # memory address
    dpid = Dpid(0x26, [p1,p2,p3]) # dpid $26
    print(dpid.get_config())
    print(p3.get_request())

if __name__ == '__main__':
    main()