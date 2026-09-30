from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-152", title="IMU sensor fusion with a complementary filter", level="H",
    tools="C firmware (complementary filter, fixed update rate) with a simulated MEMS accelerometer/gyroscope (noise, bias, vibration)",
    summary="Estimate tilt from a noisy accelerometer and a drifting gyroscope; show each sensor alone fails, predict the "
            "optimal blend coefficient from their noise properties, and measure tilt RMS error vs the filter constant.",
    problem="Accelerometers are noisy but unbiased; gyroscopes are smooth but drift. How does a complementary filter get the "
            "best of both, and what time constant should it use?",
    theory=r"""θ̂ = α(θ̂ + ω·dt) + (1 − α)θ_acc, α = τ/(τ + dt). The filter high-passes the gyro (removing drift) and low-passes the accelerometer (removing
vibration noise) with crossover $f_c=1/(2\pi\tau)$. Error ≈ gyro drift × τ (bias leaks as $b\tau$) plus accelerometer noise × √(dt/(2τ)); the optimum τ
minimises the sum, $\tau^*\approx\left(\frac{\sigma_a^2 dt}{2b^2}\right)^{1/3}$ for bias b (rad/s) and accel angle noise σ_a.""",
    method="""100 Hz updates for 120 s. True tilt: slow manoeuvres (±30°) + 20 Hz vibration on the accelerometer (σ_a ≈ 3° effective), gyro bias 0.5 °/s + 0.05 °/s
noise. τ swept 0.05–50 s; RMS error after 10 s settling.""",
)

C = r"""
#include "hal_sim.h"
int main(int argc, char **argv) {
    double tau = atof(argv[1]); log_pins = 0;
    const double dt = 0.01; double est = 0, gyro_only = 0; double se = 0, sg = 0, sa = 0; int n = 0;
    rng_state = 12345;
    for (int k = 0; k < 12000; k++) {
        double t = k * dt;
        double th = 30 * sin(0.2 * t) + 10 * sin(0.9 * t + 1);
        double w = 30 * 0.2 * cos(0.2 * t) + 10 * 0.9 * cos(0.9 * t + 1);
        double acc = th + 3.0 * rndn() + 4.0 * sin(2 * 3.14159 * 20 * t);
        double gyr = w + 0.5 + 0.05 * rndn() / sqrt(dt) * 0.1;
        double a = tau / (tau + dt);
        est = a * (est + gyr * dt) + (1 - a) * acc;
        gyro_only += gyr * dt;
        if (t > 10) { se += (est - th) * (est - th); sg += (gyro_only - th) * (gyro_only - th); sa += (acc - th) * (acc - th); n++; }
        if (k % 10 == 0) printf("X %f %f %f %f %f\n", t, th, est, gyro_only, acc);
    }
    printf("RES rms %f\nRES rms_gyro %f\nRES rms_acc %f\n", sqrt(se / n), sqrt(sg / n), sqrt(sa / n));
    return 0;
}
"""


def run(p):
    taus = np.logspace(-1.3, 1.7, 13)
    rms = []
    for tau in taus:
        r = fwk.results(fwk.run(p, {"compfilter.c": C}, args=(tau,)))
        rms.append(r["rms"])
    rms = np.array(rms)
    b = 0.5; sig_a = np.sqrt(3.0**2 + 4.0**2 / 2); dt = 0.01
    tau_star = (sig_a**2 * dt / (2 * b * b)) ** (1 / 3)
    tbest = taus[np.argmin(rms)]
    p.compare("Optimal time constant τ* = (σ_a²·dt/(2b²))^(1/3)", tau_star, tbest, "s", tol=60, note="coarse τ grid (log steps of ×1.8)")
    log = fwk.run(p, {"compfilter.c": C}, args=(tau_star,))
    r = fwk.results(log)
    p.metric("RMS tilt error: accelerometer only", r["rms_acc"], "°")
    p.metric("RMS tilt error: gyro integration only (120 s)", r["rms_gyro"], "°", "bias drifts without bound")
    p.compare("RMS error at τ* vs predicted b·τ ⊕ σ_a·√(dt/2τ)", float(np.hypot(b * tau_star, sig_a * np.sqrt(dt / (2 * tau_star)))), r["rms"], "°", tol=60)
    X = fwk.rows(log, "X")
    fig, ax = p.fig(1, 2, w=11)
    m = (X[:, 0] > 40) & (X[:, 0] < 60)
    ax[0].plot(X[m, 0], X[m, 4], color="gray", lw=.4, label="accelerometer tilt")
    ax[0].plot(X[m, 0], X[m, 3], color=COLORS[3], label="gyro integrated")
    ax[0].plot(X[m, 0], X[m, 2], color=C_MEAS, label="complementary filter")
    ax[0].plot(X[m, 0], X[m, 1], "--", color="black", lw=1, label="true tilt")
    style_axes(ax[0], "time (s)", "tilt (°)", "Fusing two imperfect sensors")
    ax[1].loglog(taus, rms, "o-", color=C_MEAS, label="measured RMS error")
    ax[1].loglog(taus, np.hypot(b * taus, sig_a * np.sqrt(dt / (2 * taus))), "--", color=C_PRED, label="b·τ ⊕ σ_a√(dt/2τ)")
    ax[1].axvline(tau_star, color="gray", ls=":")
    style_axes(ax[1], "filter time constant τ (s)", "RMS error (°)", "Choosing τ")
    p.save(fig, "fusion", "Short τ trusts the noisy accelerometer; long τ lets gyro bias leak in; the optimum lies between.")
    p.csv("tau_sweep", tau_s=taus, rms_deg=rms)
    p.discuss("""Alone, the accelerometer is unusably noisy (vibration) and the gyro drifts off by tens of degrees; blended, the error falls to about a degree.
The U-shaped error curve follows the two-term model: at short τ accelerometer noise leaks through, at long τ the gyro bias integrates
to b·τ. The simple model predicts the optimum's location to within the coarse grid; the residual comes from the manoeuvre itself
(the low-pass also lags true motion). A Kalman filter (SL-078) would estimate and remove the bias instead of merely tolerating it.""")
