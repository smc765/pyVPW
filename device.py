import serial
from utils import *
from vpw import *
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='debug.log', filemode='w')
logger.setLevel(logging.DEBUG)

class ELM327:
    '''
    Handles serial communication with scan tools using ELM327 command set
    '''
    def __init__(self, port, baudrate, timeout=1, **kwargs):
        self.port = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=serial.PARITY_NONE,
            stopbits=1,
            bytesize=8,
            timeout=timeout
        )

        self.header = None # current header
        self.protocol = None # current protocol
        
        # initalize device
        self.send_command('AT Z') # reset
        self.send_command('AT E0') # disable echo
        self.send_command('AT S0') # disable spaces
        self.send_command('AT H1') # display headers
        self.set_protocol(2) # protocol 2 = SAE J1850 VPW

    def set_protocol(self, protocol: int):
        lines = self.send_command(f'AT SP {protocol}')

        if 'OK' not in lines: raise Exception('protocol not set')

        self.protocol = protocol
        logger.debug(f'Protocol Set: {protocol}')

    def send_command(self, cmd: str, prompt_char=b'>') -> list[str]:
        logger.debug(f'TX: {cmd}')
        cmd = cmd + '\r'
        cmd = cmd.encode('ASCII')
        self.port.write(cmd)

        # read from serial port until prompt char is recieved or timeout
        buf = self.port.read_until(prompt_char)
        logger.debug(f'RX: {buf}')
        
        if len(buf) == 0: raise Exception('no data received')

        # remove prompt char
        if buf.endswith(prompt_char):
            buf = buf[:-1]

        string = buf.decode('ASCII')
        lines = [i.strip() for i in string.split('\r') if len(i) != 0] # seperate lines, strip whitespace, and remove empty lines

        return lines    

    def set_header(self, header: bytes):
        lines = self.send_command(f'ATSH {header.hex()}')

        if 'OK' not in lines: raise Exception('header not set')

        self.header = header
        logger.debug(f'Header Set: {header}')

    def send_message(self, message: VPWMessage) -> VPWMessage:
        if self.header!= message.header:
            self.set_header(message.header)

        response = self.send_command(message.hexstr)
        data_frames = []

        for line in response:
            logger.debug(f'validating line: {line}')
            try:
                frame = bytes.fromhex(line)
            except ValueError:
                logger.error(f'line contains non-hex data')
                continue

            if frame[0] != message.priority:
                logger.warning('unexpected priority')

            if frame[1] != message.source_address:
                logger.error('unexpected target address')
                continue

            if frame[2] != message.target_address:
                logger.error('unexpected source address')
                continue

            if frame[3] != message.mode + 0x40:
                logger.error('unexpected mode')
                continue

            if frame[4] != message.data[0]:
                logger.error('unexpected request byte')
                continue

            data_frames.append(frame)

        if len(data_frames) == 0: raise Exception('no valid data received')

        if len(data_frames) == 1:
            data = data_frames[0][4:]
 
        else: # multiline response
            data = bytearray([data_frames[0][4]]) # request byte
            for i, frame in enumerate(data_frames, start=1):
                if frame[5] != i: 
                    logger.error(f'multiline index error frame {i}')
                    continue
                data.extend(frame[6:])

            if len(data) <= 1: raise Exception('could not assemble multiline response')

        return VPWMessage(
            data_frames[0][0],
            data_frames[0][1],
            data_frames[0][2],
            data_frames[0][3],
            data
        )