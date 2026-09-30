from eelab import *
from eelab.comms import conv_encode_batch, viterbi_batch
from scipy.special import erfc
import networkx as nx

META = dict(
    id="AM-149", title="The Viterbi algorithm as dynamic programming", level="H",
    tools="Batch Viterbi decoder (add–compare–select as a shortest-path recursion), brute-force maximum-likelihood search over all codewords, Dijkstra on the explicit trellis graph (networkx), hard- vs soft-decision simulation, finite traceback-depth experiment on the K = 7 code",
    summary="Show that Viterbi decoding is exactly a shortest-path dynamic programme: it returns the same answer as exhaustive maximum-likelihood "
            "search and as Dijkstra on the trellis, at linear instead of exponential cost; then measure the ≈ 2 dB gain of soft decisions and the '5 × constraint length' traceback rule.",
    problem="Maximum-likelihood decoding means comparing the received signal with every possible message. How does Viterbi do that without the exponential cost?",
    theory=r"""The path metric is additive over trellis stages, so Bellman's principle applies: the best path into a state extends a best path into one of its predecessors. Keeping one survivor per state gives the ML path with $N\cdot2^{K-1}$ add–compare–select steps
instead of $2^N$ comparisons. Soft decisions (correlation metric) gain ≈ 2 dB over hard decisions (Hamming metric) on AWGN. Survivors merge after a few constraint lengths, so decisions can be released after a traceback of ≈ 5K stages with negligible loss.""",
    method="""(7,5) K = 3 code, 10 information bits + tail: all 1024 codewords scored by correlation for 400 noisy blocks at 0 dB — metric of the Viterbi output vs the true maximum. One block as an explicit graph (nodes = (time, state), edge weight = Hamming distance):
Dijkstra vs Viterbi. BER curves hard/soft, 2×10⁶ bits per point. K = 7 (171,133): BER vs traceback depth 5…70 at 3 dB.""",
)

G3 = (0o7, 0o5)


def Q(x):
    return 0.5 * erfc(x / np.sqrt(2))


