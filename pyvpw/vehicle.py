from enum import IntEnum
import re
from .vpw import (
    VpwMessage,
    Priority,
    DataRate,
    PhysicalAddress,
    FunctionalAddress,
    Mode
)
from .seedkey import seedkey
from .exceptions import VehicleException, UnlockException
from .pcm import PcmType, BlockId

import logging
logger = logging.getLogger(__name__)

class Vehicle:
    '''SAE J1979 modes'''

    def __init__(self, device):
        self._device = device

    def get_pid(self, pid: int) -> bytes:
        '''mode $01 - request PID'''
        assert pid in range(0xFF)

        request = VpwMessage(
            Priority.functional0,
            FunctionalAddress.obd_request,
            PhysicalAddress.scantool,
            Mode.get_pid,
            pid
        )

        response = self._device.send_message(request)[0]
        return response.data

    def get_supported_pids(self) -> list[int]:
        supported = []
        pid = 1
        for byte in self.get_pid(0):
            for i in range(8):
                if (byte << i) & 0b10000000:
                    supported.append(pid)
                pid += 1
        
        return supported

    def get_dtc(self) -> list[str]:
        '''mode 0x03'''
        request = VpwMessage(
            Priority.functional0,
            FunctionalAddress.obd_request,
            PhysicalAddress.scantool,
            Mode.get_dtc
        )
        raise NotImplementedError

    def clear_dtc(self):
        '''mode $04'''
        raise NotImplementedError

    def get_pending_dtc(self) -> list[str]:
        '''mode $07'''
        raise NotImplementedError

    def get_freeze_frame(self):
        '''mode $02'''
        raise NotImplementedError

    def get_test_results(self):
        '''mode $06'''
        raise NotImplementedError

class GmVehicle(Vehicle):
    '''SAE J2190 modes for General Motors J1850 VPW vehicles'''

    def __init__(self, device, **kwargs):
        super().__init__(device)
        self.osid = self.get_osid()
        self.pcm_type = kwargs.pop('pcm_type', None)

        if self.pcm_type is None:
            try:
                self.pcm_type = PcmType.from_osid(self.osid)
            except KeyError:
                logger.warning(f'unknown OSID: {self.osid}')
  
    def get_pid(self, pid: int) -> bytes:
        '''mode $22 - request PID'''
        assert pid in range(0xFFFF)

        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.get_pid_ext,
            pid.to_bytes(2),
            DataRate.single_response
        )

        response = self._device.send_message(request)[0]
        return response.data

    def define_dpid(self, dpid: int, pid: int, size: int, offset: int):
        '''mode $2C - define diagnostic data packet'''
        assert dpid in range(0xFF)
        assert pid in range(0xFFFF)
        assert offset >= 1

        byte3 = 1 << 6 | offset << 3 | size # See SAE J2190 5.19

        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.define_dpid,
            dpid,
            (byte3, *pid.to_bytes(2), 0xFF, 0xFF)
        )

        response = self._device.send_message(request)[0]

        if response.mode == Mode.general_response:
            raise VehicleException('request refused')

    def get_dpids(self, dpids: list[int, ...]) -> list[bytes]:
        '''mode $2A - request diagnostic data packet'''
        assert 1 <= len(dpids) <= 6
        assert all(d in range(0xFF) for d in dpids)

        size = len(dpids)
        assert size == len(set(dpids))

        dpids.extend([dpids[0] for _ in range(6 - size)]) # need 6 dpids

        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.get_dpid,
            DataRate.single_response,
            dpids
        )
        # must receive all 6 responses before sending anything else
        responses = self._device.send_message(request, 6)

        data = []
        for response in responses[:size]: # ignore duplicates
            if response.mode == Mode.general_response:
                raise VehicleException('request refused')

            data.append(response.data)

        return data

    def unlock(self, key: bytes | None = None):
        '''mode $27 - security access mode'''
        if key is None:
            assert self.pcm_type is not None

            seed_request = VpwMessage(
                Priority.physical0,
                PhysicalAddress.pcm,
                PhysicalAddress.scantool,
                Mode.unlock,
                0x01
            )

            seed_response = self._device.send_message(seed_request)[0]
            key = seedkey(seed_response.data, self.pcm_type.seedkey_algorithm)

        unlock_request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            0x02,
            key
        )

        unlock_response = self._device.send_message(unlock_request)[0]
        response_code = unlock_response.data[0]
        match response_code:
            case 0x34:
                return # key accepted
            case 0x35:
                raise UnlockException('key rejected')
            case 0x36:
                raise UnlockException('too many unlock attempts')
            case 0x37:
                raise UnlockException('time delay not expired')
            case _:
                raise UnlockException(f'unknown response code: {response_code}')

    def read_block(self, block_id: int) -> bytes:
        '''mode $3C - read data block'''
        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.read_block,
            block_id
        )
        response = self._device.send_message(request)[0]
        return response.data
    
    def write_block(self, block_id: int, data: bytes):
        '''mode $3B - write data block'''
        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.write_block,
            block_id,
            data
        )
        response = self._device.send_message(request)[0]

        if response.submode != request.submode:
            raise VehicleException('write failed')

    def get_vin(self) -> str:
        vin1 = self.read_block(BlockId.vin1)
        vin2 = self.read_block(BlockId.vin2)
        vin3 = self.read_block(BlockId.vin3)
        vin_bytes = bytes((*vin1[1:], *vin2, *vin3))
        return vin_bytes.decode('ASCII')

    def write_vin(self, vin: str):
        if not re.match(r'\b[(A-H|J-N|P|R-Z|0-9)]{17}\b', vin):
            raise ValueError('invalid VIN')

        vin_bytes = vin.encode('ASCII')
        self.write_block(BlockId.vin1, bytes((0x00, *vin_bytes[:5]))) # first byte is 0x00
        self.write_block(BlockId.vin2, vin_bytes[5:11])
        self.write_block(BlockId.vin3, vin_bytes[11:])

    def get_osid(self) -> int:
        return int.from_bytes(self.read_block(BlockId.osid))