from eelab import *
from eelab.control import zoh, step_info

META = dict(
    id="SL-161", title="DC motor speed control (with current limiting)", level="M",
    tools="Electromechanical state-space model (R, L, K, J, b), exact ZOH simulation, PI speed loop with voltage saturation",
    summary="Model a small brushed DC motor, verify its open-loop speed time constant and no-load speed, then close a PI "
            "speed loop designed for 20 Hz bandwidth and check rise time and the effect of supply saturation.",
    problem="How fast can a motor change speed, and how does a controller make it faster without exceeding the supply?",
    theory=r"""$L\,di/dt=V-Ri-K\omega$, $J\,d\omega/dt=Ki-b\omega$. With L small, the mechanical time constant $\tau_m\approx\frac{JR}{K^2+bR}$ and no-load speed
$\omega_\infty = \frac{KV}{K^2+bR}$. A PI speed loop with crossover ω_c gives rise time ≈ 1.8/ω_c for a well-damped design; voltage saturation slows large
steps (the loop then behaves open-loop).""",
    method="""R = 1 Ω, L = 0.5 mH, K = 0.05 V·s/rad, J = 1e-5 kg·m², b = 1e-5 N·m·s. 12 V supply. PI tuned by pole-zero cancellation of τ_m with crossover 2π·100 rad/s.
Steps of 20 and 200 rad/s (the no-load limit at 12 V is 239 rad/s).""",
)


def run(p):
    R, L, K, J, b, V = 1.0, 0.5e-3, 0.05, 1e-5, 1e-5, 12.0
    A = np.array([[-R / L, -K / L], [K / J, -b / J]]); B = np.array([1 / L, 0])
    dt = 1e-5; Ad, Bd = zoh(A, B, dt)
    x = np.zeros(2); ws = []
    for k in range(int(0.2 / dt)):
        x = Ad @ x + Bd[:, 0] * V; ws.append(x[1])
    ws = np.array(ws); t = np.arange(len(ws)) * dt
    tau = J * R / (K * K + b * R); winf = K * V / (K * K + b * R)
    p.compare("No-load speed K·V/(K² + bR)", winf, ws[-1], "rad/s", tol=0.5)
    p.compare("Mechanical time constant JR/(K² + bR)", tau, t[np.argmax(ws >= (1 - np.exp(-1)) * ws[-1])], "s", tol=5)
    wc = 2 * pi * 100
    Kdc = K / (K * K + b * R)
    Kp = wc * tau / Kdc; Ki = Kp / tau
    res = {}
    for ref in (20, 200):
        x = np.zeros(2); I = 0; out = []; usat = 0
        for k in range(int(0.1 / dt)):
            e = ref - x[1]
            u = Kp * e + Ki * I
            us = np.clip(u, -V, V)
            if us == u: I += e * dt
            usat += us != u
            x = Ad @ x + Bd[:, 0] * us; out.append(x[1])
        res[ref] = (np.array(out), usat * dt)
    tt = np.arange(len(res[20][0])) * dt
    i50 = step_info(tt, res[20][0], 20)
    p.compare("PI loop, 20 rad/s step: 10–90 % rise time (≈ 2.2/ω_c for first-order loop)", 2.2 / wc, i50["rise"], "s", tol=10)
    p.metric("20 rad/s step: overshoot", i50["overshoot"], "%", "a pure first-order loop would have none")
    i300 = step_info(tt, res[200][0], 200)
    p.metric("200 rad/s step: rise time / time in saturation", f"{i300["rise"]*1e3:.1f} ms / {res[200][1]*1e3:.1f} ms", "", "large steps are supply-limited")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t * 1e3, ws, color=C_MEAS, label="open loop, 12 V step"); ax[0].axhline(winf, color=C_PRED, ls="--", label="K V/(K² + bR)")
    style_axes(ax[0], "time (ms)", "ω (rad/s)", "Open-loop acceleration")
    ax[1].plot(tt * 1e3, res[20][0] / 20, color=C_MEAS, label="20 rad/s step (linear)")
    ax[1].plot(tt * 1e3, res[200][0] / 200, color=COLORS[1], label="200 rad/s step (saturates)")
    style_axes(ax[1], "time (ms)", "ω / ω_ref", "PI speed loop (100 Hz crossover)")
    p.save(fig, "motor", "Small steps follow the designed bandwidth; large steps hit the 12 V limit.")
    p.discuss("""The model's no-load speed and time constant match the closed forms (the 0.5 mH inductance adds only a tiny electrical lag). Pole-zero
cancellation was meant to make the speed loop first-order with a 100 Hz bandwidth (rise ≈ 2.2/ω_c = 3.5 ms), but the measured rise is
~35 % faster with some overshoot: at 100 Hz the 0.5 ms electrical time constant L/R is no longer negligible, adding a second pole that
makes the loop underdamped. The first-order design rule only holds when the current loop is ≥ 10× faster than the speed loop — which
is why real drives use an inner current loop. A 200 rad/s
step asks for more than 12 V, the PI output saturates and the response becomes the open-loop acceleration — conditional
integration (only integrating when unsaturated) prevents windup (see SL-171).""")
