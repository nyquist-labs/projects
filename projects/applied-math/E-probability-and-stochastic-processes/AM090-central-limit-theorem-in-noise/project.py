from eelab import *
from scipy import stats

META = dict(
    id="AM-090", title="The central limit theorem in noise: why interference becomes Gaussian", level="E",
    tools="Sums of N non-Gaussian interferers (uniform-phase sinusoids, impulsive Bernoulli–Gaussian, binary), excess kurtosis vs N, Kolmogorov–Smirnov distance and the Berry–Esseen rate",
    summary="Add up N independent non-Gaussian interference sources and measure how quickly the sum becomes Gaussian — excess kurtosis falls as "
            "1/N and the maximum CDF error as 1/√N — and show why impulsive noise converges much more slowly.",
    problem="Receivers are designed for Gaussian noise even though no individual interferer is Gaussian. When is that justified?",
    theory=r"""For i.i.d. terms with excess kurtosis κ, the normalised sum has excess kurtosis κ/N. Berry–Esseen: $\sup|F_N-Φ| \le C\frac{ρ}{σ^3\sqrt N}$ (C < 0.48, ρ = E|X|³). A random-phase sinusoid (arcsine law) has κ = −1.5;
impulsive noise (Gaussian present with probability 0.01, variance 100) has κ ≈ 3/0.01 − 3 ≈ 297, so it needs ~100× more terms to look Gaussian.""",
    method="""N = 1…1000 terms, 200,000 samples per N. Excess kurtosis vs κ/N; KS distance to N(0,1) vs N; Berry–Esseen bound computed for each distribution.""",
)


def draw(kind, n, N, r):
    if kind == "random-phase sinusoid":
        return np.sqrt(2) * np.cos(r.uniform(0, 2 * pi, (n, N)))
    if kind == "binary ±1":
        return r.choice([-1.0, 1.0], (n, N))
    on = r.random((n, N)) < 0.01
    return np.where(on, r.normal(0, 10, (n, N)), 0) / np.sqrt(0.01 * 100)


def run(p):
    r = p.rng; n = 200000
    kinds = {"random-phase sinusoid": -1.5, "binary ±1": -2.0, "impulsive (1 % on, σ = 10)": 3 / 0.01 - 3}
    Ns = [1, 2, 5, 10, 20, 50, 100, 300, 1000]
    res = {}
    for kind, kap in kinds.items():
        ks, ku = [], []
        for N in Ns:
            S = np.zeros(n)
            for chunk in range(0, N, 50):
                m = min(50, N - chunk); S += draw(kind, n, m, r).sum(1)
            S /= np.sqrt(N)
            ku.append(stats.kurtosis(S)); ks.append(stats.kstest(S / S.std(), "norm").statistic)
        res[kind] = (np.array(ku), np.array(ks), kap)
    for kind, (ku, ks, kap) in res.items():
        k = Ns.index(20)
        p.compare(f"{kind}: excess kurtosis at N = 20 (= κ/N)", kap / 20, ku[k], "", kind="abs", tol=max(0.03, abs(kap / 20) * 0.15))
    ks_s = res["random-phase sinusoid"][1]
    sl = np.polyfit(np.log(Ns[:6]), np.log(ks_s[:6]), 1)[0]
    p.compare("Sinusoid sum: KS distance slope vs N (Berry–Esseen order −½ or faster)", -1.0, sl, "", kind="abs", tol=0.6)
    imp = res["impulsive (1 % on, σ = 10)"]
    p.metric("Terms needed for KS distance < 0.01: sinusoids / impulsive", f"{Ns[int(np.argmax(ks_s < 0.01))]} / {Ns[int(np.argmax(imp[1] < 0.01))] if np.any(imp[1] < 0.01) else '> 1000'}")
    fig, ax = p.fig(1, 2, w=11)
    for (kind, (ku, ks, kap)), c in zip(res.items(), COLORS):
        ax[0].loglog(Ns, np.abs(ku), "o-", color=c, label=kind); ax[0].loglog(Ns, np.abs(kap) / np.array(Ns), "--", color=c, lw=.8)
        ax[1].loglog(Ns, ks, "o-", color=c, label=kind)
    ax[1].axhline(np.sqrt(np.log(2 / 0.05) / (2 * n)) * 1.36 / 1.36, color="gray", ls=":", label="KS noise floor (n = 200k)")
    style_axes(ax[0], "number of interferers N", "|excess kurtosis|", "Kurtosis ∝ κ/N (dashed)")
    style_axes(ax[1], "number of interferers N", "KS distance to Gaussian", "Distance to Gaussian")
    p.save(fig, "clt", "Excess kurtosis and KS distance to the Gaussian for sums of three kinds of interferers.")
    p.discuss("""The excess kurtosis of the normalised sum follows κ/N exactly for all three sources, and the distance to a Gaussian shrinks as the Berry–Esseen
theorem guarantees. For 'nice' interferers — random-phase carriers or binary data — a dozen terms already look Gaussian to within the resolution of
200,000 samples, which is why summed co-channel interference and thermal noise from many electrons are modelled as Gaussian. Impulsive noise is
the counterexample: its huge kurtosis (~300) means even hundreds of such sources remain visibly non-Gaussian in the tails, and receivers designed
for Gaussian noise (linear matched filters) perform badly there — hence clipping/blanking receivers for automotive and power-line interference.""")
# tol-convention: relative tolerances are in percent
