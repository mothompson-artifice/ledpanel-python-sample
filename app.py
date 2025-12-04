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

display: bytearray = bytearray(256 * 64)

# Clock: x >> 6
# Address: x % 4
# Data: (x >> 3) % 8
def get_bitstream(data: int, address: int, clock: int, colour_mask_r: int, colour_mask_g: int, colour_mask_b: int) -> Iterable[bool]:
    global display

    x = (clock << 6) | (data << 3) | address

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
    clock_domains = zip(*[get_bytestream(address, clock, colour_mask_r, colour_mask_g, colour_mask_b) for clock in range(4)])
    
    for clock_domain in clock_domains:
        for byte in clock_domain:
            yield byte
        

# GPIO pins for panel
# The pins below match the driver board built by Luis
#
# Change them as needed for your panel

oe=Pin(16,Pin.OUT)
lat=Pin(17,Pin.OUT)

# D2 needs to be immediately after D1, or the PIO won't work
p1d1 = Pin(0, Pin.OUT) # Also A0
p1d2 = Pin(1, Pin.OUT) # Also A1
p2d1 = Pin(2, Pin.OUT)
p2d2 = Pin(3, Pin.OUT)
p3d1 = Pin(4, Pin.OUT)
p3d2 = Pin(5, Pin.OUT)
p4d1 = Pin(6, Pin.OUT)
p4d2 = Pin(7, Pin.OUT)  

clk1 = Pin(18, Pin.OUT) 
clk5 = Pin(19, Pin.OUT)
clk9 = Pin(20, Pin.OUT)
clk13 = Pin(21, Pin.OUT)

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
    sm = rp2.StateMachine(0, pioclk, freq=10000000, out_base = p1d1, set_base = clk1)

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
    
buffers: list[array] = [bytearray(1540) for _ in range(4)]
for addr in range(4):
    # Have the PIOs leave the address bits in the right state
    v = addr * 0x55
    for j in range(4):
        buffers[addr][1536 + j] = v

def blit() -> None:
    global buffers
   
    # For each address line
    for addr in range(4):
        buf = buffers[addr]
        i = 0
        for byte in get_interleaved(addr, 0x20, 0x04, 0x01):
            buf[i] = byte
            i += 1

        if i != 1536:
            print("Warning: blit size mismatch", i)


# This code outputs data into the panel, one address-line (1/4 of the
# panel) per loop.
def displayupdate():
    while True:
        for address in range(4):
            # Disable display while updating
            oe.value(1)

            sm.active(1)

            # Output this buffer to the state machine's FIFO
            sm.put(buffers[address])   
            
            while sm.tx_fifo() > 0:
                pass # Wait for FIFO to empty
            
            # Stop the machine
            # sm.active(0)

            # time.sleep_ms(1)

            # Latch the data.
            lat.toggle()
            time.sleep_us(10)
            
            lat.toggle()

            # Re-enable display
            oe.value(0)

            # Show this for a bit.
            time.sleep_us(125)

def get_offset(x: int, y: int) -> int:
    return y * 256 + x

def set_pixel(x: int, y: int, r: bool, g: bool, b: bool):
    global display
    c = 0
    if r:
        c |= 0xE0
    if g:
        c |= 0x1C
    if b:
        c |= 0x03

    display[get_offset(x, y)] = 0xFF
    
def clear():
    global display
    for i in range(256 * 64):
        display[i] = BLACK
    
def main():
    setup()

    print('Moo')
    for x in range(256):
        for y in range(64):
            set_pixel(x, y, (x // 8) % 2 == 0, (y // 8) % 2 == 0, ((x // 8) + (y // 8)) % 2 == 0)
            # set_pixel(x, y, True, False, False)
    
    # Display doesn't change until blit() is called
    blit()

# Uncomment this to auto-start on import. If this file is called main.py
# it will auto-run on panel boot.

main()

for j in range(4):
    for i, v in enumerate(buffers[j]):
        if v != 0xFF:
            print(f'buffers[{j}][{i}] = {v}')


while True:
    pass