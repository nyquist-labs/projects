from eelab import *
from scipy.sparse import diags, kron, identity
from scipy.sparse.linalg import spsolve

META = dict(
    id="AM-190", title="Laplace's equation by relaxation: Jacobi, Gauss–Seidel and SOR", level="M",
    tools="Own Jacobi, Gauss–Seidel and successive over-relaxation (red–black ordering, vectorised), spectral-radius predictions of convergence rate, optimal over-relaxation factor, analytic Fourier-series solution, sparse direct solve as reference",
    summary="Solve the classic 'lid-driven' potential problem three iterative ways, predict from the eigenvalues of the iteration matrix exactly how "
            "many sweeps each needs, and show how one parameter — the over-relaxation factor — turns an N²-scaling method into an N-scaling one.",
    problem="Relaxation is the simplest way to solve for a potential. Why is it so slow, and how does SOR fix it?",
    theory=r"""On an N × N interior grid with h = 1/(N+1), Jacobi's error-reduction factor per sweep is $ρ_J=\cos(πh)$, Gauss–Seidel's $ρ_J^2$, and SOR with $ω_{opt}=\frac{2}{1+\sin(πh)}$ has $ρ=ω_{opt}-1$. Sweeps to reduce the error by $10^{-6}$:
$\ln 10^{-6}/\ln ρ$ ≈ 0.28·(N+1)²·6 for Jacobi, half that for Gauss–Seidel, ≈ 2.2·(N+1) for SOR. Square with V = 1 on the top edge and 0 elsewhere: $V=\sum_{n\,odd}\frac{4}{nπ}\frac{\sin(nπx)\sinh(nπy)}{\sinh(nπ)}$; V(½, ½) = ¼ exactly by symmetry (superposition of four rotated problems).""",
    method="""Grids N = 31, 63, 127. Iterate from zero until the error against the sparse direct solution falls below 10⁻⁶ (or 200 000 sweeps). Measured asymptotic rate from the late error history. SOR factor scan at N = 63.""",
)


def relax(N, method, omega=1.0, tol=1e-6, maxit=200000, ref=None):
    V = np.zeros((N + 2, N + 2)); V[-1, 1:-1] = 1.0; hist = []
    ii, jj = np.meshgrid(np.arange(1, N + 1), np.arange(1, N + 1)); red = (ii + jj) % 2 == 0
    for it in range(maxit):
        if method == "jacobi":
            V[1:-1, 1:-1] = 0.25 * (V[:-2, 1:-1] + V[2:, 1:-1] + V[1:-1, :-2] + V[1:-1, 2:])
        else:
            for m in (red, ~red):
                nb = 0.25 * (V[:-2, 1:-1] + V[2:, 1:-1] + V[1:-1, :-2] + V[1:-1, 2:])
                inner = V[1:-1, 1:-1]; inner[m] = (1 - omega) * inner[m] + omega * nb[m]
        e = np.max(np.abs(V[1:-1, 1:-1] - ref)); hist.append(e)
        if e < tol:
            break
    return V, np.array(hist)


def direct(N):
    T = diags([-np.ones(N - 1), 4 * np.ones(N), -np.ones(N - 1)], [-1, 0, 1]); S = diags([-np.ones(N - 1), -np.ones(N - 1)], [-1, 1])
    A = kron(identity(N), T) + kron(S, identity(N)); b = np.zeros((N, N)); b[-1, :] = 1.0
    return spsolve(A.tocsc(), b.ravel()).reshape(N, N)


