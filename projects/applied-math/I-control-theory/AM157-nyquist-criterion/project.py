from eelab import *
from scipy.optimize import brentq

META = dict(
    id="AM-157", title="The Nyquist criterion: counting encirclements", level="H",
    tools="Numerical winding number of 1 + L(jω) over the whole imaginary axis (tangent frequency mapping, phase unwrapping), comparison with closed-loop pole counts for 2000 random loops including open-loop-unstable ones, real-axis crossings for a conditionally stable loop",
    summary="Apply the argument principle numerically: the number of closed-loop right-half-plane poles equals the open-loop count plus the clockwise "
            "encirclements of −1. Verified on 2000 random loops, then used to predict the two-sided gain range of a conditionally stable, open-loop-unstable system.",
    problem="How can a plot of the open-loop frequency response tell whether the closed loop is stable — even when the open loop itself is unstable?",
    theory=r"""Argument principle on $F(s)=1+L(s)$ around the right half-plane: $Z=N+P$, with P open-loop RHP poles, N clockwise encirclements of −1 by $L(jω)$, Z closed-loop RHP poles. For strictly proper L the infinite arc maps to the origin, so N follows from the
change of $\arg(1+L(jω))$ over $ω∈(-∞,∞)$. Example $L=K\frac{s+2}{(s-1)(s^2+2s+5)}$ (P = 1): stability needs one *counter-clockwise* encirclement, i.e. −1 must lie between the two negative-real-axis crossings of L/K, giving $2.5<K<8$ (Routh:
$s^3+s^2+(3+K)s+2K-5$).""",
    method="""Random loops: 2–5 poles (each in the RHP with probability ¼, none within 0.05 of the axis), 0 to n − 1 zeros, random gain; cases where |1 + L| comes within 10⁻³ of zero are discarded as marginal. ω = tan θ with 400 001 points.
Conditionally stable example: crossings by root finding on Im L(jω) = 0; stability range compared with a root sweep over K.""",
)


def winding_ccw(num, den, npts=400001):
    th = np.linspace(-pi / 2, pi / 2, npts)[1:-1]; w = np.tan(th)
    F = 1 + np.polyval(num, 1j * w) / np.polyval(den, 1j * w)
    return np.sum(np.diff(np.unwrap(np.angle(F)))) / (2 * pi), np.min(np.abs(F))


