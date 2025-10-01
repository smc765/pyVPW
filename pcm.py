from vpw import *
from enum import IntEnum
from utils import *

class BlockId(IntEnum):
    vin1 = 0x01
    vin2 = 0x02
    vin3 = 0x03
    osid = 0x0A

class Pcm:
    def __init__(self, device, pcm_type, **kwargs):
        self.device = device
        self.pcm_type = pcm_type

        match pcm_type:
            case 'p01':
                self.key_algorithm = [36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40]

            case 'p04':
                self.key_algroithm = [4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203]

    def get_key(self, seed: int, algorithm=self.key_algorithm) -> int:
        key = seed

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

        return key & 0xFFFF

    def unlock(self):
        seed_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            bytes([0x01]) # request seed
        )

        seed_response = self.device.send_message(seed_request)

        if seed_response.data[2] == 0x37: # already unlocked
            return True

        seed = int.from_bytes(seed_response.data[1:3])
        key = self.get_key(seed)

        unlock_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            bytes((0x02, *key.to_bytes(2))) # send key
        )

        unlock_response = self.device.send_message(unlock_request)

        if unlock_response.data[1] == 0x34: # success
            return True
        
        return False

    def read_block(self, block_id: int) -> bytes:
        read_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.read_block,
            bytes([block_id])
        )

        response = self.device.send_message(read_request)
        if responce.data[0] != block_id: raise Exception('unexpected block_id')

        return response.data[1:]

    def write_block(self, block_id: int, data: bytes):
        write_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.write_block,
            bytes((block_id, *data))
        )

        if self.unlock():
            response = self.device.send_message(write_request)
        else:
            raise Exception('pcm not unlocked')

        if response.data[0] != block_id: raise Exception('unexpected block_id')