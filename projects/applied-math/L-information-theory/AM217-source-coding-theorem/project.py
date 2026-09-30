from eelab import *
from eelab.data import alice_text
from eelab.info import h2
from scipy.special import gammaln
from collections import Counter

META = dict(
    id="AM-217", title="The source coding theorem, demonstrated", level="M",
    tools="Exact binomial computations in the log domain for i.i.d. binary sequences up to n = 5000, the typical set and its size, asymptotic equipartition checked by simulation, error of optimal fixed-length block codes above and below the entropy, the same phenomenon on real English text",
    summary="Show why the entropy is the compression limit: long sequences concentrate on a 'typical set' of about 2^{nH} equally likely members, so "
            "fixed-length codes at any rate above H succeed with probability → 1 and at any rate below H fail with probability → 1. Everything is computed exactly for binary sources and checked on English.",
    problem="Why is H the number of bits per symbol needed — no more, no less — for long sequences?",
    theory=r"""For i.i.d. $X_i$ with entropy H, $-\tfrac1n\log_2p(X^n)\to H$ (AEP), with standard deviation $σ/\sqrt n$, $σ^2=\mathrm{Var}[-\log_2p(X)]$. The ε-typical set has probability → 1 and size between $(1-ε)2^{n(H-ε)}$ and $2^{n(H+ε)}$ — a vanishing fraction of all $2^n$ sequences when H < 1. A fixed-length code of rate R that lists the
$2^{nR}$ most probable sequences fails with probability → 0 if R > H and → 1 if R < H (strong converse).""",
    method="""Bernoulli(0.2) source (H = 0.722 bit). Exact: sequences sorted by probability are grouped by their number of ones; failure probability of the best code of rate R is 1 − P(the 2^{nR} most probable sequences), computed with log-binomials for n = 10…5000 and R = 0.6, 0.7, 0.75, 0.85. AEP by simulation
(20 000 sequences per n). English: letters of 'Alice' under the order-0 model, blocks of n letters.""",
    data="Project Gutenberg eBook #11 (public domain).",
)


def logC(n, k):
    return (gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)) / np.log(2)


def fail_prob(n, R, q=0.2):
    k = np.arange(n + 1); lc = logC(n, k); lp = k * np.log2(q) + (n - k) * np.log2(1 - q)            # per-sequence log-prob with k ones
    order = np.argsort(-lp); budget = n * R; cum_cnt = -np.inf; prob = 0.0
    for kk in order:                                                                                 # take whole weight classes while the count budget allows
        new = np.logaddexp2(cum_cnt, lc[kk])
        if new <= budget:
            cum_cnt = new; prob += 2.0 ** (lc[kk] + lp[kk])
        else:
            frac = 2.0 ** (budget - lc[kk]) - 2.0 ** (cum_cnt - lc[kk]) if np.isfinite(cum_cnt) else 2.0 ** (budget - lc[kk])
            prob += max(frac, 0) * 2.0 ** (lc[kk] + lp[kk]); break
    return 1 - min(prob, 1.0)


