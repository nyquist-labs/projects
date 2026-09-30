from eelab import *
from eelab.control import step_info, zoh

META = dict(
    id="SL-158", title="PID auto-tuning: relay feedback + Ziegler–Nichols", level="H",
    tools="Relay (Åström–Hägglund) experiment in simulation, describing-function estimate of K_u and T_u, Ziegler–Nichols and manual tuning",
    summary="Find the ultimate gain and period of a three-lag process automatically with a relay experiment, compare with the "
            "exact values from the Nyquist crossing, then tune PID by Ziegler–Nichols and compare its step response with a "
            "hand-tuned controller.",
    problem="How does an industrial controller tune itself at the push of a button, and how good are the classic tuning rules?",
    theory=r"""A relay of amplitude d drives a stable process into a limit cycle at the phase-crossover frequency; the describing function gives
$K_u\approx\frac{4d}{\pi a}$ from the oscillation amplitude a, and $T_u$ = the oscillation period. For $G=1/(s+1)^3$ the exact values are
$\omega_u=\sqrt3$ (T_u = 3.628 s) and $K_u=8$. ZN PID: K_p = 0.6K_u, T_i = T_u/2, T_d = T_u/8 — known to give ~50 % overshoot (quarter-decay).""",
    method="""Plant (s+1)⁻³ as a state-space model, exact ZOH at 10 ms. Relay d = 1 with small hysteresis, 60 s; amplitude and period from the last 5 cycles. ZN PID and a
manually tuned PID (K_p = 2.2, T_i = 2.4, T_d = 0.6) compared on setpoint steps.""",
)


def plant():
    A = np.array([[-1, 0, 0], [1, -1, 0], [0, 1, -1.0]]); B = np.array([1.0, 0, 0]); C = np.array([0, 0, 1.0])
    return A, B, C


def run(p):
    A, B, C = plant(); dt = 0.01
    Ad, Bd = zoh(A, B, dt)
    x = np.zeros(3); u = 1.0; ys = []; us = []
    for k in range(int(60 / dt)):
        y = C @ x
        e = -y
        if e > 0.01: u = 1.0
        elif e < -0.01: u = -1.0
        x = Ad @ x + Bd[:, 0] * u
        ys.append(y); us.append(u)
    ys = np.array(ys); t = np.arange(len(ys)) * dt
    seg = ys[t > 35]; tt = t[t > 35]
    a = (seg.max() - seg.min()) / 2
    zc = tt[1:][(seg[:-1] < 0) & (seg[1:] >= 0)]
    Tu = np.mean(np.diff(zc))
    Ku = 4 / (pi * a)
    p.compare("Ultimate period T_u (relay vs exact 2π/√3)", 2 * pi / np.sqrt(3), Tu, "s", tol=3)
    p.compare("Ultimate gain K_u (describing function vs exact 8)", 8.0, Ku, "", tol=10)
    def pid_run(Kp, Ti, Td, T=40):
        x = np.zeros(3); I = 0; prev = 0; D = 0; out = []
        for k in range(int(T / dt)):
            y = C @ x; e = 1.0 - y
            I += e * dt; D += (dt / (Td / 10 + dt)) * ((e - prev) / dt - D) if Td else 0; prev = e
            uu = Kp * (e + I / Ti + Td * D)
            x = Ad @ x + Bd[:, 0] * uu; out.append(y)
        return np.arange(len(out)) * dt, np.array(out)
    tz, yz = pid_run(0.6 * Ku, Tu / 2, Tu / 8)
    tm, ym = pid_run(2.2, 2.4, 0.6)
    iz, im = step_info(tz, yz, 1.0), step_info(tm, ym, 1.0)
    p.compare("Ziegler–Nichols PID overshoot (classic ≈ 50 %)", 50, iz["overshoot"], "%", kind="abs")
    p.metric("Manual PID: overshoot / settling", f"{im['overshoot']:.1f} % / {im['settle']:.1f} s", "", f"ZN settling {iz['settle']:.1f} s")
    fig, ax = p.fig(1, 2, w=11)
    k = t < 30
    ax[0].plot(t[k], ys[k], color=C_MEAS, label="process output"); ax[0].plot(t[k], np.array(us)[k] * 0.1, color=COLORS[1], lw=.8, label="relay output × 0.1")
    style_axes(ax[0], "time (s)", "", "Relay experiment: a self-sustained oscillation at the ultimate frequency")
    ax[1].plot(tz, yz, color=COLORS[1], label="Ziegler–Nichols PID"); ax[1].plot(tm, ym, color=C_MEAS, label="hand-tuned PID")
    ax[1].axhline(1, color="gray", ls=":")
    style_axes(ax[1], "time (s)", "output", "Step responses")
    p.save(fig, "autotune", "The relay finds K_u and T_u in a few cycles; ZN tuning is aggressive, a gentler hand tune is often preferred.")
    p.discuss("""The relay experiment recovers the ultimate period almost exactly and the ultimate gain within the describing-function approximation's
error (the relay output is a square wave, and its harmonics are only partly filtered by the third-order plant). ZN tuning from those
numbers gives the famously aggressive quarter-decay response with ~50 % overshoot; practitioners start from ZN and detune — the hand-tuned
controller trades a slower rise for much less overshoot.""")
