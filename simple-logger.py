from device import ELM327
from vpw import *
from decoders import *
import time
import csv
import logging

DPID_MAX = 4
DPID_START = 0xA0
PORTNAME = 'COM4'
BAUDRATE = 9600
TIMEOUT = 1
LOGFILE = 'log.csv'

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='debug.log',
    filemode='w',
    level=logging.DEBUG
)

parameters = [
    Parameter('rpm', (0x00,0x0C), 1, decoder=rpm), # RPM
    Parameter('map', (0x00,0x0B), 1, decoder=map_kpa), # MAP sensor
    Parameter('maf', (0x12,0x50), 1, decoder=maf_hz), # MAF sensor frequency
    Parameter('wideband', (0x11,0x4B), 1, decoder=aem30_0300), # EGR sensor voltage (using this for AEM 30-0300)
    Parameter('timing', (0x00,0x0E), 1, decoder=timing_deg), # timing
    Parameter('ect', (0x00,0x05), 1, decoder=ect_c), # ECT sensor
]

# initalize ELM327
elm = ELM327(PORTNAME, BAUDRATE, timeout=TIMEOUT)

# generate DPIDS
param_groups = [parameters[i:i + DPID_MAX] for i in range(0, len(parameters), DPID_MAX)]
dpids = [Dpid(i, params) for i, params in enumerate(param_groups, start=DPID_START)]

# setup logging
fields = ['time']
for dpid in dpids:
    logger.debug(f'attempting to define DPID {dpid.id}')

    for message in dpid.get_config():
        try:
            elm.send_message(message)
        except Exception as e:
            logger.error(f'could not define DPID: {e}') 
            break # ignore errors because I haven't written tests yet

    fields.extend([param.name for param in dpid.parameters])

# start logging
with open(LOGFILE, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(fields)

    print('logging started. press ctrl+c to stop')
    while True:
        try:
            row = [time.time()]

            for dpid in dpids:
                response = elm.send_message(dpid.request)
                try:
                    values = dpid.read_parameters(response)
                except Exception as e:
                    logger.error(e)
                    break

                row.extend(values)

            writer.writerow(row)

        except KeyboardInterrupt:
            break