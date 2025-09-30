from vpw import *
from enum import IntEnum

class BlockId(IntEnum):
    vin1 = 0x01
    vin2 = 0x02
    vin3 = 0x03
    osid = 0x0A

class Pcm:
    '''
    P01 PCM specific functions
    '''
    def __init__(self, device, **kwargs):
        self.device = device

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

        seed = seed_response.data[1:3]
        swap = seed[1] << 8 | seed[0] # swap bytes
        key = (0x1934D - swap).to_bytes(3)[1:]

        unlock_request = VPWMessage(
            Priority.node2node,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            bytes((0x02, *key)) # send key
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

        if response.data[0] != block_id: raise Exception('unexpected block_id in response')