def run(p):
    q = 0.2; Hs = h2(q); r = p.rng
    ns = [10, 50, 100, 500, 1000, 5000]; sd = []
    s_th = np.sqrt(q * (1 - q)) * abs(np.log2((1 - q) / q))
    for n in ns:
        k = r.binomial(n, q, 20000); v = -(k * np.log2(q) + (n - k) * np.log2(1 - q)) / n; sd.append(v.std())
    p.compare("AEP: std of −(1/n)log₂p(Xⁿ) at n = 1000 vs σ/√n", s_th / np.sqrt(1000), sd[4], "bit", tol=4)
    p.compare("… and its mean → H = 0.722 bit", Hs, float(v.mean()), "bit", tol=0.2)
    eps = 0.05; rows = []
    for n in ns:
        k = np.arange(n + 1); lp = k * np.log2(q) + (n - k) * np.log2(1 - q); typ = np.abs(-lp / n - Hs) <= eps
        P = np.sum(2.0 ** (logC(n, k[typ]) + lp[typ])); size = np.log2(np.sum(2.0 ** (logC(n, k[typ]) - logC(n, k[typ]).max()))) + logC(n, k[typ]).max()
        rows.append((n, P, size / n))
    rr = np.array(rows)
    p.compare("Typical set (ε = 0.05) captures almost all probability at n = 5000", 1.0, rr[-1, 1], "", tol=0.5)
    p.compare("… while its size is 2^{n·(H ± ε)}: log₂(size)/n at n = 5000", Hs, rr[-1, 2], "bit", kind="abs", tol=eps)
    p.metric("Typical-set probability for n = 10 / 100 / 1000 / 5000", " / ".join(f"{v:.3f}" for v in rr[[0, 2, 4, 5], 1]), "", "small n: the 'typical' sequences are not yet most of the probability")
    fails = {R: [fail_prob(n, R) for n in ns] for R in (0.6, 0.7, 0.75, 0.85)}
    p.compare("Rate 0.85 > H: failure probability of the best fixed-length code at n = 5000 → 0", 0.0, fails[0.85][-1], "", kind="abs", tol=1e-6)
    p.compare("Rate 0.6 < H: failure probability at n = 5000 → 1 (strong converse)", 1.0, fails[0.6][-1], "", tol=0.01)
    p.metric("Failure probability at rate 0.75 (just above H = 0.722): n = 100 / 1000 / 5000", " / ".join(f"{fails[0.75][ns.index(n)]:.3f}" for n in (100, 1000, 5000)), "", "convergence is slow near the entropy")
    text = alice_text().lower(); cnt = Counter(text); tot = sum(cnt.values()); pr = {c: v / tot for c, v in cnt.items()}; Ht = -sum(v * np.log2(v) for v in pr.values())
    lpt = np.array([-np.log2(pr[c]) for c in text]); outs = []
    for n in (10, 100, 1000):
        blocks = lpt[: len(lpt) // n * n].reshape(-1, n).mean(1); outs.append((n, blocks.mean(), blocks.std()))
    p.compare("English letters (order-0 model): per-letter −log₂p of 1000-letter blocks concentrates on H", Ht, outs[-1][1], "bit", tol=0.5)
    p.metric("Spread of block log-probabilities per letter, n = 10 / 100 / 1000 letters", " / ".join(f"{s_:.3f}" for _, _, s_ in outs), "bit", "falls roughly as 1/√n — dependence between letters slows it a little")
    fig, ax = p.fig(1, 2, w=11)
    for R, c in zip((0.6, 0.7, 0.75, 0.85), (COLORS[1], COLORS[3], C_MEAS, C_PRED)):
        ax[0].semilogx(ns, fails[R], "o-", color=c, label=f"R = {R}")
    style_axes(ax[0], "block length n", "failure probability", f"Best fixed-length code, H = {Hs:.3f}")
    ax[1].loglog(ns, sd, "o", color=C_MEAS, label="simulated"); ax[1].loglog(ns, s_th / np.sqrt(ns), "--", color=C_PRED, label="σ/√n")
    style_axes(ax[1], "n", "std of −(1/n)log₂p", "Asymptotic equipartition")
    p.save(fig, "source_coding", "Failure probability of optimal fixed-length codes versus block length for four rates, and the concentration of per-symbol log-probability.")
    p.discuss(f"""The theorem appears in the numbers as a sharpening threshold. For a Bernoulli(0.2) source with H = {Hs:.3f} bit, the best fixed-length code of rate 0.85
fails with probability {fails[0.85][-1]:.0e} at n = 5000, while a code of rate 0.6 fails with probability {fails[0.6][-1]:.4f} — above the entropy every reasonable rate
works for long enough blocks, below it none does. The reason is the typical set: −(1/n)log₂p concentrates on H with a spread falling as 1/√n exactly as
predicted, so almost all probability sits on about 2^{{nH}} sequences, a vanishing fraction of the 2ⁿ possible ones. Near the entropy convergence is slow
(rate 0.75 still fails {fails[0.75][ns.index(1000)] * 100:.1f} % of the time at n = 1000 and {fails[0.75][-1] * 100:.1f} % at n = 5000), which is why practical compressors use variable-length codes instead of waiting for
the asymptotics. English text shows the same concentration.""")
# tol-convention: relative tolerances are in percent
