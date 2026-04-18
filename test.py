import twiddle_old
import twiddle
import random
import time
from typing import Iterable

display = bytearray(256 * 64)
back = [bytearray(1536) for _ in range(12)]
back2 = [bytearray(1536) for _ in range(12)]

'''
while True:
    for i in range(256 * 64):
        display[i] = random.randint(0, 255)

    twiddle_old.blit(back, display)
    twiddle.blit(back2, display)

    for b1, b2 in zip(back, back2):
        if b1 != b2:
            print("Mismatch!")
            exit(1)

    print("OK")
'''

type BitID = tuple[int, int, int]

def get_bit(x: int, y: int, mask: int) -> BitID:
    return x, y, mask

def twiddle_fast() -> Iterable[list[BitID]]:
    # What's that, you say? Cache locality?
    for r, g, b in twiddle.PLANES:
        for addr in range(4):
            for subtile in range(8):
                for p in (b, g, r):
                    for d in range(2):
                        for i in range(8):
                            for clock in range(4):
                                y = (subtile << 3) + i
                                x = (clock << 6) | (7 << 3) | (d << 2) | addr
                                yield [(x - 8 * i, y, p) for i in range(8)]

def twiddle_fast_direct(buffer: bytearray, display: bytes) -> None:
    ptr = 0

    # What's that, you say? Cache locality?
    for r, g, b in twiddle.PLANES:
        for addr in range(4):
            for subtile in range(8):
                for p in (b, g, r):
                    for d in range(2):
                        for i in range(8):
                            for clock in range(4):
                                y = (subtile << 3) + i
                                x = (clock << 6) | (7 << 3) | (d << 2) | addr
                                q = 0
                                for j in range(8):
                                    q <<= 1
                                    if display[y * 256 + x - 8 * j] & p:
                                        q |= 1

                                buffer[ptr] = q
                                ptr += 1

PLANES = [
    # 'MSB' plane: R2, G2, B1
    (7, 4, 1),
    # R1, G1, B0
    (6, 3, 0),
    # R0, G0, B1 (duplicated)
    (5, 2, 1)
]


def twiddle_fast_direct2(buffer: bytearray, display: bytes) -> None:
    ptr = 0

    # What's that, you say? Cache locality?
    for r, g, b in PLANES:
        # (95, 63)
        src = 16323

        for addr in range(4): # Overall loop delta (4, 0)
            # delta (1, -64)
            src -= 16383
            
            for subtile in range(8): # Overall loop delta (0, 64)
                # delta (0, 8)
                src += 2048

                for p in (b, g, r): # Overall loop delta (0, 0)
                    [p0, p1, p2, p3, p4, p5, p6, p7] = [1 << (p + j) for j in range(8)]

                    # delta (-8, 0)
                    src -= 8

                    for d in range(2): # Overall loop delta (8, 0)
                        # delta (4, -8)
                        src -= 2044
                        
                        for y in range(8): # Overall loop delta (0, 8)
                            # delta (-256, 1) ... cancels
                                                   
                            for clock in range(4): # Overall loop delta (256, 0)
                                # delta (128, 0)
                                src += 128

                                q = 0
                                m = 1 << p

                                for bit in range(8): # Overall loop delta (-64, 0)
                                    # delta (-8, 0)
                                    src -= 8

                                    q <<= 1
                                    q |= (display[src] & m)

                                buffer[ptr] = q >> p
                                
                                '''
                                q = 0

                                src -= 8
                                q |= ((display[src] << 7)) & p7
                                src -= 8
                                q |= ((display[src] << 6)) & p6
                                src -= 8
                                q |= ((display[src] << 5)) & p5
                                src -= 8
                                q |= ((display[src] << 4)) & p4
                                src -= 8
                                q |= ((display[src] << 3)) & p3
                                src -= 8
                                q |= ((display[src] << 2)) & p2
                                src -= 8
                                q |= ((display[src] << 1)) & p1
                                src -= 8
                                q |= ((display[src] << 0)) & p0

                                buffer[ptr] = q >> p
                                '''
                                ptr += 1

def build_lut(r: int, g: int, b: int) -> list[int]:
    """
    Build a LUT for extracting 3 bits from an 8-bit value.

    Take bit positions 'r', 'b' and 'g' and build a 256-entry LUT where each entry:
    - Has bit 16 set to the value of bit 'b' in the index.
    - Has bit 8 set to the value of bit 'g' in the index.
    - Has bit 0 set to the value of bit 'r' in the index.
    """
    lut = []
    
    for c in range(256):
        q = 0    
        q |= (c >> r) & 1
        q |= ((c >> g) & 1) << 8
        q |= ((c >> b) & 1) << 16

        lut.append(q)

    return lut
                        
