to_int = lambda x : int.from_bytes(x, "little")
block_size = 8

def decompress(compressed_data, offset=0):
    '''Decompresses lz77-compressed images in GBA ROMs.
       Algorithm originally ported from NLZ-Advance code
       (which has copyright by Nintenlord)
       compressed data must be either a bytes() or a bytearray()'''
    size = to_int(compressed_data[offset+1:offset+4])
    decompressed_data = bytearray(size)
    if compressed_data[offset] != 0x10:
        raise Exception('Not valid lz77 data')
    decomp_pos = 0
    comp_pos = 4
    while decomp_pos < size:
        # Every bit of this byte maps to one of the eight following blocks
        # if the bit is 1, that block is compressed
        is_compressed = compressed_data[comp_pos+offset]
        comp_pos += 1
        for block_i in range(block_size):
            if is_compressed & 0x80:
                amount_to_copy = 3 + (compressed_data[comp_pos+offset]>>4)
                to_copy_from = (1 +
                                ((compressed_data[comp_pos+offset] & 0xF) << 8) +
                                compressed_data[comp_pos+offset + 1])
                if to_copy_from > size:
                    raise Exception('Not valid lz77 data')
                for i in range(amount_to_copy):
                    decompressed_data[decomp_pos] = decompressed_data[
                            decomp_pos - i - to_copy_from + (i % to_copy_from)
                            ]
                    decomp_pos += 1
                comp_pos += 2

            else:
                if decomp_pos >= size:
                    break
                decompressed_data[decomp_pos] = compressed_data[comp_pos+offset]
                decomp_pos += 1
                comp_pos += 1
            if decomp_pos > size:
                break
            is_compressed <<= 1
    return decompressed_data
