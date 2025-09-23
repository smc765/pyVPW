def aem30_0300(data: bytes):
    n = data[0]
    v = (n * 255) / 5
    afr = (2.375 * v) + 7.3125
    lam = (0.1621 * v) + 0.4990 # lambda
    return afr

def rpm(data: bytes):
    n = data[0]
    return n * 0.25

def deg(data: bytes):
    n = data[0]
    return (n / 2) - 64