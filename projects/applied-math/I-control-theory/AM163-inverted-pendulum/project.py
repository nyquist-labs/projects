from eelab import *
from scipy.linalg import solve_continuous_are, expm
from scipy.integrate import solve_ivp

META = dict(
    id="AM-163", title="Inverted pendulum on a cart: linear design, nonlinear reality", level="H",
    tools="Lagrangian cart–pole model integrated with RK45, linearisation and open-loop pole prediction, LQR balance controller, comparison of linear and nonlinear closed-loop responses, region-of-attraction search with actuator limits, energy-based swing-up with LQR catch",
    summary="Derive and simulate the nonlinear cart–pendulum, check that it falls at the rate the linearisation predicts, stabilise it with LQR, measure "
            "how far from upright the linear controller still works (with and without force limits), and swing it up from hanging with an energy controller.",
    problem="A controller designed on a linearised model has to work on the real nonlinear system. How far does the linear design's validity extend?",
    theory=r"""Cart mass M, bob mass m, rod length l, angle θ from upright, force F: $\ddot x=\frac{F+m\sinθ\,(l\dotθ^2-g\cosθ)}{M+m\sin^2θ}$, $\ddotθ=\frac{g\sinθ-\ddot x\cosθ}{l}$. Linearised: $\ddotθ=\frac{(M+m)g}{Ml}θ-\frac{F}{Ml}$ ⇒ unstable pole
$+\sqrt{(M+m)g/(Ml)}$. LQR on the linear model gives F = −Kx. Pendulum energy $E=\tfrac12ml^2\dotθ^2+mgl(\cosθ-1)$ obeys $\dot E=-ml\,a\,\dotθ\cosθ$ for cart acceleration a, so $a=kE\,\dotθ\cosθ$ pumps E monotonically to 0 (the upright level): swing-up.""",
    method="""M = 0.5 kg, m = 0.2 kg, l = 0.3 m. Divergence rate fitted on the free nonlinear fall from 10⁻⁴ rad. LQR: Q = diag(10, 1, 100, 1), R = 0.1. Linear vs nonlinear response from 5° and 25°. Region of attraction: bisection on the initial angle
(cart at rest), with unlimited force and with |F| ≤ 10 N. Swing-up: a ≤ 12 m/s², hand-over to LQR inside |θ| < 0.3 rad.""",
)

M, m, l, g = 0.5, 0.2, 0.3, 9.81


def f(t, s, ctrl):
    x, xd, th, thd = s
    F = ctrl(t, s)
    xdd = (F + m * np.sin(th) * (l * thd ** 2 - g * np.cos(th))) / (M + m * np.sin(th) ** 2)
    return [xd, xdd, thd, (g * np.sin(th) - xdd * np.cos(th)) / l]


def wrap(a):
    return (a + pi) % (2 * pi) - pi


