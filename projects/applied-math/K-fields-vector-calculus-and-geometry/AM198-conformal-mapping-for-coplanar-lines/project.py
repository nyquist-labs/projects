from eelab import *
from eelab.fields2d import Section, extrapolate
from eelab.laplace import solve as lap_solve
from scipy.special import ellipk

META = dict(
    id="AM-198", title="Conformal mapping for coplanar lines: exact answers from complex analysis", level="H",
    tools="Schwarz–Christoffel mapping of the slotted plane onto a rectangle (complete elliptic integrals), closed-form capacitance and impedance of coplanar waveguide, the analytic slot field and its r^(−½) edge singularity, partial-capacitance substrate correction, finite-difference field solver with Richardson extrapolation as the independent check",
    summary="Use a conformal map to turn the awkward geometry of a coplanar waveguide into a parallel-plate capacitor, obtain its impedance, the field "
            "distribution in the slots and the edge singularity in closed form, and confirm all three with a finite-difference solver that knows nothing about complex analysis.",
    problem="Why do so many transmission-line formulas contain elliptic integrals, and how exact are they?",
    theory=r"""Laplace's equation is invariant under analytic maps. The Schwarz–Christoffel map $w(z)=\int_0^z\frac{dt}{\sqrt{(t^2-a^2)(t^2-b^2)}}$ takes the upper half-plane with a centre strip |x| < a and grounds |x| > b onto a rectangle whose side ratio is K(k)/K(k′), k = a/b:
the capacitance per length of CPW in air is $4ε_0K(k)/K(k')$, so $Z_0=30π\,K(k')/K(k)$. The same map gives the slot field $E_x(x)=\frac{Vb}{K(k')\sqrt{(x^2-a^2)(b^2-x^2)}}$ for a < x < b, which diverges as $d^{-1/2}$ at each edge (a 2π corner). A substrate of thickness h adds a partial capacitance with
$k_1=\sinh(πa/2h)/\sinh(πb/2h)$: $ε_{eff}=1+\frac{ε_r-1}{2}\frac{K(k_1)K(k_0')}{K(k_1')K(k_0)}$.""",
    method="""Zero-thickness conductors: centre strip w = 1 mm (a = 0.5 mm), slots s = 0.5 mm (b = 1 mm), grounds to the walls of a 30 × 30 mm grounded box. Finite differences at 0.1, 0.05, 0.025 mm (grid-aligned with the slot edges) with Richardson extrapolation. Slot field from a potential solution at 0.01 mm in a 6 × 6 mm box.
Substrate case: FR-4 (ε_r = 4.4), h = 0.8 mm, far from any ground plane.""",
)

K = lambda k: ellipk(k * k)


def cpw(dx, er=None, h=0.8e-3):
    s = Section(30e-3, 30e-3, dx); y0 = 15e-3
    if er:
        s.dielectric(y0 - h, y0, er)
    s.conductor((-0.5e-3, 0.5e-3, y0, y0)); s.ground((-15e-3, -1.0e-3, y0, y0), (1.0e-3, 15e-3, y0, y0))
    return s


