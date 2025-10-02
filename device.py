import serial
from vpw import *
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='debug.log',
    filemode='w',
    level=logging.DEBUG
)

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
        logger.debug(f'protocol set: {protocol}')

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
        lines = [i.strip() for i in string.split('\r') if len(i) != 0] # seperate lines, strip whitespace, remove empty lines

        return lines

    def set_header(self, header: bytes):
        lines = self.send_command(f'ATSH {header.hex()}')

        if 'OK' not in lines: raise Exception('header not set')

        self.header = header
        logger.debug(f'header set: {header}')

    def send_message(self, message: VPWMessage) -> VPWMessage:
        if self.header!= message.header:
            self.set_header(message.header)

        response = self.send_command(message.hexstr)
        data_frames = []

        for line in response:
            try:
                frame = bytes.fromhex(line)
            except ValueError:
                logger.error(f'received non-hex data: {line}')
                continue

            data_frames.append(frame)

        if len(data_frames) == 0: raise Exception('no data')

        data_start = 4 + len(message.request)
        request = data_frames[0][4:data_start] 

        if len(data_frames) == 1:
            data = data_frames[0][data_start:]
 
        else: # multiline response
            data = bytearray(request)
            i = 1 # data index starts at 1 per ELM327 docs
            for frame in data_frames:
                logger.debug(f'processing multiline data: frame={frame} index={i}')

                if not frame.startswith(data_frames[0][:data_start]):
                    logger.error(f'invalid initial bytes')
                    continue

                if frame[data_start] != i: 
                    logger.error('invalid index')
                    continue

                data.extend(frame[data_start + 1:])
                i += 1

            if len(data) <= len(request): raise Exception('could not assemble multiline response')

        logger.debug(f'received data: {data.hex()}')

        return VPWMessage(
            data_frames[0][0], # priority
            data_frames[0][1], # target address
            data_frames[0][2], # source address
            data_frames[0][3], # mode
            request,
            data
        )