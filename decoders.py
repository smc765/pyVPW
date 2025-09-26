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