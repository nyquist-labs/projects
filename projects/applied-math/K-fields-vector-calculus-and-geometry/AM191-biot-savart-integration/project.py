from eelab import *
from scipy.special import ellipk, ellipe

MU0 = 4e-7 * pi

META = dict(
    id="AM-191", title="Biot–Savart integration for coils", level="M",
    tools="Numerical Biot–Savart integration over polygonal current paths (vectorised midpoint rule), closed-form checks (straight segment, loop on axis, loop off axis by complete elliptic integrals, finite solenoid), convergence order, Helmholtz-coil uniformity from the Taylor expansion",
    summary="Compute magnetic fields of arbitrary wire shapes by summing Biot–Savart contributions, verify against every closed form available — including the "
            "full off-axis field of a loop in elliptic integrals — and use the tool to show why the Helmholtz spacing (d = R) makes the field so uniform.",
    problem="Closed-form coil fields exist only on symmetry axes. How do we get the field everywhere, and how accurate is a discretised wire?",
    theory=r"""$B(r)=\frac{μ_0I}{4π}\oint\frac{dl\times(r-r')}{|r-r'|^3}$. Loop of radius R on axis: $B_z=\frac{μ_0IR^2}{2(R^2+z^2)^{3/2}}$; off axis: $B_z,B_ρ$ in complete elliptic integrals K(m), E(m), $m=\frac{4Rρ}{(R+ρ)^2+z^2}$. Finite segment: $B=\frac{μ_0I}{4πd}(\sin α_2-\sin α_1)$.
Solenoid of length L, n turns/m, centre: $B=μ_0nI\frac{L}{\sqrt{L^2+4R^2}}$. A polygon with N segments approximates the loop with an O(1/N²) error. Two coaxial loops spaced d apart have $\partial^2B_z/\partial z^2=0$ at the centre when d = R (Helmholtz), leaving a fourth-order variation.""",
    method="""Loop R = 50 mm, I = 1 A, 1000 segments unless stated; field compared at 200 random points off axis. Convergence N = 16…1024. Solenoid as 200 discrete turns. Helmholtz pair: field along the axis and radially within ±R/5 of the centre for d = 0.8R, R, 1.2R.""",
)


def bs(pts, path, I=1.0):
    """B at pts (M×3) from a closed or open polyline path (K×3), midpoint rule per segment."""
    a, b = path[:-1], path[1:]; dl = b - a; mid = 0.5 * (a + b)
    R = pts[:, None, :] - mid[None]; r3 = np.linalg.norm(R, axis=2) ** 3
    return MU0 * I / (4 * pi) * np.sum(np.cross(dl[None], R) / r3[..., None], axis=1)


def loop(R, n, z=0.0):
    t = np.linspace(0, 2 * pi, n + 1)
    return np.c_[R * np.cos(t), R * np.sin(t), np.full(n + 1, z)]


def loop_exact(R, rho, z, I=1.0):
    m = 4 * R * rho / ((R + rho) ** 2 + z ** 2); K, E = ellipk(m), ellipe(m)
    c = MU0 * I / (2 * pi * np.sqrt((R + rho) ** 2 + z ** 2))
    Bz = c * (K + (R ** 2 - rho ** 2 - z ** 2) / ((R - rho) ** 2 + z ** 2) * E)
    Br = c * z / rho * (-K + (R ** 2 + rho ** 2 + z ** 2) / ((R - rho) ** 2 + z ** 2) * E)
    return Br, Bz


