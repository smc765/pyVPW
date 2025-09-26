# pyVPW
A Python library for SAE J1850-VPW communication with GM PCMs using ELM327 based scan tools. See `simple-logger.py` for an example usage/proof of concept

### Features
- read mode $22 extended PIDs
- create user-defined diagnostic data packets (dpid) combining up to 4 parameters into a single packet
- define parameters by PID or memory address
- generate request messages for parameters
- read and decode parameter values from dpid packets

### Todo
- setup bench pcm for testing
- vpw bus monitoring and logging
- write to memory address
- unlock pcm


### Disclaimer
This project is still in the early stage of development and has not been throughly tested on real vehicles.
