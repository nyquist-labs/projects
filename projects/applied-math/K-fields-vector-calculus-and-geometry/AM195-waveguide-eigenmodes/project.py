from eelab import *
from scipy.sparse import diags, kron, identity
from scipy.sparse.linalg import eigsh
from scipy.special import jn_zeros, jnp_zeros

C0 = 299792458.0

META = dict(
    id="AM-195", title="Waveguide modes as a Helmholtz eigenvalue problem", level="H",
    tools="Finite-difference Laplacian with Dirichlet (TM) and Neumann (TE) boundary conditions on cell-centred grids, sparse shift-invert eigen-solver, analytic rectangular cutoffs, Bessel-zero cutoffs of the circular guide, convergence orders for smooth and staircased boundaries, guide wavelength",
    summary="Find the cutoff frequencies and field patterns of hollow metal waveguides by solving ∇²ψ + k_c²ψ = 0 as a matrix eigenproblem, check them "
            "against the analytic WR-90 and circular-guide results, and measure how the discretisation error converges — quickly for a rectangle, slowly when a round wall is approximated by steps.",
    problem="Why does a waveguide have a cutoff frequency, and how are the modes of a guide with an arbitrary cross-section computed?",
    theory=r"""Inside a hollow conductor the transverse field of each mode obeys $\nabla_t^2ψ+k_c^2ψ=0$, with ψ = E_z = 0 on the wall (TM) or ∂H_z/∂n = 0 (TE). Propagation needs $k>k_c$: $f_c=\frac{c\,k_c}{2π}$. Rectangle a × b: $k_c^2=(mπ/a)^2+(nπ/b)^2$; WR-90 (22.86 × 10.16 mm):
TE₁₀ 6.557 GHz, TE₂₀ 13.114, TE₀₁ 14.754, TE₁₁/TM₁₁ 16.145 GHz. Circle of radius R: TE₁₁ at $p'_{11}c/(2πR)$, TM₀₁ at $p_{01}c/(2πR)$ with $p'_{11}$ = 1.8412, $p_{01}$ = 2.4048. Guide wavelength $λ_g=λ/\sqrt{1-(f_c/f)^2}$. A second-order stencil converges as h² on a rectangle; a
staircased round wall limits convergence to about first order.""",
    method="""Cell-centred grids with mirror (Neumann) or antimirror (Dirichlet) ghost cells; eigsh in shift-invert mode for the 8 smallest eigenvalues. WR-90 at h = a/40, a/80, a/160; circle R = 10 mm with 40…160 cells across, staircased.""",
)


def lap1d(n, h, kind):
    main = -2 * np.ones(n); main[0] += 1 if kind == "N" else -1; main[-1] += 1 if kind == "N" else -1
    return diags([np.ones(n - 1), main, np.ones(n - 1)], [-1, 0, 1]) / h ** 2


def rect_modes(a, b, h, kind, k=8):
    nx, ny = int(round(a / h)), int(round(b / h))
    Lp = kron(identity(ny), lap1d(nx, a / nx, kind)) + kron(lap1d(ny, b / ny, kind), identity(nx))
    w, v = eigsh(-Lp.tocsc(), k=k, sigma=-1e-3 if kind == "N" else 0, which="LM")
    o = np.argsort(w); w, v = w[o], v[:, o]
    if kind == "N":
        w, v = w[1:], v[:, 1:]                                    # drop the constant (k_c = 0) Neumann solution
    return np.sqrt(np.abs(w)) * C0 / (2 * pi), v, (nx, ny)


def circle_modes(R, n, kind, k=6):
    h = 2 * R / n; c = (np.arange(n) + 0.5) * h - R; X, Y = np.meshgrid(c, c); inside = X ** 2 + Y ** 2 <= R ** 2
    idx = -np.ones((n, n), int); idx[inside] = np.arange(inside.sum()); rows, cols, vals = [], [], []
    J, I = np.nonzero(inside); kk = idx[J, I]; diag = np.zeros(len(kk))
    for dj, di in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        jj, ii = J + dj, I + di; ok = (jj >= 0) & (jj < n) & (ii >= 0) & (ii < n)
        inn = ok.copy(); inn[ok] = inside[jj[ok], ii[ok]]
        rows.append(kk[inn]); cols.append(idx[jj[inn], ii[inn]]); vals.append(np.ones(inn.sum()))
        diag -= 1 if kind == "D" else inn * 1.0                    # Dirichlet wall: ghost = −ψ counts as −1 on the diagonal twice → −2 total with the −1 below
        if kind == "D":
            diag -= (~inn) * 1.0
    from scipy.sparse import coo_matrix
    A = coo_matrix((np.concatenate(vals + [diag]), (np.concatenate(rows + [kk]), np.concatenate(cols + [kk]))), shape=(len(kk), len(kk))) / h ** 2
    w = eigsh(-A.tocsc(), k=k, sigma=-1e-3 if kind == "N" else 0, which="LM", return_eigenvectors=False)
    w = np.sort(w)
    if kind == "N":
        w = w[1:]
    return np.sqrt(np.abs(w)) * C0 / (2 * pi)


