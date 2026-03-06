from pyvpw.device import Elm327
from pyvpw.vehicle import GmVehicle
from pyvpw.datalog import Pid, DpidLogger
from pyvpw import decoders
import time, csv

import logging
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.FileHandler('debug.log'),]
    )

PORTNAME = 'COM10'
LOGFILE = 'datalog.csv'
PIDS = [
    # name, pid, size, decoder function     
    Pid('ect', 0x0005, 1, decoders.ect_c),          # coolant temp
    Pid('rpm', 0x000C, 2, decoders.rpm),            # RPM
    Pid('iat', 0x000F, 1, decoders.ect_c),          # intake air temp
    Pid('wideband', 0x114B, 1, decoders.aem30_0300) # wideband o2 (EGR sensor)
]

elm = Elm327(PORTNAME)
v = GmVehicle(elm)
dl = DpidLogger(v)

for pid in PIDS:
    dl.add_pid(pid)

with open(LOGFILE, 'w') as f:
    fieldnames = ['time'] + PIDS
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    print('logging started. press ctrl+c to stop')
    while True:
        row = {'time': (t := time.time())}
        row.update(dl.get_row())
        writer.writerow(row)
        print(f'{1 / (time.time() - t):.2f} Rows/Second')