import lz77
from tilecodecs import gba

POINTER_END = b"\x08"
FIRSTBYTE_LZ77 = 0x10

def get_rom_addr(addr):
    if addr >= 0x8000000:
        addr -= 0x8000000
    return addr

def to_int(bytes_):
    return int.from_bytes(bytes_, "little", signed=False)

def find_pointers(rom):
    pointers = set()
    start = 0
    
    while True:
        found = rom.find(POINTER_END, start)
        if found == -1:
            break
        start = found + 1
        pointerdata = rom[found-3:found+1]
        pointer = get_rom_addr(to_int(pointerdata))
        pointers.add(pointer)
    return list(sorted(pointers))

def check_valid(rom, pointer, strict=False):
    offset = get_rom_addr(pointer)
    if offset > len(rom) - 5:
        return False
    firstbyte = rom[offset]
    size = to_int(rom[offset+1:offset+4])

    if firstbyte != FIRSTBYTE_LZ77 or size < 32:
        return False
    elif size < 32 * 1024: # min 8x8 pixel, max 32kb
        if strict:
            try:
                lz77.decompress(rom, offset)
                return True
            except:
                return False
        else:
            return True
    else:
        return False

def decode_image_at(rom, codec, image_ptr, palette_ptr, image_len=None, width=16):
    image_offset = get_rom_addr(image_ptr)
    palette_offset = get_rom_addr(palette_ptr)
    bpp = codec.getBitsPerPixel()

    if check_valid(rom, image_offset, strict=True):
        print("Loading compressed image at", hex(image_ptr))
        image_data = lz77.decompress(rom, image_offset)
    elif image_len is not None:
        print("Loading uncompressed image at", hex(image_ptr))
        image_data = rom[image_offset:image_offset+image_len]
    else:
        return "MISSING_IMAGE_LENGTH"

    tile_size = codec.getTileSize()
    if len(image_data) % tile_size:
        # Fill remaining tile with padding bytes
        image_data += b"\x00" * (tile_size - len(image_data) % tile_size)

    pal_size = gba.get_palette_size(bpp)
    if check_valid(rom, palette_offset, strict=True):
        print("Loading compressed palette at", hex(palette_ptr))
        decomp_data = lz77.decompress(rom, palette_offset)
        if len(decomp_data) < pal_size:
            return "PALETTE_TOO_SMALL"

        palette_data = decomp_data[:pal_size]
    else:
        print("Loading uncompressed palette at", hex(palette_ptr))
        palette_data = rom[palette_offset:palette_offset+pal_size]
    
    try:
        palette = gba.decode_palette(palette_data, bpp=bpp)
    except:
        return "PALETTE_DECODE_FAILED"
    
    try:
        image = gba.decode_image(image_data, codec, palette, width)
    except:
        return "IMAGE_DECODE_FAILED"
    
    return image

def decode_tilemap_at(rom, codec, image_ptr, palettes_ptr, tilemap_ptr, width=16):
    image_offset = get_rom_addr(image_ptr)
    palettes_offset = get_rom_addr(palettes_ptr)
    tilemap_offset = get_rom_addr(tilemap_ptr)
    bpp = codec.getBitsPerPixel()

    if check_valid(rom, image_offset, strict=True):
        print("Loading compressed image at", hex(image_ptr))
        image_data = lz77.decompress(rom, image_offset)
    else:
        print("Loading uncompressed image at", hex(image_ptr))
        image_len = 1024 * codec.getTileSize() # Max amount of tiles
        image_data = rom[image_offset:image_offset+image_len]
    
    tile_size = codec.getTileSize()
    if len(image_data) % tile_size:
        # Fill remaining tile with padding bytes
        image_data += b"\x00" * (tile_size - len(image_data) % tile_size)

    pal_size = gba.get_palette_size(bpp)
    if check_valid(rom, palettes_offset, strict=True):
        print("Loading compressed palettes at", hex(palettes_ptr))
        palettes_data = lz77.decompress(rom, palettes_offset)
        if len(palettes_data) < pal_size:
            return "PALETTE_TOO_SMALL"
    else:
        print("Loading uncompressed palettes at", hex(palettes_ptr))
        palettes_len = 16 * pal_size # Max amount of palettes
        palettes_data = rom[palettes_offset:palettes_offset+palettes_len]

    if check_valid(rom, tilemap_offset, strict=True):
        print("Loading compressed tilemap at", hex(tilemap_ptr))
        tilemap = lz77.decompress(rom, tilemap_offset)
    else:
        print("Loading uncompressed tilemap at", hex(tilemap_ptr))
        tilemap_len = 1024 # Max tilemap size (maybe)
        tilemap = rom[tilemap_offset:tilemap_offset+tilemap_len]

    try:
        tiles = list(gba.iter_decode_tiles(codec, image_data))
    except:
        return "IMAGE_DECODE_FAILED"
    
    try:
        palettes = list(gba.iter_decode_palettes(palettes_data, bpp=bpp, alpha=True))
    except:
        return "PALETTE_DECODE_FAILED"
    
    try:
        tilemap_tiles = gba.decode_tilemap(tilemap, tiles, palettes)
        img = gba.combine_tiles(tilemap_tiles, width)
    except:
        return "TILEMAP_DECODE_FAILED"

    return img
