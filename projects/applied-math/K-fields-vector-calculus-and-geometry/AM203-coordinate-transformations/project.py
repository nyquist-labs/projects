from eelab import *
from eelab.poisson import solve

META = dict(
    id="AM-203", title="Cylindrical and spherical coordinates: operators, Jacobians and a solved problem", level="M",
    tools="Gradient, divergence, curl and Laplacian in cylindrical and spherical coordinates evaluated by finite differences in the curvilinear variables and compared with Cartesian results, rotation matrices between unit-vector bases, the Jacobian as volume element, separation of variables for a dielectric cylinder in a uniform field checked against a Cartesian finite-volume solve",
    summary="Put the curvilinear operator formulas to a numerical test on random points and fields, verify that the basis transformations are orthogonal "
            "and that r² sin θ is the right volume element, then solve a problem that is easy in polar coordinates and awkward in Cartesian ones — a dielectric rod in a uniform field — both ways.",
    problem="The ∇ formulas in cylindrical and spherical coordinates look arbitrary. Where do the extra factors come from, and how can the formulas be checked rather than memorised?",
    theory=r"""With scale factors $(h_1,h_2,h_3)$ = (1, ρ, 1) for cylindrical and (1, r, r sin θ) for spherical coordinates, $\nabla\cdot A=\frac{1}{h_1h_2h_3}\sum_i\partial_i\left(\frac{h_1h_2h_3}{h_i}A_i\right)$ and $\nabla^2f=\frac{1}{h_1h_2h_3}\sum_i\partial_i\left(\frac{h_1h_2h_3}{h_i^2}\partial_if\right)$; the volume element is $h_1h_2h_3$ (ρ, r² sin θ).
Unit-vector bases are related by rotation matrices R with $RR^T=I$. Dielectric cylinder (ε_r) in a uniform field E₀: separation of variables in polar coordinates gives a uniform interior field $E_{in}=\frac{2}{ε_r+1}E_0$ and an exterior line-dipole perturbation.""",
    method="""Test functions: f = x²y + z³ + e^{x/2} sin y (scalar), A = (yz, x²z, xy²) (vector); 300 random points; curvilinear derivatives by central differences (step 10⁻⁵). Volume of a sphere and of a cone section by integrating the Jacobian. Cylinder: radius 20 mm, ε_r = 4, between plates 400 mm apart
at ±200 V (a 200 mm box gave 2 % too much interior field: the plates' images); Cartesian finite-volume solution at 0.4 mm.""",
)

f = lambda x, y, z: x * x * y + z ** 3 + np.exp(x / 2) * np.sin(y)
lap_f = lambda x, y, z: 2 * y + 6 * z + 0.25 * np.exp(x / 2) * np.sin(y) - np.exp(x / 2) * np.sin(y)
A = lambda x, y, z: np.array([y * z, x * x * z, x * y * y])
divA = lambda x, y, z: 0.0 * x
curlA = lambda x, y, z: np.array([2 * x * y - x * x, y - y * y, 2 * x * z - z])


