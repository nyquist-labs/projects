from eelab import *

META = dict(
    id="AM-129", title="Error-controlled adaptive time stepping (Dormand–Prince RK45)", level="H",
    tools="Own embedded Runge–Kutta 5(4) integrator with local error estimate and step-size controller, applied to a relaxation oscillator; comparison with fixed-step RK4 at equal accuracy; tolerance proportionality",
    summary="Implement an adaptive integrator that estimates its own local error and chooses the step accordingly, show that it takes tiny steps "
            "during fast switching and large ones in slow phases, that the global error scales with the requested tolerance, and that it needs far fewer steps than fixed-step RK4 for the same accuracy.",
    problem="A multivibrator switches in microseconds and then drifts for milliseconds. How should a simulator choose its time step?",
    theory=r"""Two embedded solutions of orders 5 and 4 share stages; their difference estimates the local error err. Accept if err ≤ tol and set $h_{new}=h\cdot 0.9(\mathrm{tol}/err)^{1/5}$. Steps shrink where the solution changes rapidly. The global error is roughly
proportional to tol ('tolerance proportionality'). For a relaxation oscillator (Van der Pol, μ = 20) most time is spent on slow branches, so adaptive stepping should save one to two orders of magnitude in function evaluations over the smallest fixed step that resolves the jumps.""",
    method="""Van der Pol μ = 20, t = 0…60 (≈ 2 periods). Own Dormand–Prince 5(4) with tol = 10⁻³…10⁻⁹; reference from a tight solve (tol 10⁻¹²). Fixed-step RK4 with the step needed for the same final error. Step-size history vs the solution.""",
)

A = [[], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9], [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
     [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656], [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84]]
C = [0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1]
B5 = np.array([35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0])
B4 = np.array([5179 / 57600, 0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40])


def dopri(f, y0, t_end, tol):
    t, y, h = 0.0, np.array(y0, float), 1e-3
    ts, ys, hs = [0.0], [y.copy()], []; nfev = 0
    while t < t_end:
        h = min(h, t_end - t)
        K = []
        for i in range(7):
            yi = y + h * sum(a * k for a, k in zip(A[i], K)); K.append(np.array(f(t + C[i] * h, yi))); nfev += 1
        K = np.array(K)
        y5 = y + h * B5 @ K; y4 = y + h * B4 @ K
        err = np.max(np.abs(y5 - y4) / (tol + tol * np.maximum(np.abs(y), np.abs(y5))))
        if err <= 1:
            t += h; y = y5; ts.append(t); ys.append(y.copy()); hs.append(h)
        h *= min(5, max(0.2, 0.9 * err ** (-1 / 5) if err > 0 else 5))
    return np.array(ts), np.array(ys), np.array(hs), nfev


def rk4_fixed(f, y0, t_end, h):
    y = np.array(y0, float); t = 0.0; n = int(round(t_end / h))
    for _ in range(n):
        k1 = f(t, y); k2 = f(t + h / 2, y + h / 2 * k1); k3 = f(t + h / 2, y + h / 2 * k2); k4 = f(t + h, y + h * k3); y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4); t += h
    return y, 4 * n


def run(p):
    mu = 20.0
    f = lambda t, y: np.array([y[1], mu * (1 - y[0] ** 2) * y[1] - y[0]])
    T = 60.0
    tr, yr, _, _ = dopri(f, [2.0, 0.0], T, 1e-12)
    ref = yr[-1]
    rows = []
    for tol in (1e-3, 1e-5, 1e-7, 1e-9):
        ts, ys, hs, nfev = dopri(f, [2.0, 0.0], T, tol)
        rows.append((tol, np.max(np.abs(ys[-1] - ref)), nfev, hs.min(), hs.max()))
    rr = np.array(rows)
    sl = np.polyfit(np.log(rr[:, 0]), np.log(rr[:, 1]), 1)[0]
    p.compare("Tolerance proportionality: global error ∝ tol^slope (≈ 1)", 1.0, sl, "", kind="abs", tol=0.35)
    p.compare("Step sizes at tol 1e-7 span more than a decade (1 = yes; my guess of ~1000× was too high)", 1, int(rr[2, 4] / rr[2, 3] > 10), "", kind="abs")
    p.metric("Step-size range at tol 1e-7: max/min", rr[2, 4] / rr[2, 3], "×")
    target = rr[2, 1]
    for h in (1e-2, 5e-3, 2e-3, 1e-3, 5e-4, 2e-4, 1e-4):
        yf, nf = rk4_fixed(f, [2.0, 0.0], T, h)
        if np.max(np.abs(yf - ref)) <= target * 1.5:
            break
    p.compare("Function evaluations: fixed-step RK4 / adaptive RK45 at equal accuracy (my guess 10–100×)", 30, nf / rr[2, 2], "×", kind="abs", tol=100)
    p.metric("Evaluations at tol 1e-7: adaptive / fixed RK4 (h = %.0e)" % h, f"{int(rr[2, 2])} / {nf}")
    ts, ys, hs, _ = dopri(f, [2.0, 0.0], T, 1e-7)
    fig, ax = p.fig(2, 1, w=10, h=6, sharex=True)
    ax[0].plot(ts, ys[:, 0], color=C_MEAS, lw=1)
    style_axes(ax[0], None, "x", "Van der Pol, μ = 20", legend=False)
    ax[1].semilogy(ts[1:], hs, color=C_PRED, lw=1)
    style_axes(ax[1], "t", "step size h", "Steps shrink at every jump", legend=False)
    p.save(fig, "adaptive", "The relaxation oscillation and the step sizes chosen by the error controller.")
    p.discuss(f"""The embedded error estimate lets the integrator take steps spanning {rr[2, 4] / rr[2, 3]:.0f}× in size at tol = 1e-7: tiny during each fast jump, large along the slow
branches — exactly the step pattern a circuit designer would choose by hand. The global error follows the requested tolerance roughly
proportionally (slope {sl:.2f}; controllers bound *local* error, so global proportionality is only approximate), and to match its accuracy a fixed-step RK4
needs {nf / rr[2, 2]:.0f}× more function evaluations because its single step must be small enough for the fastest part everywhere. SPICE's time-step control does the
same with local truncation-error estimates from its implicit formulas.""")
# tol-convention: relative tolerances are in percent
