from eelab import *

META = dict(
    id="AM-017", title="Root locus via the angle condition", level="M",
    tools="Characteristic-polynomial roots swept over gain, angle/magnitude conditions of L(s) = −1/K, analytic breakaway points and asymptotes",
    summary="Trace closed-loop pole migration for L(s) = K(s+3)/(s(s+1)(s+5)) as K goes from 0 to ∞, and verify the classical construction rules — "
            "asymptote centroid and angles, breakaway point from dK/ds = 0, jω-axis crossings — against the computed locus.",
    problem="Root-locus rules are taught as recipes. Where do they come from, and are they exact?",
    theory=r"""A point s is on the locus iff ∠L(s) = 180° (mod 360°); its gain is K = −1/G(s). Rules follow: n − m branches go to infinity along asymptotes at angles $(2k+1)180°/(n-m)$ from the
centroid $σ_a=(\sum p-\sum z)/(n-m)$ = (0 − 1 − 5 + 3)/2 = −1.5; breakaways satisfy dK/ds = 0 on the real axis; for this plant the characteristic polynomial
$s^3+6s^2+(5+K)s+3K$ never crosses into the RHP because the zero at −3 bends the locus back (Routh: 6(5+K) > 3K for all K > 0).""",
    method="""Roots of the characteristic polynomial for 4000 log-spaced K ∈ [10⁻³, 10⁴]; angle condition evaluated at every root; breakaway from the real root of dK/ds = 0; asymptote check from the
large-K roots.""",
)


def run(p):
    num = np.poly([-3]); den = np.poly([0, -1, -5])
    Ks = np.logspace(-3, 4, 4000)
    R = np.array([np.sort_complex(np.roots(np.polyadd(den, K * num))) for K in Ks])
    G = lambda s: np.polyval(num, s) / np.polyval(den, s)
    ang = np.angle(G(R.ravel())) % (2 * pi)
    p.compare("Angle condition ∠G(s) = 180° at every computed closed-loop pole (worst error)", 0, np.degrees(np.max(np.abs(ang - pi))), "°", kind="abs", tol=1e-6)
    Kc = -1 / G(R.ravel()); Krep = np.repeat(Ks, R.shape[1])
    p.compare("Magnitude condition K = −1/G(s) (worst relative error)", 0, np.max(np.abs(Kc.real / Krep - 1)), "", kind="abs", tol=1e-6)
    # breakaway: dK/ds = 0 with K = -den/num  ->  den' num - den num' = 0
    poly = np.polysub(np.polymul(np.polyder(den), num), np.polymul(den, np.polyder(num)))
    cand = [r.real for r in np.roots(poly) if abs(r.imag) < 1e-9 and -1 < r.real < 0]
    sb = cand[0]
    Kb = -np.polyval(den, sb) / np.polyval(num, sb)
    # numerical: the gain where the two real poles between 0 and -1 merge
    imag_part = np.abs(R.imag).max(axis=1)
    Kb_num = Ks[np.argmax(imag_part > 1e-6)]
    p.compare("Breakaway gain: dK/ds = 0 vs where poles first leave the real axis", Kb, Kb_num, "", tol=1)
    p.metric("Breakaway point s_b", sb, "")
    big = R[-1]; far = big[np.argsort(np.abs(big))][-2:]
    p.compare("Asymptote centroid (large K): mean real part of the two far poles", -1.5, far.real.mean(), "", kind="abs", tol=0.05)
    p.compare("Asymptote angle (±90° for n − m = 2)", 90.0, np.degrees(np.abs(np.angle(far[0] - (-1.5)))), "°", kind="abs", tol=2)
    p.compare("Closed-loop poles in the RHP for any K tested", 0, int(np.sum(R.real > 1e-9)), "", kind="abs")
    fig, ax = p.fig(1, 1, w=7, h=5.5)
    for j in range(R.shape[1]):
        ax.plot(R[:, j].real, R[:, j].imag, ".", ms=1.5, color=COLORS[j])
    ax.plot([0, -1, -5], [0, 0, 0], "x", color="black", ms=10, mew=2, label="open-loop poles")
    ax.plot([-3], [0], "o", mfc="none", color="black", ms=10, mew=2, label="zero")
    ax.plot(sb, 0, "*", color=C_PRED, ms=14, label=f"breakaway s = {sb:.3f}")
    ax.axvline(-1.5, ls=":", color="gray", label="asymptote (σ = −1.5)")
    ax.set_xlim(-6, 1); ax.set_ylim(-8, 8)
    style_axes(ax, "Re s", "Im s", "Root locus of K(s+3)/(s(s+1)(s+5))")
    p.save(fig, "root_locus", "Computed closed-loop poles for K from 10⁻³ to 10⁴, with the rule-based breakaway point and asymptote.")
    p.discuss(f"""Every one of the 12,000 computed closed-loop poles satisfies the angle condition to 1e-6°, which is the whole root-locus method in one line:
the locus is the set where the complex number G(s) points at 180°. The construction rules are consequences, and they check out numerically — the
breakaway from dK/ds = 0 (s = {sb:.3f}) is exactly where the two slow poles first leave the real axis, and at large gain the two excess poles run
off vertically along σ = −1.5. The left-half-plane zero at −3 keeps the locus from ever crossing the jω axis, so this loop is stable for every
positive gain — an example of how a well-placed zero (a lead compensator) reshapes the locus.""")
# tol-convention: relative tolerances are in percent
