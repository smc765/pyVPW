from pyvpw import device, vehicle

elm = device.Elm327('COM10')
v = vehicle.GmVehicle(elm, 'p04')

print(f'VIN: {v.read_osid()}')
print(f'OSID: {v.read_vin()}')