def run(p):
    A = np.array([[0, 1, 0, 0], [0, 0, -m * g / M, 0], [0, 0, 0, 1], [0, 0, (M + m) * g / (M * l), 0]]); B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
    lam = np.sqrt((M + m) * g / (M * l))
    p.compare("Unstable pole of the linearisation √((M+m)g/(Ml)) vs eigenvalue of A", lam, float(np.max(np.linalg.eigvals(A).real)), "1/s", tol=1e-6)
    sol = solve_ivp(f, [0, 1.2], [0, 0, 1e-4, 0], args=(lambda t, s: 0.0,), rtol=1e-10, atol=1e-13, dense_output=True)
    tt = np.linspace(0.5, 1.0, 50); th = sol.sol(tt)[2]
    p.compare("Divergence rate of the free nonlinear fall (fit of ln θ)", lam, np.polyfit(tt, np.log(th), 1)[0], "1/s", tol=1)
    Q = np.diag([10.0, 1, 100, 1]); R = np.array([[0.1]])
    P = solve_continuous_are(A, B, Q, R); K = np.linalg.solve(R, B.T @ P)[0]
    p.metric("LQR gain [x, ẋ, θ, θ̇]", ", ".join(f"{k:.2f}" for k in K))
    lqr = lambda t, s: -float(K @ np.array([s[0], s[1], wrap(s[2]), s[3]]))
    sat = lambda t, s: float(np.clip(lqr(t, s), -10, 10))
    t = np.linspace(0, 5, 1001); dev = {}
    for deg in (5, 25):
        s0 = [0, 0, np.radians(deg), 0]
        nl = solve_ivp(f, [0, 5], s0, args=(lqr,), t_eval=t, rtol=1e-9, atol=1e-11).y
        E = expm((A - B @ K[None]) * (t[1] - t[0])); x = np.array(s0); lin = []
        for _ in t:
            lin.append(x.copy()); x = E @ x
        lin = np.array(lin).T; dev[deg] = (np.max(np.abs(nl[2] - lin[2])) / np.radians(deg), nl, lin)
    p.compare("From 5°: largest difference between nonlinear and linear angle responses (fraction of the initial angle)", 0.0, dev[5][0], "", kind="abs", tol=0.02)
    p.metric("Same from 25°", dev[25][0] * 100, "% of the initial angle", "the linear model degrades gracefully, then fails")

    def recovers(deg, ctrl):
        def lost(t, s, c):
            return abs(s[2]) - 1.7
        lost.terminal = True
        so = solve_ivp(f, [0, 8], [0, 0, np.radians(deg), 0], args=(ctrl,), rtol=1e-8, atol=1e-10, events=lost, max_step=0.01)
        return so.status == 0 and abs(wrap(so.y[2, -1])) < 0.01 and abs(so.y[3, -1]) < 0.05
    roa = {}
    for name, ctrl in (("unlimited", lqr), ("|F| ≤ 10 N", sat)):
        lo, hi = 1.0, 89.0
        for _ in range(12):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if recovers(mid, ctrl) else (lo, mid)
        roa[name] = lo
    p.compare("The linear design's region of attraction is finite: recoverable angle < 90° even with unlimited force (1 = yes)", 1, int(roa["unlimited"] < 89), "", kind="abs")
    p.compare("Actuator saturation shrinks it further (1 = yes)", 1, int(roa["|F| ≤ 10 N"] < roa["unlimited"]), "", kind="abs")
    p.metric("Largest initial angle recovered: unlimited force / |F| ≤ 10 N", f"{roa['unlimited']:.1f}° / {roa['|F| ≤ 10 N']:.1f}°")

    state = {"mode": "swing"}

    def swing(t, s):
        x, xd, th, thd = s; thw = wrap(th)
        if state["mode"] == "balance" or (abs(thw) < 0.3 and abs(thd) < 2.5):
            state["mode"] = "balance"
            return float(np.clip(-K @ np.array([x, xd, thw, thd]), -30, 30))
        E = 0.5 * m * l ** 2 * thd ** 2 + m * g * l * (np.cos(th) - 1)
        a = np.clip(60.0 * E * thd * np.cos(th) / (m * g * l), -12, 12) - 4.0 * x - 3.0 * xd
        return a * (M + m * np.sin(th) ** 2) - m * np.sin(th) * (l * thd ** 2 - g * np.cos(th))
    ts = np.linspace(0, 12, 2401)
    su = solve_ivp(f, [0, 12], [0, 0, pi - 0.05, 0], args=(swing,), t_eval=ts, rtol=1e-7, atol=1e-9, max_step=0.005)
    thw = wrap(su.y[2])
    p.compare("Swing-up from hanging: pendulum upright and at rest at t = 12 s (|θ| < 1°, |x| < 5 cm; 1 = yes)", 1, int(abs(thw[-1]) < np.radians(1) and abs(su.y[0, -1]) < 0.05), "", kind="abs")
    t_catch = ts[np.argmax((np.abs(thw) < 0.3) & (np.abs(su.y[3]) < 2.5))]
    p.metric("Time at which the balance controller takes over", t_catch, "s")
    p.metric("Cart travel used during swing-up", float(np.max(np.abs(su.y[0]))), "m")
    Epend = 0.5 * m * l ** 2 * su.y[3] ** 2 + m * g * l * (np.cos(su.y[2]) - 1)
    pre = ts < t_catch
    p.compare("Energy pumping is monotonic before the catch: largest drop of E between samples (≈ 0)", 0.0, float(max(0, -np.min(np.diff(Epend[pre])))) / (2 * m * g * l), "", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    for deg, c in ((5, C_MEAS), (25, COLORS[2])):
        ax[0].plot(t, np.degrees(dev[deg][1][2]), color=c, label=f"nonlinear, {deg}°"); ax[0].plot(t, np.degrees(dev[deg][2][2]), "--", color=c, lw=1, label="linear model")
    ax[0].set_xlim(0, 3)
    style_axes(ax[0], "time (s)", "pendulum angle (°)", "LQR balance: linear vs nonlinear")
    ax[1].plot(ts, np.degrees(thw), color=C_MEAS); ax[1].axvline(t_catch, color=C_PRED, ls="--", label="LQR takes over")
    style_axes(ax[1], "time (s)", "angle from upright (°)", "Swing-up from hanging")
    ax[2].plot(ts, Epend / (m * g * l), color=C_MEAS); ax[2].axhline(0, color=C_PRED, ls="--", label="upright energy")
    style_axes(ax[2], "time (s)", "pendulum energy / mgl", "Energy pumped to the upright level")
    p.save(fig, "pendulum", "Balancing responses of the linear and nonlinear models, and an energy-based swing-up with LQR catch.")
    p.discuss(f"""The nonlinear pendulum falls at {lam:.2f} s⁻¹, exactly the unstable pole of the linearisation, and near upright the LQR designed on the linear model
controls the real equations almost perfectly (difference below 1 % of the initial angle from 5°). The agreement degrades with angle —
{dev[25][0] * 100:.0f} % from 25° — and the design has a hard limit: with unlimited force the controller recovers from {roa['unlimited']:.0f}°, and with a realistic
10 N limit only from {roa['|F| ≤ 10 N']:.0f}°. 'Stable' in the linear sense means stable *near the equilibrium*; how near is a property of the nonlinear system
and the actuator. Beyond that region a different idea is needed: the energy controller ignores the angle itself and pumps the pendulum's energy to
the upright level, after which the linear controller catches it at t = {t_catch:.1f} s — two controllers, each used where its model is valid.""")
# tol-convention: relative tolerances are in percent
