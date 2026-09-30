from eelab import *
import scipy.sparse as sp
import scipy.sparse.linalg as spla

META = dict(
    id="AM-119", title="Finite elements from scratch: capacitance of a coaxial line", level="H",
    tools="Own 2-D FEM with linear triangles (mesh generation, element stiffness matrices, sparse assembly, Dirichlet conditions), energy-based capacitance, convergence study; comparison with 2πε/ln(b/a)",
    summary="Solve Laplace's equation in the annulus between the conductors of a coaxial line with self-written linear finite elements, compute the "
            "capacitance per metre from the stored energy, and verify both the exact value and the method's convergence rate.",
    problem="Finite differences need rectangular grids. How does FEM handle curved conductors — and how fast does it converge?",
    theory=r"""Weak form: find φ with ∫∇φ·∇v dA = 0 for all test functions v vanishing on the conductors. Linear triangles give element matrices $K_e=\frac{1}{4A}B B^T$ (B from edge vectors). Capacitance from energy: $C = ε\,φ^TKφ/V^2$.
Exact for a coax: $C'=\frac{2πε}{\ln(b/a)}$. With conforming linear elements the energy error is O(h²), so C converges from above with order 2; curved boundaries approximated by chords also contribute O(h²).""",
    method="""a = 1 mm, b = 3.5 mm, air. Structured polar mesh: n_r radial × n_θ angular divisions, each quad split into two triangles; refined 5 times. Inner conductor 1 V, outer 0 V. Error vs 2πε₀/ln 3.5; observed order; potential vs ln(r) profile.""",
)

EPS0 = 8.8541878128e-12


def mesh(nr, nt, a, b):
    r = np.linspace(a, b, nr + 1); t = np.linspace(0, 2 * pi, nt, endpoint=False)
    R, T = np.meshgrid(r, t, indexing="ij")
    pts = np.c_[(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel()]
    idx = lambda i, j: i * nt + (j % nt)
    tris = []
    for i in range(nr):
        for j in range(nt):
            a0, a1, b0, b1 = idx(i, j), idx(i, j + 1), idx(i + 1, j), idx(i + 1, j + 1)
            tris += [(a0, b0, b1), (a0, b1, a1)]
    return pts, np.array(tris), np.arange(nt), np.arange(nr * nt, (nr + 1) * nt)


def assemble(pts, tris):
    rows, cols, vals = [], [], []
    for t in tris:
        P = pts[t]
        B = np.array([[P[1, 1] - P[2, 1], P[2, 1] - P[0, 1], P[0, 1] - P[1, 1]], [P[2, 0] - P[1, 0], P[0, 0] - P[2, 0], P[1, 0] - P[0, 0]]])
        A = 0.5 * abs((P[1, 0] - P[0, 0]) * (P[2, 1] - P[0, 1]) - (P[2, 0] - P[0, 0]) * (P[1, 1] - P[0, 1]))
        Ke = B.T @ B / (4 * A)
        for i in range(3):
            for j in range(3):
                rows.append(t[i]); cols.append(t[j]); vals.append(Ke[i, j])
    n = len(pts)
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n))


def solve(nr, nt, a=1e-3, b=3.5e-3):
    pts, tris, inner, outer = mesh(nr, nt, a, b)
    K = assemble(pts, tris)
    phi = np.zeros(len(pts)); phi[inner] = 1.0
    fixed = np.zeros(len(pts), bool); fixed[inner] = fixed[outer] = True
    free = ~fixed
    phi[free] = spla.spsolve(K[free][:, free].tocsc(), -K[free][:, fixed] @ phi[fixed])
    return EPS0 * phi @ (K @ phi), pts, phi


def run(p):
    Cex = 2 * pi * EPS0 / np.log(3.5)
    rows = []
    for k in range(5):
        nr, nt = 4 * 2 ** k, 16 * 2 ** k
        C, pts, phi = solve(nr, nt)
        rows.append((nr, nt, C, len(pts)))
    rr = np.array(rows)
    err = np.abs(rr[:, 2] / Cex - 1)
    p.compare("Finest mesh: FEM capacitance vs 2πε/ln(b/a)", Cex, rr[-1, 2], "F/m", tol=0.1)
    order = np.polyfit(np.log(1 / rr[:, 0]), np.log(err), 1)[0]
    p.compare("Observed convergence order of the capacitance error (linear elements: 2)", 2.0, order, "", kind="abs", tol=0.2)
    p.compare("Energy principle: FEM capacitance approaches from above (all errors positive; 1 = yes)", 1, int(np.all(rr[:, 2] > Cex * (1 - 1e-6))), "", kind="abs")
    C, pts, phi = solve(32, 128)
    r = np.hypot(pts[:, 0], pts[:, 1])
    p.compare("Potential follows ln(b/r)/ln(b/a) (max deviation)", 0, np.max(np.abs(phi - np.log(3.5e-3 / r) / np.log(3.5))), "V", kind="abs", tol=1e-3)
    fig, ax = p.fig(1, 2, w=11)
    pts0, tris0, _, _ = mesh(4, 16, 1e-3, 3.5e-3)
    ax[0].triplot(pts0[:, 0] * 1e3, pts0[:, 1] * 1e3, tris0, color=C_MEAS, lw=.6); ax[0].set_aspect("equal")
    style_axes(ax[0], "x (mm)", "y (mm)", "Coarsest mesh (128 triangles)", legend=False)
    ax[1].loglog(rr[:, 3], err, "o-", color=C_MEAS, label="relative capacitance error"); ax[1].loglog(rr[:, 3], err[0] * (rr[:, 3] / rr[0, 3]) ** -1, "--", color=C_PRED, label="∝ N⁻¹ = h²")
    style_axes(ax[1], "number of nodes", "|C − C_exact| / C_exact", "Convergence")
    p.save(fig, "fem_coax", "The FEM mesh of the coaxial cross-section and the convergence of the computed capacitance.")
    p.discuss(f"""A hundred-odd lines of finite elements — mesh, element stiffness matrices, sparse assembly, Dirichlet conditions — compute the coax's capacitance to
{err[-1] * 100:.3f} % on the finest mesh, with the error falling as h² (observed order {order:.2f}) and always from above, as the energy (Thomson) principle guarantees
for conforming elements. The mesh follows the round conductors naturally, which is FEM's main advantage over rectangular finite differences (AM-189),
where staircased boundaries limit accuracy. Here most of the remaining error comes from representing circles by polygons; curved (isoparametric)
elements or higher-order shape functions would remove it.""")
# tol-convention: relative tolerances are in percent
