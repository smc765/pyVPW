# pyVPW
A Python module for SAE J1850-VPW communication with 1999-2003 General Motors PCMs using ELM327 scan tools.

### Features
- define and request diagnostic data packets (DPID)
- read and decode PIDs
- send and receive and VPW messages
- read and write data blocks (VIN, Serial Number, OSID, etc.)
- unlock PCM
- change VIN

### vin_writer.py usage
    python vin_writer.py [portname] [vin]

### Supported OSIDs
 - 12212156 (p01)
 - 9384022 (p04)
 - probably more, see `pcm.py`

### References
- [PCM Hammer](https://github.com/PcmHammer/PcmHammer) - Tools for reading, writing, and data logging from GM PCMs. Lots of great info here.
- [pcmhacking.net](https://pcmhacking.net/forums/) - PCM Hacking forum
- SAE J1850 - Describes message protocol
- SAE J1979 - legislated diagnostic test modes ($01-0A)
- SAE J2190 - non-legislated modes (Extended PIDs, DPIDs, reading/writing memory, etc.)
- SAE J2178/1 - detailed header format and physical address assignments
- [GM SeedKey Algorithm Paper](https://pcmhacking.net/forums/viewtopic.php?t=5876) - Reverse engineered PCM unlock algorithm
- [ELM327 Datasheet](https://cdn.sparkfun.com/assets/learn_tutorials/8/3/ELM327DS.pdf)
