from eelab import *
from scipy.stats import qmc

META = dict(
    id="AM-127", title="Monte Carlo integration where quadrature fails", level="M",
    tools="Tensor-product Gauss–Legendre quadrature vs plain Monte Carlo vs quasi-Monte Carlo (scrambled Sobol) for integrals in 1–20 dimensions, error scaling, a circuit-yield integral as application",
    summary="Integrate smooth functions in increasing dimension with three methods and measure where each breaks down: tensor quadrature's cost explodes "
            "(curse of dimensionality), Monte Carlo's error stays ∝ N^{−1/2} in any dimension, and quasi-Monte Carlo approaches N^{−1}.",
    problem="A yield integral over 10 toleranced components is a 10-dimensional integral. Why is Monte Carlo the standard tool?",
    theory=r"""With n points per axis, a d-dimensional tensor rule costs n^d evaluations and its error for smooth f decays like n^{−2m}; for fixed budget N the effective n = N^{1/d} collapses as d grows. Monte Carlo: error σ_f/√N, independent of d.
Quasi-MC (low-discrepancy points): error ~ (log N)^d/N — better for smooth, effectively low-dimensional integrands. Test: $\int_{[0,1]^d}\prod_i\frac{π}{2}\sin(πx_i)\,dx = 1$.""",
    method="""d = 1, 2, 5, 10, 20; budgets 10²–10⁶. Gauss–Legendre tensor rule with n = min(64, ⌊N^{1/d}⌋) per axis, plain MC (20 repeats → RMS error), scrambled Sobol QMC (20 scrambles). Application: yield of a 10-component circuit whose output is a smooth function of
the tolerances, vs a 10⁷-sample reference.""",
)


def f(X):
    return np.prod(pi / 2 * np.sin(pi * X), axis=1)


def tensor_gl(d, n):
    if n ** d > 2e6:
        return np.nan, n ** d
    x, w = np.polynomial.legendre.leggauss(n); x = (x + 1) / 2; w = w / 2
    grids = np.meshgrid(*[x] * d, indexing="ij"); W = np.ones_like(grids[0])
    for k in range(d):
        W = W * np.meshgrid(*[w] * d, indexing="ij")[k]
    X = np.stack([g.ravel() for g in grids], 1)
    return np.sum(W.ravel() * f(X)), n ** d


def run(p):
    r = p.rng
    rows = []
    for d in (1, 2, 5, 10, 20):
        for N in (100, 1000, 10000, 100000):
            n = min(64, max(1, int(np.floor(N ** (1 / d)))))      # >64 nodes per axis is already at machine precision (and leggauss(10⁵) would need an eigen-solve of that size)
            q, used = tensor_gl(d, n)
            mc = [np.mean(f(r.random((N, d)))) for _ in range(20)]
            qm = [np.mean(f(qmc.Sobol(d, scramble=True, seed=int(r.integers(1e9))).random(N))) for _ in range(20)]
            rows.append((d, N, abs(q - 1) if np.isfinite(q) else np.nan, np.sqrt(np.mean((np.array(mc) - 1) ** 2)), np.sqrt(np.mean((np.array(qm) - 1) ** 2))))
    rr = np.array(rows)
    for d in (1, 10):
        m = rr[:, 0] == d
        p.compare(f"d = {d}: Monte Carlo RMS error ∝ N^slope (−½, independent of d)", -0.5, np.polyfit(np.log(rr[m, 1]), np.log(rr[m, 3]), 1)[0], "", kind="abs", tol=0.1)
    m = rr[:, 0] == 5
    p.compare("d = 5: quasi-Monte Carlo error slope (≈ −1 for smooth integrands)", -1.0, np.polyfit(np.log(rr[m, 1]), np.log(rr[m, 4]), 1)[0], "", kind="abs", tol=0.3)
    p.metric("Error with N = 10⁵ in d = 10: tensor Gauss (2 points/axis) / MC / QMC", f"{rr[(rr[:, 0] == 10) & (rr[:, 1] == 1e5)][0, 2]:.1e} / {rr[(rr[:, 0] == 10) & (rr[:, 1] == 1e5)][0, 3]:.1e} / {rr[(rr[:, 0] == 10) & (rr[:, 1] == 1e5)][0, 4]:.1e}")
    m1 = (rr[:, 0] == 1) & (rr[:, 1] == 1000)
    p.compare("d = 1: Gauss quadrature is vastly better than MC at equal N (error ratio MC/GL)", 1e6, rr[m1, 3][0] / max(rr[m1, 2][0], 1e-17), "×", kind="abs", tol=1e30)
    tol = 0.05
    def yield_fn(U):
        e = (U - 0.5) * 2 * tol
        out = np.sum(e[:, :5], 1) * 0.5 - np.sum(e[:, 5:] ** 2, 1) * 3 + e[:, 0] * e[:, 5] * 5
        return (np.abs(out) < 0.06).astype(float)
    ref = np.mean([np.mean(yield_fn(r.random((10 ** 6, 10)))) for _ in range(10)])        # 10⁷ samples in chunks (memory)
    est_mc = np.mean(yield_fn(r.random((10 ** 4, 10))))
    p.compare("10-component yield: MC with 10⁴ samples vs 10⁷ reference (within 3σ)", ref, est_mc, "", kind="abs", tol=3 * np.sqrt(ref * (1 - ref) / 1e4))
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    for k, (lab, c) in enumerate((("tensor Gauss", COLORS[1]), ("Monte Carlo", C_MEAS), ("quasi-MC (Sobol)", COLORS[2]))):
        for d, mk_ in ((1, "o"), (10, "s")):
            m = rr[:, 0] == d
            ax[0 if d == 1 else 1].loglog(rr[m, 1], np.maximum(rr[m, 2 + k], 1e-17), mk_ + "-", color=c, label=lab)
    style_axes(ax[0], "evaluations N", "error", "d = 1")
    style_axes(ax[1], "evaluations N", "error", "d = 10")
    N = 100000
    ax[2].semilogy(rr[rr[:, 1] == N, 0], np.maximum(rr[rr[:, 1] == N, 2], 1e-17), "o-", color=COLORS[1], label="tensor Gauss")
    ax[2].semilogy(rr[rr[:, 1] == N, 0], rr[rr[:, 1] == N, 3], "s-", color=C_MEAS, label="MC"); ax[2].semilogy(rr[rr[:, 1] == N, 0], rr[rr[:, 1] == N, 4], "^-", color=COLORS[2], label="QMC")
    style_axes(ax[2], "dimension d", "error at N = 10⁵", "Curse of dimensionality")
    p.save(fig, "monte_carlo", "Integration error vs evaluations in 1-D and 10-D, and vs dimension at a fixed budget.")
    p.discuss("""In one dimension Gauss–Legendre quadrature is untouchable — machine precision with a few points, while Monte Carlo is stuck at N^{−1/2}. In ten
dimensions the picture reverses: a tensor rule can afford only two points per axis within 10⁵ evaluations and its error is enormous, whereas Monte
Carlo's error is the same N^{−1/2} as in 1-D — dimension does not appear in it. Quasi-Monte Carlo with scrambled Sobol points is better still for this
smooth integrand, approaching N^{−1}. That is why tolerance and yield analysis (a 10–100-dimensional integral over component values) is done by
Monte Carlo, and why QMC is increasingly used when the response is smooth; a pass/fail yield indicator is discontinuous, which blunts QMC's gain.""")
# tol-convention: relative tolerances are in percent
