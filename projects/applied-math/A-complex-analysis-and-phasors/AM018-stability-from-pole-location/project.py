from eelab import *
from scipy import signal

META = dict(
    id="AM-018", title="Stability from pole location, demonstrated", level="M",
    tools="Impulse responses of systems with poles left of, on and right of the jω axis, growth-rate fitting, BIBO test with a bounded input",
    summary="Show with worked examples that an LTI system is BIBO-stable exactly when all poles have negative real part: measure the growth rate of "
            "impulse responses (it equals the pole's real part), the integrability of |h|, and the response to a bounded input for marginal cases.",
    problem="Why is the left half-plane the stable one — and what happens exactly on the boundary?",
    theory=r"""$h(t)=\sum r_ke^{p_kt}$ (simple poles), so |h| grows or decays like $e^{\max\mathrm{Re}\,p\;t}$: ∫|h| < ∞ iff all Re p < 0, which is exactly BIBO stability. On the axis, a simple pole gives a
bounded but non-decaying h (∫|h| diverges), and a bounded input at the pole's frequency drives an unbounded output (resonance: t·sin ωt); a double pole on the axis gives
polynomial growth t^{m−1}.""",
    method="""Pole pairs at σ ± 2j for σ ∈ {−0.5, −0.1, 0, +0.1}; plus s = 0 simple and double. Impulse responses on 0–60 s; growth rate from a line fit of log of the local peak envelope;
∫₀ᵀ|h| as T grows; bounded input sin(2t) to the σ = 0 system.""",
)


def run(p):
    t = np.linspace(0, 60, 60001)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    rates = []
    for sig, c in zip((-0.5, -0.1, 0.0, 0.1), COLORS):
        b, a = [2.0], np.poly([sig + 2j, sig - 2j]).real
        _, h = signal.impulse((b, a), T=t)
        pk, _ = signal.find_peaks(np.abs(h))
        slope = np.polyfit(t[pk], np.log(np.abs(h[pk])), 1)[0]
        rates.append((sig, slope))
        I = np.cumsum(np.abs(h)) * (t[1] - t[0])
        ax[0].plot(t, h, color=c, lw=.8, label=f"σ = {sig:+g}"); ax[1].semilogy(t, I, color=c)
    for sig, slope in rates:
        p.compare(f"Impulse-response growth rate for poles at {sig:+g} ± 2j (= σ)", sig, slope, "1/s", kind="abs", tol=1e-3)
    _, h0 = signal.impulse(([1.0], [1, 0, 4]), T=t)
    _, y, _ = signal.lsim(([1.0], [1, 0, 4]), np.sin(2 * t), t)
    env = np.abs(y)
    growth = np.polyfit(t[t > 10], np.maximum.accumulate(env)[t > 10], 1)[0]
    p.compare("Marginal pole pair ±2j driven by sin(2t): output envelope grows linearly with slope 1/4", 0.25, growth, "1/s", tol=5)
    _, hd = signal.impulse(([1.0], [1, 0, 0]), T=t)
    p.compare("Double pole at 0: impulse response = t", 0, np.max(np.abs(hd - t)), "", kind="abs", tol=1e-6)
    ax[0].set_ylim(-3, 3)
    style_axes(ax[0], "t (s)", "h(t)", "Impulse responses")
    style_axes(ax[1], "T (s)", "∫₀ᵀ |h| dt", "BIBO: bounded only for σ < 0", legend=False)
    ax[2].plot(t, y, color=C_MEAS, lw=.6); ax[2].plot(t, t / 4, "--", color=C_PRED, label="t/4 envelope"); ax[2].plot(t, -t / 4, "--", color=C_PRED)
    style_axes(ax[2], "t (s)", "y(t)", "Marginal system, bounded input")
    p.save(fig, "stability", "Growth or decay of impulse responses follows the pole's real part; a marginal system resonates without bound.")
    p.discuss("""The fitted growth rates equal the poles' real parts to three decimal places, including the unstable +0.1 case — pole location is not a proxy for
stability, it *is* the exponent. The integral ∫|h| saturates only for σ < 0: that is the BIBO criterion. The boundary cases are the instructive
ones: a simple pole pair on the jω axis has a bounded impulse response (it just keeps ringing) yet is *not* BIBO-stable, because a bounded input at
its own frequency produces the t/4 envelope measured here; a double pole at the origin integrates twice and ramps. 'Marginally stable' systems
are unstable in the sense that matters for engineering.""")
# tol-convention: relative tolerances are in percent