def run(p):
    R = 0.05; r = p.rng
    seg = np.array([[0, -0.1, 0], [0, 0.3, 0.0]]); pt = np.array([[0.02, 0.05, 0.0]])
    a1, a2 = np.arctan2(-0.1 - 0.05, 0.02), np.arctan2(0.3 - 0.05, 0.02)
    Bs = bs(pt, np.vstack([seg[0] + (seg[1] - seg[0]) * s for s in np.linspace(0, 1, 4001)]))
    p.compare("Finite straight segment: μ₀I(sin α₂ − sin α₁)/(4πd)", MU0 / (4 * pi * 0.02) * (np.sin(a2) - np.sin(a1)), float(np.linalg.norm(Bs)), "T", tol=0.01)
    zs = np.linspace(-0.1, 0.1, 41); Bz = bs(np.c_[np.zeros(41), np.zeros(41), zs], loop(R, 1000))[:, 2]
    ex = MU0 * R ** 2 / (2 * (R ** 2 + zs ** 2) ** 1.5)
    p.compare("Loop on axis: worst relative error vs μ₀IR²/(2(R² + z²)^{3/2})", 0.0, float(np.max(np.abs(Bz - ex) / ex)), "", kind="abs", tol=1e-4)
    P = np.c_[r.uniform(0.005, 0.12, 200), np.zeros(200), r.uniform(-0.08, 0.08, 200)]
    P = P[np.hypot(P[:, 0] - R, P[:, 2]) > 0.005]
    B = bs(P, loop(R, 1000)); Br, Bze = loop_exact(R, P[:, 0], P[:, 2])
    err = np.hypot(B[:, 0] - Br, B[:, 2] - Bze) / np.hypot(Br, Bze)
    p.compare(f"Off-axis field vs the elliptic-integral solution ({len(P)} points ≥ 5 mm from the wire): median relative error", 0.0, float(np.median(err)), "", kind="abs", tol=1e-4)
    p.metric("… worst point", float(err.max()), "", "closest to the wire, where a 1000-gon's corners are resolved")
    Ns = [16, 32, 64, 128, 256, 512, 1024]; ce = []
    q = np.array([[0.03, 0, 0.01]]); Br1, Bz1 = loop_exact(R, 0.03, 0.01)
    for N in Ns:
        b_ = bs(q, loop(R, N))[0]; ce.append(np.hypot(b_[0] - Br1, b_[2] - Bz1) / np.hypot(Br1, Bz1))
    order = -np.polyfit(np.log(Ns), np.log(ce), 1)[0]
    p.compare("Convergence with the number of polygon segments: error ∝ N^−order", 2.0, order, "", kind="abs", tol=0.1)
    L = 0.3; nturn = 200; path = np.vstack([loop(0.02, 200, z) for z in np.linspace(-L / 2, L / 2, nturn)])
    Bsol = sum(bs(np.array([[0, 0, 0.0]]), loop(0.02, 200, z))[0, 2] for z in np.linspace(-L / 2, L / 2, nturn))
    p.compare("Finite solenoid, centre: μ₀nI·L/√(L² + 4R²)", MU0 * nturn / L * L / np.sqrt(L ** 2 + 4 * 0.02 ** 2), Bsol, "T", tol=0.5)
    res = {}
    for dfac in (0.8, 1.0, 1.2):
        d = dfac * R; coils = [loop(R, 600, -d / 2), loop(R, 600, d / 2)]
        zz = np.linspace(-R / 5, R / 5, 41); ptsz = np.c_[np.zeros(41), np.zeros(41), zz]
        bz = sum(bs(ptsz, c_)[:, 2] for c_ in coils); b0 = bz[20]
        rho_ = np.linspace(1e-4, R / 5, 21); ptsr = np.c_[rho_, np.zeros(21), np.zeros(21)]; br = sum(bs(ptsr, c_)[:, 2] for c_ in coils)
        res[dfac] = (np.max(np.abs(bz / b0 - 1)), np.max(np.abs(br / b0 - 1)), zz, bz / b0)
    p.compare("Helmholtz spacing d = R: field variation within ±R/5 on the axis (Taylor: 144/125·(z/R)⁴ ≈ 0.18 %)", 144 / 125 * (1 / 5) ** 4 * 100, res[1.0][0] * 100, "%", tol=20)
    p.compare("d = R is flatter than d = 0.8R and d = 1.2R (1 = yes)", 1, int(res[1.0][0] < res[0.8][0] and res[1.0][0] < res[1.2][0]), "", kind="abs")
    p.metric("Axial / radial field variation within R/5: d = 0.8R, R, 1.2R", " ; ".join(f"{res[k][0] * 100:.2f} % / {res[k][1] * 100:.2f} %" for k in (0.8, 1.0, 1.2)))
    fig, ax = p.fig(1, 2, w=11)
    xs = np.linspace(-0.1, 0.1, 41); zs2 = np.linspace(-0.1, 0.1, 41); GX, GZ = np.meshgrid(xs, zs2)
    G = bs(np.c_[GX.ravel(), np.zeros(GX.size), GZ.ravel()], loop(R, 400)); Bm = np.linalg.norm(G, axis=1).reshape(GX.shape)
    ax[0].streamplot(xs * 1e3, zs2 * 1e3, G[:, 0].reshape(GX.shape), G[:, 2].reshape(GX.shape), color=np.log10(Bm), cmap="viridis", density=1.2)
    ax[0].plot([-R * 1e3, R * 1e3], [0, 0], "o", color=C_PRED); ax[0].set_aspect("equal"); ax[0].grid(False)
    ax[0].set_title("Field lines of a current loop (cross-section)", loc="left", fontsize=10); ax[0].set_xlabel("x (mm)"); ax[0].set_ylabel("z (mm)")
    for k, c in ((0.8, COLORS[1]), (1.0, C_MEAS), (1.2, COLORS[2])):
        ax[1].plot(res[k][2] / R, (res[k][3] - 1) * 100, color=c, label=f"d = {k:g}R")
    style_axes(ax[1], "z / R", "B_z / B_z(0) − 1 (%)", "Helmholtz pair: flattest at d = R")
    p.save(fig, "biot_savart", "Field lines of a single loop and axial uniformity of coil pairs at three spacings.")
    p.discuss(f"""Summing Biot–Savart contributions over a polygon reproduces every closed form: the straight segment, the loop on its axis and — the strongest
check — the full off-axis field given by elliptic integrals, to a median error of {np.median(err):.0e}. The error of an N-segment polygon falls as
N^−{order:.1f}, the expected second order of the midpoint rule, and grows only very close to the wire, where the polygon's corners become visible.
A 200-turn solenoid lands on μ₀nI·L/√(L² + 4R²). With a trustworthy tool, design questions become experiments: at the Helmholtz spacing the
axial field varies by only {res[1.0][0] * 100:.2f} % within ±R/5 — the fourth-order residual predicted by the Taylor expansion — against {res[0.8][0] * 100:.1f} % and {res[1.2][0] * 100:.1f} %
at 0.8R and 1.2R, which is why calibration coils and MRI shim designs start from this geometry.""")
# tol-convention: relative tolerances are in percent
