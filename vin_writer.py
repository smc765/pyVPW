import argparse, sys, re
from pyvpw import device, vehicle

parser = argparse.ArgumentParser(description='Change VIN for P01 and P04 PCMs using ELM327 scantools')
parser.add_argument('portname', help='Serial port of scantool (e.g. COM10)')
parser.add_argument('pcm_type', help='Supported values are p01, p04, and p04_early')
parser.add_argument('vin', help='New VIN')

args = parser.parse_args()

if args.pcm_type not in vehicle.SEEDKEY_ALGORITHMS.keys():
    sys.exit(f'pcm_type: {args.pcm_type} not supported')

if not re.match(r'\b[(A-H|J-N|P|R-Z|0-9)]{17}\b', args.vin):
    sys.exit(f'Invalid VIN: {args.vin}')

scantool = device.Elm327(args.portname)
v = vehicle.GmVehicle(scantool, args.pcm_type)

print(f'Current VIN: {v.read_vin()}')
confirm = input(f'Change VIN to {args.vin}? [y/n]: ')
if confirm != 'y':
    sys.exit()

print('Attempting to unlock PCM')
v.unlock()
print('PCM unlocked, attempting to write VIN')
v.write_vin(args.vin)
print(f'VIN set to {v.read_vin()}')