from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-140", title="Hobby-servo controller: angle from pulse width", level="E",
    tools="C firmware (16-bit timer compare model) on the simulated MCU, pulse-width decoding",
    summary="Generate the 50 Hz servo signal (1.0–2.0 ms pulses) from a 16-bit timer with prescaler 8 at 16 MHz, sweep the "
            "commanded angle, and measure pulse width, angular resolution and timing jitter from the pin log.",
    problem="A servo's position is set purely by the width of a pulse repeated every 20 ms. How precisely can a microcontroller "
            "timer command it?",
    theory=r"""Timer tick = prescaler / f_clk = 8/16 MHz = 0.5 µs, so 1.0–2.0 ms spans 2,000 ticks over 180° → 0.09° per tick. Period 20 ms = 40,000
ticks. Pulse width = 1000 µs + angle/180 × 1000 µs (standard convention).""",
    method="""Firmware converts angle (0–180°, 0.5° steps) to compare value with integer rounding and drives the pin high at each period start and low
at compare match. 361 commands × 3 periods simulated; widths decoded in Python.""",
)

C = r"""
#include "hal_sim.h"
#define SERVO 9
int main(void) {
    const double tick_us = 0.5;                  /* 16 MHz / 8 */
    for (int a2 = 0; a2 <= 360; a2++) {
        double angle = a2 * 0.5;
        uint16_t ocr = (uint16_t)lround((1000.0 + angle / 180.0 * 1000.0) / tick_us);
        for (int k = 0; k < 3; k++) {
            uint64_t start = sim_us;
            digitalWrite(SERVO, 1);
            /* simulated time advances in half-microsecond ticks: accumulate in 2x units */
            static uint64_t half_us = 0;
            half_us = 0; (void)half_us;
            sim_us = start + (ocr / 2); if (ocr % 2) { printf("H %d %u\n", a2, ocr); }
            digitalWrite(SERVO, 0);
            sim_us = start + 20000;
        }
        printf("C %f %u\n", angle, ocr);
    }
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"servo.c": C})
    t, v = fwk.gpio(log)[9]
    rises = t[:-1][v[:-1] == 1]; falls = t[1:][v[1:] == 0]
    widths = falls[:len(rises)] - rises[:len(falls)]
    per = np.median(np.diff(rises))
    p.compare("Servo frame period", 20e-3, per * 1e-6, "s", tol=0.1)
    cmd = fwk.rows(log, "C")
    ocr = cmd[:, 1]
    wexp = ocr * 0.5
    w3 = widths.reshape(-1, 3)[:, 0]
    err = np.abs(w3 - np.floor(wexp))
    p.compare("Pulse width at 90°", 1.5e-3, w3[180] * 1e-6, "s", tol=0.5)
    p.compare("Angular resolution per timer tick (180°/2000 ticks)", 0.09, 180 / (ocr[-1] - ocr[0]), "°", tol=1)
    jit = np.std(np.diff(rises) - 20000)
    p.metric("Period jitter", jit, "µs", "timer-generated: zero in simulation")
    p.metric("Pulse width range", f"{w3.min():.0f}–{w3.max():.0f} µs")
    fig, ax = p.fig()
    ax.plot(cmd[:, 0], w3, color=C_MEAS, label="decoded pulse width")
    ax.plot(cmd[:, 0], 1000 + cmd[:, 0] / 180 * 1000, "--", color=C_PRED, label="1 ms + angle/180 × 1 ms")
    style_axes(ax, "commanded angle (°)", "pulse width (µs)", "Servo command transfer curve")
    p.save(fig, "servo", "Pulse width is linear in angle; resolution is set by the 0.5 µs timer tick.")
    p.discuss("""The decoded pulses sit on the 1–2 ms line and repeat every 20 ms. The simulated pin log is quantised to 1 µs, so it shows
the 0.5 µs timer ticks as a floor-rounded staircase; on a real AVR the compare unit places the edge on the exact tick, giving
the 0.09° resolution computed here — far finer than a hobby servo's own deadband (~1–2 µs ≈ 0.2–0.4°), so the timer is never
the limit. Software-timed (delayMicroseconds) servo pulses, by contrast, jitter whenever an interrupt fires mid-pulse.""")
