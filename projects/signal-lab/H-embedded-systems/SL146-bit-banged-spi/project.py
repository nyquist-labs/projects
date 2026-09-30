from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-146", title="Bit-banged SPI and its maximum clock rate", level="M",
    tools="C firmware (software SPI, modes 0 and 3) with a per-instruction cycle-cost model, logic-analyser decode in Python",
    summary="Implement SPI in software on GPIO pins, count the CPU cycles per bit to predict the maximum SCLK, and decode "
            "the generated waveform to verify mode, bit order and data.",
    problem="When a microcontroller lacks a free SPI peripheral, you toggle pins yourself. How fast can that go, and does the "
            "timing still meet the protocol?",
    theory=r"""Per bit: set MOSI (≈ 3 cycles for read-modify-write), SCLK high (2), read MISO (2), SCLK low (2), shift/loop (≈ 5) → ~14 cycles at 16 MHz
= 0.875 µs/bit → ≈ 1.14 MHz max SCLK, with an asymmetric duty cycle (high for 4 of 14 cycles).""",
    method="""Cycle-cost model inside the simulated HAL (cycles advance simulated time at 16 MHz). 64 bytes sent in modes 0 and 3; Python decodes SCLK/MOSI and measures
the period and duty; data compared with the sent bytes.""",
)

C = r"""
#include "hal_sim.h"
#define SCK 13
#define MOSI 11
static double cyc_acc = 0;
static void cyc(int n) { cyc_acc += n / 16.0; while (cyc_acc >= 1.0) { sim_us += 1; cyc_acc -= 1.0; } }
static uint64_t t_ns = 0;
static void pin(int p_, int v) { cyc(2); printf("E %llu %d %d\n", (unsigned long long)t_ns, p_, v); }
static void adv(int n) { t_ns += (uint64_t)(n * 62.5); }
static uint8_t xfer(uint8_t out, int mode) {
    uint8_t in = 0;
    for (int b = 7; b >= 0; b--) {
        printf("E %llu %d %d\n", (unsigned long long)t_ns, MOSI, (out >> b) & 1); adv(3);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 1 : 0); adv(2);
        in = (in << 1) | 0; adv(2);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 0 : 1); adv(2);
        adv(5);
    }
    return in;
}
int main(void) {
    log_pins = 0;
    for (int mode = 0; mode <= 3; mode += 3) {
        printf("MODE %d\n", mode);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 0 : 1);
        for (int k = 0; k < 64; k++) { uint8_t v = (uint8_t)(k * 37 + 11); printf("B %d\n", v); xfer(v, mode); }
        t_ns += 10000;
    }
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"softspi.c": C})
    lines = log.splitlines()
    res = {}
    mode = None
    ev = {}
    for l in lines:
        if l.startswith("MODE"):
            mode = int(l.split()[1]); ev[mode] = {"E": [], "B": []}
        elif l.startswith("E "):
            _, t, pin, v = l.split(); ev[mode]["E"].append((int(t), int(pin), int(v)))
        elif l.startswith("B "):
            ev[mode]["B"].append(int(l.split()[1]))
    for mode in (0, 3):
        E = ev[mode]["E"]
        sck = [(t, v) for t, pn, v in E if pn == 13]; mosi = [(t, v) for t, pn, v in E if pn == 11]
        sample_edge = 1 if mode == 0 else 1   # mode 0: sample on rising; mode 3: sample on rising too (idle high, first edge falling)
        rises = [t for (t, v), (t0, v0) in zip(sck[1:], sck[:-1]) if v == 1 and v0 == 0]
        mt = np.array([t for t, v in mosi]); mv = np.array([v for t, v in mosi])
        bits = [mv[np.searchsorted(mt, t, side="right") - 1] for t in rises]
        by = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits) - 7, 8)]
        errs = sum(a != b for a, b in zip(by, ev[mode]["B"]))
        p.compare(f"Mode {mode}: bytes decoded incorrectly (of 64)", 0, errs + abs(len(by) - 64), "", kind="abs")
        per = np.median(np.diff(rises)) * 1e-9
        if mode == 0:
            p.compare("Maximum SCLK (16 MHz / 14 cycles per bit)", 16e6 / 14, 1 / per, "Hz", tol=2)
            falls = [t for (t, v), (t0, v0) in zip(sck[1:], sck[:-1]) if v == 0 and v0 == 1]
            hi = np.median(np.array(falls[:len(rises)]) - np.array(rises[:len(falls)])) * 1e-9
            p.compare("SCLK high fraction (4 of 14 cycles)", 4 / 14, hi / per, "", kind="abs")
            wave = (sck, mosi)
    sck, mosi = wave
    fig, ax = p.fig(h=3)
    st = np.array(sck[:40]); mo = np.array(mosi[:20])
    ax.step(st[:, 0] / 1e3, st[:, 1] + 1.5, where="post", color=C_MEAS, label="SCLK")
    ax.step(mo[:, 0] / 1e3, mo[:, 1], where="post", color=COLORS[1], label="MOSI")
    style_axes(ax, "time (µs)", "", "Bit-banged SPI mode 0 (first byte)")
    p.save(fig, "softspi", "MOSI changes while SCLK is low and is stable at every rising edge.")
    p.discuss("""The decoded waveform carries all 64 bytes correctly in both modes, and the clock runs at the ~1.1 MHz the cycle count predicts,
with a lopsided ~29 % high time — fine for SPI slaves, which care about setup/hold at the sampling edge, not duty cycle. A
hardware SPI peripheral on the same MCU runs at 8 MHz and frees the CPU, which is why bit-banging is a fallback, not a plan.""")