def ber(gens, K, ebn0, nbits, rng, hard=False, blk=1000):
    sig = np.sqrt(1 / (2 * 0.5 * 10 ** (ebn0 / 10))); err = 0; tot = 0
    while tot < nbits:
        B = min(2000, (nbits - tot) // blk)
        u = rng.integers(0, 2, (B, blk), dtype=np.int8)
        y = 1 - 2.0 * conv_encode_batch(u, gens, K) + sig * rng.standard_normal((B, blk + K - 1, 2))
        if hard:
            y = np.sign(y)
        err += int(np.sum(viterbi_batch(y, gens, K)[:, :blk] != u)); tot += u.size
    return err / tot


def run(p):
    r = p.rng; nb = 10
    allmsg = np.array([[(m >> i) & 1 for i in range(nb)] for m in range(2 ** nb)], np.int8)
    allcw = 1 - 2.0 * conv_encode_batch(allmsg, G3, 3).reshape(2 ** nb, -1)
    u = r.integers(0, 2, (400, nb), dtype=np.int8)
    tx = 1 - 2.0 * conv_encode_batch(u, G3, 3)
    y = tx + 1.0 * r.standard_normal(tx.shape)                       # Eb/N0 = 0 dB: many decoding errors, a hard test
    dec = viterbi_batch(y, G3, 3)[:, :nb]
    yf = y.reshape(400, -1)
    corr = yf @ allcw.T
    best = corr.max(1)
    got = np.einsum("ij,ij->i", yf, 1 - 2.0 * conv_encode_batch(dec, G3, 3).reshape(400, -1))
    p.compare("Viterbi path metric vs exhaustive ML maximum over 1024 codewords (max difference, 400 blocks)", 0.0, float(np.max(np.abs(best - got))), "", kind="abs", tol=1e-4)
    p.compare("Blocks where Viterbi and brute-force ML choose different messages", 0, int(np.sum(np.any(allmsg[corr.argmax(1)] != dec, axis=1))), "", kind="abs")
    p.metric("Blocks decoded wrongly at 0 dB (by both — ML is optimal, not infallible)", int(np.sum(np.any(dec != u, axis=1))), "of 400")
    # explicit trellis graph, hard decisions
    hard = (y[0] < 0).astype(int); T = hard.shape[0]; Gr = nx.DiGraph()
    for t in range(T):
        for s in range(4):
            for b in ((0, 1) if t < nb else (0,)):
                full = (s << 1) | b
                o = [bin(full & g).count("1") & 1 for g in G3]
                Gr.add_edge((t, s), (t + 1, full & 3), weight=int(o[0] != hard[t, 0]) + int(o[1] != hard[t, 1]), bit=b)
    dj = nx.dijkstra_path(Gr, (0, 0), (T, 0)); cost = nx.path_weight(Gr, dj, "weight")
    vit = viterbi_batch((1 - 2.0 * hard)[None], G3, 3)[0]
    vcost = int(np.sum(conv_encode_batch(vit[None, :nb], G3, 3)[0] != hard))
    p.compare("Hamming cost of the Viterbi path vs Dijkstra's shortest path on the trellis graph", cost, vcost, "", kind="abs")
    p.metric("Work: add–compare–selects (N·2^(K−1)·2) vs codewords to compare (2^N), N = 1000, K = 3", f"{1000 * 4 * 2} vs 2^1000")
    es = np.arange(2.0, 8.1, 1.0); soft = []; hrd = []
    for e in es:
        nbits = 400_000 if e < 5 else 2_000_000 if e < 7 else 6_000_000
        soft.append(ber(G3, 3, e, nbits, r)); hrd.append(ber(G3, 3, e, nbits, r, hard=True))
    soft = np.array(soft); hrd = np.array(hrd)
    ok_s = soft > 0; ok_h = hrd > 0
    at = lambda b, x, m: np.interp(np.log10(1e-4), np.log10(b[m])[::-1], x[m][::-1])
    gain = at(hrd, es, ok_h) - at(soft, es, ok_s)
    p.compare("Soft-decision gain over hard decisions at BER 10⁻⁴", 2.0, gain, "dB", kind="abs", tol=0.4)
    G7 = (0o171, 0o133); B, blk = 200, 2000; ebn0 = 3.0; sig = np.sqrt(1 / 10 ** (ebn0 / 10))
    u7 = r.integers(0, 2, (B, blk), dtype=np.int8)
    y7 = 1 - 2.0 * conv_encode_batch(u7, G7, 7) + sig * r.standard_normal((B, blk + 6, 2))
    full, decs, beststate, _ = viterbi_batch(y7, G7, 7, return_all=True)
    ber_full = np.mean(full[:, :blk] != u7)
    depths = [5, 10, 15, 20, 28, 35, 50, 70]; bd = []
    bi = np.arange(B)[:, None]
    for D in depths:
        tt = np.arange(0, blk - 70)                                 # decide bit t from the best state at time t + D
        st = beststate[tt + D].T.copy()                             # (B, len)
        for k in range(D):
            st = (st | (decs[tt + D - k, bi, st].astype(int) << 6)) >> 1
        bd.append(np.mean((st & 1) != u7[:, tt]))
    bd = np.array(bd)
    p.compare("K = 7: BER with traceback depth 5K = 35 relative to full-block traceback", 1.0, bd[depths.index(35)] / ber_full, "×", tol=25)
    p.compare("K = 7: traceback depth K = 7 is far too short (BER ratio to full > 10; 1 = yes)", 1, int(bd[depths.index(5)] / ber_full > 10), "", kind="abs")
    p.metric("K = 7 at 3 dB: BER at depth 5 / 15 / 35 / full", f"{bd[0]:.1e} / {bd[2]:.1e} / {bd[5]:.1e} / {ber_full:.1e}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(es[ok_s], soft[ok_s], "o-", color=C_MEAS, label="soft decisions"); ax[0].semilogy(es[ok_h], hrd[ok_h], "s-", color=C_PRED, label="hard decisions")
    ax[0].semilogy(es, Q(np.sqrt(2 * 10 ** (es / 10))), ":", color="gray", label="uncoded BPSK")
    style_axes(ax[0], "Eb/N0 (dB)", "bit error rate", "(7,5) code: soft vs hard metrics")
    ax[1].semilogy(depths, bd, "o-", color=C_MEAS, label="finite traceback"); ax[1].axhline(ber_full, color=C_PRED, ls="--", label="full block"); ax[1].axvline(35, color="gray", ls=":", label="5K")
    style_axes(ax[1], "traceback depth (stages)", "bit error rate", "K = 7 at 3 dB: survivors merge")
    p.save(fig, "viterbi", "Soft- versus hard-decision BER of the (7,5) code and the effect of traceback depth for the K = 7 code.")
    p.discuss(f"""On 400 heavily corrupted blocks the Viterbi decoder returned a codeword with exactly the maximum correlation found by scoring all 1024
candidates, and on the explicit trellis graph its path cost equals Dijkstra's shortest path — it *is* dynamic programming on a layered graph, with
the state as the 'everything that matters about the past'. The cost is linear in message length: 8000 add–compare–selects for a 1000-bit block
instead of 2¹⁰⁰⁰ comparisons. Feeding the decoder unquantised channel values instead of hard bits is worth {gain:.1f} dB at BER 10⁻⁴, essentially
for free. And survivors really do merge: with the K = 7 code a traceback of 35 stages gives the same BER as waiting for the whole block
({bd[depths.index(35)]:.1e} vs {ber_full:.1e}), while 5 stages is catastrophic — the practical basis of the '5K' rule used in hardware decoders.""")
# tol-convention: relative tolerances are in percent
