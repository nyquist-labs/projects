from eelab import *
from scipy.sparse import diags, kron, identity
from scipy.sparse.linalg import eigsh, eigs

META = dict(
    id="SL-124", title="Rectangular waveguide modes and cutoff frequencies", level="H",
    tools="Finite-difference Helmholtz eigenproblem on the waveguide cross-section (SciPy sparse eigensolver)",
    summary="Solve for the TE and TM modes of a WR-90 X-band waveguide numerically, compare cutoff frequencies with "
            "f_c = (c/2)√((m/a)²+(n/b)²), and plot the field patterns of the lowest modes.",
    problem="A hollow metal pipe only carries microwaves above a cutoff frequency. Which modes exist, and where do they "
            "start?",
    theory=r"""Cross-section fields obey $\nabla_t^2\psi+k_c^2\psi=0$ with Dirichlet (TM, E_z) or Neumann (TE, H_z) walls. Rectangular a×b:
$k_c=\pi\sqrt{(m/a)^2+(n/b)^2}$, $f_c=ck_c/2\pi$. WR-90: a = 22.86 mm, b = 10.16 mm → TE₁₀ 6.557 GHz, TE₂₀ 13.11 GHz, TE₀₁ 14.76 GHz,
TE/TM₁₁ 16.15 GHz. Single-mode band 6.56–13.1 GHz.""",
    method="""Grid 92×41 points (0.25 mm). 5-point Laplacian with Dirichlet or Neumann (ghost-point) boundaries, smallest eigenvalues by shift-invert
Lanczos; f_c = c√λ/2π.""",
)


def lap1d(n, h, bc):
    main = -2 * np.ones(n); off = np.ones(n - 1)
    L = diags([off, main, off], [-1, 0, 1]).tolil()
    if bc == "N":
        L[0, 1] = 2; L[-1, -2] = 2
    return L.tocsr() / h**2


def run(p):
    c = 299792458.0
    a, b = 22.86e-3, 10.16e-3
    res = {}
    for kind, bc, npts in (("TM", "D", None), ("TE", "N", None)):
        if bc == "D":
            nx, ny = 91, 39; hx, hy = a / (nx + 1), b / (ny + 1)
        else:
            nx, ny = 92, 41; hx, hy = a / (nx - 1), b / (ny - 1)
        Lx, Ly = lap1d(nx, hx, bc), lap1d(ny, hy, bc)
        L = kron(identity(ny), Lx) + kron(Ly, identity(nx))
        if bc == "D":
            vals, vecs = eigsh(-L, k=7, sigma=0.0, which="LM")
        else:   # ghost-point Neumann rows make L non-symmetric: use the general eigensolver
            vals, vecs = eigs(-L, k=8, sigma=1.0, which="LM"); vals, vecs = vals.real, vecs.real
        order = np.argsort(vals)
        vals, vecs = vals[order], vecs[:, order]
        fc = c * np.sqrt(np.maximum(vals, 0)) / (2 * pi)
        res[kind] = (fc, vecs, nx, ny)
    mn = lambda m, n: c / 2 * np.sqrt((m / a) ** 2 + (n / b) ** 2)
    te = [f for f in res["TE"][0] if f > 1e6]
    p.compare("TE₁₀ cutoff", mn(1, 0), te[0], "Hz", tol=0.5)
    p.compare("TE₂₀ cutoff", mn(2, 0), te[1], "Hz", tol=0.5)
    p.compare("TE₀₁ cutoff", mn(0, 1), te[2], "Hz", tol=0.5)
    p.compare("TM₁₁ cutoff", mn(1, 1), res["TM"][0][0], "Hz", tol=0.5)
    p.metric("Single-mode bandwidth", f"{te[0]/1e9:.3f}–{te[1]/1e9:.3f} GHz")
    fig, axs = p.fig(2, 3, w=11, h=5)
    names = []
    tel = [i for i, f in enumerate(res["TE"][0]) if f > 1e6][:3]
    for j, idx in enumerate(tel):
        fc, vecs, nx, ny = res["TE"]
        axs[0][j].imshow(vecs[:, idx].reshape(ny, nx), cmap="RdBu", aspect="equal"); axs[0][j].axis("off")
        axs[0][j].set_title(f"TE mode, f_c = {fc[idx]/1e9:.2f} GHz (H_z)", fontsize=9)
    for j in range(3):
        fc, vecs, nx, ny = res["TM"]
        axs[1][j].imshow(vecs[:, j].reshape(ny, nx), cmap="RdBu", aspect="equal"); axs[1][j].axis("off")
        axs[1][j].set_title(f"TM mode, f_c = {fc[j]/1e9:.2f} GHz (E_z)", fontsize=9)
    p.save(fig, "modes", "Numerical eigenmodes: TE₁₀, TE₂₀, TE₀₁ (top) and TM₁₁, TM₂₁, TM₃₁ (bottom).")
    p.csv("te_cutoffs", fc_hz=res["TE"][0]); p.csv("tm_cutoffs", fc_hz=res["TM"][0])
    p.discuss("""The finite-difference eigenvalues reproduce the analytic cutoffs to a fraction of a percent (a first run fed the
non-symmetric Neumann matrix to a *symmetric* eigensolver and got TE cutoffs 1–4 % off — the solver silently assumed a
property the matrix did not have) (the residual is the O(h²)
discretisation error of the 5-point Laplacian), and the eigenvectors show the familiar half-sine patterns. TE₁₀ is
alone between 6.56 and 13.1 GHz, which is why X-band radar uses WR-90 there: a single mode means a single, predictable
propagation velocity. The same solver works for any cross-section (ridged, circular) where no closed form exists.""")
