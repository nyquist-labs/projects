#include <stdio.h>
#include <stdint.h>
typedef struct { uint8_t buf[8]; uint8_t head, tail, count; } ring_t;
int ring_push(ring_t *r, uint8_t v); int ring_pop(ring_t *r, uint8_t *v);
uint16_t crc16_ccitt(const uint8_t *d, int n); int16_t q15_mul(int16_t a, int16_t b);
static int fails = 0, total = 0;
#define CHECK(c) do { total++; if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
int main(void) {
    ring_t r = {0}; uint8_t v;
    CHECK(!ring_pop(&r, &v));
    for (int i = 0; i < 8; i++) CHECK(ring_push(&r, (uint8_t)i));
    CHECK(!ring_push(&r, 99));
    CHECK(ring_pop(&r, &v) && v == 0);
    CHECK(ring_push(&r, 8));
    for (int i = 1; i <= 8; i++) CHECK(ring_pop(&r, &v) && v == i);
    CHECK(!ring_pop(&r, &v));
    CHECK(crc16_ccitt((const uint8_t *)"123456789", 9) == 0x29B1);
    CHECK(crc16_ccitt((const uint8_t *)"", 0) == 0xFFFF);
    CHECK(q15_mul(16384, 16384) == 8192);
    CHECK(q15_mul(-32768, -32768) == 32767);
    CHECK(q15_mul(-16384, 16384) == -8192);
    CHECK(q15_mul(1, 16384) == 1);
    printf("RES total %d\nRES fails %d\n", total, fails);
    return fails != 0;
}
