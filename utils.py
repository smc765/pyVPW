from collections.abc import Iterable
import math

def get_bytes(n):
    if isinstance(n, Iterable):
        return bytes(n)

    elif n <= 0xFF:
        return bytes([n])

    return n.to_bytes(math.ceil(n.bit_length() / 8))

def is_hex(string: str):
    return all(i in set('0123456789abcdefABCDEF') for i in string)

def get_key(seed: bytes, algorithm: list[int, ...]) -> bytes:
    key = int.from_bytes(seed, 'big')
    for i in range(1, 13, 3):
        high = algorithm[i+1]
        low = algorithm[i+2]

        match algorithm[i]:
            case 0x14: # add HHLL
                key += high << 8 | low

            case 0x2A:
                if high > low:
                    key = ~key
                else:
                    key = ~key + 1

            case 0x4C: # rotate left by HH bits
                key = (key << high | key >> (16 - high)) & 0xFFFF

            case 0x6B: # rotate right by LL bits
                key = (key >> low | key << (16 - low)) & 0xFFFF

            case 0x7E: # swap bytes of key, if LL>HH add LLHH, else add HHLL
                key = (key & 0xFF) << 8 | (key & 0xFF00) >> 8

                if low > high:
                    key += low << 8 | high
                else:
                    key += high << 8 | low

            case 0x98: # subtract HHLL
                key -= (high << 8 | low)

            case _:
                continue

    key = key & 0xFFFF
    return key.to_bytes(2)