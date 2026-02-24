# pyVPW
A Python library for SAE J1850-VPW communication with 1999-2003 GM PCMs using ELM327 scan tools.

### Features
- define diagnostic data packets (DPID) combining up to 4 PIDs
- read and decode PIDs
- send/receive and VPW messages
- read/write data blocks (VIN, Serial Number, OSID, etc.)
- unlock PCM
- change VIN

### VIN Writer Usage
    python vin_writer.py [portname] [pcm_type] [vin]

### Todo
- write to memory (modes $34-$37)
- read/erase DTCs
- freeze frame

### References
- [PCM Hammer](https://github.com/PcmHammer/PcmHammer) - Tools for reading, writing, and data logging from GM PCMs. Lots of great info here.
- [pcmhacking.net](https://pcmhacking.net/forums/) - PCM Hacking forum
- SAE J1850 - Describes message protocol
- SAE J1979 - legislated diagnostic test modes ($01-0A)
- SAE J2190 - non-legislated modes (Extended PIDs, DPIDs, reading/writing memory, etc.)
- SAE J2178/1 - detailed header format and physical address assignments
- [GM SeedKey Algorithm Paper](https://pcmhacking.net/forums/viewtopic.php?t=5876) - Reverse engineered PCM unlock algorithm
- [ELM327 Datasheet](https://cdn.sparkfun.com/assets/learn_tutorials/8/3/ELM327DS.pdf)

### Disclaimer
This project is still in the early stage of development and has not been throughly tested on real vehicles.