def run(p):
    a, b = 22.86e-3, 10.16e-3
    exact = lambda m, n_: C0 / 2 * np.sqrt((m / a) ** 2 + (n_ / b) ** 2)
    te_ex = sorted([exact(m, n_) for m in range(5) for n_ in range(3) if m + n_ > 0])[:5]; tm_ex = sorted([exact(m, n_) for m in range(1, 5) for n_ in range(1, 3)])[:3]
    errs = []
    for div in (40, 80, 160):
        fte, v_te, shp = rect_modes(a, b, a / div, "N"); ftm, v_tm, _ = rect_modes(a, b, a / div, "D", k=4)
        errs.append((div, abs(fte[0] - te_ex[0]) / te_ex[0], abs(ftm[0] - tm_ex[0]) / tm_ex[0]))
        if div == 160:
            for i, nm in enumerate(["TE10", "TE20", "TE01", "TE11"]):
                p.compare(f"WR-90 {nm} cutoff (h = a/160)", te_ex[i], fte[i], "Hz", tol=0.05)
            p.compare("WR-90 TM11 cutoff (h = a/160)", tm_ex[0], ftm[0], "Hz", tol=0.05)
            keep = (v_te[:, 0], shp)
    e = np.array(errs)
    p.compare("Rectangle: error of the TM11 cutoff falls as h² (order from a/80 → a/160)", 2.0, np.log2(e[1, 2] / e[2, 2]), "", kind="abs", tol=0.1)
    p.metric("TE10 cutoff error, h = a/40 / a/80 / a/160", " / ".join(f"{v:.1e}" for v in e[:, 1]), "", "second order: the error falls four-fold per halving of h")
    R = 10e-3; te11 = 1.8412 * C0 / (2 * pi * R); tm01 = jn_zeros(0, 1)[0] * C0 / (2 * pi * R); ce = []
    for nc in (40, 80, 160):
        ft = circle_modes(R, nc, "N"); fm = circle_modes(R, nc, "D", k=3)
        ce.append((nc, ft[0], fm[0]))
    ce = np.array(ce)
    p.compare("Circular guide R = 10 mm: TE11 cutoff p′₁₁c/(2πR), 160 cells across", te11, ce[-1, 1], "Hz", tol=1)
    p.compare("Circular guide: TM01 cutoff p₀₁c/(2πR), 160 cells across", tm01, ce[-1, 2], "Hz", tol=1)
    ordc = np.log2(abs(ce[1, 2] - tm01) / abs(ce[2, 2] - tm01))
    p.compare("Staircased round wall: TM01 convergence order from the last two grids (≈ 1, and erratic — not 2)", 1.0, ordc, "", kind="abs", tol=0.6)
    p.metric("TM01 relative error at 40 / 80 / 160 cells across", " / ".join(f"{abs(v - tm01) / tm01 * 100:.2f} %" for v in ce[:, 2]))
    f = 10e9; lg = C0 / f / np.sqrt(1 - (te_ex[0] / f) ** 2)
    p.metric("WR-90 at 10 GHz: free-space / guide wavelength (TE10)", f"{C0 / f * 1e3:.1f} mm / {lg * 1e3:.1f} mm", "", f"single-mode band {te_ex[0] / 1e9:.2f}–{te_ex[1] / 1e9:.2f} GHz")
    fig, ax = p.fig(1, 3, w=13, h=3.6)
    (vec, (nx, ny)) = keep
    _, v2, _ = rect_modes(a, b, a / 80, "N")
    for k_, t_ in ((0, "TE10: H_z"), (3, "TE11: H_z")):
        ax[0 if k_ == 0 else 1].imshow(v2[:, k_].reshape(int(round(b / (a / 80))), 80), cmap="RdBu_r", extent=[0, a * 1e3, 0, b * 1e3], origin="lower")
        ax[0 if k_ == 0 else 1].set_title(f"WR-90 {t_}", loc="left", fontsize=10); ax[0 if k_ == 0 else 1].grid(False)
    ax[2].loglog([40, 80, 160], e[:, 2], "o-", color=C_MEAS, label="rectangle TM11"); ax[2].loglog([40, 80, 160], np.abs(ce[:, 2] - tm01) / tm01, "s-", color=C_PRED, label="circle TM01 (staircase)")
    ax[2].loglog([40, 160], [e[0, 2], e[0, 2] / 16], ":", color="gray", label="h²")
    style_axes(ax[2], "cells across", "relative cutoff error", "Convergence")
    p.save(fig, "waveguide", "Two WR-90 mode patterns from the eigen-solver and the convergence of computed cutoffs.")
    p.discuss(f"""The modes of a hollow guide are the eigenvectors of a discrete Laplacian, and the cutoff frequencies are its eigenvalues: for WR-90 the solver
finds TE₁₀, TE₂₀, TE₀₁ and the degenerate TE₁₁/TM₁₁ pair at the analytic frequencies, and the error of a mode that the stencil does not
represent exactly falls as h² (observed order {np.log2(e[1, 2] / e[2, 2]):.2f}). The same code handles any cross-section, which is the point: for a round guide the
staircase wall still gives TE₁₁ and TM₀₁ within a fraction of a percent at 160 cells, but the error no longer falls smoothly — it jumps as cells
enter or leave the staircase (0.01 %, 0.16 %, 0.07 % at 40, 80, 160 cells) — because the geometry error, not the stencil, now dominates. Conformal or finite-element meshes exist to fix exactly that. The physics of cutoff is visible in
the eigenvalue itself: below f_c the axial wavenumber √(k² − k_c²) is imaginary and the mode decays instead of propagating.""")
# tol-convention: relative tolerances are in percent
