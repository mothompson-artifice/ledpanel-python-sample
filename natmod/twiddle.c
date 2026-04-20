// MicroPython native module: twiddle
// Target: RP2040 (armv6m / Cortex-M0+)
//
// Ported from twiddle.py — converts a 256x64 display bytearray into packed
// bitstream buffers for the LED panel shift-register chain.

#include "py/dynruntime.h"

// ---------------------------------------------------------------------------
// Placeholder: will become blit(back, display)
// ---------------------------------------------------------------------------

uint32_t lut[3][256];

static void build_lut(uint32_t* lut, uint8_t r, uint8_t g, uint8_t b) {
    for (int c = 0; c < 256; c++) {
        uint32_t q = 0;
        q |= ((c >> r) & 1) << 0;
        q |= ((c >> g) & 1) << 8;
        q |= ((c >> b) & 1) << 16;

        lut[c] = q;
    }
}

// blit(back: list[bytearray], display: bytearray) -> None
static mp_obj_t variant4(mp_obj_t dest_obj, mp_obj_t src_obj) {
    mp_buffer_info_t dest_bufinfo;
    mp_buffer_info_t src_bufinfo;

    mp_get_buffer_raise(dest_obj, &dest_bufinfo, MP_BUFFER_WRITE);
    mp_get_buffer_raise(src_obj, &src_bufinfo, MP_BUFFER_READ);

    // Validate expected buffer sizes.
    if (dest_bufinfo.len != 3 * 6144)
        mp_raise_ValueError(MP_ERROR_TEXT("dest buffer must be 18432 bytes"));
        
    if (src_bufinfo.len != 256 * 64)
        mp_raise_ValueError(MP_ERROR_TEXT("src buffer must be 16384 bytes"));
        
    uint8_t* dest = dest_bufinfo.buf;
    const uint8_t* src = src_bufinfo.buf;

    dest -= 128;
    
    // With apologies to Mr. Donald Knuth
    uint32_t q[3] = { 0, 0, 0 };


    src += 16323;

    int addr = 4;
    while (--addr >= 0) {
        src -= 16383;

        int subtile = 8;

        while (--subtile >= 0) {
            src += 2040;
            dest += 128;

            int d = 2;

            while (--d >= 0) {
                src -= 2044;

                int y = 8;

                while (--y >= 0) {
                    int clock = 4;

                    while (--clock >= 0) {
                        src += 128;

                        q[0] = 0;
                        q[1] = 0;
                        q[2] = 0;

                        int bit = 8;
                        while (--bit >= 0) {
                            src -= 8;
                            uint8_t c = *src;

                            q[0] <<= 1;
                            q[0] |= lut[0][c];

                            q[1] <<= 1;
                            q[1] |= lut[1][c];

                            q[2] <<= 1;
                            q[2] |= lut[2][c];
                        }

                        dest[0] = (q[0] >> 16) & 0xFF;
                        dest[64] = (q[0] >> 8) & 0xFF;
                        dest[128] = (q[0] >> 0) & 0xFF;
                        dest[6144] = (q[1] >> 16) & 0xFF;
                        dest[6144 + 64] = (q[1] >> 8) & 0xFF;
                        dest[6144 + 128] = (q[1] >> 0) & 0xFF;
                        dest[12288] = (q[2] >> 16) & 0xFF;
                        dest[12288 + 64] = (q[2] >> 8) & 0xFF;
                        dest[12288 + 128] = (q[2] >> 0) & 0xFF;

                        ++dest;
                    }
                }
            }
        }
    }

    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2(variant4_obj, variant4);

// ---------------------------------------------------------------------------
// Module entry point
// ---------------------------------------------------------------------------

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY

    mp_store_global(MP_QSTR_blit, MP_OBJ_FROM_PTR(&variant4_obj));

    build_lut(lut[0], 7, 4, 1);
    build_lut(lut[1], 6, 3, 0);
    build_lut(lut[2], 5, 2, 1);

    MP_DYNRUNTIME_INIT_EXIT
}
