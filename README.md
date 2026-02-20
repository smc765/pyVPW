# pyVPW
A Python library for SAE J1850-VPW communication with GM P01 PCMs (99-03 LS motors) using ELM327 scan tools.

### Features
- define diagnostic data packets (dpid) combining up to 4 parameters
- define parameters by PID or memory address
- generate request messages for parameters
- read and decode PIDs
- send/receive and validate VPW messages
- read/write data blocks (VIN, Serial Number, OSID, etc.)
- unlock PCM
- change VIN

### Todo
- setup bench PCM with simulated inputs for testing
- data logging config files
- VPW bus monitoring
- write to RAM (modes $34-$37)
- read/erase DTCs
- read/reset emissions monitors
- freeze frame
- support for Antus' kernel (see [PCM Hammer wiki](https://github.com/LegacyNsfw/PcmHacks/wiki/Implementation))
- test device present (mode $3F)

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
