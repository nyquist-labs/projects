from eelab import *
from scipy.special import erfc
import networkx as nx

META = dict(
    id="AM-150", title="LDPC codes: decoding by passing messages on a bipartite graph", level="H",
    tools="Random regular (3,6) Tanner-graph construction with 4-cycle removal, girth by breadth-first search (checked with networkx), GF(2) Gaussian elimination for an encoder, vectorised sum-product (belief-propagation) decoder, density evolution by population dynamics, Monte-Carlo BER",
    summary="Build a rate-½ LDPC code as a sparse bipartite graph, decode it by iterative message passing, predict its noise threshold with density "
            "evolution, and compare the simulated waterfall of a 2000-bit code with that threshold and with the Shannon limit.",
    problem="How can a code defined by a random sparse graph get within a decibel of the Shannon limit — with a decoder that only passes local messages?",
    theory=r"""Tanner graph: variable nodes (bits) and check nodes (parity equations). Sum-product: variable→check message = channel LLR + other incoming checks; check→variable: $2\tanh^{-1}\prod\tanh(m/2)$ over the other edges. On a cycle-free graph this is exact
bit-wise MAP; short cycles (girth 4) hurt. Density evolution tracks the message distribution for infinite length: the regular (3,6) ensemble has a BI-AWGN threshold of **1.11 dB** (Richardson–Urbanke), against the rate-½ Shannon limit of 0.19 dB. A finite code's
waterfall sits a few tenths of a dB above the threshold and sharpens with length.""",
    method="""n = 2000, m = 1000, column weight 3, row weight 6: random socket permutation, then edge swaps until no double edges or 4-cycles remain. Encoder from Gaussian elimination (H·c = 0 verified). BP: up to 60 iterations, 200 blocks per Eb/N0 (all-zero
codeword by symmetry, plus random codewords at one point as a check). Density evolution: 50 000 sampled messages, 400 iterations, bisection on Eb/N0.""",
)


def build(n, dv, dc, rng):
    m = n * dv // dc
    for attempt in range(20):
        vs = rng.permutation(np.repeat(np.arange(n), dv)); cs = np.repeat(np.arange(m), dc)
        for it in range(4000):
            Hm = np.zeros((m, n), np.int16); np.add.at(Hm, (cs, vs), 1)
            dup = np.argwhere(Hm > 1)
            ov = Hm > 0; of = ov.astype(np.float32); S = of @ of.T; np.fill_diagonal(S, 0)       # float32 → BLAS
            bad = np.argwhere(np.triu(S) > 1)
            if len(dup) == 0 and len(bad) == 0:
                return (Hm > 0).astype(np.uint8), vs, cs
            e = []
            for c, v in dup[:50]:
                e.append(int(np.flatnonzero((cs == c) & (vs == v))[0]))
            for c1, c2 in bad[:50]:
                common = np.flatnonzero(ov[c1] & ov[c2])
                e.append(int(np.flatnonzero((cs == c1) & (vs == common[0]))[0]))
            for i in e:                                            # swap the offending edge's variable with a random other edge
                j = int(rng.integers(len(vs))); vs[i], vs[j] = vs[j], vs[i]
    raise RuntimeError("construction failed")


def girth(H):
    m, n = H.shape
    adj = [list(np.flatnonzero(H[:, v]) + n) for v in range(n)] + [list(np.flatnonzero(H[c])) for c in range(m)]
    best = 99
    for root in range(0, n, 7):
        dist = {root: 0}; par = {root: -1}; q = [root]
        while q:
            nq = []
            for x in q:
                for y in adj[x]:
                    if y not in dist:
                        dist[y] = dist[x] + 1; par[y] = x; nq.append(y)
                    elif par[x] != y:
                        best = min(best, dist[x] + dist[y] + 1)
            if nq and dist[nq[0]] * 2 > best:
                break
            q = nq
    return best