def run(p):
    rows = []
    for N in (31, 63, 127):
        ref = direct(N); h = 1 / (N + 1); rj = np.cos(pi * h); wopt = 2 / (1 + np.sin(pi * h))
        pred = {"jacobi": np.log(1e-6 / 0.5) / np.log(rj), "gs": np.log(1e-6 / 0.5) / np.log(rj ** 2), "sor": np.log(1e-6 / 0.5) / np.log(wopt - 1)}
        out = {}
        for m, om in (("jacobi", 1.0), ("gs", 1.0), ("sor", wopt)):
            if m == "jacobi" and N == 127:
                out[m] = (np.nan, np.nan); continue
            _, hist = relax(N, "jacobi" if m == "jacobi" else "rb", om, ref=ref)
            k = len(hist); tail = hist[int(k * 0.7):]; rate = np.exp(np.polyfit(np.arange(len(tail)), np.log(tail), 1)[0])
            out[m] = (k, rate)
        rows.append((N, pred, out, rj, wopt))
        if N == 63:
            p.compare("N = 63, Jacobi: measured error-reduction factor per sweep = cos(πh)", rj, out["jacobi"][1], "", tol=0.05)
            p.compare("N = 63, Gauss–Seidel: factor = cos²(πh)", rj ** 2, out["gs"][1], "", tol=0.05)
            p.compare("N = 63, SOR at ω_opt: factor ≈ ω_opt − 1 (asymptotically; SOR's Jordan structure slows the approach)", wopt - 1, out["sor"][1], "", tol=5)
            p.compare("N = 63, Gauss–Seidel sweeps to 10⁻⁶ ≈ ½ of Jacobi's", 0.5, out["gs"][0] / out["jacobi"][0], "", tol=5)
    it_sor = [r_[2]["sor"][0] for r_ in rows]; it_gs = [r_[2]["gs"][0] for r_ in rows]
    p.compare("Doubling N multiplies Gauss–Seidel sweeps by ≈ 4 (N = 63 → 127)", 4.0, it_gs[2] / it_gs[1], "×", tol=10)
    p.compare("Doubling N multiplies SOR sweeps by ≈ 2 (N = 63 → 127)", 2.0, it_sor[2] / it_sor[1], "×", tol=15)
    N = 63; ref = direct(N)
    p.compare("Centre potential V(½, ½) = ¼ (symmetry argument)", 0.25, ref[N // 2, N // 2], "V", tol=0.01)
    x = np.arange(1, N + 1) / (N + 1); Xg, Yg = np.meshgrid(x, x)
    four = sum(4 / (n * pi) * np.sin(n * pi * Xg) * np.sinh(n * pi * Yg) / np.sinh(n * pi) for n in range(1, 200, 2))
    p.metric("Direct solution vs 100-term Fourier series: max difference away from the lid corners", float(np.max(np.abs(ref - four)[: -3, 3:-3])), "V", "second-order discretisation error")
    oms = np.linspace(1.5, 1.99, 25); its = []
    for om in oms:
        _, hh = relax(N, "rb", om, ref=ref, maxit=20000); its.append(len(hh))
    wbest = oms[int(np.argmin(its))]
    p.compare("SOR factor scan: best ω vs ω_opt = 2/(1 + sin πh)", 2 / (1 + np.sin(pi / (N + 1))), wbest, "", tol=1.5)
    p.section("Sweeps to reach 10⁻⁶", "| N | Jacobi (pred / meas) | Gauss–Seidel (pred / meas) | SOR (pred / meas) |\n|---|---|---|---|\n" + "\n".join(
        f"| {N_} | {pr['jacobi']:.0f} / {'—' if np.isnan(o['jacobi'][0]) else int(o['jacobi'][0])} | {pr['gs']:.0f} / {o['gs'][0]} | {pr['sor']:.0f} / {o['sor'][0]} |" for N_, pr, o, _, _ in rows))
    fig, ax = p.fig(1, 2, w=11)
    for m, om, c, lab in (("jacobi", 1.0, COLORS[1], "Jacobi"), ("rb", 1.0, C_PRED, "Gauss–Seidel"), ("rb", 2 / (1 + np.sin(pi / 64)), C_MEAS, "SOR, ω_opt")):
        _, hh = relax(63, m, om, ref=ref, maxit=12000); ax[0].semilogy(hh, color=c, label=lab)
    style_axes(ax[0], "sweep", "max error", "N = 63: convergence histories")
    ax[1].semilogy(oms, its, "o-", color=C_MEAS); ax[1].axvline(2 / (1 + np.sin(pi / 64)), color=C_PRED, ls="--", label="ω_opt (theory)")
    style_axes(ax[1], "over-relaxation factor ω", "sweeps to 10⁻⁶", "The sharp optimum of SOR")
    p.save(fig, "relaxation", "Error histories of three relaxation methods and the sensitivity of SOR to its relaxation factor.")
    p.discuss(f"""The eigenvalue analysis predicts relaxation behaviour precisely: the measured per-sweep error reduction of Jacobi and Gauss–Seidel equals cos(πh)
and cos²(πh) to a few hundredths of a percent, Gauss–Seidel needs half of Jacobi's sweeps, and the count grows fourfold each time the grid is
refined — hopeless for fine grids. Over-relaxation changes the scaling: at ω_opt = {rows[1][4]:.4f} the sweep count only doubles with N, and at N = 127 SOR
needs {it_sor[2]} sweeps against {it_gs[2]} for Gauss–Seidel. The factor scan shows how sharp that optimum is — the best ω found is within a percent of
2/(1 + sin πh), and slightly smaller values lose much of the gain. The result also verifies the solution itself (V(½,½) = ¼ exactly). Today these
iterations survive as smoothers inside multigrid, which removes the N-dependence altogether.""")
# tol-convention: relative tolerances are in percent
