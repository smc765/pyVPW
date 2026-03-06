def aem30_0300(data: bytes):
    '''PID $114B (EGR sensor)'''
    n = int.from_bytes(data)
    v = (n * 255) / 5
    afr = (2.375 * v) + 7.3125
    lam = (0.1621 * v) + 0.4990 # lambda
    return afr

def rpm(data):
    '''PID $000C'''
    return int.from_bytes(data) * 0.25

def ect_c(data):
    '''PID $0005'''
    return int.from_bytes(data) - 40

def timing_deg(data):
    '''PID $000E'''
    return (int.from_bytes(data) / 2) - 64

def map_kpa(data):
    '''PID S000B'''
    return int.from_bytes(data)

def maf_hz(data):
    '''PID S1250'''
    return int.from_bytes(data) * 2.048

def tps(data):
    '''PID $0011'''
    return int.from_bytes(data) / 2.56

def kph(data):
    '''PID $000D'''
    return int.from_bytes(data)

def fuel_trim(data):
    '''
    LTFT bank 1 = $0007
    LTFT bank 2 = $0009
    STFT bank 1 = $0006
    STFT bank 2 = $0008
    '''
    return (int.from_bytes(data) - 128) / 1.28