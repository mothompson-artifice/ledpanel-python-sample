# Micropython LED panel driver

from machine import Pin
import rp2

from sys import exit
import _thread
from array import array
import time

if False:
    from typing import Iterable, TypeAlias
    # type BitColour = tuple[int, int, int]
    BitColour: typing.TypeAlias = tuple[int, int, int]

BLACK = 0
WHITE = 0b11111111

qr_data = [[False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, False, False, True, False, True, False, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, True, True, False, True, False, True, False, False, False, False, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, False, False, True, True, True, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, False, True, False, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, False, True, False, False, False, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, True, True, False, True, False, False, False, False, False, True, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, False, True, False, True, False, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, False, True, True, True, False, False, True, False, True, False, True, False, True, False, True, False, False, False, False, False], [False, False, False, False, False, False, True, False, True, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, False, True, True, True, False, False, True, False, True, False, True, True, True, True, True, True, False, False, True, True, False, False, False, False, False], [False, False, False, False, True, True, False, False, True, True, False, False, True, False, True, True, False, True, False, False, True, True, True, False, False, False, False, False, False], [False, False, False, False, False, False, False, True, True, True, True, False, True, True, False, False, True, False, True, False, True, True, False, False, True, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, True, False, True, False, False, False, False, True, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, True, False, True, True, False, True, True, False, False, True, True, False, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, False, True, True, False, False, True, False, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, False, True, False, False, True, True, True, True, False, True, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, True, False, False, False, False, False, True, False, True, False, False, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, False, False, False, True, False, True, True, False, False, True, False, False, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, True, False, True, False, False, True, True, True, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, False, True, False, True, False, True, True, False, True, False, True, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]]

display: bytearray = bytearray(256 * 64)

