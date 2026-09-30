from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-155", title="A custom Wokwi chip: I²C 12-bit DAC written with the Chips API", level="H",
    tools="C chip model in the style of the Wokwi Chips API (chip.c + chip.json) with a host-side mock of the API for testing",
    summary="Write a simulated I²C 12-bit DAC (MCP4725-like) as a Wokwi custom chip, then test it on the PC by mocking the "
            "Chips API: the harness plays an I²C master, sends 4,096 codes and checks the analog output voltage and "
            "the fast-write command format.",
    problem="Simulators only ship common parts. How do you add your own component — and test its model before trusting it?",
    theory=r"""MCP4725 fast-write: two bytes [0 0 PD1 PD0 D11 D10 D9 D8][D7…D0]; V_out = V_DD·code/4096. Resolution = 3.3 V/4096 = 0.806 mV; the model must reproduce
every code exactly, ignore bytes for other addresses and answer ACK only for its own address (0x60).""",
    method="""chip.c implements the Wokwi callbacks (`chip_init`, `on_i2c_connect`, `on_i2c_write`, `on_i2c_disconnect`) and drives an analog pin. A host mock
(`wokwi-api-mock.h`) implements `i2c_init`, `pin_dac_write` and friends so the same chip.c compiles on the PC; the harness writes all codes.""",
)

CHIP = r"""
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
"""
JSON = r"""{ "name": "MCP4725-like DAC", "author": "Anna Lin (Nyquist Labs)", "pins": ["VCC", "GND", "SCL", "SDA", "OUT"], "controls": [] }"""
MOCK = r"""
// wokwi-api.h (host mock) — just enough of the Wokwi Chips API to unit-test chip.c on a PC
#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef int pin_t;
enum { INPUT, OUTPUT, ANALOG };
typedef struct { void *user_data; uint32_t address; pin_t scl, sda;
  bool (*connect)(void *, uint32_t, bool); uint8_t (*read)(void *); bool (*write)(void *, uint8_t); void (*disconnect)(void *); } i2c_config_t;
pin_t pin_init(const char *name, int mode);
void pin_dac_write(pin_t pin, float v);
int i2c_init(const i2c_config_t *cfg);
"""
HARNESS = r"""
#include <stdio.h>
#include "wokwi-api.h"
static i2c_config_t bus; static float last_v = -1;
pin_t pin_init(const char *name, int mode) { (void)name; (void)mode; return 1; }
void pin_dac_write(pin_t pin, float v) { (void)pin; last_v = v; }
int i2c_init(const i2c_config_t *cfg) { bus = *cfg; return 0; }
void chip_init(void);
int main(void) {
    chip_init();
    int wrong_addr_acks = 0;
    for (uint32_t a = 0; a < 128; a++) if (a != 0x60 && bus.connect(bus.user_data, a, false)) wrong_addr_acks++;
    printf("RES wrong_addr_acks %d\n", wrong_addr_acks);
    for (int code = 0; code < 4096; code++) {
        bus.connect(bus.user_data, 0x60, false);
        bus.write(bus.user_data, (uint8_t)(code >> 8)); bus.write(bus.user_data, (uint8_t)(code & 0xFF));
        bus.disconnect(bus.user_data);
        printf("V %d %.7f\n", code, last_v);
    }
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"chip.c": CHIP, "harness.c": HARNESS, "wokwi-api.h": MOCK, "chip.json": JSON})
    r = fwk.results(log)
    V = fwk.rows(log, "V")
    code, v = V[:, 0], V[:, 1]
    ideal = 3.3 * code / 4096
    p.compare("Addresses other than 0x60 that ACK (of 127)", 0, r["wrong_addr_acks"], "", kind="abs")
    p.compare("Max |V_out − 3.3·code/4096| over all 4,096 codes", 0, np.max(np.abs(v - ideal)), "V", kind="abs", note="float32 rounding only")
    p.compare("LSB size", 3.3 / 4096, np.median(np.diff(v)), "V", tol=0.1)
    p.compare("Monotonic (all steps > 0)", 1, int(np.all(np.diff(v) > 0)), "", kind="abs")
    fig, ax = p.fig()
    ax.plot(code, v, color=C_MEAS, label="chip model output")
    ax.plot(code, ideal, "--", color=C_PRED, label="3.3·code/4096")
    style_axes(ax, "DAC code", "V_out (V)", "Custom chip transfer function (tested on the host)")
    p.save(fig, "dac", "The chip model reproduces the ideal transfer function for every code.")
    p.section("Use it in Wokwi", "Add `firmware/chip.c` and `firmware/chip.json` to a Wokwi project as a custom chip (the real `wokwi-api.h` is provided by Wokwi); "
              "`firmware/wokwi-api.h` and `firmware/harness.c` are only the PC-side test mock.")
    p.discuss("""Because the chip is written against a narrow API, mocking that API on the PC turns an in-browser component into unit-testable
C: all 4,096 codes produce the ideal voltage (to float32 precision), the model ignores other I²C addresses, and the output is
monotonic. That is the same pattern professional firmware teams use — a hardware-abstraction layer thin enough to fake — and it is
the subject of SL-156.""")
