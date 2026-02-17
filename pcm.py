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

class PcmException(Exception):
    pass

class Pcm:
    def __init__(self, device, pcm_type, **kwargs):
        self.device = device
        match pcm_type:
            case 'p01':
                self.key_algorithm = [36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40]
            case 'p04':
                self.key_algroithm = [4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203]

    def get_key(self, seed: bytes, algorithm=self.key_algorithm) -> bytes:
        key = int.from_bytes(seed)

        for i in range(1, 13, 3):
            high = algorithm[i+1]
            low = algorithm[i+2]

            match algorithm[i]:
                case 0x14:
                    # add HHLL
                    key += high << 8 | low

                case 0x2A:
                    if high > low:
                        key = ~key
                    else:
                        key = ~key + 1

                case 0x4C:
                    # rotate left by HH bits
                    key = (key << high | key >> (16 - high)) & 0xFFFF

                case 0x6B:
                    # rotate right by LL bits
                    key = (key >> low | key << (16 - low)) & 0xFFFF

                case 0x7E:
                    # swap bytes of key, if LL>HH add LLHH, else add HHLL
                    key = (key & 0xFF) << 8 | (key & 0xFF00) >> 8
                    if low > high:
                        key += low << 8 | high
                    else:
                        key += high << 8 | low

                case 0x98:
                    # subtract HHLL
                    key -= high << 8 | low

                case _:
                    continue

        key = key & 0xFFFF
        return key.to_bytes(2)

    def unlock(self) -> bool:
        seed_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            0x01 # request seed
        )

        seed_response = self.device.send_message(seed_request)

        if not seed_request.validate(seed_response):
            raise PcmException('invalid seed response')

        if seed_response.data[0] == 0x37: # already unlocked
            return True

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

        unlock_response = self.device.send_message(unlock_request)

        if not unlock_request.validate(unlock_response):
            return False

        match unlock_response.data[0]:
            case 0x34: # key accepted
                return True
            case 0x34: 
                logger.error('access denied')
            case 0x35:
                logger.error('invalid key')
            case 0x36:
                logger.error('too many attempts')
            case 0x37:
                logger.error('time delay not expired')

        return False

    def read_block(self, block_id: int) -> bytes:
        read_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.read_block,
            block_id
        )

        response = self.device.send_message(read_request)

        if not read_request.validate(read_request):
            # raise PcmException('invalid response')
            logger.error('invalid read block response')
            return b''

        return response.data

    def write_block(self, block_id: int, data: bytes) -> bool:
        write_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.write_block,
            block_id,
            data
        )

        response = self.device.send_message(write_request)

        return write_request.validate(response)

    def get_osid(self) -> int:
        osid_bytes = read_block(BlockId.osid)
        return int.from_bytes(osid_bytes)

    def get_vin(self) -> str:
        vin1 = self.read_block(BlockId.vin1)
        vin2 = self.read_block(BlockId.vin2)
        vin3 = self.read_block(BlockId.vin3)
        vin_bytes = bytes((*vin1[1:], *vin2, *vin3))

        if vin_bytes == b'':
            raise PcmException('read failed')

        return vin_bytes.decode('ASCII')

    def write_vin(self, vin: str):
        if len(vin != 17): raise ValueError('vin must be 17 characters')
        vin_bytes = vin.encode('ASCII')

        if not self.unlock():
            raise PcmException('could not unlock pcm')

        if not all((
            self.write_block(BlockId.vin1, bytes((0x00, *vin_bytes[:5]))),
            self.write_block(BlockId.vin2, vin_bytes[5:11]),
            self.write_block(BlockId.vin2, vin_bytes[11:])
        )): raise PcmException('write failed')