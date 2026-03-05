def seedkey(seed: bytes, algorithm) -> bytes:
    key = int.from_bytes(seed)

    for i in range(1, 13, 3): # opcodes are every 3rd value starting at index 1
        high = algorithm[i+1] # next 2 values are operands
        low = algorithm[i+2]

        match algorithm[i]:
            case 0x14:
                # add HHLL
                key += high << 8 | low

            case 0x2A:
                if high > low:
                    key = ~key # 1's complement
                else:
                    key = ~key + 1 # 2's complement

            case 0x4C:
                # rotate left by HH bits
                key = (key << high | key >> (16 - high)) & 0xFFFF

            case 0x6B:
                # rotate right by LL bits
                key = (key >> low | key << (16 - low)) & 0xFFFF

            case 0x7E:
                # swap bytes, if LL>HH add LLHH, else add HHLL
                key = (key & 0xFF) << 8 | (key & 0xFF00) >> 8
                if low > high:
                    key += low << 8 | high
                else:
                    key += high << 8 | low

            case 0x98:
                # subtract HHLL
                key -= high << 8 | low

            case _:
                continue

        key = key & 0xFFFF # truncate to 2 bytes
        
    return key.to_bytes(2)