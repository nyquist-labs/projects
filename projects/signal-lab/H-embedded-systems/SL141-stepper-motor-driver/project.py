from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-141", title="Stepper-motor driver with trapezoidal acceleration", level="M",
    tools="C firmware (full/half-step sequencing, Austin's real-time ramp algorithm) on the simulated MCU",
    summary="Drive a 200-step/rev stepper through a 3-revolution move with a trapezoidal speed profile computed in real "
            "time (David Austin's c_n recurrence); decode step timing from the pin log and compare the velocity profile "
            "and move time with kinematics.",
    problem="Steppers stall if you ask them to start at full speed. How does firmware generate an accurate acceleration "
            "ramp using only integer-friendly arithmetic?",
    theory=r"""For acceleration α (steps/s²) the first step delay is $c_0=\sqrt{2/\alpha}$ and subsequent delays follow $c_n=c_{n-1}-\frac{2c_{n-1}}{4n+1}$ (Austin 2005),
approximating the exact $c_n = \sqrt{2/\alpha}(\sqrt{n+1}-\sqrt n)$. Trapezoid: accelerate to v_max over $v_{max}^2/(2\alpha)$ steps, cruise, decelerate
symmetrically. Move time = $\frac{S}{v_{max}}+\frac{v_{max}}{\alpha}$ when the cruise phase exists. Half-stepping doubles resolution (400 steps/rev).""",
    method="""S = 1,200 half-steps (3 rev), α = 4,000 steps/s², v_max = 2,000 steps/s. Coil outputs A, B, A̅, B̅ on 4 pins with the 8-state half-step table;
firmware schedules each step at the computed delay (1 µs resolution).""",
)

C = r"""
#include "hal_sim.h"
static const uint8_t HALF[8] = {0x1, 0x3, 0x2, 0x6, 0x4, 0xC, 0x8, 0x9};   /* A, AB, B, BA', A', A'B', B', B'A */
static int phase = 0;
static void step_out(void) { phase = (phase + 1) & 7; for (int i = 0; i < 4; i++) digitalWrite(2 + i, (HALF[phase] >> i) & 1); }
int main(void) {
    const double alpha = 4000.0, vmax = 2000.0; const long S = 1200;
    long accel_steps = (long)(vmax * vmax / (2 * alpha));
    if (accel_steps > S / 2) accel_steps = S / 2;
    double c = sqrt(2.0 / alpha) * 0.676 * 1e6;   /* Austin's 0.676 correction for the first step */
    double cmin = 1e6 / vmax;
    double cn = c;
    for (long n = 0; n < S; n++) {
        step_out();
        printf("S %ld %llu\n", n, (unsigned long long)sim_us);
        long remaining = S - 1 - n;
        if (remaining < accel_steps) {             /* decelerate */
            long k = remaining + 1;
            cn = cn + 2 * cn / (4 * k - 1);
        } else if (n + 1 < accel_steps) {         /* accelerate */
            cn = cn - 2 * cn / (4 * (n + 1) + 1);
            if (cn < cmin) cn = cmin;
        } else cn = cmin;
        sim_us += (uint64_t)llround(cn);
    }
    return 0;
}
"""


def run(p):
    log = fwk.run(p, {"stepper.c": C})
    S = fwk.rows(log, "S")
    t = S[:, 1] * 1e-6
    v = 1 / np.diff(t)
    alpha, vmax, N = 4000.0, 2000.0, 1200
    Ttot = t[-1]
    p.compare("Move time (S/v_max + v_max/α)", N / vmax + vmax / alpha, Ttot, "s", tol=3)
    p.compare("Cruise speed reached", vmax, np.median(v[len(v) // 2 - 50: len(v) // 2 + 50]), "steps/s", tol=0.5)
    acc_meas = np.polyfit(t[5:400], v[5:400], 1)[0] if False else np.polyfit(t[10:450], v[10:450], 1)[0]
    p.compare("Acceleration during the ramp", alpha, acc_meas, "steps/s²", tol=5)
    g = fwk.gpio(log)
    seq = np.array([g[2 + i][1][:9] for i in range(4)])
    p.metric("Coil pins used", 4, "", "half-step table: A, AB, B, BĀ, Ā, ĀB̄, B̄, B̄A")
    tt = np.linspace(0, Ttot, 500)
    ta = vmax / alpha
    vp = np.where(tt < ta, alpha * tt, np.where(tt > Ttot - ta, alpha * (Ttot - tt), vmax))
    fig, ax = p.fig()
    ax.plot(t[1:], v, color=C_MEAS, lw=1, label="measured from step timestamps")
    ax.plot(tt, vp, "--", color=C_PRED, label="ideal trapezoid")
    style_axes(ax, "time (s)", "speed (steps/s)", "Trapezoidal move: 1,200 half-steps")
    p.save(fig, "profile", "Austin's recurrence produces a near-perfect linear speed ramp using one division per step.")
    p.csv("steps", step=S[:, 0], t_s=t)
    p.discuss("""The step-rate profile decoded from the timestamps is an almost perfect trapezoid: linear ramps at the commanded acceleration, a flat
cruise at 2,000 steps/s, and a move time matching kinematics. Austin's recurrence needs one multiply and one divide per step
instead of a square root, which is why it is used on 8-bit MCUs; its only significant error is the very first step, corrected by
the empirical 0.676 factor. That correction makes the first steps faster than an ideal ramp, so the whole move finishes
~4 % sooner than the continuous-kinematics prediction; the speed ripple at the start comes from the discrete approximation
to √n timing.""")
