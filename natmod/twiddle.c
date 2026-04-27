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

uint16_t lut_332_565[256];

uint8_t b64lut[256];

static void memcpy2(void* dest, const void* src, size_t n) {
    uint8_t* d = dest;
    const uint8_t* s = src;

    while (n--)
        *d++ = *s++;
}   

static void build_lut(uint32_t* lut, uint8_t r, uint8_t g, uint8_t b) {
    for (int c = 0; c < 256; c++) {
        uint32_t q = 0;
        q |= ((c >> r) & 1) << 0;
        q |= ((c >> g) & 1) << 8;
        q |= ((c >> b) & 1) << 16;

        lut[c] = q;
    }
}

static uint16_t convert_332_565(uint8_t c) {
    uint16_t q = 0;
    q |= ((c >> 5) & 7) << 11;
    q |= ((c >> 2) & 7) << 5;
    q |= ((c >> 0) & 3) << 0;

    return q;
}

static void build_lut_332_565(uint16_t* lut) {
    for (int c = 0; c < 256; c++)
        lut[c] = convert_332_565(c);
}

static void build_b64lut(uint8_t* lut) {
    for (int c = 0; c < 256; c++) {
        if (c >= 'A' && c <= 'Z')
            lut[c] = c - 'A';
        else if (c >= 'a' && c <= 'z')
            lut[c] = c - 'a' + 26;
        else if (c >= '0' && c <= '9')
            lut[c] = c - '0' + 52;
        else if (c == '+')
            lut[c] = 62;
        else if (c == '/')
            lut[c] = 63;
        else
            lut[c] = 0xFF;
    }
}

// twiddle(back: list[bytearray], display: bytearray) -> None
static mp_obj_t twiddle(mp_obj_t dest_obj, mp_obj_t src_obj) {
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

static MP_DEFINE_CONST_FUN_OBJ_2(twiddle_obj, twiddle);

// blit(target: bytearray, stride: int, source: bytearray, x: int, y: int, w: int, h: int) -> None
static mp_obj_t blit(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t dest_bufinfo;
    mp_buffer_info_t src_bufinfo;

    mp_get_buffer_raise(args[0], &dest_bufinfo, MP_BUFFER_WRITE);
    mp_get_buffer_raise(args[2], &src_bufinfo, MP_BUFFER_READ);

    uint8_t* dest = dest_bufinfo.buf;
    const uint8_t* src = src_bufinfo.buf;

    int stride = mp_obj_get_int(args[1]);
    int x = mp_obj_get_int(args[3]);
    int y = mp_obj_get_int(args[4]);
    int w = mp_obj_get_int(args[5]);
    int h = mp_obj_get_int(args[6]);

    // Basic bounds checks
    if (x < 0 || y < 0 || w < 0 || h < 0)
        mp_raise_ValueError(MP_ERROR_TEXT("x, y, w, h must be non-negative"));

    if (w == 0 || h == 0)
        return mp_const_none;

    const unsigned int dest_max = (y + h - 1) * stride + x + w;
    if (dest_max > dest_bufinfo.len)
        mp_raise_ValueError(MP_ERROR_TEXT("dest buffer too small for given x, y, w, h, stride"));

    const unsigned int src_max = h * w;
    if (src_max > src_bufinfo.len)
        mp_raise_ValueError(MP_ERROR_TEXT("source buffer too small for given w, h"));
        
    uint8_t* d = dest + y * stride + x;

    for (int j = 0; j < h; j++) {
        memcpy2(d, src, w);

        src += w;
        d += stride;
    }

    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(blit_obj, 7, 7, blit);

// blit_332_565(target: bytearray, stride: int, source: bytearray, x: int, y: int, w: int, h: int) -> None
static mp_obj_t blit_332_565(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t dest_bufinfo;
    mp_buffer_info_t src_bufinfo;

    mp_get_buffer_raise(args[0], &dest_bufinfo, MP_BUFFER_WRITE);
    mp_get_buffer_raise(args[2], &src_bufinfo, MP_BUFFER_READ);

    uint16_t* dest = dest_bufinfo.buf;
    const uint8_t* src = src_bufinfo.buf;

    int stride = mp_obj_get_int(args[1]);
    int x = mp_obj_get_int(args[3]);
    int y = mp_obj_get_int(args[4]);
    int w = mp_obj_get_int(args[5]);
    int h = mp_obj_get_int(args[6]);

    // Basic bounds checks
    if (x < 0 || y < 0 || w < 0 || h < 0)
        mp_raise_ValueError(MP_ERROR_TEXT("x, y, w, h must be non-negative"));

    if (w == 0 || h == 0)
        return mp_const_none;

    const unsigned int dest_max = 2 * ((y + h - 1) * stride + x + w);
    if (dest_max > dest_bufinfo.len)
        mp_raise_ValueError(MP_ERROR_TEXT("dest buffer too small for given x, y, w, h, stride"));

    const unsigned int src_max = h * w;
    if (src_max > src_bufinfo.len)
        mp_raise_ValueError(MP_ERROR_TEXT("source buffer too small for given w, h"));
        
    uint16_t* d = dest + y * stride + x;

    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            uint8_t c = *src++;
            *d++ = lut_332_565[c];
        }
        d += stride - w;
    }

    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(blit_332_565_obj, 7, 7, blit_332_565);

// b64decode(dest: bytearray, source: str) -> None
static mp_obj_t b64decode(mp_obj_t dest_obj, mp_obj_t src_obj) {
    mp_buffer_info_t dest_bufinfo;

    mp_get_buffer_raise(dest_obj, &dest_bufinfo, MP_BUFFER_WRITE);

    uint8_t* dest = dest_bufinfo.buf;

    size_t src_len;
    const char* src = mp_obj_str_get_data(src_obj, &src_len);

    // Validate expected buffer sizes.
    if (dest_bufinfo.len < (src_len * 3) / 4)
        mp_raise_ValueError(MP_ERROR_TEXT("dest buffer too small for given source string"));

    size_t i = 0;
    while (i < src_len) {
        uint32_t q = 0;

        for (int j = 0; j < 4; j++) {
            q <<= 6;

            if (i >= src_len)
                break;

            char c = src[i++];
            uint8_t v = b64lut[(uint8_t)c];
            if (v == 0xFF) {
                if (c == '=')
                    break;
                else
                    mp_raise_ValueError(MP_ERROR_TEXT("invalid character in base64 string"));
            }
            q |= v;
        }

        *dest++ = (q >> 16) & 0xFF;
        *dest++ = (q >> 8) & 0xFF;
        *dest++ = (q >> 0) & 0xFF;
    }

    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2(b64decode_obj, b64decode);

// ---------------------------------------------------------------------------
// Module entry point
// ---------------------------------------------------------------------------

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args) {
    MP_DYNRUNTIME_INIT_ENTRY

    mp_store_global(MP_QSTR_twiddle, MP_OBJ_FROM_PTR(&twiddle_obj));
    mp_store_global(MP_QSTR_blit, MP_OBJ_FROM_PTR(&blit_obj));
    mp_store_global(MP_QSTR_blit_332_565, MP_OBJ_FROM_PTR(&blit_332_565_obj));
    mp_store_global(MP_QSTR_b64decode, MP_OBJ_FROM_PTR(&b64decode_obj));

    build_lut(lut[0], 7, 4, 1);
    build_lut(lut[1], 6, 3, 0);
    build_lut(lut[2], 5, 2, 1);

    build_lut_332_565(lut_332_565);
    build_b64lut(b64lut);

    MP_DYNRUNTIME_INIT_EXIT
}
