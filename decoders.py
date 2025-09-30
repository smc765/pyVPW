def aem30_0300(data: bytes):
    '''
    PID $114B (EGR sensor)
    '''
    n = data[0]
    v = (n * 255) / 5
    afr = (2.375 * v) + 7.3125
    lam = (0.1621 * v) + 0.4990 # lambda
    return afr

def rpm(data):
    '''
    PID $000C
    '''
    n = data[0]
    return n * 0.25

def ect_c(data):
    '''
    PID $0005
    '''
    n = data[0]
    return n - 40

def timing_deg(data):
    '''
    PID $000E
    '''
    n = data[0]
    return (n / 2) - 64

def map_kpa(data):
    '''
    PID S000B
    '''
    return data[0]

def maf_hz(data):
    '''
    PID S1250
    '''
    return data[0] * 2.048

def tps(data):
    '''
    PID $0011
    '''
    return data[0] / 2.56

def kph(data):
    '''
    PID $000D
    '''
    return data[0]

def fuel_trim(data):
    '''
    LTFT bank 1 = $0007
    LTFT bank 2 = $0009
    STFT bank 1 = $0006
    STFT bank 2 = $0008
    '''
    n = data[0]
    return (y - 128) / 1.28