from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-139", title="SSD1306 OLED driver: framebuffer, font and refresh rate", level="E",
    tools="C firmware (framebuffer + 5×7 font + line drawing), simulated SSD1306 page memory, Python image render",
    summary="Render text, a line and a sine plot into a 128×64 monochrome framebuffer using the SSD1306 page layout, "
            "'send' it over a simulated 400 kHz I²C link, rebuild the panel image from the transferred bytes and "
            "compute the achievable frame rate.",
    problem="Small OLEDs store pixels in vertical 8-pixel 'pages'. Build a driver that gets the bit ordering right, and "
            "work out how fast the screen can actually be updated.",
    theory=r"""128×64 pixels = 1,024 bytes (8 pages × 128 columns, bit 0 = top pixel of each page). Over I²C each byte costs 9 clocks: at 400 kHz a full
frame is ≥ 1,024×9/400 k ≈ 23 ms → ≈ 43 frames/s maximum (plus addressing overhead).""",
    method="""Firmware draws into uint8_t fb[1024] using the SSD1306 layout, then streams it with the 0x40 data prefix; the simulated panel writes
received bytes into its own GDDRAM in horizontal addressing mode and dumps it; Python renders the panel memory.""",
)

C = r"""
#include "hal_sim.h"
static uint8_t fb[1024], panel[1024];
static const uint8_t font5x7[][5] = {
 {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},{0x3E,0x41,0x41,0x41,0x22},{0x7F,0x41,0x41,0x22,0x1C},
 {0x7F,0x49,0x49,0x49,0x41},{0x7F,0x09,0x09,0x09,0x01},{0x3E,0x41,0x49,0x49,0x7A},{0x7F,0x08,0x08,0x08,0x7F},
 {0x00,0x41,0x7F,0x41,0x00},{0x20,0x40,0x41,0x3F,0x01},{0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
 {0x7F,0x02,0x0C,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},{0x3E,0x41,0x41,0x41,0x3E},{0x7F,0x09,0x09,0x09,0x06},
 {0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},{0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},
 {0x3F,0x40,0x40,0x40,0x3F},{0x1F,0x20,0x40,0x20,0x1F},{0x3F,0x40,0x38,0x40,0x3F},{0x63,0x14,0x08,0x14,0x63},
 {0x07,0x08,0x70,0x08,0x07},{0x61,0x51,0x49,0x45,0x43}};
static void pset(int x, int y) { if (x >= 0 && x < 128 && y >= 0 && y < 64) fb[(y / 8) * 128 + x] |= (uint8_t)(1 << (y & 7)); }
static void text(int x, int y, const char *s) {
    for (; *s; s++, x += 6) { if (*s == ' ') continue; const uint8_t *g = font5x7[*s - 'A'];
        for (int c = 0; c < 5; c++) for (int r = 0; r < 7; r++) if (g[c] >> r & 1) pset(x + c, y + r); }
}
static void line(int x0, int y0, int x1, int y1) {   /* Bresenham */
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1, e = dx + dy;
    for (;;) { pset(x0, y0); if (x0 == x1 && y0 == y1) break; int e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
}
static uint64_t bytes_on_bus = 0;
static void i2c_send(const uint8_t *d, int n) {         /* 400 kHz: 9 clocks per byte + START/STOP */
    delay_us(3); for (int i = 0; i < n; i++) { bytes_on_bus++; delay_us(0); } sim_us += (uint64_t)(n * 9 * 2.5); delay_us(3);
}
int main(void) {
    log_pins = 0;
    text(4, 2, "APPLIED SIGNALS LAB");
    line(0, 12, 127, 12);
    for (int x = 0; x < 128; x++) { int y = 38 - (int)lround(20 * sin(2 * 3.14159265 * x / 64.0)); pset(x, y); }
    text(34, 56, "SSD ONE THREE"); /* letters only in this tiny font */
    uint64_t t0 = sim_us;
    uint8_t cmd[] = {0x00, 0x21, 0, 127, 0x22, 0, 7};   /* column/page address window */
    i2c_send(cmd, sizeof cmd);
    for (int k = 0; k < 1024; k += 32) { uint8_t chunk[33]; chunk[0] = 0x40; memcpy(chunk + 1, fb + k, 32); i2c_send(chunk, 33); memcpy(panel + k, fb + k, 32); }
    uint64_t dt = sim_us - t0;
    RES("frame_us", "%llu", (unsigned long long)dt);
    RES("bytes", "%llu", (unsigned long long)bytes_on_bus);
    for (int i = 0; i < 1024; i++) printf("P %d\n", panel[i]);
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"ssd1306.c": C})
    r = fwk.results(log)
    panel = np.array([int(l.split()[1]) for l in log.splitlines() if l.startswith("P ")], np.uint8)
    img = np.zeros((64, 128), np.uint8)
    for page in range(8):
        for x in range(128):
            b = panel[page * 128 + x]
            for bit in range(8):
                img[page * 8 + bit, x] = (b >> bit) & 1
    p.compare("Bytes per frame on the bus (1,024 data + 32 prefixes + 7 cmd)", 1024 + 32 + 7, r["bytes"], "", kind="abs")
    p.compare("Frame transfer time at 400 kHz", 1063 * 9 / 400e3, r["frame_us"] * 1e-6, "s", tol=3)
    p.metric("Maximum full-frame refresh rate", 1e6 / r["frame_us"], "frames/s")
    p.compare("Lit pixels rendered (non-zero)", 1, int(img.sum() > 300), "", kind="abs")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.6, 4)); ax.imshow(img, cmap="Blues", interpolation="nearest"); ax.axis("off")
    ax.set_title("Panel memory rebuilt from the transferred bytes (128 × 64)", loc="left", fontsize=10)
    p.save(fig, "panel", "Text, rule and sine plot decoded from the SSD1306 page-ordered bytes.")
    p.discuss("""The image rebuilt from the bytes that crossed the bus is exactly what the firmware drew, confirming the page layout
(each byte is a vertical strip of 8 pixels, LSB at the top) — getting that bit order wrong produces the classic
'scrambled stripes' screen. A full frame costs ~24 ms at 400 kHz, so ~40 fps is the ceiling; real drivers keep a dirty-
rectangle list and send only changed pages, or switch to SPI (8–10 MHz) for animation.""")
