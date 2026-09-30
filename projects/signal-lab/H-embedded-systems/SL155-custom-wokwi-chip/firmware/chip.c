// chip.c — MCP4725-style 12-bit I2C DAC for Wokwi (Chips API)
#include "wokwi-api.h"
#include <stdlib.h>
typedef struct { pin_t out; uint8_t buf[2]; int n; uint16_t code; } chip_state_t;
static bool on_connect(void *u, uint32_t address, bool read) { chip_state_t *c = u; c->n = 0; return address == 0x60; }
static bool on_write(void *u, uint8_t data) {
    chip_state_t *c = u; if (c->n < 2) c->buf[c->n++] = data;
    if (c->n == 2) { c->code = (uint16_t)(((c->buf[0] & 0x0F) << 8) | c->buf[1]); pin_dac_write(c->out, 3.3f * c->code / 4096.0f); c->n = 0; }
    return true;
}
static uint8_t on_read(void *u) { chip_state_t *c = u; return (uint8_t)(c->code >> 4); }
static void on_disconnect(void *u) { (void)u; }
void chip_init(void) {
    chip_state_t *c = calloc(1, sizeof *c);
    c->out = pin_init("OUT", ANALOG);
    const i2c_config_t cfg = { .user_data = c, .address = 0x60, .scl = pin_init("SCL", INPUT), .sda = pin_init("SDA", INPUT),
        .connect = on_connect, .read = on_read, .write = on_write, .disconnect = on_disconnect };
    i2c_init(&cfg);
}
