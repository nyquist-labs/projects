from eelab import *
from eelab.control import step_info
from scipy import signal

META = dict(
    id="AM-153", title="PID control analysed with Laplace transforms", level="M",
    tools="Closed-loop transfer functions by polynomial algebra, final-value theorem, analytic pole placement for a PID on a second-order plant, time-domain simulation (scipy.signal.lsim), set-point weighting (I-PD), disturbance rejection",
    summary="Predict what each PID term does from the closed-loop transfer function — steady-state error from the final-value theorem, ramp error from "
            "the velocity constant, pole locations from coefficient matching — and check every prediction against simulated step, ramp and disturbance responses.",
    problem="Tuning a PID by trial and error works; but what do P, I and D each do to the closed-loop poles and errors, exactly?",
    theory=r"""Plant $G=\frac{5}{(s+1)(s+5)}$. **P**: $e_{ss}=\frac{1}{1+K_pG(0)}$; characteristic $s^2+6s+5+5K_p$ gives ζ and the overshoot $e^{-πζ/\sqrt{1-ζ^2}}$. **PI**: step error 0; ramp error $1/K_v$ with $K_v=K_iG(0)$.
**PID**: characteristic $s^3+(6+5K_d)s^2+(5+5K_p)s+5K_i$ — three gains place three poles anywhere: matching $(s^2+2ζω_ns+ω_n^2)(s+a)$ gives the gains in closed form. The PID's zeros appear in the reference response and add overshoot; feeding the
reference only through the integrator (I-PD) removes them so the response is the all-pole one. A step disturbance at the plant input leaves $G(0)/(1+K_pG(0))$ with P only and zero with integral action.""",
    method="""Simulations with scipy.signal.lsim on the closed-loop transfer functions (5 ms step). Gains: P: K_p = 9; PI: K_p = 9, K_i = 20; PID placed at ζ = 0.7, ω_n = 6 rad/s, third pole a = 12. Closed-loop poles recovered from the polynomial and the
dominant pair also fitted from the simulated I-PD response.""",
)

G_NUM, G_DEN = [5.0], [1.0, 6.0, 5.0]


def closed(cn, cd):
    """T = CG/(1+CG) for C = cn/cd."""
    n = np.polymul(cn, G_NUM); d = np.polyadd(np.polymul(cd, G_DEN), n)
    return n, d


