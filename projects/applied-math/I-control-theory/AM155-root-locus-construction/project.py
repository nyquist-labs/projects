from eelab import *

META = dict(
    id="AM-155", title="Root-locus construction rules, checked against the computed locus", level="M",
    tools="Numerical root locus (polynomial roots over a dense gain sweep), rule-based predictions (real-axis segments, asymptote angles and centroid, breakaway point from dK/ds = 0, jω-axis crossing from the Routh array, angle of departure), branch tracking",
    summary="Sketching rules let an engineer draw how closed-loop poles move with gain without a computer. Here each rule is turned into a numerical "
            "prediction for a fourth-order loop and compared with the locus actually computed from the characteristic polynomial.",
    problem="Where do the closed-loop poles go as the gain is raised — and can six sketching rules really predict it?",
    theory=r"""$L(s)=K\frac{s+2}{s(s+1)(s^2+8s+20)}$: n = 4 poles (0, −1, −4 ± 2j), m = 1 zero (−2). Rules: (1) real-axis points left of an odd number of real poles/zeros are on the locus: (−1, 0) and (−∞, −2); (2) n − m = 3 asymptotes at ±60°, 180° from the
centroid $σ=\frac{\sum p-\sum z}{n-m}=-\frac73$; (3) breakaway where $dK/ds=0$ on (−1, 0); (4) imaginary-axis crossing: $s^4+9s^3+28s^2+(20+K)s+2K$ with s = jω gives $ω^2=5+\sqrt{65}$, $K=9ω^2-20≈97.6$; (5) departure angle from −4 + 2j:
$180°-\sum∠(p-p_i)+\sum∠(p-z_i)≈-74.7°$.""",
    method="""Roots of the characteristic polynomial for 40 000 gains from 10⁻⁴ to 10⁶ (log-spaced). Measurements: real-root positions, merge point of the two real branches, gain where a pole pair crosses the axis, direction of the first
small step away from the complex pole, mean and angles of the three far roots at K = 10⁶.""",
)

NUM = np.array([1.0, 2.0]); DEN = np.polymul(np.polymul([1, 0], [1, 1]), [1, 8, 20])


def roots_at(K):
    return np.roots(np.polyadd(DEN, K * np.pad(NUM, (len(DEN) - len(NUM), 0))))


