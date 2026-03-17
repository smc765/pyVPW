import serial
from enum import IntEnum
from .vpw import VpwMessage
from .exceptions import DeviceException

import logging
logger = logging.getLogger(__name__)

ELM_PROMPT = b'>'

class Device:
    '''scantool base class'''

    def set_header(self, header: bytes):
        raise NotImplementedError('this is only implemented in derived classes')

    def send_command(self, command: str, num_lines: int | None = None) -> list[str]:
        raise NotImplementedError('this is only implemented in derived classes')

    def send_message(self, message: VpwMessage, num_lines: int | None = None) -> list[VpwMessage]:
        '''send VpwMessage and return responses'''

        if self._header != message.get_header():
            self.set_header(message.get_header())

        response = self.send_command(repr(message), num_lines)

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

            # TODO validate checksum here, maybe check mode/submode too?
            
            if response_message.mode != message.mode + 0x40:
                logger.warning('unexpected response mode')

            messages.append(response_message)

        if len(messages) == 0:
            raise DeviceException('no valid data received')

        return messages

class ElmProtocol(IntEnum):
    '''ELM327 protocols'''
    auto = 0
    j1850vpw = 2

class Elm327(Device):
    '''handles serial communication with ELM327 scantools'''

    def __init__(self, portname: str, **kwargs):
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

        self.set_protocol(
            kwargs.pop('protocol', ElmProtocol.j1850vpw))
        
        self._header = None # current message header

    def send_command(self, command: str, num_lines: int | None = None) -> list[str]:
        '''
        send command and wait for response(s)
        num_lines should not be used to ignore messages
        ignored messages remain in elm buffer and may be treated as responses to subsequent commands
        num_lines = None -> read unitl elm timeout
        '''
        logger.debug(f'TX: {command}')

        if num_lines:
            command = command + str(num_lines) + '\r'
        else:
            command = command + '\r'

        self._port.write(command.encode('ASCII'))

        # read from serial port until ELM_PROMPT or timeout
        buffer = self._port.read_until(ELM_PROMPT)

        if len(buffer) == 0:
            raise DeviceException('no data')

        assert buffer.endswith(ELM_PROMPT)
        buffer = buffer[:-1]

        # decode buffer, split lines, remove empty lines, remove whitespace 
        string = buffer.decode('ASCII')
        lines = [line.strip() for line in string.split('\r') if line]

        logger.debug(f'RX: {lines}')

        if '?' in lines:
            raise DeviceException('invalid message')

        if num_lines and (len(lines) != num_lines):
            raise DeviceException(f'expected {num_lines} responses but received {len(lines)}')

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