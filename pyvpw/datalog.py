from typing import Any

DPID_MAX = 0xFE
DPID_MIN = 0xF2
DPID_MAX_BYTES = 6

class Pid:
    def __init__(self, name: str, pid: int, size: int, decoder=lambda x: x):
        assert pid in range(0xFFFF)
        self.name = name
        self.id = pid
        self.size = size # number of data bytes returned
        self.decoder = decoder

    def __bytes__(self):
        return self.id.to_bytes(2)

    def __eq__(self, other):
        if isinstance(other, Pid):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        elif isinstance(other, bytes):
            return bytes(self) == other
        else:
            raise NotImplementedError

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class Dpid:
    '''diagnostic data packet'''
    def __init__(self, dpid: int):
        assert dpid in range(0xFF)
        self.id = dpid
        self.pids = []

    def __bytes__(self):
        return self.id.to_bytes()

    def __eq__(self, other):
        if isinstance(other, Dpid):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        elif isinstance(other, bytes):
            return bytes(self) == other
        else:
            raise NotImplementedError

    def __hash__(self):
        return hash(self.id)

    def __contains__(self, key):
        if isinstance(key, Pid):
            return key in self.pids
        elif isinstance(key, int):
            return key in [pid.id for pid in self.pids]
        elif isinstance(key, bytes):
            return key in [bytes(pid) for pid in self.pids]
        else:
            raise NotImplementedError

    def __len__(self):
        return sum([pid.size for pid in self.pids])

    def bytes_free(self):
        return DPID_MAX_BYTES - len(self)

    def unpack(self, data: bytes) -> dict[Pid, bytes]:
        values = dict.fromkeys(self.pids)
        read_byte = 0
        for pid in values:
            values[pid] = data[read_byte: read_byte + pid.size]
            read_byte += pid.size

        return values

class DpidLogger:
    def __init__(self, vehicle):
        self._vehicle = vehicle
        self.pids = []
        self._dpids = []
        self._avaliable_dpids = [Dpid(i) for i in range(DPID_MIN, DPID_MAX+1)]

    def add_pid(self, pid: Pid):
        assert pid not in self.pids
        
        for dpid in self._dpids:
            if dpid.bytes_free() >= pid.size:
                self._vehicle.define_dpid(dpid.id, pid.id, pid.size, len(dpid)+1)
                dpid.pids.append(pid)
                self.pids.append(pid)
                return
        
        dpid = self._avaliable_dpids.pop()
        self._vehicle.define_dpid(dpid.id, pid.id, pid.size, 1)
        dpid.pids.append(pid)
        self.pids.append(pid)
        self._dpids.append(dpid)

    def remove_pid(self, pid: Pid):
        raise NotImplementedError

    def get_row(self) -> dict[Pid, Any]:
        values = dict.fromkeys(self.pids)
        dpid_groups = [self._dpids[i:i + 6] for i in range(0, len(self._dpids), 6)]
        for dpid_group in dpid_groups:
            responses = self._vehicle.get_dpids([dpid.id for dpid in dpid_group])
            for i, data in enumerate(responses):
                values.update(dpid_group[i].unpack(data))

        return {pid: pid.decoder(value) for pid, value in values.items()}