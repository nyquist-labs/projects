from eelab import *

META = dict(
    id="AM-088", title="Bursty errors: a two-state Markov (Gilbert–Elliott) channel", level="H",
    tools="Two-state Markov chain simulation, stationary distribution, burst-length statistics, block-error rates with and without interleaving, comparison with an i.i.d. channel of equal average BER",
    summary="Model a channel that alternates between good and bad states, predict its average error rate and burst-length distribution from the "
            "transition probabilities, and show that a block code that fixes 2 errors fails far more often on bursty errors — until interleaving spreads them out.",
    problem="Fading and interference produce errors in clumps. Why does the average bit-error rate say so little about how a code will perform?",
    theory=r"""States G/B with P(G→B) = p, P(B→G) = q: stationary π_B = p/(p+q); average BER = π_G e_G + π_B e_B. Sojourn in B is geometric with mean 1/q. For a t-error-correcting block code of length n, block failure = P(>t errors);
on an i.i.d. channel this is a binomial tail, on the bursty channel much larger for the same average BER. Interleaving to depth D ≫ 1/q makes errors within a codeword nearly independent.""",
    method="""p = 0.002, q = 0.1, e_G = 10⁻⁴, e_B = 0.3 (average BER ≈ 0.6 %). 10⁷ simulated bits. Codewords of n = 63 correcting t = 2 errors (BCH-like); block failure rates: bursty, bursty + interleaving (depth 64), i.i.d. with the same BER.""",
)


def run(p):
    r = p.rng
    pGB, pBG, eG, eB = 0.002, 0.1, 1e-4, 0.3
    N = 10 ** 7
    u = r.random(N); state = np.empty(N, bool); s = False
    for k in range(N):
        s = (u[k] < pGB) if not s else (u[k] >= pBG)
        state[k] = s
    err = r.random(N) < np.where(state, eB, eG)
    piB = pGB / (pGB + pBG)
    p.compare("Fraction of time in the bad state = p/(p+q)", piB, state.mean(), "", tol=3)
    p.compare("Average BER = π_G e_G + π_B e_B", (1 - piB) * eG + piB * eB, err.mean(), "", tol=3)
    d = np.diff(np.r_[0, state.astype(int), 0]); starts = np.flatnonzero(d == 1); ends = np.flatnonzero(d == -1)
    lens = ends - starts
    p.compare("Mean bad-state sojourn = 1/q (geometric)", 1 / pBG, lens.mean(), "bits", tol=3)
    n, t = 63, 2
    blocks = err[: N // n * n].reshape(-1, n).sum(1)
    D = 64
    E2 = err[: N // (n * D) * n * D].reshape(-1, n, D).transpose(0, 2, 1).reshape(-1, n).sum(1)
    iid = (r.random((len(blocks), n)) < err.mean()).sum(1)
    from scipy.stats import binom
    pb = err.mean()
    p.compare("i.i.d. channel: block failure P(>2 errors in 63) vs binomial", 1 - binom.cdf(t, n, pb), np.mean(iid > t), "", tol=5)
    p.metric("Block failure: bursty / bursty+interleaved (D = 64) / i.i.d.", f"{np.mean(blocks > t):.3f} / {np.mean(E2 > t):.4f} / {np.mean(iid > t):.4f}")
    p.compare("Interleaving restores near-i.i.d. block performance (ratio interleaved / i.i.d.)", 1.0, np.mean(E2 > t) / np.mean(iid > t), "", tol=30)
    fig, ax = p.fig(1, 2, w=11)
    h = np.bincount(lens)[1:60] / len(lens)
    ax[0].semilogy(np.arange(1, 60), h, "o", ms=3, color=C_MEAS, label="simulated"); ax[0].semilogy(np.arange(1, 60), pBG * (1 - pBG) ** np.arange(0, 59), "--", color=C_PRED, label="geometric q(1−q)^{k−1}")
    style_axes(ax[0], "bad-state duration (bits)", "probability", "Burst lengths")
    kk = np.arange(0, 20)
    for data, lab, c in ((blocks, "bursty", COLORS[1]), (E2, "interleaved", C_MEAS), (iid, "i.i.d.", COLORS[2])):
        ax[1].semilogy(kk, [np.mean(data == k) + 1e-7 for k in kk], "o-", ms=3, color=c, label=lab)
    ax[1].axvline(t + 0.5, color="black", ls=":")
    style_axes(ax[1], "errors per 63-bit codeword", "probability", "Same average BER, very different blocks")
    p.save(fig, "gilbert_elliott", "Burst-length distribution of the two-state channel and the number of errors per codeword with and without interleaving.")
    p.discuss(f"""The chain's statistics follow from its two transition probabilities: {state.mean() * 100:.1f} % of the time in the bad state, bursts of geometric length with mean 10
bits, and an average BER of ~0.6 %. That average hides everything that matters for coding: on the bursty channel a 2-error-correcting 63-bit code
fails on {np.mean(blocks > t) * 100:.1f} % of blocks because errors arrive in clumps, while an i.i.d. channel with the same BER breaks only {np.mean(iid > t) * 100:.2f} %. Interleaving
64 codewords spreads each burst across many codewords and restores almost exactly the i.i.d. behaviour — at the cost of latency, which is the
trade-off every digital broadcast and storage system makes.""")
# tol-convention: relative tolerances are in percent
