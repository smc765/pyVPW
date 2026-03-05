import argparse, sys
from pyvpw import device, vehicle

parser = argparse.ArgumentParser(description='Change VIN on P04 PCMs with ELM327 scantools')
parser.add_argument('portname', help='Serial port of scantool (e.g. COM10)')
parser.add_argument('vin', help='New VIN')

args = parser.parse_args()

scantool = device.Elm327(args.portname)
v = vehicle.GmVehicle(scantool)

print(f'Current VIN: {v.get_vin()}')

confirm = input(f'Change VIN to {args.vin}? [y/n]: ')
if confirm != 'y':
    sys.exit()

print('Unlocking PCM...')
v.unlock()
print('Writing VIN...')
v.write_vin(args.vin)
print(f'VIN set to: {v.get_vin()}')