# pyVPW
A Python library for SAE J1850-VPW communication with GM P01/512kb PCMs (99-03 LS motors) using ELM327 based scan tools. See `simple-logger.py` for an example usage/proof of concept

### Features
- read mode $22 extended PIDs
- create user-defined diagnostic data packets (dpid) combining up to 4 parameters into a single packet
- define parameters by PID or memory address
- generate request messages for parameters
- read and decode parameter values from dpid packets

### Todo
- setup bench pcm for testing
- security access mode ($27)
- read/write data blocks (mode $3C/$3B)
- load parameters from config file
- vpw bus monitoring, logging and message filtering
- data transfer (modes $34-$37)

### References
- [PCM Hammer](https://github.com/PcmHammer/PcmHammer) - Tools for reading, writing, and data logging from GM PCMs. Lots of great info here.
- SAE J1850 - Describes message protocol
- SAE J1979 - legislated diagnostic test modes ($01-0A)
- SAE J2190 - non-legislated modes (Extended PIDs, DPIDs, reading/writing memory, etc.)
- SAE J2178/1 - detailed header format and physical address assignments
- SAE J2186 - Data link security

### Disclaimer
This project is still in the early stage of development and has not been throughly tested on real vehicles.