def twiddle_fast_direct3(buffer: bytearray, display: bytes) -> None:
    dest_ptr = -128

    # What's that, you say? Cache locality?
    for r, g, b in PLANES:
        lut = build_lut(r, g, b)

        # (95, 63)
        src_ptr = 16323
        
        for addr in range(4): # Overall loop delta (4, 0)
            # delta (1, -64)
            src_ptr -= 16383
            
            for subtile in range(8): # Overall loop delta (0, 64)
                # delta (-8, 8)
                src_ptr += 2040
                dest_ptr += 128
               
                for d in range(2): # Overall loop delta (8, 0)
                    # delta (4, -8)
                    src_ptr -= 2044
                    
                    for y in range(8): # Overall loop delta (0, 8)
                        # delta (-256, 1) ... cancels
                                                
                        for clock in range(4): # Overall loop delta (256, 0)
                            # delta (128, 0)
                            src_ptr += 128

                            q = 0

                            '''
                            for bit in range(8): # Overall loop delta (-64, 0)
                                # delta (-8, 0)
                                src_ptr -= 8
                                c = display[src_ptr]

                                q <<= 1

                                q |= lut[c]
                            '''

                            src_ptr -= 8
                            c0 = display[src_ptr]
                            src_ptr -= 8
                            c1 = display[src_ptr]
                            src_ptr -= 8
                            c2 = display[src_ptr]
                            src_ptr -= 8
                            c3 = display[src_ptr]
                            src_ptr -= 8
                            c4 = display[src_ptr]
                            src_ptr -= 8
                            c5 = display[src_ptr]
                            src_ptr -= 8
                            c6 = display[src_ptr]
                            src_ptr -= 8
                            c7 = display[src_ptr]
                            
                            q |= (lut[c0] << 7)
                            q |= (lut[c1] << 6)
                            q |= (lut[c2] << 5)
                            q |= (lut[c3] << 4)
                            q |= (lut[c4] << 3)
                            q |= (lut[c5] << 2)
                            q |= (lut[c6] << 1)
                            q |= (lut[c7] << 0)
                            
                            buffer[dest_ptr] = (q >> 16) & 0xFF
                            buffer[dest_ptr + 64] = (q >> 8) & 0xFF
                            buffer[dest_ptr + 128] = (q >> 0) & 0xFF
                           
                            dest_ptr += 1            

def twiddle_fast_direct4(buffer: bytearray, display: bytes) -> None:
    # With apologies to Mr. Donald Knuth

    dest_ptr = -128

    # (95, 63)
    src_ptr = 16323
    
    # What's that, you say? Cache locality?
    lut = []
    for r, g, b in PLANES:
        lut.append(build_lut(r, g, b))

    for addr in range(4): # Overall loop delta (4, 0)
        # delta (1, -64)
        src_ptr -= 16383
        
        for subtile in range(8): # Overall loop delta (0, 64)
            # delta (-8, 8)
            src_ptr += 2040
            dest_ptr += 128
            
            for d in range(2): # Overall loop delta (8, 0)
                # delta (4, -8)
                src_ptr -= 2044
                
                for y in range(8): # Overall loop delta (0, 8)
                    # delta (-256, 1) ... cancels
                                            
                    for clock in range(4): # Overall loop delta (256, 0)
                        # delta (128, 0)
                        src_ptr += 128

                        q = [0 for _ in range(len(PLANES))]

                        for bit in range(8): # Overall loop delta (-64, 0)
                            # delta (-8, 0)
                            src_ptr -= 8
                            c = display[src_ptr]

                            for i in range(len(PLANES)):
                                q[i] <<= 1
                                q[i] |= lut[i][c]
                    
                        for i in range(len(PLANES)):
                            buffer[dest_ptr + 6144 * i] = (q[i] >> 16) & 0xFF
                            buffer[dest_ptr + 6144 * i + 64] = (q[i] >> 8) & 0xFF
                            buffer[dest_ptr + 6144 * i + 128] = (q[i] >> 0) & 0xFF
                        
                        dest_ptr += 1            
                            
'''         
for a, b in zip(twiddle.blit_inner(get_bit, lambda bits: list(bits)), twiddle_fast()):
    print(a, b)
    if a != b:
        print("Mismatch!")
        time.sleep(1)
'''
direct_buffer = bytearray(1536 * 12)

while True:
    for i in range(256 * 64):
        display[i] = random.randint(0, 255)

    start = time.time()
    twiddle_old.blit(back, display)
    end = time.time()

    print(f"Old: {end - start:.3f} seconds")

    p = ((i, j) for i in range(12) for j in range(1536))
    start = time.time()
    twiddle_fast_direct4(direct_buffer, display)
    end = time.time()

    print(f"New: {end - start:.3f} seconds")

    for i, b1 in enumerate(back):
        if b1 != direct_buffer[1536 * i:1536 * (i + 1)]:
            print("Mismatch!")
            exit(1)

    print("OK")