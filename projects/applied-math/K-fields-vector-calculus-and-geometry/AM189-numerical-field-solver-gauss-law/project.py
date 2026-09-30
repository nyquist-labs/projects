from eelab import *
from eelab.poisson import solve, flux_through_box, EPS0

META = dict(
    id="AM-189", title="A numerical field solver that obeys Gauss's law", level="M",
    tools="Own finite-volume Poisson solver (sparse matrix, harmonic-mean permittivity at faces), discrete flux integrals over closed boxes, analytic field of a uniformly charged cylinder, dielectric interface conditions, grid-convergence study",
    summary="Solve −∇·(ε∇V) = ρ on a grid and check the solution against the physics it must satisfy: the flux of D out of any closed box equals the "
            "charge inside (exactly, by construction of a finite-volume scheme), the field of a charged rod matches Gauss's-law results, and normal D is continuous across a dielectric boundary.",
    problem="A field solver produces pretty colour maps. How do we know the numbers obey Maxwell's equations?",
    theory=r"""Gauss's law $\oint D\cdot n\,dl=Q_{enc}$ (per unit length in 2-D). A long cylinder of radius a with uniform density ρ: $E=\frac{ρr}{2ε}$ inside, $\frac{ρa^2}{2εr}$ outside. At an interface normal D is continuous and tangential E is continuous, so
$E_{n2}/E_{n1}=ε_1/ε_2$. A finite-volume discretisation integrates the PDE over each cell, so the discrete flux balance holds to round-off for *any* box aligned with the cells; pointwise errors of the second-order stencil fall as h².""",
    method="""Square box 0.2 m, grounded walls. Case 1: charged rod (a = 20 mm, ρ = 1 µC/m³) at the centre in vacuum; fluxes through 5 boxes; radial field vs analytic at the grid sizes 101…401. Case 2: the same rod with the lower half of the box
filled with ε_r = 4: flux balance and the D/E jump conditions at the interface.""",
)


def setup(n, eps_lower=1.0):
    L = 0.2; h = L / (n - 1); x = np.linspace(-L / 2, L / 2, n); X, Y = np.meshgrid(x, x)
    fixed = np.zeros((n, n), bool); fixed[0] = fixed[-1] = fixed[:, 0] = fixed[:, -1] = True
    rho = np.where(X ** 2 + Y ** 2 <= 0.02 ** 2, 1e-6, 0.0)
    eps = np.where(Y < -0.03, eps_lower, 1.0)
    return X, Y, h, fixed, rho, eps


