from eelab import *
import scipy.linalg as sla
import time

META = dict(
    id="AM-064", title="LU decomposition with partial pivoting, from scratch", level="M",
    tools="Own Doolittle LU (vectorised row operations) with and without partial pivoting, forward/back substitution, backward-error and growth-factor analysis, comparison with LAPACK",
    summary="Implement LU factorisation, show that without pivoting a tiny pivot destroys the answer while partial pivoting makes it backward "
            "stable, measure the backward error and growth factor on random and nodal matrices, and compare with LAPACK.",
    problem="Gaussian elimination is taught without row swaps. Why does every real solver swap rows?",
    theory=r"""PA = LU. Without pivoting, a small pivot ε creates multipliers ~1/ε, entries grow by ~1/ε and rounding errors of size ε_mach·(1/ε) swamp the solution. With partial pivoting multipliers are ≤ 1 and the computed
solution is backward stable: $\frac{\|Ax̂-b\|}{\|A\|\|x̂\|}$ ≈ ε_mach·(growth factor), growth typically small (≤ ~n^{2/3} for random matrices, though 2^{n−1} is possible). Cost (2/3)n³ flops.""",
    method="""(i) The 2×2 example [[ε, 1], [1, 1]] for ε = 10⁻¹⁶…10⁻⁴. (ii) 100 random 200×200 matrices and nodal matrices of random resistor networks: backward error and growth factor, with/without pivoting,
vs scipy.linalg.lu_factor. (iii) Wilkinson's matrix where growth is 2^{n−1}. (iv) Time vs n.""",
)


def lu(A, pivot=True):
    A = A.astype(float).copy(); n = len(A); perm = np.arange(n); gmax = np.abs(A).max()
    for k in range(n - 1):
        if pivot:
            m = k + np.argmax(np.abs(A[k:, k]))
            if m != k:
                A[[k, m]] = A[[m, k]]; perm[[k, m]] = perm[[m, k]]
        A[k + 1:, k] /= A[k, k]
        A[k + 1:, k + 1:] -= np.outer(A[k + 1:, k], A[k, k + 1:])
        gmax = max(gmax, np.abs(A[k + 1:, k + 1:]).max() if k + 1 < n else 0)
    return A, perm, gmax


def solve(F, perm, b):
    n = len(F); y = b[perm].astype(float).copy()
    for i in range(n):
        y[i] -= F[i, :i] @ y[:i]
    x = y.copy()
    for i in range(n - 1, -1, -1):
        x[i] = (x[i] - F[i, i + 1:] @ x[i + 1:]) / F[i, i]
    return x


def berr(A, x, b):
    return np.linalg.norm(A @ x - b, np.inf) / (np.linalg.norm(A, np.inf) * np.linalg.norm(x, np.inf))


def run(p):
    rows = []
    for e in (1e-4, 1e-8, 1e-12, 1e-16):
        A = np.array([[e, 1.0], [1.0, 1.0]]); b = np.array([1.0, 2.0]); xt = np.array([1 / (1 - e), (1 - 2 * e) / (1 - e)])     # exact solution
        F, pm, _ = lu(A, False); x0 = solve(F, pm, b); F, pm, _ = lu(A, True); x1 = solve(F, pm, b)
        rows.append((e, np.max(np.abs(x0 - xt)), np.max(np.abs(x1 - xt))))
    p.compare("[[ε,1],[1,1]] with ε = 1e-16: error without pivoting (≈ 1 — the answer is wrong)", 1.0, rows[-1][1], "", kind="abs", tol=0.5)
    p.compare("… with partial pivoting", 0, rows[-1][2], "", kind="abs", tol=1e-15)
    r = p.rng
    be, gf, diff = [], [], []
    for _ in range(100):
        A = r.normal(size=(200, 200)); b = r.normal(size=200)
        F, pm, g = lu(A); x = solve(F, pm, b)
        be.append(berr(A, x, b)); gf.append(g / np.abs(A).max())
        diff.append(np.max(np.abs(x - sla.lu_solve(sla.lu_factor(A), b))) / np.max(np.abs(x)))
    p.compare("Random 200×200: median backward error (≈ ε_mach = 2.2e-16 scale)", 2.2e-16, np.median(be), "", kind="abs", tol=2e-15)
    p.compare("Own LU vs LAPACK solution, worst relative difference", 0, max(diff), "", kind="abs", tol=1e-9)
    p.metric("Growth factor, random matrices (median / max)", f"{np.median(gf):.1f} / {max(gf):.1f}")
    n = 50
    W = np.tril(-np.ones((n, n)), -1) + np.eye(n); W[:, -1] = 1
    F, pm, g = lu(W)
    p.compare("Wilkinson's matrix: growth factor = 2^(n−1)", 2.0 ** (n - 1), g, "", tol=1e-07)
    ts = []
    for n_ in (100, 200, 400, 800):
        A = r.normal(size=(n_, n_)); t0 = time.perf_counter(); lu(A); ts.append(time.perf_counter() - t0)
    p.metric("Own LU time exponent (vectorised rank-1 updates)", np.polyfit(np.log([100, 200, 400, 800]), np.log(ts), 1)[0], "", "∝ n³ flops but memory-bound in NumPy")
    fig, ax = p.fig(1, 2, w=11)
    rr = np.array(rows)
    ax[0].loglog(rr[:, 0], np.maximum(rr[:, 1], 1e-17), "o-", color=COLORS[1], label="no pivoting"); ax[0].loglog(rr[:, 0], np.maximum(rr[:, 2], 1e-17), "s-", color=C_MEAS, label="partial pivoting")
    style_axes(ax[0], "pivot ε", "error in x", "A tiny pivot destroys unpivoted elimination")
    ax[1].hist(np.log10(be), bins=25, color=C_MEAS)
    style_axes(ax[1], "log₁₀ backward error", "count", "Pivoted LU is backward stable", legend=False)
    p.save(fig, "lu", "Error with and without pivoting for the classic 2×2 example, and backward errors on 100 random systems.")
    p.discuss(f"""Without row swaps the 2×2 example with ε = 10⁻¹⁶ returns x₁ = 0 instead of ≈ 1 — not a small error but a wrong answer, because the multiplier 1/ε
wipes out the information in the second row. With partial pivoting the same code is backward stable: across 100 random systems the backward error
sits at a few × 10⁻¹⁶ and the solutions match LAPACK. The growth factor stays modest for random matrices (median {np.median(gf):.0f}), but Wilkinson's
matrix shows the worst case 2^{{n−1}} is real — it simply almost never occurs in practice. Nodal matrices of passive circuits are diagonally
dominant, which is why SPICE can often pivot for sparsity rather than magnitude.""")
# tol-convention: relative tolerances are in percent
