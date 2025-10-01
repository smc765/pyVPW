from collections.abc import Iterable
import math

def get_bytes(n: int | Iterable) -> bytes:
    if isinstance(n, Iterable):
        return bytes(n)

    return n.to_bytes(math.ceil(n.bit_length() / 8))

def is_hex(string: str) -> bool:
    return all(i in set('0123456789abcdefABCDEF') for i in string)