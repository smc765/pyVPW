class VehicleException(Exception):
    '''raised when vehicle responds with error'''

class UnlockException(VehicleException):
    '''raised when PCM unlock fails'''

class DeviceException(Exception):
    '''raised for scantool errors'''