def run(p):
    r = p.rng; h = 1e-4; N = 300
    P = r.uniform(0.3, 2, (N, 3)) * r.choice([-1, 1], (N, 3))
    rho = np.hypot(P[:, 0], P[:, 1]); ph = np.arctan2(P[:, 1], P[:, 0]); z = P[:, 2]
    F = lambda rh, pp, zz: f(rh * np.cos(pp), rh * np.sin(pp), zz)
    d2 = lambda g, a, b, c, i: (g(*[v + (h if k == i else 0) for k, v in enumerate((a, b, c))]) - 2 * g(a, b, c) + g(*[v - (h if k == i else 0) for k, v in enumerate((a, b, c))])) / h ** 2
    d1 = lambda g, a, b, c, i: (g(*[v + (h if k == i else 0) for k, v in enumerate((a, b, c))]) - g(*[v - (h if k == i else 0) for k, v in enumerate((a, b, c))])) / (2 * h)
    lap_cyl = d2(F, rho, ph, z, 0) + d1(F, rho, ph, z, 0) / rho + d2(F, rho, ph, z, 1) / rho ** 2 + d2(F, rho, ph, z, 2)
    ex = lap_f(*P.T)
    p.compare("Cylindrical Laplacian ∂ρρ + ∂ρ/ρ + ∂φφ/ρ² + ∂zz vs Cartesian (worst relative error, 300 points)", 0.0, float(np.max(np.abs(lap_cyl - ex) / (np.abs(ex) + 1))), "", kind="abs", tol=1e-4)
    rr = np.linalg.norm(P, axis=1); th = np.arccos(P[:, 2] / rr)
    Fs = lambda R_, T_, Q_: f(R_ * np.sin(T_) * np.cos(Q_), R_ * np.sin(T_) * np.sin(Q_), R_ * np.cos(T_))
    lap_sph = (d2(Fs, rr, th, ph, 0) + 2 / rr * d1(Fs, rr, th, ph, 0) + d2(Fs, rr, th, ph, 1) / rr ** 2 + np.cos(th) / (np.sin(th) * rr ** 2) * d1(Fs, rr, th, ph, 1)
               + d2(Fs, rr, th, ph, 2) / (rr ** 2 * np.sin(th) ** 2))
    p.compare("Spherical Laplacian vs Cartesian (worst relative error)", 0.0, float(np.max(np.abs(lap_sph - ex) / (np.abs(ex) + 1))), "", kind="abs", tol=1e-4)
    def sph_components(R_, T_, Q_):
        x, y, zz = R_ * np.sin(T_) * np.cos(Q_), R_ * np.sin(T_) * np.sin(Q_), R_ * np.cos(T_); a = A(x, y, zz)
        er = np.array([np.sin(T_) * np.cos(Q_), np.sin(T_) * np.sin(Q_), np.cos(T_)]); et = np.array([np.cos(T_) * np.cos(Q_), np.cos(T_) * np.sin(Q_), -np.sin(T_)]); eq = np.array([-np.sin(Q_), np.cos(Q_), 0 * Q_])
        return np.sum(a * er, 0), np.sum(a * et, 0), np.sum(a * eq, 0)
    Ar = lambda a, b, c: a * a * sph_components(a, b, c)[0]; At = lambda a, b, c: np.sin(b) * sph_components(a, b, c)[1]; Aq = lambda a, b, c: sph_components(a, b, c)[2]
    div_sph = d1(Ar, rr, th, ph, 0) / rr ** 2 + d1(At, rr, th, ph, 1) / (rr * np.sin(th)) + d1(Aq, rr, th, ph, 2) / (rr * np.sin(th))
    p.compare("Spherical divergence of A = (yz, x²z, xy²) (Cartesian divergence is 0): worst |value|", 0.0, float(np.max(np.abs(div_sph))), "", kind="abs", tol=1e-5)
    Ac = lambda a, b, c: np.sum(A(a * np.cos(b), a * np.sin(b), c) * np.array([np.cos(b), np.sin(b), 0 * b]), 0)
    Aphi = lambda a, b, c: np.sum(A(a * np.cos(b), a * np.sin(b), c) * np.array([-np.sin(b), np.cos(b), 0 * b]), 0)
    Az = lambda a, b, c: A(a * np.cos(b), a * np.sin(b), c)[2]
    curl_z = (d1(lambda a, b, c: a * Aphi(a, b, c), rho, ph, z, 0) - d1(Ac, rho, ph, z, 1)) / rho
    curl_r = d1(Az, rho, ph, z, 1) / rho - d1(Aphi, rho, ph, z, 2)
    cc = curlA(*P.T); cr_ex = cc[0] * np.cos(ph) + cc[1] * np.sin(ph)
    p.compare("Cylindrical curl, z and ρ components vs the Cartesian curl (worst abs. error)", 0.0, float(max(np.max(np.abs(curl_z - cc[2])), np.max(np.abs(curl_r - cr_ex)))), "", kind="abs", tol=1e-5)
    Rm = lambda T_, Q_: np.array([[np.sin(T_) * np.cos(Q_), np.sin(T_) * np.sin(Q_), np.cos(T_)], [np.cos(T_) * np.cos(Q_), np.cos(T_) * np.sin(Q_), -np.sin(T_)], [-np.sin(Q_), np.cos(Q_), 0]])
    orth = max(np.max(np.abs(Rm(t_, q_) @ Rm(t_, q_).T - np.eye(3))) for t_, q_ in zip(th, ph))
    p.compare("Cartesian → spherical unit-vector matrix is orthogonal: max |RRᵀ − I|", 0.0, orth, "", kind="abs", tol=1e-12)
    x_, w_ = np.polynomial.legendre.leggauss(40); Rs = 1.3
    rq = (x_ + 1) / 2 * Rs; tq = (x_ + 1) / 2 * pi; wr = w_ * Rs / 2; wt = w_ * pi / 2
    vol = 2 * pi * np.sum(np.outer(wr * rq ** 2, wt * np.sin(tq)))
    p.compare("∭ r² sin θ dr dθ dφ over a sphere of radius 1.3 = 4πR³/3", 4 * pi * Rs ** 3 / 3, vol, "", tol=1e-10)
    tq2 = (x_ + 1) / 2 * (pi / 6); wt2 = w_ * (pi / 6) / 2; vc = 2 * pi * np.sum(np.outer(wr * rq ** 2, wt2 * np.sin(tq2)))
    p.compare("Spherical cone of half-angle 30°: volume 2πR³(1 − cos 30°)/3", 2 * pi * Rs ** 3 * (1 - np.cos(pi / 6)) / 3, vc, "", tol=1e-10)
    hh = 0.4e-3; Lb = 0.4; n = int(round(Lb / hh)) + 1; c = (np.arange(n) - (n - 1) / 2) * hh; X, Y = np.meshgrid(c, c)
    eps = np.where(X ** 2 + Y ** 2 <= 0.02 ** 2, 4.0, 1.0)
    fixed = np.zeros((n, n), bool); fixed[0] = fixed[-1] = True; V0 = np.zeros((n, n)); V0[0] = 200.0; V0[-1] = -200.0
    Vn = solve(fixed, V0, np.zeros((n, n)), hh, eps)
    E0 = 400 / Lb; Ey = -np.gradient(Vn, hh, axis=0); inside = X ** 2 + Y ** 2 <= 0.012 ** 2
    p.compare("Dielectric rod (ε_r = 4): interior field / applied field = 2/(ε_r + 1) (separation of variables)", 2 / 5, float(np.mean(Ey[inside]) / E0), "", tol=2)
    p.compare("… and it is uniform inside (std/mean of E_y within r < 12 mm)", 0.0, float(np.std(Ey[inside]) / np.mean(Ey[inside])), "", kind="abs", tol=0.02)
    rr2 = np.hypot(X, Y); ang = np.arctan2(Y, X); a0 = 0.02; ring = (np.abs(rr2 - 0.04) < hh)
    Vex = -E0 * (rr2 - a0 ** 2 * (4 - 1) / (4 + 1) / rr2) * np.sin(ang)
    p.compare("Outside, r = 40 mm: potential vs −E₀(r − a²(ε_r−1)/((ε_r+1)r)) sin φ (worst error / E₀a)", 0.0, float(np.max(np.abs(Vn[ring] - Vex[ring])) / (E0 * a0)), "", kind="abs", tol=0.08)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].contour(X * 1e3, Y * 1e3, Vn, 30, cmap="RdBu_r"); th_ = np.linspace(0, 2 * pi, 200); ax[0].plot(20 * np.cos(th_), 20 * np.sin(th_), "k", lw=1.5)
    ax[0].set_xlim(-60, 60); ax[0].set_ylim(-60, 60); ax[0].set_aspect("equal"); ax[0].grid(False); ax[0].set_title("Equipotentials: dielectric rod in a uniform field", loc="left", fontsize=10)
    ax[1].plot(c * 1e3, Ey[:, (n - 1) // 2] / E0, color=C_MEAS, label="Cartesian finite volumes (x = 0)")
    yv = np.linspace(-0.1, 0.1, 801); ya = np.abs(yv)
    ex_line = np.where(ya < a0, 2 / 5, 1 + a0 ** 2 * 3 / 5 / np.maximum(ya, 1e-9) ** 2)
    ax[1].plot(yv * 1e3, ex_line, "--", color=C_PRED, label="polar-coordinate solution"); ax[1].set_xlim(-60, 60)
    style_axes(ax[1], "y (mm)", "E_y / E₀", "Field along the symmetry axis")
    p.save(fig, "coordinates", "A dielectric rod in a uniform field: equipotentials and the field along the axis, Cartesian solve vs the polar-coordinate solution.")
    p.discuss(f"""Evaluated by finite differences in the curvilinear variables themselves, the cylindrical and spherical Laplacians, the spherical divergence
and the cylindrical curl agree with their Cartesian counterparts at 300 random points to the precision of the differencing, so the scale-factor
formulas are not something to memorise but something that can be checked. The basis change is a rotation (RRᵀ = I to machine precision) and r² sin θ
integrates to the exact volumes of a sphere and a cone. The payoff is in problems with the right symmetry: in polar coordinates the dielectric rod in a
uniform field is solved in two lines — a uniform interior field of 2/(ε_r + 1) = 0.40 of the applied field — and a Cartesian finite-volume solve with a
staircased rod agrees ({np.mean(Ey[inside]) / E0:.3f}) once the plates are far enough away — with plates at five radii my first run gave 0.409, the
extra 2 % coming from the plates' image dipoles, which the unbounded analytic solution does not have — with the exterior line-dipole perturbation matching as well. Choosing coordinates that follow the boundary turns a
numerical problem into an algebraic one.""")
# tol-convention: relative tolerances are in percent