def encoder(H):
    m, n = H.shape; A = H.copy(); piv = []; row = 0
    for col in range(n - 1, -1, -1):                              # pivots from the right: parity bits at the end where possible
        if row == m:
            break
        r_ = np.flatnonzero(A[row:, col])
        if len(r_) == 0:
            continue
        r0 = row + r_[0]
        if r0 != row:
            A[[row, r0]] = A[[r0, row]]
        others = np.flatnonzero(A[:, col]); others = others[others != row]
        A[others] ^= A[row]
        piv.append(col); row += 1
    rank = row; free = np.array([c for c in range(n) if c not in set(piv)])

    def enc(u):
        c = np.zeros((u.shape[0], n), np.uint8); c[:, free] = u
        par = (u @ A[:rank][:, free].T) % 2
        c[:, piv] = par
        return c
    return enc, len(free), rank


def bp(llr, vs, cs, order, dv, dc, iters=60):
    B = llr.shape[0]; n = llr.shape[1]; E = len(vs); m = E // dc
    v2c = llr[:, vs].copy(); hard = llr < 0
    H_syn = None
    for it in range(iters):
        t = np.tanh(np.clip(v2c, -30, 30) / 2).reshape(B, m, dc)
        pre = np.ones_like(t); suf = np.ones_like(t)
        for k in range(1, dc):
            pre[:, :, k] = pre[:, :, k - 1] * t[:, :, k - 1]; suf[:, :, dc - 1 - k] = suf[:, :, dc - k] * t[:, :, dc - k]
        c2v = 2 * np.arctanh(np.clip(pre * suf, -1 + 1e-12, 1 - 1e-12)).reshape(B, E)
        cs_ = c2v[:, order].reshape(B, n, dv)
        tot = llr + cs_.sum(2)
        v2c[:, order] = (tot[:, :, None] - cs_).reshape(B, E)
        hard = tot < 0
        synd = hard[:, vs].reshape(B, m, dc).sum(2) % 2
        if not synd.any():
            break
    return hard, it + 1


def density_evolution(ebn0, rate=0.5, dv=3, dc=6, P=50000, iters=400, rng=None):
    s2 = 1 / (2 * rate * 10 ** (ebn0 / 10)); mu = 2 / s2
    ch = lambda: mu + np.sqrt(2 * mu) * rng.standard_normal(P)
    v = ch()
    for _ in range(iters):
        t = np.ones(P)
        for _ in range(dc - 1):
            t *= np.tanh(np.clip(v[rng.integers(0, P, P)], -30, 30) / 2)
        c = 2 * np.arctanh(np.clip(t, -1 + 1e-12, 1 - 1e-12))
        v = ch() + sum(c[rng.integers(0, P, P)] for _ in range(dv - 1))
        if np.mean(v < 0) == 0 and np.mean(v) > 25:
            return 0.0
    return float(np.mean(v < 0))


