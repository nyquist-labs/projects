#include <stdint.h>
#include <string.h>
typedef struct { uint8_t buf[8]; uint8_t head, tail, count; } ring_t;
int ring_push(ring_t *r, uint8_t v) { if (r->count == 8) return 0; r->buf[r->head] = v; r->head = (r->head + 1) & 7; r->count++; return 1; }
int ring_pop(ring_t *r, uint8_t *v) { if (r->count == 0) return 0; *v = r->buf[r->tail]; r->tail = (r->tail + 1) & 7; r->count--; return 1; }
uint16_t crc16_ccitt(const uint8_t *d, int n) { uint16_t c = 0xFFFF; for (int i = 0; i < n; i++) { c ^= (uint16_t)(d[i] << 8);
    for (int b = 0; b < 8; b++) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1); } return c; }
int16_t q15_mul(int16_t a, int16_t b) { int32_t p = ((int32_t)a * b + (1 << 14)) >> 15; if (p > 32767) p = 32767; if (p < -32768) p = -32768; return (int16_t)p; }
