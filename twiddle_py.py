from __future__ import annotations

from typing import Iterable, Callable

def get_offset(x: int, y: int) -> int:
    return y * 256 + x

def get_bit(display: bytearray, x: int, y: int, mask: int) -> bool:
    o = get_offset(x, y)
    return (display[o] & mask) != 0

type GetBitFn[T] = Callable[[int, int, int], T]
type MergeFn[T, I] = Callable[[Iterable[T]], I]

# The total panel size is 256 by 64 pixels.
# It's formed of 4, 64 x 64 clock domains.
# Each clock domain controls 4, 16 x 64 panels,
# fed by 8 data lines - 2 per panel, one covering the 'left' 8 pixels, the other the 'right'.
# Each clock/data combination, in turn, drives 8 'subtiles' of 8 x 8 pixels.
# Each subtile contains 3, 16-bit drivers, one per colour plane, each driving
# one quarter of the subtile at a time (determined by 'address'):
# Address 0: column 0 and 4,
# Address 1: column 1 and 5,
# Address 2: column 2 and 6,
# Address 3: column 3 and 7.
# 
# The bitstream is produced for each clock/data/address combination independently,
# and is comprised of 384 bits: blue, green and red for each of the 8 subtiles, in that order. 
# 
# Clock: x >> 6
# Address: x % 4
# Data: (x >> 3) % 8
def get_bitstream[T](fn: GetBitFn[T], data: int, address: int, clock: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[T]:
    x = (clock << 6) | ((7 ^ data) << 3) | address

    # 16 bits: one driver.
    def generate_driver_bitstream(subtile: int, colour_mask: int) -> Iterable[T]:
        for i in range(8):
            y = subtile * 8 + i
            yield fn(x, y, colour_mask)
            
        for i in range(8):
            y = subtile * 8 + i
            yield fn(x + 4, y, colour_mask)

    # 3 drivers: one subtile, 48 bits.
    def generate_subtile_bitstream(subtile: int) -> Iterable[T]:
        # Blue
        yield from generate_driver_bitstream(subtile, colour_mask_b)

        # Green
        yield from generate_driver_bitstream(subtile, colour_mask_g)

        # Red
        yield from generate_driver_bitstream(subtile, colour_mask_r)

    # 8 subtiles: 384 bits.
    for subtile in range(8):
        yield from generate_subtile_bitstream(subtile)

def bits_to_byte(bits: Iterable[bool]) -> int:
    v: int = 0
    for b in bits:
        v <<= 1
        if b:
            v |= 1

    return v

# Clock: x >> 6
# Address: x % 4
def get_bytestream[T, I](fn: GetBitFn[T], merge: MergeFn[T, I], address: int, clock: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[I]:
    # 64 subtiles: 4 panels.
    for bits in zip(*[get_bitstream(fn, data, address, clock, colour_mask_r, colour_mask_g, colour_mask_b) for data in range(8)]):
        yield merge(bits)
    
def get_interleaved[T, I](fn: GetBitFn[T], merge: MergeFn[T, I], address: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[I]:
    clk0 = get_bytestream(fn, merge, address, 0, colour_mask_r, colour_mask_g, colour_mask_b)
    clk1 = get_bytestream(fn, merge, address, 1, colour_mask_r, colour_mask_g, colour_mask_b)
    clk2 = get_bytestream(fn, merge, address, 2, colour_mask_r, colour_mask_g, colour_mask_b)
    clk3 = get_bytestream(fn, merge, address, 3, colour_mask_r, colour_mask_g, colour_mask_b)

    clock_domains = zip(clk0, clk1, clk2, clk3)
    
    for b0, b1, b2, b3 in clock_domains:
        yield b0
        yield b1
        yield b2
        yield b3

PLANES = [
    # 'MSB' plane: R2, G2, B1
    (0x80, 0x10, 0x02),
    # R1, G1, B0
    (0x40, 0x08, 0x01),
    # R0, G0, B1 (duplicated)
    (0x20, 0x04, 0x02)
]

def blit_inner[T, I](fn: GetBitFn[T], merge: MergeFn[T, I]) -> Iterable[I]:
    for p, (colour_mask_r, colour_mask_g, colour_mask_b) in enumerate(PLANES):
        # For each address line
        for addr in range(4):
            for byte in get_interleaved(fn, merge, addr, colour_mask_r, colour_mask_g, colour_mask_b):
                yield byte

def blit(back: list[bytearray], display: bytearray) -> None:
    def get_bit_fn(x: int, y: int, mask: int) -> bool:
        return get_bit(display, x, y, mask)
    
    p = ((i, j) for i in range(12) for j in range(1536))
    for (i, j), byte in zip(p, blit_inner(get_bit_fn, bits_to_byte)):
        back[i][j] = byte
        
    