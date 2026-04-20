import twiddle_old
import twiddle
import random
import time

display = bytearray(256 * 64)
back = [bytearray(1536) for _ in range(12)]

while True:
    for i in range(256 * 64):
        display[i] = random.randint(0, 255)

    start = time.time()
    twiddle_old.blit(back, display)
    end = time.time()

    print(f"Old: {end - start:.3f} seconds")

    p = ((i, j) for i in range(12) for j in range(1536))
    direct_buffer = bytearray(1536 * 12)
    start = time.time()
    twiddle.blit(direct_buffer, display)
    end = time.time()

    print(f"New: {end - start:.3f} seconds")

    for i, b1 in enumerate(back):
        if b1 != direct_buffer[1536 * i:1536 * (i + 1)]:
            print("Mismatch!")
            exit(1)

    print("OK")