def run(p):
    a, b = 0.5e-3, 1.0e-3; k = a / b; kp = np.sqrt(1 - k * k)
    z_exact = 30 * pi * K(kp) / K(k)
    z_fd, raw, order = extrapolate(lambda dx: cpw(dx), dxs=(0.1e-3, 0.05e-3, 0.025e-3))
    p.compare("CPW in air: Z₀ = 30π·K(k′)/K(k) vs extrapolated finite-difference solution", z_exact, z_fd, "Ω", tol=1)
    p.metric("Finite-difference Z₀ at 0.1 / 0.05 / 0.025 mm and observed order", " / ".join(f"{v:.2f}" for v in raw) + f" Ω, order {order:.2f}", "", "≈ 1 rather than 2: the field is singular at the strip edges")
    dx = 0.01e-3; Lb = 6e-3; n = int(round(Lb / dx)) + 1; x = (np.arange(n) - (n - 1) / 2) * dx; j0 = (n - 1) // 2     # smaller box, finer grid for the local field
    fixed = np.zeros((n, n), bool); fixed[0] = fixed[-1] = fixed[:, 0] = fixed[:, -1] = True; V0 = np.zeros((n, n))
    strip = np.abs(x) <= a + 1e-12; gnd = np.abs(x) >= b - 1e-12
    fixed[j0, strip | gnd] = True; V0[j0, strip] = 1.0
    V = lap_solve(fixed, V0)
    slot = (x > a + 1e-12) & (x < b - 1e-12); Ex = -np.gradient(V[j0], dx)
    ex = b / (K(kp) * np.sqrt((x[slot] ** 2 - a ** 2) * (b ** 2 - x[slot] ** 2)))
    mid = np.abs(x[slot] - (a + b) / 2) < 0.2e-3
    p.compare("Slot field between the edges vs the conformal-mapping expression (median ratio in the middle 0.4 mm)", 1.0, float(np.median(Ex[slot][mid] / ex[mid])), "", tol=2)
    d = x[slot] - a; sel = (d > 3 * dx) & (d < 0.06e-3)
    slope = np.polyfit(np.log(d[sel]), np.log(Ex[slot][sel]), 1)[0]
    p.compare("Edge singularity: E ∝ d^slope near the strip edge (theory −½)", -0.5, slope, "", kind="abs", tol=0.1)
    er, h = 4.4, 0.8e-3; k1 = np.sinh(pi * a / (2 * h)) / np.sinh(pi * b / (2 * h)); k1p = np.sqrt(1 - k1 * k1)
    ee = 1 + (er - 1) / 2 * K(k1) * K(kp) / (K(k1p) * K(k))
    ee_fd = [cpw(dx_, er).line()["eps_eff"] for dx_ in (0.1e-3, 0.05e-3)]
    p.compare("CPW on 0.8 mm FR-4: ε_eff from the partial-capacitance mapping vs field solver", ee, ee_fd[-1], "", tol=2)
    p.compare("… and Z₀ = 30π·K(k′)/(√ε_eff·K(k))", z_exact / np.sqrt(ee), z_fd / np.sqrt(ee_fd[-1]), "Ω", tol=2)
    p.metric("Simple estimate ε_eff ≈ (ε_r + 1)/2 for an infinitely thick substrate", (er + 1) / 2, "", f"the 0.8 mm substrate gives {ee:.2f}: part of the field is in the air below")
    fig, ax = p.fig(1, 2, w=11)
    c_ = (n - 1) // 2; m_ = 250
    GX, GY = np.meshgrid(x[c_ - m_: c_ + m_ + 1], x[c_: c_ + m_ + 1] - x[c_])
    ax[0].contour(GX * 1e3, GY * 1e3, V[j0: j0 + m_ + 1, c_ - m_: c_ + m_ + 1], 20, cmap="viridis")
    ax[0].plot([-a * 1e3, a * 1e3], [0, 0], color=C_PRED, lw=4); ax[0].plot([-2.5, -b * 1e3], [0, 0], "k", lw=4); ax[0].plot([b * 1e3, 2.5], [0, 0], "k", lw=4)
    ax[0].set_aspect("equal"); ax[0].grid(False); ax[0].set_title("Equipotentials above a CPW (strip at 1 V)", loc="left", fontsize=10); ax[0].set_xlabel("mm")
    ax[1].plot(x[slot] * 1e3, Ex[slot] / 1e3, ".", ms=3, color=C_MEAS, label="finite differences"); ax[1].plot(x[slot] * 1e3, ex / 1e3, color=C_PRED, label="conformal mapping")
    ax[1].set_ylim(0, 8)
    style_axes(ax[1], "x (mm)", "E_x (kV/m per volt)", "Field in the slot: singular at both edges")
    p.save(fig, "conformal", "Equipotentials of a coplanar waveguide and the slot field from the mapping and from finite differences.")
    p.discuss(f"""The conformal map delivers the answers exactly where a grid struggles. Its impedance for CPW in air, 30π·K(k′)/K(k) = {z_exact:.2f} Ω, is confirmed by the
finite-difference solver after extrapolation ({z_fd:.2f} Ω) — and the solver's slow, roughly first-order convergence is itself explained by the mapping: the
field at a thin conductor's edge diverges as d^(−½) (measured exponent {slope:.2f}), a singularity no finite grid resolves. Between the edges the whole slot
field follows the closed form b/(K(k′)√((x²−a²)(b²−x²))). The substrate correction, also a conformal-mapping result, predicts ε_eff = {ee:.2f} for
0.8 mm FR-4 against {ee_fd[-1]:.2f} from the solver. Elliptic integrals appear in these formulas because the Schwarz–Christoffel map of a slotted plane onto
a rectangle *is* an elliptic integral.""")
# tol-convention: relative tolerances are in percent
