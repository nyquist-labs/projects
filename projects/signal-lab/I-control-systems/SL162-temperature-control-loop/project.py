from eelab import *
from eelab.control import zoh

META = dict(
    id="SL-162", title="Temperature control with dead time: why lag causes oscillation", level="M",
    tools="First-order-plus-dead-time (FOPDT) oven model, delay-line simulation, Nyquist/phase-crossover analysis",
    summary="Control an oven whose heater acts through a 20 s transport delay; predict the proportional gain at which the loop "
            "oscillates and the oscillation period from the phase-crossover condition, and find both by simulation.",
    problem="Why does turning up the gain on a slow thermal system make it oscillate, and how high can it go?",
    theory=r"""$G(s)=\frac{K e^{-\theta s}}{\tau s+1}$ with K = 2 °C/%, τ = 200 s, θ = 20 s. Phase crossover: $-\arctan(\omega\tau)-\omega\theta=-\pi$ → ω_u; ultimate gain
$K_u=\frac{\sqrt{1+(\omega_u\tau)^2}}{K}$, oscillation period $2\pi/\omega_u$. The delay's phase −ωθ grows without bound, so every such loop has a finite K_u.""",
    method="""Delay implemented as a sample FIFO (0.1 s steps). P gains swept; K_u found as the gain where the oscillation neither grows nor decays (log-decrement
= 0, bisection).""",
)


def simulate(Kp, T=3000, dt=0.1, K=2.0, tau=200.0, th=20.0):
    n = int(T / dt); buf = [0.0] * int(th / dt); y = 0.0; out = []
    a = np.exp(-dt / tau)
    for k in range(n):
        u = Kp * (1.0 - y)
        buf.append(u); ud = buf.pop(0)
        y = a * y + (1 - a) * K * ud
        out.append(y)
    return np.array(out)


def decay(y, dt=0.1):
    e = y - y[-5000:].mean()
    pk = [i for i in range(1, len(e) - 1) if e[i] > e[i - 1] and e[i] >= e[i + 1] and e[i] > 0]
    if len(pk) < 4:
        return -1.0, np.nan
    amps = e[pk]
    return np.log(amps[-1] / amps[1]) / (len(pk) - 2), np.mean(np.diff(pk[1:])) * dt


def run(p):
    from scipy.optimize import brentq
    K, tau, th = 2.0, 200.0, 20.0
    wu = brentq(lambda w: np.arctan(w * tau) + w * th - pi, 1e-4, pi / th)
    Ku = np.sqrt(1 + (wu * tau) ** 2) / K
    lo, hi = 0.5 * Ku, 1.5 * Ku
    for _ in range(25):
        mid = (lo + hi) / 2
        d, _ = decay(simulate(mid))
        lo, hi = (mid, hi) if d < 0 else (lo, mid)
    Ku_sim = (lo + hi) / 2
    _, Tu_sim = decay(simulate(Ku_sim, T=6000))
    p.compare("Ultimate gain K_u (phase-crossover prediction)", Ku, Ku_sim, "%/°C", tol=2)
    p.compare("Oscillation period 2π/ω_u", 2 * pi / wu, Tu_sim, "s", tol=2)
    p.compare("Steady-state error with K_p = 0.5·K_u: 1/(1+K·K_p)", 1 / (1 + K * 0.5 * Ku), 1 - simulate(0.5 * Ku, T=4000)[-1], "", tol=3)
    fig, ax = p.fig()
    t = np.arange(int(1500 / 0.1)) * 0.1
    for i, f in enumerate((0.3, 0.7, 1.0, 1.15)):
        ax.plot(t, simulate(f * Ku, T=1500), color=COLORS[i], label=f"K_p = {f:.2f}·K_u")
    style_axes(ax, "time (s)", "temperature rise (normalised)", "Proportional control with 20 s dead time")
    p.save(fig, "deadtime", "Below K_u the oscillation decays, at K_u it persists, above it grows.")
    p.discuss("""The simulated loop breaks into sustained oscillation exactly at the gain predicted from the phase-crossover condition, with the predicted period.
Dead time is the culprit: its phase lag −ωθ grows linearly with frequency while the lag of the thermal time constant saturates at −90°, so
the loop inevitably reaches −180° at some frequency. It also caps the useful gain, leaving a large proportional offset — hence PI control
with modest gains, or a Smith predictor that models the delay explicitly.""")