def run(p):
    r = p.rng; bad = 0; used = 0; unstable_ol = 0; stab = 0
    while used < 2000:
        n = int(r.integers(2, 6)); poles = []
        while len(poles) < n:
            re = r.uniform(0.05, 3) * (1 if r.random() < 0.25 else -1)
            if n - len(poles) >= 2 and r.random() < 0.5:
                im = r.uniform(0.2, 4); poles += [complex(re, im), complex(re, -im)]
            else:
                poles.append(re)
        m = int(r.integers(0, n)); zeros = []
        while len(zeros) < m:
            re = r.uniform(0.05, 3) * r.choice([-1, 1])
            if m - len(zeros) >= 2 and r.random() < 0.4:
                im = r.uniform(0.2, 4); zeros += [complex(re, im), complex(re, -im)]
            else:
                zeros.append(re)
        den = np.real(np.poly(poles)); num = np.atleast_1d(np.real(np.poly(zeros))) * 10 ** r.uniform(-1, 2) * r.choice([1, 1, -1])
        wn, dmin = winding_ccw(num, den)
        if dmin < 1e-3:
            continue
        P = int(np.sum(np.real(poles) > 0)); Zp = P - int(round(wn))
        Z = int(np.sum(np.real(np.roots(np.polyadd(den, np.pad(num, (len(den) - len(num), 0))))) > 0))
        used += 1; bad += Zp != Z; unstable_ol += P > 0; stab += Z == 0
    p.compare("Z = N + P from the encirclement count vs closed-loop RHP poles from the roots (2000 random loops): mismatches", 0, bad, "", kind="abs")
    p.metric("Of those: open-loop unstable / closed-loop stable", f"{unstable_ol} / {stab}")
    num0 = np.array([1.0, 2.0]); den0 = np.polymul([1, -1], [1, 2, 5])
    L0 = lambda w: np.polyval(num0, 1j * w) / np.polyval(den0, 1j * w)
    w = np.linspace(1e-3, 20, 200000); im = np.imag(L0(w)); i = np.flatnonzero(np.diff(np.sign(im)))
    wc = [brentq(lambda x: np.imag(L0(x)), w[k], w[k + 1]) for k in i]
    x0 = L0(0).real; x1 = L0(wc[0]).real
    p.compare("Real-axis crossing at ω = 0: L(0)/K = −2/5", -0.4, x0, "", tol=0.01)
    p.compare("Second crossing of the negative real axis: −1/8", -0.125, x1, "", tol=0.01)
    p.metric("Frequency of the second crossing", wc[0], "rad/s")
    Ks = np.linspace(0.5, 12, 2301)
    st = np.array([np.max(np.real(np.roots(np.polyadd(den0, k * np.pad(num0, (2, 0)))))) < 0 for k in Ks])
    p.compare("Lower stability limit K = −1/x₀ (Nyquist) vs root sweep", -1 / x0, Ks[st][0], "", tol=0.5)
    p.compare("Upper stability limit K = −1/x₁ (Nyquist) vs root sweep", -1 / x1, Ks[st][-1], "", tol=0.5)
    for k, want in ((1.0, 1), (5.0, 0), (10.0, 2)):
        wn, _ = winding_ccw(k * num0, den0)
        p.compare(f"K = {k:g}: closed-loop RHP poles predicted by Z = P − (CCW encirclements)", int(np.sum(np.real(np.roots(np.polyadd(den0, k * np.pad(num0, (2, 0))))) > 0)), 1 - int(round(wn)), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    th = np.linspace(-pi / 2, pi / 2, 20001)[1:-1]; wv = np.tan(th)
    for k, c in ((1.0, COLORS[1]), (5.0, C_MEAS), (10.0, COLORS[2])):
        Lv = k * L0(wv); ax[0].plot(Lv.real, Lv.imag, color=c, lw=1, label=f"K = {k:g}")
    ax[0].plot([-1], [0], "k+", ms=14, mew=2); ax[0].set_xlim(-4.5, 1); ax[0].set_ylim(-2, 2)
    style_axes(ax[0], "Re L(jω)", "Im L(jω)", "Open-loop unstable plant: −1 must be encircled once CCW")
    ax[1].plot(Ks, [np.max(np.real(np.roots(np.polyadd(den0, k * np.pad(num0, (2, 0)))))) for k in Ks], color=C_MEAS)
    ax[1].axhline(0, color="gray", lw=.6); ax[1].axvline(-1 / x0, color=C_PRED, ls="--", label="Nyquist limits"); ax[1].axvline(-1 / x1, color=C_PRED, ls="--")
    style_axes(ax[1], "gain K", "largest real part of closed-loop poles", "Conditionally stable: 2.5 < K < 8")
    p.save(fig, "nyquist", "Nyquist plots for three gains of an open-loop-unstable plant and the resulting stability window.")
    p.discuss(f"""Counting encirclements of −1 predicted the number of unstable closed-loop poles correctly for all 2000 random loops, {unstable_ol} of which
were open-loop unstable — the cases where Bode-plot intuition ('stay away from −180° at unity gain') gives the wrong answer and the full
criterion is needed. The example shows why: with one unstable open-loop pole the Nyquist curve *must* encircle −1 once counter-clockwise, which
happens only while −1 lies between the two real-axis crossings at −0.4K and −0.125K. That gives the window 2.5 < K < 8, confirmed by the root
sweep: too little gain fails to stabilise the plant, too much destabilises it again, and 'gain margin' has to be quoted in both directions.""")
# tol-convention: relative tolerances are in percent
