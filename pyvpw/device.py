import serial
from enum import IntEnum
from .utils import *
from .vpw import *

import logging
logger = logging.getLogger(__name__)

ELM_PROMPT = b'>'

class DeviceException(Exception):
    '''raised for scantool errors'''

class Device:
    '''scantool base class'''

    def set_header(self, header: bytes):
        raise NotImplementedError('this is only implemented in derived classes')

    def send_command(self, command: str) -> list[str]:
        raise NotImplementedError('this is only implemented in derived classes')

    def send_message(self, message: VpwMessage) -> list[VpwMessage]:
        '''send VpwMessage and return responses'''

        if self._header != message.get_header():
            self.set_header(message.get_header())

        response = self.send_command(repr(message))

        data_frames = []
        for line in response:
            try:
                data_frames.append(bytes.fromhex(line))
            except ValueError:
                logger.warning(f'non-hex data: {line}')

        data_start = 4 + len(message.submode)
        messages = []
        for frame in data_frames:
            try:
                response_message = VpwMessage(
                    frame[0], # priority
                    frame[1], # target address
                    frame[2], # source address
                    frame[3], # mode
                    frame[4:data_start], # submode
                    frame[data_start:-1] # data
                )

                crc = frame[-1] # checksum

            except IndexError:
                logger.warning(f'invalid frame: {frame.hex()}')

            #TODO: validate checksum here, maybe check mode/submode too?
            
            if response_message.mode != message.mode + 0x40:
                logger.warning(f'unexpected response mode')

            messages.append(response_message)

        if len(messages) == 0:
            raise DeviceException('no valid data')

        return messages

class ElmProtocol(IntEnum):
    '''ELM327 protocols'''
    auto = 0
    j1850vpw = 2

class Elm327(Device):
    '''handles serial communication with ELM327 scantools'''

    def __init__(self, portname, **kwargs):
        self._baudrate = kwargs.pop('baudrate', 115200)
        self._timeout = kwargs.pop('timeout', 1)

        self._port = serial.Serial(
            port=portname,
            baudrate=self._baudrate,
            parity=serial.PARITY_NONE,
            stopbits=1,
            bytesize=8,
            timeout=self._timeout
        )

        # initalize device
        self.send_command('AT Z') # reset
        self.send_command('AT E0') # disable echo
        self.send_command('AT S0') # disable spaces
        self.send_command('AT H1') # display headers
        self.send_command('AT AL') # allow long (>7 byte) messages
        
        self._header = None # current message header

    def send_command(self, command: str) -> list[str]:
        '''send command and wait for response'''
        
        logger.debug(f'TX: {command}')

        command = command + '\r'
        self._port.write(command.encode('ASCII'))

        # read from serial port until ELM_PROMPT or timeout
        buffer = self._port.read_until(ELM_PROMPT)

        if len(buffer) == 0:
            raise DeviceException('no data')

        # remove prompt char
        if buffer.endswith(ELM_PROMPT):
            buffer = buffer[:-1]
        else:
            logger.warning('prompt char missing')

        # decode buffer, split lines, remove empty lines, remove whitespace 
        string = buffer.decode('ASCII')
        lines = [line.strip() for line in string.split('\r') if bool(line)]

        logger.debug(f'RX: {string}')

        if '?' in lines:
            raise DeviceException('invalid message not sent')

        return lines

    def set_header(self, header: bytes):
        '''set message header'''

        if 'OK' not in self.send_command(f'ATSH {header.hex()}'):
            raise DeviceException('set header failed')

        self._header = header

    def set_protocol(self, protocol: int):
        '''set protocol'''

        if 'OK' not in self.send_command(f'ATSP{protocol}'):
            raise DeviceException('set protocol failed')