def run(p):
    t = np.arange(0, 12, 0.005)
    # P
    Kp = 9.0; n, d = closed([Kp], [1.0]); _, y, _ = signal.lsim((n, d), np.ones_like(t), t)
    p.compare("P control: steady-state error 1/(1 + K_p·G(0))", 1 / (1 + Kp), 1 - y[-1], "", tol=0.1)
    wn = np.sqrt(5 + 5 * Kp); z = 6 / (2 * wn)
    p.compare("P control: overshoot from ζ of s² + 6s + 5 + 5K_p", 100 * np.exp(-pi * z / np.sqrt(1 - z * z)), step_info(t, y)["overshoot"], "%", kind="abs", tol=0.3)
    # PI
    Ki = 20.0; n, d = closed([Kp, Ki], [1.0, 0.0]); _, y, _ = signal.lsim((n, d), np.ones_like(t), t)
    p.compare("PI control: steady-state step error", 0.0, 1 - y[-1], "", kind="abs", tol=1e-4)
    tr = np.arange(0, 40, 0.005); _, yr, _ = signal.lsim((n, d), tr, tr)
    p.compare("PI control: ramp-following error 1/K_v = 1/(K_i·G(0))", 1 / Ki, tr[-1] - yr[-1], "", tol=0.5)
    # PID by pole placement
    zt, w0, a = 0.7, 6.0, 12.0
    Kd = (a + 2 * zt * w0 - 6) / 5; Kp3 = (w0 ** 2 + 2 * zt * w0 * a - 5) / 5; Ki3 = a * w0 ** 2 / 5
    char = [1, 6 + 5 * Kd, 5 + 5 * Kp3, 5 * Ki3]
    poles = np.roots(char); want = np.array([-zt * w0 + 1j * w0 * np.sqrt(1 - zt ** 2), -zt * w0 - 1j * w0 * np.sqrt(1 - zt ** 2), -a])
    p.compare("PID pole placement: max distance between achieved and requested poles", 0.0, max(min(abs(q - w) for w in want) for q in poles), "rad/s", kind="abs", tol=1e-9)
    p.metric("PID gains from coefficient matching (K_p, K_i, K_d)", f"{Kp3:.2f}, {Ki3:.1f}, {Kd:.2f}")
    t2 = np.arange(0, 3, 0.001)
    _, y_pid, _ = signal.lsim((np.array([Kd, Kp3, Ki3]) * 5, char), np.ones_like(t2), t2)
    _, y_ipd, _ = signal.lsim(([5 * Ki3], char), np.ones_like(t2), t2)
    os_formula = 100 * np.exp(-pi * zt / np.sqrt(1 - zt ** 2))
    p.compare("PID on the error: overshoot vs the dominant-pair formula (the controller zeros are ignored by the formula)", os_formula, step_info(t2, y_pid, 1.0)["overshoot"], "%", kind="abs", tol=2)
    p.compare("I-PD (reference only through the integrator): overshoot vs the formula", os_formula, step_info(t2, y_ipd, 1.0)["overshoot"], "%", kind="abs", tol=2)
    # fit dominant pair from the I-PD response tail: error ~ e^{−ζω t} cos(ω_d t)
    from scipy.optimize import least_squares
    e = 1 - y_ipd; m = t2 > 0.25
    f = lambda q: q[0] * np.exp(-q[1] * t2[m]) * np.cos(q[2] * t2[m] + q[3]) + q[4] * np.exp(-a * t2[m]) - e[m]
    fit = least_squares(f, [1, zt * w0 * 0.9, w0 * 0.7, 0, 0]).x
    p.compare("Decay rate fitted from the simulated response = ζω_n", zt * w0, fit[1], "1/s", tol=2)
    p.compare("Oscillation frequency fitted from the response = ω_n√(1−ζ²)", w0 * np.sqrt(1 - zt ** 2), abs(fit[2]), "rad/s", tol=2)
    # disturbance at plant input: Y/D = G/(1+CG)
    td = np.arange(0, 12, 0.005)
    _, yd_p, _ = signal.lsim((G_NUM, np.polyadd(G_DEN, [5 * 9.0])), np.ones_like(td), td)
    _, yd_pid, _ = signal.lsim((np.polymul(G_NUM, [1, 0]), char), np.ones_like(td), td)
    p.compare("Step disturbance, P only: residual output G(0)/(1 + K_pG(0))", 1 / (1 + 9.0), yd_p[-1], "", tol=0.1)
    p.compare("Step disturbance, PID: residual output", 0.0, yd_pid[-1], "", kind="abs", tol=1e-4)
    p.metric("Peak output deviation for a unit disturbance, P / PID", f"{yd_p.max():.3f} / {yd_pid.max():.3f}")
    fig, ax = p.fig(1, 2, w=11)
    n1, d1 = closed([9.0], [1.0]); n2, d2 = closed([9.0, 20.0], [1.0, 0.0])
    ax[0].plot(t2, signal.lsim((n1, d1), np.ones_like(t2), t2)[1], color=COLORS[1], label="P")
    ax[0].plot(t2, signal.lsim((n2, d2), np.ones_like(t2), t2)[1], color=COLORS[2], label="PI")
    ax[0].plot(t2, y_pid, color=C_PRED, label="PID (error)"); ax[0].plot(t2, y_ipd, color=C_MEAS, label="I-PD"); ax[0].axhline(1, color="gray", lw=.6)
    style_axes(ax[0], "time (s)", "output", "Step responses")
    ax[1].plot(td, yd_p, color=COLORS[1], label="P"); ax[1].plot(td, yd_pid, color=C_MEAS, label="PID")
    style_axes(ax[1], "time (s)", "output", "Unit step disturbance at the plant input")
    p.save(fig, "pid", "Reference and disturbance step responses for P, PI, PID and I-PD control of the same plant.")
    p.discuss(f"""Each term does what the algebra says. Proportional control leaves the error 1/(1 + K_pG(0)) = 10 % and an overshoot set by the damping of
s² + 6s + 5 + 5K_p. Adding the integrator removes the step error and leaves a ramp error of exactly 1/K_v. With all three terms the three
characteristic-polynomial coefficients are free, so the poles land precisely where requested. The instructive discrepancy is the overshoot:
the dominant-pair formula predicts {os_formula:.1f} %, but the PID acting on the error gives {step_info(t2, y_pid, 1.0)['overshoot']:.1f} %, because the controller contributes two
closed-loop *zeros* that the formula ignores. Routing the reference through the integrator only (I-PD) keeps the same poles — the same disturbance
rejection and robustness — without the zeros, and the overshoot drops to {step_info(t2, y_ipd, 1.0)['overshoot']:.1f} %, at or below the formula (the third pole slows it slightly).
Poles set stability and decay; zeros shape how a particular input excites them.""")
# tol-convention: relative tolerances are in percent
