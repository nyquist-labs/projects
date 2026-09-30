from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-045", title="RLC damping regimes from the characteristic equation", level="M",
    tools="Roots of Ls² + Rs + 1/C, closed-form step responses for under-, critically and over-damped cases, MNA transient verification",
    summary="Classify a series RLC step response from the discriminant of its characteristic equation, write the exact solution for each regime, "
            "and confirm the solutions, overshoot and settling behaviour against simulation — including why critical damping is the fastest without overshoot.",
    problem="One circuit, three completely different behaviours. Where exactly are the boundaries, and what does each look like?",
    theory=r"""$v_C$ obeys $LC\ddot v+RC\dot v+v=V$. With α = R/2L, ω0 = 1/√(LC): α < ω0 under-damped (ringing at $ω_d=\sqrt{ω_0^2-α^2}$, overshoot $e^{-απ/ω_d}$), α = ω0 critically damped
($v=V[1-(1+ω_0t)e^{-ω_0t}]$), α > ω0 over-damped (two real exponentials). Critical R = 2√(L/C). Among non-overshooting responses the critically damped one reaches 98 % soonest.""",
    method="""L = 10 mH, C = 1 µF (R_crit = 200 Ω, f0 = 1.59 kHz). R = 20, 100, 200, 400, 1000 Ω; closed-form responses vs transient simulation; overshoot and 2 % settling time measured.""",
)


def analytic(t, R, L, C, V=1.0):
    a = R / (2 * L); w0 = 1 / np.sqrt(L * C)
    if abs(a - w0) < 1e-9 * w0:
        return V * (1 - (1 + w0 * t) * np.exp(-w0 * t))
    if a < w0:
        wd = np.sqrt(w0 * w0 - a * a)
        return V * (1 - np.exp(-a * t) * (np.cos(wd * t) + a / wd * np.sin(wd * t)))
    s1, s2 = -a + np.sqrt(a * a - w0 * w0), -a - np.sqrt(a * a - w0 * w0)
    return V * (1 + (s2 * np.exp(s1 * t) - s1 * np.exp(s2 * t)) / (s1 - s2))


def run(p):
    L, C = 10e-3, 1e-6
    w0 = 1 / np.sqrt(L * C); Rc = 2 * np.sqrt(L / C)
    p.metric("Critical resistance 2√(L/C)", Rc, "Ω")
    fig, ax = p.fig(1, 2, w=11)
    rows = []
    for R, c in zip((20, 100, 200, 400, 1000), COLORS):
        ck = Circuit("rlc"); ck.V("s", "a", "0", dc=1.0); ck.R("r", "a", "b", R); ck.L("l", "b", "c", L); ck.C("c", "c", "0", C)
        tr = ck.tran(10e-3, 2e-6, method="trap", ic={"c": 0.0, "I(l)": 0.0})
        t, v = tr.t, tr.v("c")
        va = analytic(t, R, L, C)
        a = R / (2 * L)
        os_meas = max(0, v.max() - 1)
        os_pred = np.exp(-a * pi / np.sqrt(w0 ** 2 - a ** 2)) if a < w0 else 0
        out = np.flatnonzero(np.abs(v - 1) > 0.02); ts = t[out[-1] + 1] if len(out) else 0
        rows.append((R, np.max(np.abs(v - va)), os_pred, os_meas, ts))
        ax[0].plot(t * 1e3, v, color=c, label=f"R = {R} Ω")
    for R, err, op, om, ts in rows:
        p.compare(f"R = {R} Ω: max |simulation − closed form|", 0, err, "V", kind="abs", tol=5e-4)
        if op > 0:
            p.compare(f"R = {R} Ω: overshoot e^(−απ/ω_d)", op, om, "", tol=1)
    ts = {r[0]: r[4] for r in rows}
    p.compare("Non-overshooting responses: critical (200 Ω) settles faster than over-damped (400 Ω)", 1, int(ts[200] < ts[400] < ts[1000]), "", kind="abs")
    p.metric("2 % settling times (ms)", ", ".join(f"{R} Ω: {ts[R] * 1e3:.2f}" for R in ts))
    style_axes(ax[0], "t (ms)", "v_C (V)", "Step responses across the three regimes")
    Rs = np.linspace(10, 1000, 400)
    for sgn, c in ((1, C_MEAS), (-1, C_PRED)):
        roots = np.array([np.roots([L, R, 1 / C]) for R in Rs])
        ax[1].plot(roots[:, 0].real, roots[:, 0].imag, ".", ms=2, color=C_MEAS); ax[1].plot(roots[:, 1].real, roots[:, 1].imag, ".", ms=2, color=C_PRED)
    ax[1].plot(-w0, 0, "k*", ms=12, label="critical damping (double root)")
    style_axes(ax[1], "Re s", "Im s", "Roots as R goes from 10 Ω to 1 kΩ")
    p.save(fig, "damping", "Step responses for five resistances and the root trajectory of the characteristic equation.")
    p.discuss("""The closed-form solutions for all three regimes match the simulated waveforms to ~0.2 mV (the trapezoidal rule's O(Δt²) error at a 2 µs step), and the under-damped overshoot follows e^(−απ/ω_d)
exactly. The root plot shows the geometry: as R grows the complex pair slides along the circle |s| = ω0, collides on the real axis at R = 200 Ω
(the double root of critical damping), then splits into one fast and one ever-slower real root. That slow root is why over-damping is *not* the
safe fast choice — the 1 kΩ response crawls — and why critical damping is the fastest response without overshoot.""")
# tol-convention: relative tolerances are in percent
