from collections.abc import Iterable
import math

def get_bytes(n: int | Iterable) -> bytes:
    '''Return bytes from an integer or iterable yielding integers in range(0xFF)'''
    if isinstance(n, int):
        return n.to_bytes(max(1, math.ceil(n.bit_length() / 8)))

    return bytes(n)

def is_hex(string: str) -> bool:
    return all(i in set('0123456789abcdefABCDEF') for i in string)