def run(p):
    r = p.rng; n, dv, dc = 2000, 3, 6
    H, vs, cs = build(n, dv, dc, r)
    order = np.argsort(vs, kind="stable")
    p.compare("Column weight / row weight of H (regular: 3 and 6; number of violations)", 0, int(np.sum(H.sum(0) != 3) + np.sum(H.sum(1) != 6)), "", kind="abs")
    g = girth(H)
    p.compare("Girth of the Tanner graph after removing 4-cycles", 6, g, "", kind="abs")
    Gx = nx.Graph(); Gx.add_edges_from((int(v), int(n + c)) for v, c in zip(vs, cs))
    p.compare("… confirmed by networkx.girth", g, nx.girth(Gx), "", kind="abs")
    enc, k, rank = encoder(H)
    u = r.integers(0, 2, (50, k), dtype=np.uint8); c = enc(u)
    p.compare("Encoder: H·cᵀ = 0 for 50 random codewords (non-zero syndromes)", 0, int(((c.astype(int) @ H.T.astype(int)) % 2).sum()), "", kind="abs")
    p.metric("Rank of H / code dimension k", f"{rank} / {k}", "", f"rate {k / n:.4f} (H has {1000 - rank} redundant rows)")
    lo, hi = 0.6, 1.8
    for _ in range(7):
        mid = (lo + hi) / 2
        (lo, hi) = (lo, mid) if density_evolution(mid, rng=r) == 0.0 else (mid, hi)
    thr = (lo + hi) / 2
    p.compare("Density-evolution threshold of the (3,6) ensemble (literature: 1.11 dB)", 1.11, thr, "dB", kind="abs", tol=0.12)
    es = np.array([1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]); bers = []; fers = []; its = []
    for e in es:
        s2 = 1 / (2 * 0.5 * 10 ** (e / 10)); nblk = 200 if e < 2 else 400
        y = 1 + np.sqrt(s2) * r.standard_normal((nblk, n))
        hard, it = bp(2 * y / s2, vs, cs, order, dv, dc)
        bers.append(hard.mean()); fers.append(np.mean(hard.any(1))); its.append(it)
    bers = np.array(bers); fers = np.array(fers)
    e_w = float(np.interp(-3, np.log10(np.maximum(bers, 1e-7))[::-1], es[::-1]))
    p.compare("Waterfall (BER = 10⁻³) of the n = 2000 code vs the infinite-length threshold (finite-length gap < 0.7 dB)", 1.11, e_w, "dB", kind="abs", tol=0.7)
    p.metric("Gap to the rate-½ BI-AWGN Shannon limit (0.19 dB) at BER 10⁻³", e_w - 0.187, "dB")
    s2 = 1 / 10 ** 0.2; cw = enc(r.integers(0, 2, (100, k), dtype=np.uint8))
    y = (1 - 2.0 * cw) + np.sqrt(s2) * r.standard_normal(cw.shape)
    hard, _ = bp(2 * y / s2, vs, cs, order, dv, dc)
    p.compare("Random (non-zero) codewords at 2 dB: blocks decoded correctly", 100, int(np.sum(~np.any(hard != cw.astype(bool), axis=1))), "of 100", kind="abs", tol=3)
    p.metric("Uncoded BPSK BER at 2 dB (for scale)", 0.5 * erfc(np.sqrt(10 ** 0.2)))
    p.metric("BER / FER at 1.5 dB and 2.0 dB", f"{bers[2]:.1e} / {fers[2]:.2f}   and   {bers[4]:.1e} / {fers[4]:.3f}")
    p.csv("ber", ebn0_db=es, ber=bers, fer=fers)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].spy(H[:60, :120], markersize=2, color=C_MEAS); ax[0].set_title("Corner of H (3 ones per column, 6 per row)", loc="left", fontsize=10); ax[0].grid(False)
    ok = bers > 0
    ax[1].semilogy(es[ok], bers[ok], "o-", color=C_MEAS, label="LDPC (3,6), n = 2000, BP")
    ax[1].semilogy(es, 0.5 * erfc(np.sqrt(10 ** (es / 10))), ":", color="gray", label="uncoded BPSK")
    ax[1].axvline(thr, color=C_PRED, ls="--", label=f"density evolution {thr:.2f} dB"); ax[1].axvline(0.187, color=COLORS[2], ls="-.", label="Shannon limit 0.19 dB")
    ax[1].set_ylim(1e-6, 0.3)
    style_axes(ax[1], "Eb/N0 (dB)", "bit error rate", "Waterfall")
    p.save(fig, "ldpc", "Part of the sparse parity-check matrix and the simulated BER with the density-evolution threshold and Shannon limit.")
    p.discuss(f"""A code that is nothing but a random sparse bipartite graph, decoded by nodes exchanging local beliefs, shows a cliff: the bit error rate of the
2000-bit code collapses between 1.25 and 2 dB (BER 10⁻³ at {e_w:.2f} dB), {e_w - 0.187:.1f} dB from the Shannon limit, where uncoded BPSK still has
an error rate of 4 %. Density evolution run on sampled message populations puts the infinite-length threshold of the (3,6) ensemble at
{thr:.2f} dB (literature 1.11 dB); the finite code's waterfall is a few tenths of a dB above it, as expected from finite-length scaling. The
construction removed all 4-cycles (girth {g}), which matters because message passing assumes incoming messages are independent — exactly true only
on a tree. Irregular degree distributions optimised by density evolution close most of the remaining gap to capacity; that, plus linear-time
decoding, is why LDPC codes are in Wi-Fi, DVB-S2 and 5G.""")
# tol-convention: relative tolerances are in percent
