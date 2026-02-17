# pyVPW
A Python library for SAE J1850-VPW communication with GM P01 PCMs (99-03 LS motors) using ELM327 scan tools.

### Features
- define diagnostic data packets (dpid) combining up to 4 parameters
- define parameters by PID or memory address
- generate request messages for parameters
- read and decode PIDs
- send/receive and validate VPW messages
- read/write data blocks
- unlock PCM
- change VIN

### Todo
- setup bench pcm for testing
- load parameters from config file
- VPW bus monitoring, logging and message filtering
- data transfer (modes $34-$37)
- read/erase DTCs
- read emissions monitors and freeze frame data
- test other PCMs
- improve exception handling

### References
- [PCM Hammer](https://github.com/PcmHammer/PcmHammer) - Tools for reading, writing, and data logging from GM PCMs. Lots of great info here.
- [pcmhacking.net](https://pcmhacking.net/forums/) - PCM Hacking forum
- SAE J1850 - Describes message format
- SAE J1979 - legislated diagnostic test modes ($01-0A)
- SAE J2190 - non-legislated modes (Extended PIDs, DPIDs, reading/writing memory, etc.)
- SAE J2178/1 - detailed header format and physical address assignments
- [GM SeedKey Algorithm Paper](https://ls1tech.com/forums/attachments/pcm-diagnostics-tuning/705619-inexpensive-opensource-flashing-read-100-working-gm-seedkey.doc) - Reverse engineered PCM unlock algorithm (author unknown)

### Disclaimer
This project is still in the early stage of development and has not been throughly tested on real vehicles.
