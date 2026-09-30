from eelab import *
from eelab.control import step_info
from scipy import signal
from scipy.integrate import solve_ivp

META = dict(
    id="SL-157", title="PID control of a second-order plant", level="M",
    tools="Closed-loop transfer functions (SciPy), nonlinear-free time simulation with a discrete PID, dominant-pole predictions",
    summary="Tune P, PI and PID controllers on a two-lag plant; predict overshoot and settling time from the closed-loop "
            "poles and verify them in a time-domain simulation with a sampled controller.",
    problem="What does each term of a PID controller actually do to a step response, and can the response be predicted "
            "from pole locations?",
    theory=r"""Plant $G=\frac{1}{(s+1)(0.2s+1)}$. With P control the steady-state error is 1/(1+K_p); integral action removes it. For dominant poles with damping ζ the
overshoot is $e^{-\pi\zeta/\sqrt{1-\zeta^2}}$ and the 2 % settling time ≈ 4/(ζω_n). Derivative action adds damping.""",
    method="""Controllers: P (K_p = 10), PI (K_p = 4, K_i = 5), PID (K_p = 8, K_i = 10, K_d = 0.5 with a 0.02 s derivative filter). Closed-loop poles from the characteristic
polynomial; dominant pair → predicted overshoot and settling. Simulation: plant discretised exactly (zero-order hold, matrix exponential), controller sampled at 1 kHz.""",
)


def sim(Kp, Ki, Kd, T=6.0, dt=1e-3):
    x = np.zeros(2); integ = 0.0; dfilt = 0.0; prev_e = 1.0
    ys, ts = [], []
    A = np.array([[0, 1], [-5, -6]]); B = np.array([0, 5])
    from eelab.control import zoh
    Ad, Bd = zoh(A, B, dt)
    for k in range(int(T / dt)):
        y = x[0]; e = 1.0 - y
        integ += e * dt
        dfilt += (dt / (0.02 + dt)) * ((e - prev_e) / dt - dfilt); prev_e = e
        u = Kp * e + Ki * integ + Kd * dfilt
        x = Ad @ x + Bd[:, 0] * u
        ts.append((k + 1) * dt); ys.append(x[0])
    return np.array(ts), np.array(ys)


def run(p):
    cases = {"P": (10, 0, 0), "PI": (4, 5, 0), "PID": (8, 10, 0.5)}
    fig, ax = p.fig()
    for i, (nm, (Kp, Ki, Kd)) in enumerate(cases.items()):
        # plant 5/(s^2+6s+5); controller (Kd s^2 + Kp s + Ki)/s
        num_c = [Kd, Kp, Ki] if Ki or Kd else [Kp]
        den_c = [1, 0] if Ki or Kd else [1]
        num_ol = np.polymul(num_c, [5]); den_ol = np.polymul(den_c, [1, 6, 5])
        char = np.polyadd(den_ol, np.pad(num_ol, (len(den_ol) - len(num_ol), 0)))
        poles = np.roots(char)
        cp = poles[np.iscomplex(poles)]
        dom = cp[np.argmax(cp.real)] if len(cp) else poles[np.argmax(poles.real)]
        wn = abs(dom); zeta = -dom.real / wn
        os_pred = 100 * np.exp(-pi * zeta / np.sqrt(1 - zeta**2)) if zeta < 1 else 0.0
        t, y = sim(Kp, Ki, Kd)
        yf = 1.0 if Ki else 5 * Kp / (5 + 5 * Kp)
        info = step_info(t, y, yf)
        p.compare(f"{nm}: overshoot from dominant poles", os_pred, info["overshoot"], "%", kind="abs")
        if not Ki:
            p.compare("P: steady-state error 1/(1 + K_p·G(0))", 1 / (1 + Kp), 1 - y[-1], "", tol=1)
        p.metric(f"{nm}: dominant poles", f"{dom.real:.2f} ± {abs(dom.imag):.2f}j (ζ = {zeta:.2f})")
        p.metric(f"{nm}: 2 % settling time", info["settle"], "s", f"4/(ζω_n) = {4/(zeta*wn):.2f} s")
        ax.plot(t, y, color=COLORS[i], label=f"{nm}")
    ax.axhline(1, color="gray", ls=":")
    style_axes(ax, "time (s)", "output", "Step responses with P, PI and PID")
    p.save(fig, "pid", "P leaves an offset; I removes it but adds overshoot; D damps it.")
    p.discuss("""The dominant-pole formula predicts overshoot well when the other closed-loop poles (and the controller zeros) are far from the dominant pair,
as for P control. With PI and PID the controller zeros sit close to the dominant poles and add overshoot the pure second-order formula cannot
see — a standard caveat of 'dominant pole' reasoning. The P controller's residual offset matches 1/(1 + K_p) exactly, the reason integral
action exists.""")
