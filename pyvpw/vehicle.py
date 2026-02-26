from enum import IntEnum
from typing import Any
import re
from .vpw import *
from .device import *

class GmBlockId(IntEnum):
    vin1 = 0x01 # 0x00, first 5 bytes
    vin2 = 0x02 # next 6 bytes
    vin3 = 0x03 # last 6 bytes
    osid = 0x0A # operating system id

# found in STGTERM.DAT from Tech2
SEEDKEY_ALGORITHMS = {
    'p01': [36, 20, 82, 1, 126, 56, 151, 42, 190, 56, 152, 212, 40],
    'p04': [4, 107, 80, 2, 126, 80, 210, 76, 5, 253, 152, 24, 203],
    'p04_early': [160, 42, 169, 58, 20, 1, 191, 107, 237, 11, 76, 5, 205]
}

# these values should work but need to test more
DPID_START = 0xFA
DPID_MAX_PIDS = 4

class VehicleException(Exception):
    '''raised when vehicle responds with error'''

class UnlockException(VehicleException):
    '''raised when PCM unlock fails'''

class Vehicle:
    '''implements SAE J1979 modes'''

    def __init__(self, device):
        self._device = device

    def request_pid(self, pid: Pid):
        '''mode $01 - request PID'''
        
        if pid.id not in range(0xFF):
            raise VehicleException('PID not supported')

        request = VpwMessage(
            Priority.functional0,
            FunctionalAddress.obd_request,
            PhysicalAddress.scantool,
            Mode.get_pid,
            pid.id
        )

        response = self._device.send_message(request)[0]
        return pid.decoder(response.data)

class GmVehicle(Vehicle):
    '''implements GM specific SAE J2190 modes'''

    def __init__(self, device, pcm_type):
        super().__init__(device)
        self._device.set_protocol(ElmProtocol.j1850vpw)
        self._seedkey_algorithm = SEEDKEY_ALGORITHMS[pcm_type]
        self.dpids = set() # defined DPIDs

    def request_pid(self, pid: Pid):
        '''mode $22 - request PID'''

        request = VpwMessage(
            Priority.functional0,
            FunctionalAddress.obd_request,
            PhysicalAddress.scantool,
            Mode.get_pid_ext,
            bytes(pid),
            DataRate.single_response
        )

        response = self._device.send_message(request)[0]
        return pid.decoder(response.data)

    def define_dpid(self, dpid: Dpid):
        '''mode $2C - define diagnostic data packet'''

        config_messages = []
        start_byte = 0b001 # byte offset of data in response packet

        for pid in dpid.pids:
            byte3 = 0b01 << 6 | start_byte << 3 | pid.size # See SAE J2190 5.19
            start_byte += pid.size
            config_messages.append(VpwMessage(
                Priority.physical0,
                PhysicalAddress.pcm,
                PhysicalAddress.scantool,
                Mode.define_dpid,
                dpid.id,
                (byte3, *bytes(pid), 0xFF, 0xFF)
            ))
        
        for message in config_messages:
            response = self._device.send_message(message)[0]
            
            if response.submode != bytes(dpid):
                raise VehicleException('could not define DPID')

        self.dpids.add(dpid)

    def request_dpid(self, dpid: Dpid) -> dict[Pid, Any]:
        '''mode $2A - request diagnostic data packet'''

        request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.request_dpid,
            DataRate.single_response,
            dpid.id
        )

        response = self._device.send_message(request)[0]
        data = dpid.unpack(response.data)

        for pid, value in data.items():
            data[pid] = pid.decoder(value)

        return data
    
    def setup_dpids(self, pids: list[Pid], max_pids=DPID_MAX_PIDS, start=DPID_START):
        '''setup DPIDs for a list of PIDs'''

        if self.dpids:
            start = max(dpid.id for dpid in self.dpids) + 1 # get next available DPID

        # split PIDs into DPIDs of size <= max size
        pid_groups = [pids[i:i + max_pids] for i in range(0, len(pids), max_pids)]
        dpids = [Dpid(i, group) for i, group in enumerate(pid_groups, start=start)]
        
        for dpid in dpids:
            self.define_dpid(dpid)

    def unlock(self):
        '''mode $27 - security access mode'''

        seed_request = VpwMessage(
            Priority.physical0,
            PhysicalAddress.pcm,
            PhysicalAddress.scantool,
            Mode.unlock,
            0x01
        )

        seed_response = self._device.send_message(seed_request)[0]
        key = seedkey(seed_response.data, self._seedkey_algorithm)

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
                raise UnlockException('key not accepted')
            case 0x36:
                raise UnlockException('too many unlock attempts')
            case 0x37:
                raise UnlockException('time delay not expired')
            case _:
                raise UnlockException(f'unknown response code: {response_code}')

    def read_block(self, block_id: int) -> bytes:
        '''read data block'''
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

    def read_vin(self) -> str:
        vin1 = self.read_block(GmBlockId.vin1)
        vin2 = self.read_block(GmBlockId.vin2)
        vin3 = self.read_block(GmBlockId.vin3)
        vin_bytes = bytes((*vin1[1:], *vin2, *vin3))
        return vin_bytes.decode('ASCII')

    def write_vin(self, vin: str):
        if not re.match(r'\b[(A-H|J-N|P|R-Z|0-9)]{17}\b', vin):
            raise ValueError('invalid VIN')

        vin_bytes = vin.encode('ASCII')
        self.write_block(GmBlockId.vin1, bytes((0x00, *vin_bytes[:5]))) # first byte is 0x00
        self.write_block(GmBlockId.vin2, vin_bytes[5:11])
        self.write_block(GmBlockId.vin3, vin_bytes[11:])

    def read_osid(self) -> int:
        return int.from_bytes(self.read_block(GmBlockId.osid))