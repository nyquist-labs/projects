from eelab import *
from eelab.data import fsdd
from eelab.info import h2

META = dict(
    id="AM-207", title="Rate–distortion theory against real quantisers", level="H",
    tools="Gaussian and binary rate–distortion functions, Blahut's algorithm for R(D) of a discrete source, own Lloyd–Max quantiser, entropy-coded uniform quantiser, k-means vector quantiser, real speech samples",
    summary="Compare the best achievable trade-off between bits and distortion with what practical quantisers achieve: the 6.02 dB-per-bit rule, the 1.53 dB "
            "'space-filling' gap of scalar quantisation at high rate, how entropy coding and vector quantisation close part of it, and the numbers on real speech.",
    problem="How many bits per sample does a given fidelity really require, and how far from that limit are the quantisers used in practice?",
    theory=r"""Gaussian source, squared error: $D(R)=σ^22^{-2R}$ — SNR = 6.02 R dB. Binary source with Hamming distortion: $R(D)=1-H_2(D)$. The optimal fixed-rate scalar (Lloyd–Max) quantiser of a Gaussian at high rate has $D≈\frac{\sqrt3π}{2}σ^22^{-2R}$ (4.35 dB above the bound); a uniform quantiser followed by ideal
entropy coding reaches $D≈\frac{πe}{6}σ^22^{-2R}$, i.e. 1.53 dB (≈ 0.25 bit) from the limit; vector quantisers in higher dimension recover part of that gap. Blahut's algorithm computes R(D) of any discrete source by alternating minimisation.""",
    method="""Gaussian source: Lloyd–Max for 1–6 bits with exact conditional means (iterated to convergence); 10⁶ Gaussian samples for the others: uniform quantiser with step chosen for entropy-coded rates 1–6 bits (entropy of the output as the rate); 2-D vector quantiser by k-means at 2 bits/sample. Binary source: Blahut R(D) vs 1 − H₂(D). Speech: all FSDD
recordings concatenated and normalised; 8-bit uniform PCM and μ-law, SNR vs the Gaussian bound at the same rate.""",
    data="Free Spoken Digit Dataset (CC BY-SA 4.0).",
)


def lloyd_max(x, levels, iters=200):
    c = np.quantile(x, (np.arange(levels) + 0.5) / levels)
    for _ in range(iters):
        t = (c[1:] + c[:-1]) / 2; idx = np.searchsorted(t, x); c = np.array([x[idx == k].mean() for k in range(levels)])
    t = (c[1:] + c[:-1]) / 2; return c, np.mean((x - c[np.searchsorted(t, x)]) ** 2)


def lloyd_max_gauss(levels, iters=20000, tol=1e-13):
    """Lloyd–Max for a unit Gaussian using exact conditional means (no sampling). Many levels need thousands of iterations."""
    from scipy import stats
    c = stats.norm.ppf((np.arange(levels) + 0.5) / levels)
    for it in range(iters):
        t = np.r_[-np.inf, (c[1:] + c[:-1]) / 2, np.inf]
        cn = (stats.norm.pdf(t[:-1]) - stats.norm.pdf(t[1:])) / (stats.norm.cdf(t[1:]) - stats.norm.cdf(t[:-1]))
        if np.max(np.abs(cn - c)) < tol:
            c = cn; break
        c = cn
    t = np.r_[-np.inf, (c[1:] + c[:-1]) / 2, np.inf]; P = stats.norm.cdf(t[1:]) - stats.norm.cdf(t[:-1])
    m2 = (stats.norm.cdf(t[1:]) - stats.norm.cdf(t[:-1])) - (np.nan_to_num(t[1:] * stats.norm.pdf(t[1:])) - np.nan_to_num(t[:-1] * stats.norm.pdf(t[:-1])))
    return c, float(1 - np.sum(c * c * P)), it + 1            # D = E[x²] − Σ c²P for centroid quantisers


def blahut_rd(px, dist, s):
    q = np.full(dist.shape[1], 1 / dist.shape[1])
    for _ in range(2000):
        A = q[None] * np.exp(-s * dist); Q = A / A.sum(1, keepdims=True); q = px @ Q
    D = np.sum(px[:, None] * Q * dist); R = np.sum(px[:, None] * Q * np.log2(np.where(Q > 0, Q / q[None], 1)))
    return R, D


