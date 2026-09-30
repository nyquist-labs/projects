from eelab import *
from eelab.laplace import solve, energy

META = dict(
    id="SL-126", title="Coaxial cable: fields, capacitance and impedance", level="M",
    tools="2-D finite-difference Laplace solver (eelab.laplace), energy method, analytic coax formulas",
    summary="Solve the electrostatic field of RG-58 and RG-6 geometries on a square grid, extract capacitance per metre "
            "from the stored energy and compare Z₀ with (60/√ε_r)·ln(b/a); plot E and the (TEM) B-field lines.",
    problem="Why is coaxial cable 50 or 75 Ω? Derive the impedance from the geometry and confirm it with a field solver.",
    theory=r"""Between conductors of radii a < b: $E_r=\frac{V}{r\ln(b/a)}$, $C'=\frac{2\pi\varepsilon}{\ln(b/a)}$, $L'=\frac{\mu}{2\pi}\ln\frac ba$ and
$Z_0=\sqrt{L'/C'}=\frac{60}{\sqrt{\varepsilon_r}}\ln\frac ba$. RG-58: a = 0.45 mm, b = 1.47 mm, ε_r = 2.25 (PE) → 47.3 Ω nominal 50;
RG-6: a = 0.51 mm, b = 2.34 mm, foam ε_r = 1.5 → 74.6 Ω.""",
    method="""Square grid (Δ = b/60), inner conductor at 1 V, outer at 0 V (staircase circles). C′ = 2W/V² from the field energy. Two grid sizes
show the staircasing error trend.""",
)


def coax(a, b, er, n):
    h = 2.2 * b / n
    y, x = (np.mgrid[0:n, 0:n] - (n - 1) / 2) * h
    r = np.hypot(x, y)
    fixed = (r <= a) | (r >= b)
    V0 = np.where(r <= a, 1.0, 0.0)
    eps = np.full((n, n), er)
    V = solve(fixed, V0, eps)
    return 2 * energy(V, eps, h), V, r, h


def run(p):
    c = 299792458.0
    for name, a, b, er in (("RG-58", 0.45e-3, 1.47e-3, 2.25), ("RG-6", 0.51e-3, 2.34e-3, 1.5)):
        Cs = []
        for n in (161, 321):
            C, V, r, h = coax(a, b, er, n)
            Cs.append(C)
        C = 2 * Cs[1] - Cs[0]
        Cth = 2 * pi * 8.854e-12 * er / np.log(b / a)
        Z = np.sqrt(er) / (c * C / er * 1) if False else np.sqrt(er) / (c * (C / er)) / 1
        Zfd = 1 / (c * np.sqrt(C * C / er))
        p.compare(f"{name}: capacitance per metre", Cth, C, "F", tol=2)
        p.compare(f"{name}: Z₀ = (60/√ε_r)·ln(b/a)", 60 / np.sqrt(er) * np.log(b / a), Zfd, "Ω", tol=2)
        if name == "RG-58":
            Vs, rs, hs = V, r, h
    fig, ax = p.fig(1, 2, w=10)
    n = Vs.shape[0]
    ax[0].contour(Vs, 12, cmap="viridis", linewidths=1)
    th = np.linspace(0, 2 * pi, 13)[:-1]
    for t in th:
        ax[0].plot((n - 1) / 2 + np.array([0.45e-3, 1.47e-3]) / hs * np.cos(t), (n - 1) / 2 + np.array([0.45e-3, 1.47e-3]) / hs * np.sin(t), color=C_PRED, lw=.8)
    ax[0].set_aspect("equal"); ax[0].axis("off"); ax[0].set_title("equipotentials (E lines radial, B lines circular)", loc="left", fontsize=10)
    Ey, Ex = np.gradient(-Vs, hs)
    j = n // 2
    rr = rs[j, j:]; ee = np.hypot(Ex[j, j:], Ey[j, j:])
    m = (rr > 0.5e-3) & (rr < 1.42e-3)
    ax[1].plot(rr[m] * 1e3, ee[m] / 1e3, "o", ms=3, color=C_MEAS, label="FD solver")
    rt = np.linspace(0.45e-3, 1.47e-3, 100)
    ax[1].plot(rt * 1e3, 1 / (rt * np.log(1.47 / 0.45)) / 1e3, "--", color=C_PRED, label="V/(r ln(b/a))")
    style_axes(ax[1], "r (mm)", "|E| (kV/m per volt)", "Radial field in RG-58")
    p.save(fig, "coax", "Field solver vs the analytic 1/r field between the conductors.")
    p.discuss("""The energy-based capacitance matches 2πε/ln(b/a) to about a percent once the staircase error of drawing circles on a square
grid is extrapolated out, and the impedances land on the analytic values — 47 Ω for RG-58's nominal geometry (manufacturers
tune the dielectric/diameters to hit 50 Ω) and ~75 Ω for RG-6. The ln(b/a) dependence explains the numbers: 50 Ω is a
compromise between minimum loss (≈ 77 Ω for air) and maximum power handling (≈ 30 Ω).""")
