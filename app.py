# Micropython LED panel driver

from machine import Pin
import rp2
import twiddle

import sys
from sys import exit
import _thread
from array import array
import time
import binascii

if False:
    from typing import Iterable, TypeAlias
    # type BitColour = tuple[int, int, int]
    BitColour: typing.TypeAlias = tuple[int, int, int]

BLACK = 0
WHITE = 0b11111111

qr_data = [[False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, False, False, True, False, True, False, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, True, True, False, True, False, True, False, False, False, False, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, False, False, True, True, True, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, False, True, False, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, False, True, False, False, False, False, True, False, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, True, True, False, True, False, False, False, False, False, True, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, False, True, False, True, False, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, True, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, False, True, True, True, False, False, True, False, True, False, True, False, True, False, True, False, False, False, False, False], [False, False, False, False, False, False, True, False, True, False, False, False, False, False, False, False, False, True, True, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, False, True, True, True, False, False, True, False, True, False, True, True, True, True, True, True, False, False, True, True, False, False, False, False, False], [False, False, False, False, True, True, False, False, True, True, False, False, True, False, True, True, False, True, False, False, True, True, True, False, False, False, False, False, False], [False, False, False, False, False, False, False, True, True, True, True, False, True, True, False, False, True, False, True, False, True, True, False, False, True, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, True, False, True, False, False, False, False, True, True, True, True, False, True, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, True, False, True, True, False, True, True, False, False, True, True, False, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, False, True, True, False, False, True, False, True, True, True, True, True, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, False, True, False, False, True, True, True, True, False, True, True, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, True, True, False, False, False, False, False, True, False, True, False, False, False, False, False, False], [False, False, False, False, True, False, True, True, True, False, True, False, True, False, False, False, True, False, True, True, False, False, True, False, False, False, False, False, False], [False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, True, False, True, False, False, True, True, True, False, False, False, False, False, False], [False, False, False, False, True, True, True, True, True, True, True, False, True, False, True, False, True, False, True, True, False, True, False, True, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False], [False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]]

display: bytearray = bytearray(256 * 64)

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
    sm = rp2.StateMachine(0, pioclk, freq=50000000, out_base = p1d1, set_base = clk1)

    sm.active(1)
    
    # Run the display-update loop on the second core
    _thread.start_new_thread(displayupdate, ())

# Set the brightness of the panels by configuring the driver chip
# Minimum brightness = 0
# Maximum brightness = 63
def dim(v: int):
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

front = bytearray(1536 * 4 * len(PLANES))
back = bytearray(1536 * 4 * len(PLANES))
front_planes = [front[i * 1536: (i + 1) * 1536] for i in range(4 * len(PLANES))]

def blit() -> None:
    global front, back
    global front_planes

    twiddle.twiddle(back, display)

    back, front = front, back
    front_planes = [front[i * 1536: (i + 1) * 1536] for i in range(4 * len(PLANES))]


avg_loop_duration = 0

# This code outputs data into the panel, one address-line (1/4 of the
# panel) per loop.
def displayupdate():
    global avg_loop_duration

    plane_indices = [0, 1, 0, 2, 0, 1, 0]
    # plane_indices = [0]

    while True:
        # Hold time for plane #0
        m = 2

        for p in plane_indices:
            for address in range(4 * p, 4 * p + 4):
                loop_start = time.ticks_us()

                # Output this buffer to the state machine's FIFO
                sm.put(front_planes[address])
                
                while sm.tx_fifo() > 0:
                    pass # Wait for FIFO to empty

                loop_duration = time.ticks_us() - loop_start
                avg_loop_duration = (avg_loop_duration * 15 + loop_duration) >> 4

                # Disable display while updating
                oe.value(1)

                a0.value(((address >> 0) & 1) != 0)
                a1.value(((address >> 1) & 1) != 0)

                # Latch the data.
                lat.toggle()
                # time.sleep_us(1)
                
                lat.toggle()

                # Re-enable display
                oe.value(0)

                # Show this for a bit.
                time.sleep_us(m)

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
    global avg_loop_duration
    global display

    setup()

    print('Moo')
    clear()

    while True:
        # Read 332-encoded frame data from stdin
        packet = sys.stdin.readline().strip()
        temp = bytearray(4096)

        try:
            if packet:
                now = time.ticks_ms()
                mode, x0, y0, w, h, data = packet.split(',', 5)
                x0, y0, w, h = int(x0), int(y0), int(w), int(h)
                # data = binascii.a2b_base64(data)
                twiddle.b64decode(temp, data)

                # 'Raw' 332 data
                if mode == 'R':
                    twiddle.blit(display, 256, temp, x0, y0, w, h)
                    
                # Solid colour
                elif mode == '0':
                    twiddle.fill_332(display, 256, temp[0], x0, y0, w, h)
                
                # Per-block palette (with 1, 2, 3, 4 index bits)
                elif mode == '1':
                    twiddle.blit_palettized(display, 256, temp, 1, x0, y0, w, h)
                    
                elif mode == '2':
                    twiddle.blit_palettized(display, 256, temp, 2, x0, y0, w, h)

                elif mode == '3':
                    twiddle.blit_palettized(display, 256, temp, 3, x0, y0, w, h)
                    
                elif mode == '4':
                    twiddle.blit_palettized(display, 256, temp, 4, x0, y0, w, h)

                # RLE-encoded per-block palette
                elif mode == 'A':
                    twiddle.blit_palettized_rle(display, 256, temp, 1, x0, y0, w, h)
                    
                elif mode == 'B':
                    twiddle.blit_palettized_rle(display, 256, temp, 2, x0, y0, w, h)

                elif mode == 'C':
                    twiddle.blit_palettized_rle(display, 256, temp, 3, x0, y0, w, h)
                    
                elif mode == 'D':
                    twiddle.blit_palettized_rle(display, 256, temp, 4, x0, y0, w, h)
                
                else:
                    print(f'Unknown mode: {mode}')
                    continue

                delta = time.ticks_ms() - now
                # print(f"Frame {mode} ({w}x{h}) processed in {delta} ms")
                
            else:
                # Flush buffer on a blank line

                blit()
                print(f'Frame rendered. Avg loop duration: {avg_loop_duration}us')

        except Exception as e:
            print(f'Parse error: {e}')

main()