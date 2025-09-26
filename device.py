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
        self.send_cmd('AT Z') # reset
        self.send_cmd('AT E0') # disable echo
        self.send_cmd('AT S0') # disable spaces
        self.send_cmd('AT H1') # display headers
        self.set_protocol(2) # protocol 2 = SAE J1850 VPW


    def set_protocol(self, protocol: int):
        lines = self.send_cmd(f'AT SP {protocol}')

        if 'OK' not in lines: raise Exception('protocol not set')

        self.protocol = protocol
        logger.debug(f'Protocol Set: {protocol}')


    def send_cmd(self, cmd: str, prompt_char=b'>') -> list[str]:
        logger.debug(f'TX: {cmd}')
        cmd = cmd + '\r'
        cmd = cmd.encode('ASCII')
        self.port.write(cmd)

        # read from serial port until prompt char is recieved or timeout
        buf = self.port.read_until(prompt_char)
        logger.debug(f'RX: {buf}')
        
        if len(buf) == 0: raise Exception('no data recieved')

        # remove prompt char
        if buf.endswith(prompt_char):
            buf = buf[:-1]

        string = buf.decode('ASCII')
        lines = [i.strip() for i in string.split('\r') if len(i) != 0] # seperate lines, strip whitespace, and remove empty lines

        return lines


    def set_header(self, header: bytes):
        lines = self.send_cmd(f'ATSH {header.hex()}')

        if 'OK' not in lines: raise Exception('header not set')

        self.header = header
        logger.debug(f'Header Set: {header}')


    def send_message(self, message: VPWMessage) -> VPWMessage:
        if self.header!= message.header:
            self.set_header(message.header)

        response_lines = self.send_cmd(message.hex_str)
        data_frames = [bytes.fromhex(line) for line in response_lines if is_hex(line)] # filter non-hex lines
        
        if len(data_frames) == 0: raise Exception('no valid data frames recieved')
        
        # expected response values
        priority = data_frames[0][0]
        target_addr = message.source_addr
        source_addr = message.target_addr
        mode = (message.mode + 0x40)

        # validate data frames
        for frame in data_frames:
            if frame[:3] != bytes((priority, target_addr, source_addr)): raise Exception(f'unexpected header in frame: {frame}')
            if frame[3] != mode: raise Exception(f'unexpected mode in frame: {frame}')
        
        # multiline response (ELM327 Manual page 42)
        if len(data_frames) > 1:
            data = bytearray()

            for i, frame in enumerate(data_frames, start=1):
                if frame[4] != i: raise Exception(f'invalid multiline response in frame {frame}')
                data.extend(frame[5:])
                
            if len(data) == 0: raise Exception('could not assemble multiline response')

        # single line response
        else:
            data = data_frames[0][4:]

        return VPWMessage(
            priority,
            target_addr,
            source_addr,
            mode,
            data,
        )