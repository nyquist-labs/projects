from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-116", title="Trapezoidal vs backward Euler in circuit transients", level="H",
    tools="Both integration rules applied to an LC tank and a stiff RC step (own implementation and the repository's MNA simulator), amplitude factors per step, numerical damping and trapezoidal 'ringing'",
    summary="Integrate a lossless LC tank and a stiff RC network with the two workhorse methods of SPICE, predict per-step amplitude factors from "
            "the stability functions, and show each method's characteristic artefact: backward Euler's artificial damping and the trapezoidal rule's point-to-point ringing.",
    problem="SPICE offers 'trap' and 'gear'. What does each do wrong, and when does it matter?",
    theory=r"""For y' = λy: backward Euler multiplies by $R_{BE}=\frac1{1-hλ}$, trapezoidal by $R_{TR}=\frac{1+hλ/2}{1-hλ/2}$. On an undamped oscillator (λ = ±jω) |R_TR| = 1 exactly — energy is conserved — while |R_BE| = 1/√(1+(hω)²) < 1: the tank decays
artificially, e.g. by e^{−½(hω)²·N} over N steps. For a very fast real pole (hλ ≪ −1), R_TR → −1: the component does not decay but flips sign each step (ringing), whereas R_BE → 0 damps it at once.""",
    method="""LC tank: L = 1 mH, C = 1 µF (ω = 31.6 krad/s), initial 1 V, 200 cycles, h = T/40. Stiff RC: τ_fast = 1 ns with h = 1 µs after a step. Own integrators on the state equations and the repository's simulator with method = 'be'/'trap'.""",
)


def lc(method, h, n, w):
    A = np.array([[0, 1.0], [-w * w, 0]]); I = np.eye(2)
    M = np.linalg.solve(I - h * A, I) if method == "be" else np.linalg.solve(I - h / 2 * A, I + h / 2 * A)
    x = np.array([1.0, 0.0]); out = [x[0]]; E = [1.0]
    for _ in range(n):
        x = M @ x; out.append(x[0]); E.append(x[0] ** 2 + (x[1] / w) ** 2)
    return np.array(out), np.array(E)


def run(p):
    L, C = 1e-3, 1e-6; w = 1 / np.sqrt(L * C); T = 2 * pi / w; h = T / 40; n = 200 * 40
    _, Ebe = lc("be", h, n, w); _, Etr = lc("trap", h, n, w)
    p.compare("Trapezoidal: energy after 200 cycles (conserved, |R| = 1)", 1.0, Etr[-1], "", tol=1e-07)
    p.compare("Backward Euler: energy after 200 cycles = (1+(hω)²)^(−N)", (1 + (h * w) ** 2) ** (-n), Ebe[-1], "", tol=0.0001)
    ck = Circuit("lc"); ck.L("l", "a", "0", L); ck.C("c", "a", "0", C)
    res = {}
    for m in ("be", "trap"):
        tr = ck.tran(50 * T, h, method=m, ic={"a": 1.0, "I(l)": 0.0}); v = tr.v("a")
        pk = np.flatnonzero((np.abs(v[1:-1]) >= np.abs(v[:-2])) & (np.abs(v[1:-1]) > np.abs(v[2:]))) + 1
        res[m] = (np.abs(v[-80:]).max(), np.polyfit(pk[2:], np.log(np.abs(v[pk[2:]])), 1)[0])
    p.compare("Repository simulator, trap, 50 cycles: amplitude = (1+(hω)²)^(−½) (it takes one backward-Euler start-up step)", (1 + (h * w) ** 2) ** -0.5, res["trap"][0], "V", tol=0.4)
    p.compare("Repository simulator, trap: decay rate per step after start-up", 0.0, res["trap"][1], "1/step", kind="abs", tol=1e-6)
    p.compare("Repository simulator, BE: decay rate per step = −½·ln(1+(hω)²)", -0.5 * np.log(1 + (h * w) ** 2), res["be"][1], "1/step", tol=1)
    lam = -1e9; hs = 1e-6
    x_be = [1.0]; x_tr = [1.0]
    for _ in range(10):
        x_be.append(x_be[-1] / (1 - hs * lam)); x_tr.append(x_tr[-1] * (1 + hs * lam / 2) / (1 - hs * lam / 2))
    p.compare("Stiff fast mode (hλ = −1000): trapezoidal factor → −1 (ringing)", (1 + hs * lam / 2) / (1 - hs * lam / 2), x_tr[1], "", tol=1e-10)
    p.metric("Fast-mode value after 10 steps: BE / trap", f"{x_be[-1]:.1e} / {x_tr[-1]:+.3f}")
    fig, ax = p.fig(1, 2, w=11)
    vb, _ = lc("be", h, n, w); vt, _ = lc("trap", h, n, w); t = np.arange(n + 1) * h
    ax[0].plot(t / T, vt, color=C_MEAS, lw=.5, label="trapezoidal"); ax[0].plot(t / T, vb, color=C_PRED, lw=.5, label="backward Euler")
    style_axes(ax[0], "cycles", "v_C (V)", "Lossless LC tank, 40 steps per cycle")
    ax[1].plot(x_tr, "o-", color=C_MEAS, label="trapezoidal"); ax[1].plot(x_be, "s-", color=C_PRED, label="backward Euler")
    style_axes(ax[1], "step", "fast-mode amplitude", "Stiff mode (τ = 1 ns, h = 1 µs)")
    p.save(fig, "trap_vs_be", "An undamped LC tank integrated with each method, and the behaviour of a fast stiff mode.")
    p.discuss("""Both artefacts appear exactly as the stability functions predict. Backward Euler loses energy at a rate set by (hω)², so a lossless tank simulated
with a reasonable 40 steps per cycle decays visibly over a few hundred cycles — a real danger when simulating high-Q resonators or oscillators
(oscillators may even fail to start). The trapezoidal rule conserves the tank's energy to machine precision, which is why SPICE uses it by default.
(The repository's own simulator shows a 1.2 % amplitude loss with 'trap' that puzzled me at first: it is exactly one backward-Euler step, which the
simulator takes at t = 0 to start the trapezoidal recursion — after that the amplitude is constant.) The trapezoidal rule has its own flaw, though:
a fast stiff mode is not damped at all: its factor tends to −1, so the node voltage alternates sign every step ('trap ringing') after sharp
switching edges. Simulators therefore switch to backward Euler or Gear for a step or two after breakpoints — the best of both, and the reason the
'gear' option exists.""")
# tol-convention: relative tolerances are in percent
