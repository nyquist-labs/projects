from eelab import *
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

META = dict(
    id="AM-056", title="Duffing oscillator: nonlinear resonance, hysteresis and jumps", level="H",
    tools="Driven Duffing equation integrated with RK45, slow up/down frequency sweeps, harmonic-balance frequency response (cubic in A²), backbone curve",
    summary="Drive a hardening Duffing oscillator (e.g. a resonator with a nonlinear inductor or capacitor) through resonance with slowly rising "
            "and falling frequency, measure the two different response curves and the jump frequencies, and compare with harmonic balance.",
    problem="A resonator with a slightly nonlinear element can show two different amplitudes at the same drive frequency. Which one you get depends on history — why?",
    theory=r"""$\ddot x+δ\dot x+ω_0^2x+βx^3=F\cos ωt$. Harmonic balance with x ≈ A cos(ωt − φ): $\big[(ω_0^2+\tfrac34βA^2-ω^2)^2+(δω)^2\big]A^2=F^2$. The resonance bends along the backbone $ω=\sqrt{ω_0^2+\tfrac34βA^2}$; where the cubic in A²
has three real roots the middle one is unstable, so an upward sweep follows the upper branch until it ends (jump down) and a downward sweep follows the lower branch until it ends (jump up).""",
    method="""ω0 = 1, δ = 0.1, β = 0.2, F = 0.3. Frequency swept 0.6 → 2.0 → 0.6 in 140 steps, each integrated for 60 drive periods, amplitude from the last 10 periods, state carried over. Harmonic-balance curve
from the cubic's roots; jump frequencies where the stable branches end (discriminant/turning points).""",
)


def hb_roots(w, w0=1.0, d=0.1, b=0.2, F=0.3):
    # cubic in u = A²: (9/16)b²u³ + (3/2)b(w0²−w²)u² + [(w0²−w²)² + d²w²]u − F² = 0
    k = w0 ** 2 - w ** 2
    r = np.roots([9 / 16 * b * b, 1.5 * b * k, k * k + (d * w) ** 2, -F * F])
    return np.sort(np.sqrt(r[np.abs(r.imag) < 1e-9].real[r[np.abs(r.imag) < 1e-9].real > 0]))


def sweep(ws, x0=(0.0, 0.0)):
    state = np.array(x0); amps = []
    for w in ws:
        T = 2 * pi / w
        s = solve_ivp(lambda t, y: [y[1], -0.1 * y[1] - y[0] - 0.2 * y[0] ** 3 + 0.3 * np.cos(w * t)], (0, 60 * T), state, rtol=1e-8, atol=1e-10, dense_output=True)
        tt = np.linspace(50 * T, 60 * T, 2000)
        amps.append(np.max(np.abs(s.sol(tt)[0])))
        # restart the next frequency at the same phase of the drive (t = 0): take the state at a whole number of periods
        state = s.sol(60 * T)
    return np.array(amps)


def run(p):
    ws = np.linspace(0.6, 2.0, 70)
    up = sweep(ws); down = sweep(ws[::-1])[::-1]
    nroots = np.array([len(hb_roots(w)) for w in ws])
    hb_up = np.array([hb_roots(w)[-1] for w in ws])
    hb_dn = np.array([hb_roots(w)[0] for w in ws])
    multi = ws[nroots == 3]
    j_down_pred, j_up_pred = multi.max(), multi.min()
    j_down = ws[np.argmax(np.abs(np.diff(up)))]; j_up = ws[np.argmax(np.abs(np.diff(down)))]
    p.compare("Upward sweep: jump-down frequency (end of the upper branch)", j_down_pred, j_down, "rad/s", tol=4)
    p.compare("Downward sweep: jump-up frequency (end of the lower branch)", j_up_pred, j_up, "rad/s", tol=4)
    single = (nroots == 1) & (np.abs(ws - j_down_pred) > 0.06) & (np.abs(ws - j_up_pred) > 0.06)     # away from the jumps, where the sweep is still in transition
    p.compare("Amplitude where the response is unique: simulation vs harmonic balance (max relative)", 0, np.max(np.abs(up[single] / hb_up[single] - 1)), "", kind="abs", tol=0.05)
    Apk = up.max()
    p.compare("Peak amplitude lies on the backbone ω = √(1 + ¾βA²)", np.sqrt(1 + 0.75 * 0.2 * Apk ** 2), ws[np.argmax(up)], "rad/s", tol=3)
    fig, ax = p.fig(1, 1, w=8, h=5)
    wf = np.linspace(0.6, 2.0, 600)
    for w in wf:
        for A in hb_roots(w):
            ax.plot(w, A, ",", color="gray")
    ax.plot(ws, up, "o-", ms=3, color=C_MEAS, label="upward sweep")
    ax.plot(ws, down, "s-", ms=3, color=C_PRED, label="downward sweep")
    Ab = np.linspace(0, 3.5, 100); ax.plot(np.sqrt(1 + 0.75 * 0.2 * Ab ** 2), Ab, ":", color=COLORS[2], label="backbone")
    style_axes(ax, "drive frequency ω", "amplitude A", "Hysteresis of a hardening Duffing resonator (grey: harmonic balance)")
    p.save(fig, "duffing", "Upward and downward frequency sweeps against the harmonic-balance curve and the backbone.")
    p.discuss(f"""The simulated sweeps trace two different curves: going up, the response rides the bent upper branch until it runs out near ω ≈ {j_down:.2f} and
drops; coming down, it follows the lower branch until ω ≈ {j_up:.2f} and jumps up. Both jump frequencies match the ends of harmonic balance's
three-root region, and where only one solution exists the simulated amplitude equals the harmonic-balance value within a few percent (the
single-harmonic ansatz ignores the 3ω component). The middle harmonic-balance branch is never observed — it is unstable. For a circuit designer
this means a resonator with a saturating inductor or varactor can latch into a high- or low-amplitude state depending on how the frequency was
approached, a classic source of 'mysterious' behaviour in power converters and MEMS oscillators.""")
# tol-convention: relative tolerances are in percent
