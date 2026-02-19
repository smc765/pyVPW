from vpw import *
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='debug.log',
    filemode='w',
    level=logging.DEBUG
)

class BlockId(IntEnum):
    vin1 = 0x01 # 0x00, first 5 bytes
    vin2 = 0x02 # next 6 bytes
    vin3 = 0x03 # last 6 bytes
    osid = 0x0A # operating system id

class PcmUnlockException(Exception):
    '''Raised when unlock fails'''

class Pcm:
    def __init__(self, device, pcm_type='p01', **kwargs):
        self.device = device

        match pcm_type:
            case 'p01':
                # unlock algorithms from stgterm.dat in GM software
                self.key_algorithm = [36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40]

            case 'p04':
                self.key_algroithm = [4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203]

    def get_key(self, seed: bytes, algorithm=self.key_algorithm) -> bytes:

        if len(seed) != 2: raise ValueError('seed must be 2 bytes')

        key = int.from_bytes(seed)

        for i in range(1, 13, 3): # operations defined by every 3rd byte starting at index 1
            high = algorithm[i+1] # next 2 bytes are the operands
            low = algorithm[i+2]

            match algorithm[i]: # match operand
                case 0x14:
                    # add HHLL to key
                    key += high << 8 | low

                case 0x2A:
                    if high > low:
                        key = ~key # 1's complement
                    else:
                        key = ~key + 1 # 2's complement

                case 0x4C:
                    # rotate key left by HH bits
                    key = (key << high | key >> (16 - high)) & 0xFFFF

                case 0x6B:
                    # rotate key right by LL bits
                    key = (key >> low | key << (16 - low)) & 0xFFFF

                case 0x7E:
                    # swap bytes of key, if LL>HH add LLHH, else add HHLL
                    key = (key & 0xFF) << 8 | (key & 0xFF00) >> 8
                    if low > high:
                        key += low << 8 | high
                    else:
                        key += high << 8 | low

                case 0x98:
                    # subtract HHLL from key
                    key -= high << 8 | low

                case _:
                    continue

        key = key & 0xFFFF # truncate to 2 bytes
        return key.to_bytes(2)

    def unlock(self):

        seed_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            0x01 # request seed
        )

        seed_response = self.device.send_message(seed_request)

        if seed_response.data[0] == 0x37: return # PCM is already unlocked

        seed = seed_response.data
        key = self.get_key(seed)
        
        logger.debug(f'received seed: {seed}')
        logger.debug(f'sending key: {key}')

        unlock_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            0x02, # send key
            key
        )

        response_code = self.device.send_message(unlock_request).data[0]

        match response_code:
            case 0x34: # key accepted
                return

            case 0x34:
                raise PcmUnlockException('access denied')

            case 0x35:
                raise PcmUnlockException('key not accepted')

            case 0x36:
                raise PcmUnlockException('too many unlock attempts')

            case 0x37:
                raise PcmUnlockException('time delay not expired')

    def read_block(self, block_id: int) -> bytes:

        read_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.read_block,
            block_id
        )

        response = self.device.send_message(read_request)
        return response.data

    def write_block(self, block_id: int, data: bytes):
        '''Write data block. PCM must be unlocked'''

        write_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.write_block,
            block_id,
            data
        )

        self.device.send_message(write_request)

    def get_osid(self) -> int:

        osid_bytes = read_block(BlockId.osid)
        return int.from_bytes(osid_bytes)

    def get_vin(self) -> str:

        vin1 = self.read_block(BlockId.vin1)
        vin2 = self.read_block(BlockId.vin2)
        vin3 = self.read_block(BlockId.vin3)

        vin_bytes = bytes((*vin1[1:], *vin2, *vin3))

        return vin_bytes.decode('ASCII')

    def write_vin(self, vin: str):

        if len(vin) != 17: raise ValueError('VIN must be 17 characters')

        vin_bytes = vin.encode('ASCII')

        self.write_block(BlockId.vin1, bytes((0x00, *vin_bytes[:5]))) # first byte is 0x00
        self.write_block(BlockId.vin2, vin_bytes[5:11])
        self.write_block(BlockId.vin2, vin_bytes[11:])