# Clock: x >> 6
# Address: x % 4
# Data: (x >> 3) % 8
def get_bitstream(data: int, address: int, clock: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[bool]:
    global display

    x = (clock << 6) | ((7 ^ data) << 3) | address

    # 16 bits: one driver.
    def generate_driver_bitstream(subtile: int, colour_mask: int) -> Iterable[bool]:
        for i in range(8):
            y = subtile * 8 + i
            o = get_offset(x, y)
            yield (display[o] & colour_mask) != 0

        for i in range(8):
            y = subtile * 8 + i
            o = get_offset(x + 4, y)
            yield (display[o] & colour_mask) != 0

    # 3 drivers: one subtile, 48 bits.
    def generate_subtile_bitstream(subtile: int) -> Iterable[bool]:
        # Blue
        yield from generate_driver_bitstream(subtile, colour_mask_b)

        # Green
        yield from generate_driver_bitstream(subtile, colour_mask_g)

        # Red
        yield from generate_driver_bitstream(subtile, colour_mask_r)

    # 8 subtiles: 384 bits.
    for subtile in range(8):
        yield from generate_subtile_bitstream(subtile)

# Clock: x >> 6
# Address: x % 4
def get_bytestream(address: int, clock: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[int]:
    def bits_to_byte(bits: Iterable[tuple[bool, ...]]) -> int:
        v: int = 0
        for b in bits:
            v <<= 1
            if b:
                v |= 1

        return v

    # 64 subtiles: 4 panels.
    for bits in zip(*[get_bitstream(data, address, clock, colour_mask_r, colour_mask_g, colour_mask_b) for data in range(8)]):
        yield bits_to_byte(bits)
    
def get_interleaved(address: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[int]:
    clk0 = get_bytestream(address, 0, colour_mask_r, colour_mask_g, colour_mask_b)
    clk1 = get_bytestream(address, 1, colour_mask_r, colour_mask_g, colour_mask_b)
    clk2 = get_bytestream(address, 2, colour_mask_r, colour_mask_g, colour_mask_b)
    clk3 = get_bytestream(address, 3, colour_mask_r, colour_mask_g, colour_mask_b)

    clock_domains = zip(clk0, clk1, clk2, clk3)
    
    for b0, b1, b2, b3 in clock_domains:
        yield b0
        yield b1
        yield b2
        yield b3
        

# GPIO pins for panel
# The pins below match the driver board built by Luis
#
# Change them as needed for your panel

oe = Pin(6, Pin.OUT)
lat = Pin(7, Pin.OUT)

# D2 needs to be immediately after D1, or the PIO won't work
p1d1 = Pin(8, Pin.OUT)
p1d2 = Pin(9, Pin.OUT)
p2d1 = Pin(10, Pin.OUT)
p2d2 = Pin(11, Pin.OUT)
p3d1 = Pin(12, Pin.OUT)
p3d2 = Pin(13, Pin.OUT)
p4d1 = Pin(14, Pin.OUT)
p4d2 = Pin(15, Pin.OUT)  

a0 = Pin(4, Pin.OUT)
a1 = Pin(5, Pin.OUT)

clk1 = Pin(0, Pin.OUT) 
clk5 = Pin(1, Pin.OUT)
clk9 = Pin(2, Pin.OUT)
clk13 = Pin(3, Pin.OUT)

@rp2.asm_pio(out_init=(rp2.PIO.OUT_LOW,) * 8, set_init=(rp2.PIO.OUT_LOW,) * 4, autopull = True, pull_thresh = 0, fifo_join = rp2.PIO.JOIN_TX)
def pioclk():
    # Output data for clk1-4
    out(null, 24)
    out(pins, 8)
    set(pins, 1)
    # ... for clk5-8
    out(null, 24)
    out(pins, 8)
    set(pins, 2)
    # ... for clk9-12
    out(null, 24)
    out(pins, 8)
    set(pins, 4)
    # and for clk13-16
    out(null, 24)
    out(pins, 8)
    set(pins, 8)
    set(pins, 0)
    
# PIO state machine
sm = None

# Get the panel ready
def setup():
    # Output disable
    oe.value(1)

    # Set LAT and CLK to 0
    lat.value(0)
    for clk in (clk1, clk5, clk9, clk13):
        clk.value(0)

    # Feed in zeros to clear the shift registers
    for data in (p1d1, p1d2, p2d1, p2d2, p3d1, p3d2, p4d1, p4d2):
        data.value(0)

    # Clock 384 bits into each register
    for _ in range(384):
        for clk in (clk1, clk5, clk9, clk13):
            clk.toggle()
        for clk in (clk1, clk5, clk9, clk13):
            clk.toggle()

    # Latch
    lat.toggle()
    lat.toggle()

    # Set overall brightness
    dim(0)      # 12.5%. As low as it can be.
    # This can only be set before the PIO state machine is initialised,
    # as the state machine takes over the GPIO pins

    # Clear the display
    clear()

    global sm
    sm = rp2.StateMachine(0, pioclk, freq=5000000, out_base = p1d1, set_base = clk1)

    sm.active(1)
    
    # Run the display-update loop on the second core
    _thread.start_new_thread(displayupdate, ())

# Set the brightness of the panels by configuring the driver chip
# Minimum brightness = 0
# Maximum brightness = 63
def dim(v):
    lat.value(0)

    clocks = (clk1, clk5, clk9, clk13)
    data_pins = (p1d1, p1d2, p2d1, p2d2, p3d1, p3d2, p4d1, p4d2)

    # Take all clocks low
    for clk in clocks:
        clk.value(0)

    # ... and all data
    for d in data_pins:
        d.value(0)

    # Set LED driver chip to desired brightness
    # 0111000101xxxxxx where xxxxxx = brightness (from 12.5% to 200%)
    # See LED driver datasheet for explanation
    preamble = [ 0, 1, 1, 1, 0, 0, 0, 1, 0, 1]
    data = [ 1 if v & (2**x) else 0 for x in range(5,-1,-1)]

    # Do this 24 times. Once per driver chip. Otherwise only part of the
    # panel will be updated.
    for count in range(24):
        for c,x in enumerate(preamble+data):
            for d in data_pins:
                d.value(x)
            for clk in clocks:
                clk.toggle()
                clk.toggle()

            if (c==11):
                lat.value(1)

        lat.value(0)
    

PLANES = [(0x80, 0x10, 0x02), (0x40, 0x08, 0x01), (0x20, 0x04, 0x02)]

front: list[bytearray] = [bytearray(1536) for _ in range(4 * len(PLANES))]
back: list[bytearray] = [bytearray(1536) for _ in range(4 * len(PLANES))]

def blit() -> None:
    global front, back
   
    for p, (colour_mask_r, colour_mask_g, colour_mask_b) in enumerate(PLANES):
        # For each address line
        for addr in range(4):
            buf = back[4 * p + addr]
            i = 0
            for byte in get_interleaved(addr, colour_mask_r, colour_mask_g, colour_mask_b):
                buf[i] = byte
                i += 1

            if i != 1536:
                print("Warning: blit size mismatch", i)

    back, front = front, back

# This code outputs data into the panel, one address-line (1/4 of the
# panel) per loop.
def displayupdate():
   
    while True:
        # Hold time for plane #0
        m = 240

        for p in range(len(PLANES)):
            for address in range(4 * p, 4 * p + 4):
                # Disable display while updating
                oe.value(1)

                a0.value(((address >> 0) & 1) != 0)
                a1.value(((address >> 1) & 1) != 0)

                # Output this buffer to the state machine's FIFO
                sm.put(front[address])   
                
                while sm.tx_fifo() > 0:
                    pass # Wait for FIFO to empty

                # Latch the data.
                lat.toggle()
                time.sleep_us(10)
                
                lat.toggle()

                # Re-enable display
                oe.value(0)

                # Show this for a bit.
                time.sleep_us(m)

                m >>= 1

def get_offset(x: int, y: int) -> int:
    return y * 256 + x

def set_pixel(x: int, y: int, c: int):
    global display
    
    display[get_offset(x, y)] = c
    
def clear():
    global display
    for i in range(256 * 64):
        display[i] = BLACK
    
def rgb332(r: int, g: int, b: int) -> int:
    return ((r & 0b11100000) | ((g & 0b11100000) >> 3) | ((b & 0b11000000) >> 6))

def main():
    setup()

    print('Moo')
    while True:
        clear()
        
        t = time.ticks_ms()
        for y, row in enumerate(qr_data):
            for x, value in enumerate(row):
                c = WHITE if value else BLACK
                set_pixel(32 + 2 * x, 2 * y, c)
                set_pixel(32 + 2 * x + 1, 2 * y, c)
                set_pixel(32 + 2 * x, 2 * y + 1, c)
                set_pixel(32 + 2 * x + 1, 2 * y + 1, c)
                
            # Display doesn't change until blit() is called

        print('Set pixels done', time.ticks_diff(time.ticks_ms(), t))
        t = time.ticks_ms()
        blit()
        print('Blit done', time.ticks_diff(time.ticks_ms(), t))
        time.sleep_ms(100)
        
# Uncomment this to auto-start on import. If this file is called main.py
# it will auto-run on panel boot.

main()

while True:
    pass