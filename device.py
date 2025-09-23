import serial
from utils import *
from queue import Queue

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


    def send_cmd(self, cmd: str, prompt_char=b'>') -> str:
        '''
        send a command and return list of response lines
        '''
        cmd = cmd + '\r'
        cmd = cmd.encode('ASCII')

        self.port.write(cmd)

        # read from serial port until prompt char is recieved or timeout
        buf = self.port.read_until(prompt_char)
        
        if len(buf) == 0:
            raise Exception('no data recieved')

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

    def send_message(self, message) -> bytes:
        '''
        send a VPWMessage
        returns response data bytes
        '''
        if self.header != message.header:
            self.set_header(message.header)

        lines = self.send_cmd(message.hexstr)

        vpw_frames = []
        for line in lines:
            if is_hex(line):
                frame = bytes.fromhex(line)[3:] # convert to bytes and remove header bytes

                if frame[0] != (message.mode + 0x40): # response mode should = message mode + $40
                    raise Exception(f'invalid frame: {line}')

                vpw_frames.append(frame)

        if len(vpw_frames) == 0:
            raise Exception('no VPW frames in response')

        if len(vpw_frames) > 1: # multiline response
            data = []
            for frame in vpw_frames:
                data.append(frame)
            
        else:
            data = vpw_frames[0][1:]

        # print(data.hex())

        return data