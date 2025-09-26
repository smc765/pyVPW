from collections.abc import Iterable

HEX_DIGITS = set('0123456789abcdefABCDEF')

def get_bytes(n):
    if type(n) is bytes:
        return n

    elif isinstance(n, Iterable):
        return bytes(n)

    return bytes([n])

def is_hex(string: str):
    return all(i in HEX_DIGITS for i in string)