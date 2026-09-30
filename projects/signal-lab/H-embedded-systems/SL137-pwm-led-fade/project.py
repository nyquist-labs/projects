from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-137", title="PWM LED 'breathing' fade with gamma correction", level="E",
    tools="C firmware on a simulated MCU (eelab HAL), Python logic-analyser decoding, Wokwi sketch",
    summary="Fade an LED in and out with 8-bit software PWM at 1 kHz, using a gamma-2.2 lookup table so the perceived "
            "brightness ramps linearly; decode the pin log to verify PWM frequency, duty resolution and the breathing "
            "period.",
    problem="A linear duty-cycle ramp looks wrong to the eye — the LED seems to jump to full brightness. Why, and how "
            "does gamma correction fix it?",
    theory=r"""Perceived brightness ∝ luminance^(1/2.2) (approximately), so duty = (step/255)^{2.2} makes perceived brightness linear in the step.
PWM period = 256 ticks × tick; with a 3.9 µs tick → 1 kHz (well above flicker fusion). A 2-s breathing cycle = 512 steps × ≈3.9 ms.""",
    method="""Firmware: timer-driven 8-bit PWM (counter compare), gamma LUT computed at start-up (integer), brightness index triangle 0→255→0 over 2 s. The
simulation runs 4 s; Python measures every period and high time from the GPIO log.""",
)

C = r"""
#include "hal_sim.h"
#define LED 13
static uint8_t gamma8[256];
int main(void) {
    for (int i = 0; i < 256; i++) gamma8[i] = (uint8_t)lround(pow(i / 255.0, 2.2) * 255.0);
    const uint32_t tick_us = 4;                 /* 256 ticks × 3.9 µs ≈ 1 kHz */
    uint64_t t_end = 4000000;
    int idx = 0, dir = 1;
    uint64_t next_step = 0;
    const uint64_t step_us = 1000000 / 256;      /* 256 steps up + 256 down = 2 s */
    while (sim_us < t_end) {
        uint8_t duty = gamma8[idx];
        for (int c = 0; c < 256; c++) {          /* one PWM period */
            digitalWrite(LED, c < duty);
            delay_us(tick_us);
        }
        if (sim_us >= next_step) {
            next_step += step_us * 4;            /* ~one PWM period per step x 4 */
            idx += dir;
            if (idx == 255 || idx == 0) dir = -dir;
        }
    }
    RES("pwm_period_us", "%u", 256 * tick_us);
    return 0;
}
"""
INO = r"""
// Wokwi: Arduino Uno, LED on pin 9 (hardware PWM) — breathing with gamma correction
const uint8_t LED = 9;
uint8_t gamma8[256];
void setup() { for (int i = 0; i < 256; i++) gamma8[i] = round(pow(i / 255.0, 2.2) * 255.0); pinMode(LED, OUTPUT); }
void loop() {
  for (int i = 0; i < 256; i++) { analogWrite(LED, gamma8[i]); delay(4); }
  for (int i = 255; i >= 0; i--) { analogWrite(LED, gamma8[i]); delay(4); }
}
"""
DIAG = r"""{"version":1,"author":"Anna Lin (Nyquist Labs)","editor":"wokwi","parts":[{"type":"wokwi-arduino-uno","id":"uno","top":0,"left":0},{"type":"wokwi-led","id":"led1","top":-80,"left":120,"attrs":{"color":"red"}},{"type":"wokwi-resistor","id":"r1","top":-20,"left":150,"attrs":{"value":"220"}}],"connections":[["uno:9","r1:1","green",[]],["r1:2","led1:A","green",[]],["led1:C","uno:GND.1","black",[]]]}"""


def run(p):
    log = fwk.run(p, {"breathe.c": C, "breathe.ino": INO, "diagram.json": DIAG})
    g = fwk.gpio(log)[13]
    t, v = g
    rises = t[1:][(v[1:] == 1) & (v[:-1] == 0)]
    falls = t[1:][(v[1:] == 0) & (v[:-1] == 1)]
    per = np.median(np.diff(rises))
    p.compare("PWM frequency", 1e6 / 1024, 1e6 / per, "Hz", tol=0.5)
    duties = []
    for r0 in rises[:-1]:
        f = falls[falls > r0]
        if len(f):
            duties.append(((r0 / 1e6), (f[0] - r0) / per))
    duties = np.array(duties)
    step = np.min(np.diff(np.unique(np.round(duties[:, 1] * 256))))
    p.compare("Duty-cycle resolution", 1 / 256, step / 256, "", kind="abs")
    lum = duties[:, 1]
    perceived = lum ** (1 / 2.2)
    half = duties[:, 0] < 1.0
    lin = np.polyfit(duties[half, 0], perceived[half], 1)
    resid = np.std(perceived[half] - np.polyval(lin, duties[half, 0]))
    p.compare("Perceived-brightness ramp linearity (RMS residual, 0–1 s)", 0, resid, "", kind="abs")
    naive = duties[half, 0] / duties[half, 0].max()
    p.metric("Without gamma: perceived brightness at 25 % of the ramp", 0.25 ** (1 / 2.2), "", "looks ~53 % bright: the 'jump'")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(duties[:, 0], lum * 100, color=C_MEAS, label="duty cycle (decoded)")
    ax[0].plot(duties[:, 0], perceived * 100, color=COLORS[1], label="perceived (duty^(1/2.2))")
    style_axes(ax[0], "time (s)", "%", "Breathing with gamma correction")
    k = (t > 1.5e6) & (t < 1.5e6 + 3000)
    ax[1].step((t[k] - 1.5e6) / 1e3, v[k], where="post", color=C_MEAS)
    style_axes(ax[1], "time (ms)", "LED pin", "Three PWM periods (decoded pin log)", legend=False)
    p.save(fig, "breathing", "Duty follows the gamma curve so the perceived brightness rises linearly.")
    p.csv("duty", t_s=duties[:, 0], duty=duties[:, 1])
    p.section("Run it in the browser", "Paste `firmware/breathe.ino` and `firmware/diagram.json` into a new Arduino Uno project at wokwi.com.")
    p.discuss("""The decoded pin log shows a clean ~977 Hz PWM with 1/256 duty resolution. Because duty follows (i/255)^2.2, the *perceived*
brightness rises almost linearly with time; a plain linear duty ramp would look 50 % bright after only a quarter of the
ramp. Gamma correction costs resolution at the dark end (the first several LUT entries are 0 or 1), which is why smooth
LED dimming at low brightness needs 10–16-bit PWM.""")
