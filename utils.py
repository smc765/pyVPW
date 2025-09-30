from collections.abc import Iterable
import math

HEX_DIGITS = set('0123456789abcdefABCDEF')

def get_bytes(n):
    if isinstance(n, Iterable):
        return bytes(n)

    elif n <= 0xFF:
        return bytes([n])

    return n.to_bytes(math.ceil(n.bit_length() / 8))

def is_hex(string: str):
    return all(i in HEX_DIGITS for i in string)