def run(p):
    r = p.rng; x = r.normal(size=1_000_000); rows = []
    for b in range(1, 7):
        c, D, its = lloyd_max_gauss(2 ** b)
        rows.append((b, 10 * np.log10(1 / D), its))
    rr = np.array(rows)
    p.compare("Lloyd–Max, 1 bit: SNR (optimal 2-level quantiser of a Gaussian: 1 − 2/π distortion → 4.40 dB)", 10 * np.log10(1 / (1 - 2 / pi)), rr[0, 1], "dB", kind="abs", tol=0.02)
    p.compare("Lloyd–Max at 6 bits: gap to the bound 6.02·R dB (high-rate Panter–Dite limit: 4.35 dB, approached from below)", 4.35, 6.02 * 6 - rr[5, 1], "dB", kind="abs", tol=0.2)
    ent = []
    for step in np.logspace(np.log10(2.5), np.log10(0.05), 12):
        q = np.round(x / step); vals, cnt = np.unique(q, return_counts=True); pr = cnt / cnt.sum(); Rn = -np.sum(pr * np.log2(pr))
        ent.append((Rn, 10 * np.log10(1 / np.mean((x - q * step) ** 2))))
    ent = np.array(ent); hi = ent[ent[:, 0] > 4]
    p.metric("Lloyd–Max iterations needed at 1…6 bits", " / ".join(str(int(v)) for v in rr[:, 2]), "", "my first run stopped at 200 iterations and reported a 5.4 dB gap at 6 bits — not yet converged")
    p.compare("Entropy-coded uniform quantiser at high rate: gap to the bound (theory 10·log₁₀(πe/6) = 1.53 dB)", 1.533, float(np.mean(6.02 * hi[:, 0] - hi[:, 1])), "dB", kind="abs", tol=0.1)
    X2 = x[:200000].reshape(-1, 2); from eelab.ml import kmeans
    lab, C, _ = kmeans(X2, 16, r, iters=60); D2 = np.mean(np.sum((X2 - C[lab]) ** 2, 1)) / 2
    c2, D1 = lloyd_max(x[:200000], 4)
    p.compare("2-D vector quantiser (16 cells = 2 bit/sample) beats the 4-level scalar quantiser (1 = yes)", 1, int(D2 < D1), "", kind="abs")
    p.metric("At 2 bit/sample: SNR scalar Lloyd–Max / 2-D VQ / Shannon bound", f"{10 * np.log10(1 / D1):.2f} / {10 * np.log10(1 / D2):.2f} / {6.02 * 2:.2f} dB")
    px = np.array([0.5, 0.5]); dist = np.array([[0, 1.0], [1.0, 0]]); pts = []
    for s_ in np.linspace(0.5, 8, 16):
        pts.append(blahut_rd(px, dist, s_))
    pts = np.array(pts)
    p.compare("Binary source: Blahut R(D) vs 1 − H₂(D) (worst difference over the curve)", 0.0, float(np.max(np.abs(pts[:, 0] - (1 - h2(pts[:, 1]))))), "bit", kind="abs", tol=1e-6)
    sp = np.concatenate([a_ for _, _, _, a_, _ in fsdd()[:600]]).astype(float); sp = sp[np.abs(sp) > 1e-4]; sp /= np.max(np.abs(sp))
    for name, fwd, inv in (("uniform 8-bit PCM", lambda v: v, lambda v: v), ("μ-law 8-bit", lambda v: np.sign(v) * np.log1p(255 * np.abs(v)) / np.log1p(255), lambda v: np.sign(v) * ((1 + 255) ** np.abs(v) - 1) / 255)):
        q = inv(np.round(fwd(sp) * 127) / 127); snr = 10 * np.log10(np.mean(sp ** 2) / np.mean((sp - q) ** 2))
        if name.startswith("uniform"):
            s_u = snr
        else:
            s_m = snr
    pk = np.max(np.abs(sp)); crest = 20 * np.log10(pk / np.std(sp))
    p.compare("Speech, uniform 8-bit PCM: SNR = 6.02·8 + 4.77 − crest factor (dB)", 6.02 * 8 + 4.77 - crest, s_u, "dB", kind="abs", tol=1.5)
    p.compare("μ-law companding gives a higher SNR than uniform 8-bit on real speech (1 = yes)", 1, int(s_m > s_u), "", kind="abs")
    p.metric("Speech at 8 bit/sample: uniform / μ-law SNR vs Gaussian R–D bound 48.2 dB", f"{s_u:.1f} / {s_m:.1f} dB", "", f"crest factor {crest:.1f} dB — speech spends most of its time far below full scale")
    fig, ax = p.fig(1, 2, w=11)
    R_ = np.linspace(0, 6.5, 100)
    ax[0].plot(R_, 6.02 * R_, "k-", label="Shannon bound D(R)"); ax[0].plot(rr[:, 0], rr[:, 1], "o-", color=C_PRED, label="Lloyd–Max (fixed rate)")
    ax[0].plot(ent[:, 0], ent[:, 1], "s-", color=C_MEAS, label="uniform + entropy coding"); ax[0].plot([2], [10 * np.log10(1 / D2)], "^", color=COLORS[2], ms=9, label="2-D VQ")
    style_axes(ax[0], "rate (bits/sample)", "SNR (dB)", "Gaussian source")
    ax[1].plot(pts[:, 1], pts[:, 0], "o", color=C_MEAS, label="Blahut algorithm"); dd = np.linspace(1e-4, 0.5, 200); ax[1].plot(dd, 1 - h2(dd), "--", color=C_PRED, label="1 − H₂(D)")
    style_axes(ax[1], "Hamming distortion D", "rate R (bits)", "Binary symmetric source")
    p.save(fig, "rate_distortion", "Practical quantisers against the Gaussian rate–distortion bound, and R(D) of a binary source.")
    p.discuss(f"""The rate–distortion bound is reachable only in the limit, and the measurements show how far each practical step gets. A fixed-rate optimal
scalar quantiser stays about {6.02 * 6 - rr[5, 1]:.1f} dB below the 6.02-dB-per-bit line at high rate, as the Panter–Dite formula predicts; adding entropy
coding to a plain uniform quantiser closes most of that, leaving {np.mean(6.02 * hi[:, 0] - hi[:, 1]):.2f} dB — the 1.53 dB 'space-filling' loss of cubic cells, i.e. a
quarter of a bit per sample; a two-dimensional vector quantiser already recovers some of that at 2 bits. Blahut's algorithm reproduces the binary
R(D) = 1 − H₂(D) exactly. Real speech is the humbling case: 8-bit uniform PCM delivers only {s_u:.0f} dB because speech has a crest factor of {crest:.0f} dB and
wastes most codes on rare peaks; μ-law companding raises it to {s_m:.0f} dB by spending resolution where the signal usually is.""")
# tol-convention: relative tolerances are in percent