def run(p):
    Ks = np.logspace(-4, 6, 40000)
    R = np.array([roots_at(k) for k in Ks])
    real = np.abs(R.imag) < 1e-7
    rv = R.real[real]
    inside = ((rv > -1 - 1e-6) & (rv < 1e-6)) | (rv < -2 + 1e-6)
    p.compare("Real-axis rule: real closed-loop poles found outside (−1, 0) ∪ (−∞, −2)", 0, int(np.sum(~inside)), "", kind="abs")
    # breakaway: dK/ds = 0 with K(s) = −D(s)/N(s)
    dK = np.polysub(np.polymul(np.polyder(DEN), NUM), np.polymul(DEN, np.polyder(NUM)))
    cand = [q.real for q in np.roots(dK) if abs(q.imag) < 1e-9 and -1 < q.real < 0]
    sb = cand[0]; Kb = -np.polyval(DEN, sb) / np.polyval(NUM, sb)
    nreal_near = np.array([np.sum(real[i] & (R.real[i] > -1.001) & (R.real[i] < 0.001)) for i in range(len(Ks))])
    i_b = np.flatnonzero(nreal_near == 2)[-1]
    p.compare("Breakaway point on (−1, 0) from dK/ds = 0", sb, float(np.mean(R.real[i_b][real[i_b] & (R.real[i_b] > -1.001) & (R.real[i_b] < 0.001)])), "", tol=1)
    p.compare("Gain at breakaway", Kb, Ks[i_b], "", tol=0.2)
    w2 = 5 + np.sqrt(65); Kc = 9 * w2 - 20
    mx = R.real.max(axis=1); i_c = np.flatnonzero(mx > 0)[0]
    p.compare("jω-axis crossing gain (Routh): K = 9ω² − 20", Kc, Ks[i_c], "", tol=0.1)
    p.compare("Crossing frequency ω = √(5 + √65)", np.sqrt(w2), float(np.abs(R[i_c][np.argmax(R[i_c].real)].imag)), "rad/s", tol=0.1)
    pole = -4 + 2j
    th = 180 - np.degrees(np.angle(pole - 0) + np.angle(pole + 1) + np.angle(pole - np.conj(pole))) + np.degrees(np.angle(pole + 2))
    th = (th + 180) % 360 - 180
    near = roots_at(1e-3); q = near[np.argmin(np.abs(near - pole))]
    p.compare("Angle of departure from the pole −4 + 2j", th, np.degrees(np.angle(q - pole)), "°", kind="abs", tol=0.5)
    far = roots_at(1e6); far = far[np.argsort(-np.abs(far))][:3]
    sig = (0 - 1 - 4 - 4 - (-2)) / 3
    p.compare("Asymptote centroid (Σpoles − Σzeros)/(n − m) vs mean of the three far roots at K = 10⁶", sig, float(np.mean(far).real), "", tol=1)
    ang = np.sort(np.abs(np.degrees(np.angle(far - sig))))
    p.compare("Asymptote angles ±60°, 180°: largest deviation", 0.0, float(np.max(np.abs(ang - np.array([60.0, 60.0, 180.0])))), "°", kind="abs", tol=0.5)
    fourth = roots_at(1e6); fourth = fourth[np.argmin(np.abs(fourth + 2))]
    p.compare("The fourth branch ends on the zero at −2 (position at K = 10⁶)", -2.0, float(fourth.real), "", tol=0.1)
    fig, ax = p.fig(1, 1, w=7.5, h=6)
    sel = Ks < 3000
    ax.plot(R.real[sel].ravel(), R.imag[sel].ravel(), ".", ms=1, color=C_MEAS)
    ax.plot(np.roots(DEN).real, np.roots(DEN).imag, "x", color="k", ms=9, label="open-loop poles"); ax.plot([-2], [0], "o", mfc="none", color="k", ms=9, label="zero")
    for a_ in (60, 180, -60):
        ax.plot([sig, sig + 14 * np.cos(np.radians(a_))], [0, 14 * np.sin(np.radians(a_))], "--", color=C_PRED, lw=1)
    ax.plot([sb], [0], "s", color=COLORS[2], label=f"breakaway {sb:.3f}"); ax.plot([0, 0], [np.sqrt(w2), -np.sqrt(w2)], "D", color=COLORS[3], label=f"jω crossing, K = {Kc:.1f}")
    ax.set_xlim(-12, 5); ax.set_ylim(-9, 9); ax.axvline(0, color="gray", lw=.6)
    style_axes(ax, "Re s", "Im s", "Computed locus with the rule-based predictions")
    p.save(fig, "root_locus", "Numerically computed root locus with asymptotes, breakaway point and imaginary-axis crossing predicted by the sketching rules.")
    p.discuss(f"""Every construction rule lands on the computed locus: real poles appear only on the predicted real-axis segments, the two real branches meet
and leave the axis at s = {sb:.3f} (K = {Kb:.3f}), the complex poles depart at {th:.1f}°, the loop goes unstable at K = {Kc:.1f} with the poles
crossing at ±j{np.sqrt(w2):.2f}, and for large gain three branches run out along the ±60°/180° asymptotes from the centroid −7/3 while the fourth
ends on the zero. None of this needed the roots — only the open-loop poles and zeros — which is what made root locus a design tool: it
shows at a glance that adding gain alone can never give this loop both speed and damping, and where a compensator zero would have to go to bend
the branches left.""")
# tol-convention: relative tolerances are in percent
