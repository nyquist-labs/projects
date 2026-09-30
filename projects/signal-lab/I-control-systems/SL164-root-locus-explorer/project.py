from eelab import *

META = dict(
    id="SL-164", title="Root locus: asymptotes, breakaway and the stability limit", level="M",
    tools="Closed-loop pole computation by polynomial roots over a gain sweep (NumPy), analytic root-locus rules",
    summary="Trace the root locus of G = 1/(s(s+2)(s+5)), and check the plotted branches against the construction rules: "
            "asymptote centroid and angles, breakaway point from dK/ds = 0, and the jω-crossing gain from Routh.",
    problem="How do closed-loop poles move as gain increases, and can a few hand rules predict the whole picture?",
    theory=r"""Poles 0, −2, −5; three asymptotes at ±60°, 180° from centroid σ = (0−2−5)/3 = −2.333. Breakaway where dK/ds = 0 for K = −s(s+2)(s+5):
$3s^2+14s+10=0$ ⇒ s = −0.880. Routh on $s^3+7s^2+10s+K$: instability at K = 70 with poles at ±j√10.""",
    method="""Gains 0…150 on a fine grid; closed-loop poles = roots of s³ + 7s² + 10s + K. Breakaway = where the two real poles merge; crossing = first K with a
right-half-plane pole.""",
)


def run(p):
    Ks = np.linspace(0, 150, 150001)
    poles = np.array([np.roots([1, 7, 10, K]) for K in Ks[::10]])
    Kc = Ks[::10]
    real_pair = np.array([np.sum(np.abs(r.imag) < 1e-9) for r in poles])
    kb = Kc[np.argmax(real_pair < 3)]
    rb = np.roots([1, 7, 10, kb])
    sb = rb[np.argmax(np.abs(rb.imag))].real
    p.compare("Breakaway point (dK/ds = 0)", (-14 + np.sqrt(196 - 120)) / 6, sb, "", kind="abs")
    unstable = Kc[np.argmax([np.max(r.real) > 0 for r in poles])]
    p.compare("Gain at the jω-axis crossing (Routh: K = 70)", 70, unstable, "", tol=0.2)
    rc = np.roots([1, 7, 10, 70])
    p.compare("Crossing frequency √10", np.sqrt(10), np.max(rc.imag), "rad/s", tol=0.5)
    big = np.roots([1, 7, 10, 1e7])
    cplx = big[np.argmax(big.imag)]
    p.compare("Asymptote angle for large K", 60, np.degrees(np.angle(cplx - (-7 / 3))), "°", kind="abs")
    fig, ax = p.fig(w=7, h=6)
    ax.plot(poles.real, poles.imag, ".", ms=1, color=C_MEAS)
    ax.plot([0, -2, -5], [0, 0, 0], "x", color="black", ms=10, label="open-loop poles")
    for a in (60, -60):
        ax.plot([-7 / 3, -7 / 3 + 8 * np.cos(np.radians(a))], [0, 8 * np.sin(np.radians(a))], "--", color=C_PRED, lw=1)
    ax.plot(sb, 0, "o", color=COLORS[2], label=f"breakaway {sb:.3f}")
    ax.plot([0, 0], [-np.sqrt(10), np.sqrt(10)], "s", color=COLORS[7], label="jω crossing (K = 70)")
    ax.set_xlim(-9, 3); ax.set_ylim(-7, 7); ax.set_aspect("equal")
    style_axes(ax, "Re s", "Im s", "Root locus of K/(s(s+2)(s+5))")
    p.save(fig, "root_locus", "Numerically traced branches follow the asymptotes, break away at −0.88 and cross into instability at K = 70.")
    p.discuss("""Every construction rule is confirmed by brute-force root finding: the real-axis branches meet at the dK/ds = 0 breakaway, the complex branches
bend toward the ±60° asymptotes from the centroid −7/3, and the locus crosses the imaginary axis at exactly the Routh gain and frequency.
The rules are still worth knowing — they tell you in a minute where to put a zero (lead compensation) to bend the locus away from the axis.""")
