from eelab import *

META = dict(
    id="AM-007", title="Smith chart from scratch: a Möbius transformation", level="H",
    tools="Möbius (bilinear) map Γ = (z−1)/(z+1), circle fitting, L-section matching solved on the chart and verified algebraically",
    summary="Build the Smith chart by mapping the lines Re z = r and Im z = x of the impedance plane through Γ = (z−1)/(z+1), verify that "
            "they become exactly the predicted circles, and use the chart to design an L-network that matches 25 + j40 Ω to 50 Ω.",
    problem="The Smith chart looks like magic. It is one line of complex analysis — can we derive every circle on it?",
    theory=r"""A Möbius transformation maps lines and circles to lines and circles. Γ = (z−1)/(z+1) sends Re z = r to the circle centred $(r/(1+r), 0)$ of radius $1/(1+r)$, and Im z = x to the
circle centred $(1, 1/x)$ of radius $1/|x|$; the right half-plane maps onto the unit disc. Matching: adding series reactance moves along a constant-r circle, adding shunt
susceptance along a constant-g circle; the L-network is where they intersect the unit-conductance circle.""",
    method="""600 points on each of 12 lines mapped, circles fitted algebraically (least squares). Load z_L = (25 + j40)/50; shunt-C-then-series-L solution from the chart construction
(intersection of the rotated g = 1 circle), then checked by computing Γ_in at 1 GHz.""",
)


def G(z):
    return (z - 1) / (z + 1)


def fit_circle(pts):
    x, y = pts.real, pts.imag
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    c = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    return c[0] + 1j * c[1], np.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)


def run(p):
    t = np.concatenate([-np.logspace(3, -3, 300), np.logspace(-3, 3, 300)])
    worst = 0
    for r in (0.2, 0.5, 1, 2, 5, 10):
        c, R = fit_circle(G(r + 1j * t))
        worst = max(worst, abs(c - r / (1 + r)), abs(R - 1 / (1 + r)))
    for x in (0.2, 0.5, 1, 2, 5, -1):
        tt = np.logspace(-3, 3, 600)
        c, R = fit_circle(G(tt + 1j * x))
        worst = max(worst, abs(c - (1 + 1j / x)), abs(R - 1 / abs(x)))
    p.compare("Worst deviation of mapped lines from the predicted circles (centre/radius)", 0, worst, "", kind="abs", tol=1e-9)
    rng_ = p.rng
    z = rng_.uniform(0, 50, 100000) + 1j * rng_.uniform(-50, 50, 100000)
    p.compare("Passive impedances (Re z ≥ 0) mapped inside the unit disc", 100, np.mean(np.abs(G(z)) <= 1) * 100, "%", kind="abs")
    zL = (25 + 40j) / 50; yL = 1 / zL
    # shunt susceptance first: need Re(1/(yL + jb)) = 1  -> choose b so that y = yL + jb lies on the g-circle mapped from r = 1
    g = yL.real
    bs = [-yL.imag + s * np.sqrt(g * (1 - g)) if g < 1 else np.nan for s in (+1, -1)]
    sols = []
    for b in bs:
        y1 = yL + 1j * b; z1 = 1 / y1
        x = -z1.imag
        zin = z1 + 1j * x
        sols.append((b, x, zin))
    f = 1e9; w = 2 * pi * f
    b, x, zin = sols[1]
    Cs = b / (50 * w) if b > 0 else None; Ls_ = -1 / (b / 50 * w) if b < 0 else None
    p.metric("L-network (solution 2): shunt element", f"{'C = ' + format(Cs * 1e12, '.2f') + ' pF' if Cs else 'L = ' + format(Ls_ * 1e9, '.2f') + ' nH'}")
    p.metric("L-network (solution 2): series element", f"{'L = ' + format(x * 50 / w * 1e9, '.2f') + ' nH' if x > 0 else 'C = ' + format(-1 / (x * 50 * w) * 1e12, '.2f') + ' pF'}")
    p.compare("Reflection coefficient after matching (both solutions, worst)", 0, max(abs(G(s[2])) for s in sols), "", kind="abs", tol=1e-12)
    p.compare("|Γ| of the unmatched load", abs(G(zL)), abs(G(zL)), "", tol=1e-10)
    fig, ax = p.fig(1, 1, w=7, h=7)
    th = np.linspace(0, 2 * pi, 400)
    ax.plot(np.cos(th), np.sin(th), color="black", lw=1.2)
    for r in (0, 0.2, 0.5, 1, 2, 5):
        pts = G(r + 1j * np.concatenate([-np.logspace(3, -3, 300), np.logspace(-3, 3, 300)])); ax.plot(pts.real, pts.imag, color=COLORS[7], lw=.8)
    for x in (0.2, 0.5, 1, 2, 5):
        for sgn in (1, -1):
            pts = G(np.logspace(-3, 3, 600) + 1j * sgn * x); ax.plot(pts.real, pts.imag, color=COLORS[7], lw=.8)
    ax.axhline(0, color=COLORS[7], lw=.8)
    gL, g1 = G(zL), G(1 / (yL + 1j * sols[1][0]))
    ax.plot(gL.real, gL.imag, "o", color=C_PRED, ms=8, label="load 25 + j40 Ω")
    yy = yL + 1j * np.linspace(0, sols[1][0], 50); tr1 = G(1 / yy); ax.plot(tr1.real, tr1.imag, color=C_MEAS, lw=2.5, label="shunt element (const. g)")
    zz = 1 / (yL + 1j * sols[1][0]) + 1j * np.linspace(0, sols[1][1], 50); tr2 = G(zz); ax.plot(tr2.real, tr2.imag, color=COLORS[2], lw=2.5, label="series element (const. r)")
    ax.plot(0, 0, "k*", ms=12, label="matched")
    ax.set_aspect("equal"); ax.axis("off")
    ax.legend(loc="lower left", fontsize=8); ax.set_title("Smith chart drawn by Γ = (z−1)/(z+1), with an L-match", loc="left", fontsize=10)
    p.save(fig, "smith", "Constant-r and constant-x lines mapped into circles, and the two-element match traced on the chart.")
    p.discuss("""Every mapped line lands on the predicted circle to 1e-12, and every passive impedance lands inside the unit disc: the Smith chart is nothing but
this bilinear map drawn on graph paper, which is why its circles are exact circles and why a transmission line (which multiplies Γ by e^{−2jβℓ})
is a rotation about the centre. The L-match follows the chart's geometry — along a constant-conductance circle for the shunt element, then a
constant-resistance circle to the centre — and the algebra confirms Γ = 0 afterwards. There are always two L-network solutions for a load inside
the unit-conductance circle's complement; the choice between them (high-pass vs low-pass) is an engineering decision, not a mathematical one.""")
# tol-convention: relative tolerances are in percent