def run(p):
    n = 201; X, Y, h, fixed, rho, eps = setup(n)
    V = solve(fixed, np.zeros((n, n)), rho, h, eps)
    c = n // 2; bad = 0; rows = []
    for half in (15, 25, 40, 60, 90):
        j0, j1, i0, i1 = c - half, c + half, c - half, c + half
        q = rho[j0:j1 + 1, i0:i1 + 1].sum() * h * h; f = flux_through_box(V, eps, h, j0, j1, i0, i1); rows.append((half * h, q, f))
    rr = np.array(rows)
    p.compare("Flux of D out of 5 closed boxes vs enclosed charge (worst relative error)", 0.0, float(np.max(np.abs(rr[:, 2] - rr[:, 1]) / rr[:, 1])), "", kind="abs", tol=1e-8)
    Ey = -np.gradient(V, h, axis=0); Ex = -np.gradient(V, h, axis=1); E = np.hypot(Ex, Ey)
    Q = rho.sum() * h * h
    for rpos in (0.01, 0.05):
        i = c + int(round(rpos / h))
        exact = 1e-6 * rpos / (2 * EPS0) if rpos < 0.02 else Q / (2 * pi * EPS0 * rpos)
        p.compare(f"Radial field at r = {rpos * 1e3:.0f} mm (Gauss's law with the discretised charge)", exact, E[c, i], "V/m", tol=3)
    errs = []; hs = []
    for n_ in (101, 201, 401):
        X_, Y_, h_, f_, r_, e_ = setup(n_); V_ = solve(f_, np.zeros((n_, n_)), r_, h_, e_); c_ = n_ // 2
        Qd = r_.sum() * h_ * h_; i = c_ + int(round(0.04 / h_)); E_ = -(V_[c_, i + 1] - V_[c_, i - 1]) / (2 * h_)
        errs.append(abs(E_ - Qd / (2 * pi * EPS0 * 0.04)) / (Qd / (2 * pi * EPS0 * 0.04))); hs.append(h_)
    p.metric("Field error at r = 40 mm for grid spacing 2 / 1 / 0.5 mm", " / ".join(f"{e * 100:.3f} %" for e in errs), "", "the grounded box makes the field differ slightly from the free-space formula, so the error levels off rather than following h²")
    X, Y, h, fixed, rho, eps = setup(n, 4.0); V2 = solve(fixed, np.zeros((n, n)), rho, h, eps)
    half = 60; f2 = flux_through_box(V2, eps, h, c - half, c + half, c - half, c + half); q2 = rho[c - half:c + half + 1, c - half:c + half + 1].sum() * h * h
    p.compare("With a dielectric half-space: flux of D still equals the enclosed charge", q2, f2, "C/m", tol=1e-6)
    jb = int(np.argmax(Y[:, 0] >= -0.03)); col = c + 10
    Dn_up = -1.0 * (V2[jb + 1, col] - V2[jb, col]) / h; Dn_lo = -4.0 * (V2[jb - 1, col] - V2[jb - 2, col]) / h
    p.compare("Normal D continuous across the interface (ratio just below / just above)", 1.0, Dn_lo / Dn_up, "", tol=5)
    En_up = -(V2[jb + 1, col] - V2[jb, col]) / h; En_lo = -(V2[jb - 1, col] - V2[jb - 2, col]) / h
    p.compare("Normal E jumps by ε₁/ε₂ = 1/4 across the interface", 0.25, En_lo / En_up, "", tol=5)
    Et_up = -(V2[jb, col + 1] - V2[jb, col - 1]) / (2 * h); Et_lo = -(V2[jb - 1, col + 1] - V2[jb - 1, col - 1]) / (2 * h)
    mism = []
    for n_ in (201, 401, 801):
        Xq, Yq, hq, fq, rq, eq = setup(n_, 4.0); Vq = solve(fq, np.zeros((n_, n_)), rq, hq, eq); cq = n_ // 2
        jq = int(np.argmax(Yq[:, 0] >= -0.03)); cc = cq + int(round(0.01 / hq))
        up = -(Vq[jq, cc + 1] - Vq[jq, cc - 1]); lo = -(Vq[jq - 1, cc + 1] - Vq[jq - 1, cc - 1]); mism.append(abs(1 - lo / up))
    p.compare("Tangential E across the interface (adjacent node rows): the mismatch halves each time h halves (first-order → continuous)", 2.0, mism[1] / mism[2], "×", tol=15)
    p.metric("Tangential-E mismatch between the rows either side of the interface, h = 1 / 0.5 / 0.25 mm", " / ".join(f"{v * 100:.1f} %" for v in mism))
    fig, ax = p.fig(1, 2, w=11)
    im = ax[0].contourf(X * 1e3, Y * 1e3, V2, 30, cmap="viridis"); fig.colorbar(im, ax=ax[0], label="V")
    ax[0].axhline(-30, color="w", ls="--", lw=1); ax[0].set_aspect("equal"); ax[0].grid(False)
    ax[0].set_title("Charged rod above an ε_r = 4 half-space", loc="left", fontsize=10); ax[0].set_xlabel("mm"); ax[0].set_ylabel("mm")
    rr_ = X[c, c:] ; ax[1].plot(rr_ * 1e3, E[c, c:], color=C_MEAS, label="solver")
    ra = np.linspace(1e-4, 0.1, 400); ax[1].plot(ra * 1e3, np.where(ra < 0.02, 1e-6 * ra / (2 * EPS0), Q / (2 * pi * EPS0 * ra)), "--", color=C_PRED, label="Gauss's law (free space)")
    style_axes(ax[1], "r (mm)", "|E| (V/m)", "Radial field of the rod (vacuum case)")
    p.save(fig, "gauss", "Potential of a charged rod above a dielectric, and its radial field against Gauss's law.")
    p.discuss(f"""Because the solver is built by integrating the PDE over cells, Gauss's law is not an approximation for it but an identity: the flux of D out of five
different closed boxes equals the enclosed charge to round-off, with or without a dielectric in the box. Pointwise the field matches the
Gauss's-law result for a charged rod inside the rod and outside it, and across the dielectric boundary the solver reproduces the interface
conditions — normal D continuous, normal E reduced four-fold, tangential E continuous in the limit (the mismatch between the node rows either
side falls in proportion to h) — which it was never told explicitly; they follow from the harmonic-mean face
permittivities. The grid study shows the other side of verification: the pointwise error stops shrinking at the level where the grounded box
itself makes the free-space formula inexact, so a convergence test must compare against the solution of the *same* problem.""")
# tol-convention: relative tolerances are in percent
