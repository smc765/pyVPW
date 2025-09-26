from device import ELM327
from vpw import *
from decoders import *
import time
import csv

DPID_MAX = 4
DPID_START = 0xA0
PORTNAME = 'COM4'
BAUDRATE = 9600
TIMEOUT = 1
LOGFILE = 'log.csv'

def main():
    dpid_params = [
        Parameter('ect', (0x00,0x05), 1), # ECT sensor
        Parameter('rpm', (0x00,0x0C), 1), # RPM
        Parameter('map', (0x00,0x0B), 1), # MAP sensor
        Parameter('timing', (0x00,0x0E), 1), # timing
        Parameter('maf', (0x12,0x50), 1), # MAF sensor frequency
        Parameter('wideband', (0x11,0x4B), 1, decoder=aem30_0300), # EGR sensor voltage (using this for AEM 30-0300)
    ]

    # initalize ELM327
    elm = ELM327(PORTNAME, BAUDRATE, timeout=TIMEOUT)

    # generate DPIDS
    param_groups = [dpid_params[i:i + DPID_MAX] for i in range(0, len(dpid_params), DPID_MAX)] # split dpid_params into lists of size DPID_MAX
    dpids = []
    n = DPID_START
    for group in param_groups:
        dpids.append(Dpid(n, group))
        n += 1

    msg_q = [] # DPID config message queue
    fields = [] # logging fields
    for dpid in dpids:
        fields.extend([param.name for param in dpid.parameters])
        msg_q.extend(dpid.get_config())

    # send DPID definition messages
    for msg in msg_q:
        elm.send_message(msg)
    
    # start logging
    with open(LOGFILE, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(fields)

        print('logging started. press ctrl+c to stop')
        try:
            while True:
                row = []
                row.append(time.time())
                for dpid in dpids:
                    res = elm.send_message(dpid.get_request())[0]
                    for param in dpid.parameters:
                        data = dpid.get_param(res, param)
                        if param.decoder is None:
                            row.append(data.hex())
                        else:
                            row.append(param.decoder(data))
                
                writer.writerow(row)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()