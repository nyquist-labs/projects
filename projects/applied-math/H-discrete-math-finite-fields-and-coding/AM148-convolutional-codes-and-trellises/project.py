from eelab import *
from eelab.comms import conv_encode_batch, viterbi_batch
from scipy.special import erfc
from math import gcd

META = dict(
    id="AM-148", title="Convolutional codes: state diagrams, trellises and distance spectra", level="H",
    tools="Trellis enumeration of error events (distance spectrum) by dynamic programming over (state, weight), transfer-function closed form for the (7,5) code, catastrophic-code test via polynomial GCD, batch Viterbi simulation against the union bound",
    summary="Compute the free distance and distance spectrum of convolutional codes directly from their trellis, check the K = 3 result against the "
            "transfer function T(D) = D⁵/(1 − 2D) and the K = 7 NASA code against published values, demonstrate a catastrophic code, and compare simulated BER with the union bound.",
    problem="A convolutional code has no block length and no codeword list. What determines how well it corrects errors?",
    theory=r"""The encoder is a finite-state machine; codewords are paths in its trellis. Performance is governed by paths that leave the all-zero path and re-merge: for the (7,5)₈ K = 3 code, signal-flow-graph reduction gives $T(D)=D^5/(1-2D)$ ⇒ $d_{free}=5$,
$a_d=2^{d-5}$ paths and $c_d=(d-4)2^{d-5}$ information-bit errors at distance d. The K = 7 (171,133)₈ code has $d_{free}=10$, $a_{10}=11$, $a_{12}=38$, $c_{10}=36$, $c_{12}=211$. Soft-decision bound: $P_b\le\sum_d c_d\,Q(\sqrt{2dR\,E_b/N_0})$.
A code is catastrophic iff gcd(g₁, g₂) ≠ 1: some infinite-weight input produces finite-weight output.""",
    method="""Spectrum: propagate a table {(state, output weight, input weight): count} from the first diverging branch until paths re-merge, keeping weights ≤ d_max. Simulation: BPSK/AWGN, terminated 1000-bit blocks, soft Viterbi, 4×10⁶ bits at 5 dB
and 2×10⁷ at 6 dB. Catastrophic example (6,5)₈: g₁ = 1+D, g₂ = 1+D² share the factor 1+D.""",
)


def spectrum(gens, K, dmax):
    S = 1 << (K - 1)
    step = {}
    for s in range(S):
        for b in (0, 1):
            full = (s << 1) | b
            step[(s, b)] = (full & (S - 1), sum(bin(full & g).count("1") & 1 for g in gens))
    ns, w = step[(0, 1)]
    cur = {(ns, w, 1): 1}; a = {}; c = {}
    while cur:
        nxt = {}
        for (s, w, iw), cnt in cur.items():
            for b in (0, 1):
                s2, dw = step[(s, b)]
                w2 = w + dw
                if w2 > dmax:
                    continue
                if s2 == 0:
                    a[w2] = a.get(w2, 0) + cnt; c[w2] = c.get(w2, 0) + cnt * (iw + b)
                else:
                    key = (s2, w2, iw + b); nxt[key] = nxt.get(key, 0) + cnt
        cur = nxt
    return a, c


def gf2_gcd(a, b):
    while b:
        while a.bit_length() >= b.bit_length() and a:
            a ^= b << (a.bit_length() - b.bit_length())
        a, b = b, a
    return a


def Q(x):
    return 0.5 * erfc(x / np.sqrt(2))


def run(p):
    a, c = spectrum((0o7, 0o5), 3, 14)
    p.compare("(7,5) K = 3: free distance", 5, min(a), "", kind="abs")
    p.compare("(7,5): path counts a_d = 2^(d−5) for d = 5…14 (mismatches)", 0, sum(a[d] != 2 ** (d - 5) for d in range(5, 15)), "", kind="abs")
    p.compare("(7,5): bit weights c_d = (d−4)·2^(d−5) for d = 5…14 (mismatches)", 0, sum(c[d] != (d - 4) * 2 ** (d - 5) for d in range(5, 15)), "", kind="abs")
    a7, c7 = spectrum((0o171, 0o133), 7, 14)
    p.compare("(171,133) K = 7: free distance", 10, min(a7), "", kind="abs")
    p.compare("(171,133): a₁₀", 11, a7[10], "", kind="abs")
    p.compare("(171,133): a₁₂", 38, a7[12], "", kind="abs")
    p.compare("(171,133): c₁₀", 36, c7[10], "", kind="abs")
    p.compare("(171,133): c₁₂", 211, c7[12], "", kind="abs")
    p.compare("(171,133): no odd-weight error events (a₁₁ + a₁₃)", 0, a7.get(11, 0) + a7.get(13, 0), "", kind="abs")
    p.compare("gcd(g₁, g₂) for (7,5): 1 ⇒ non-catastrophic", 1, gf2_gcd(0o7, 0o5), "", kind="abs")
    p.compare("gcd(g₁, g₂) for (6,5): 1 + D = 0b11 ⇒ catastrophic", 0b11, gf2_gcd(0o6, 0o5), "", kind="abs")
    ones = np.ones((1, 2000), np.int8)
    wc = int(conv_encode_batch(ones, (0o6, 0o5), 3, terminate=False).sum()); wg = int(conv_encode_batch(ones, (0o7, 0o5), 3, terminate=False).sum())
    p.metric("All-ones input (weight 2000): output weight, catastrophic (6,5) vs good (7,5)", f"{wc} vs {wg}", "", "a handful of channel errors can therefore cause unbounded decoded errors")
    r = p.rng; R = 0.5; sims = {}
    for ebn0, nblk in ((3.0, 1000), (4.0, 2000), (5.0, 4000), (6.0, 20000)):
        err = 0; tot = 0; sig = np.sqrt(1 / (2 * R * 10 ** (ebn0 / 10)))
        for ch in range(0, nblk, 2000):
            B = min(2000, nblk - ch)
            u = r.integers(0, 2, (B, 1000), dtype=np.int8)
            x = 1 - 2.0 * conv_encode_batch(u, (0o7, 0o5), 3)
            y = x + sig * r.standard_normal(x.shape)
            d = viterbi_batch(y, (0o7, 0o5), 3)[:, :1000]
            err += int(np.sum(d != u)); tot += u.size
        sims[ebn0] = (err / tot, err)
    bound = lambda e: sum(c[d] * Q(np.sqrt(2 * d * R * 10 ** (e / 10))) for d in c)
    p.compare(f"(7,5) soft Viterbi BER at 5 dB vs union bound ({sims[5.0][1]} errors)", bound(5.0), sims[5.0][0], "", tol=35)
    p.compare(f"(7,5) soft Viterbi BER at 6 dB vs union bound ({sims[6.0][1]} errors)", bound(6.0), sims[6.0][0], "", tol=35)
    p.metric("BER at 3 dB: simulated vs union bound (bound is loose at low SNR)", f"{sims[3.0][0]:.2e} vs {bound(3.0):.2e}")
    e = np.linspace(2, 8, 50)
    fig, ax = p.fig(1, 2, w=11)
    ds = sorted(a7)
    ax[0].semilogy(sorted(a), [a[d] for d in sorted(a)], "o-", color=C_MEAS, label="(7,5), K = 3"); ax[0].semilogy(ds, [a7[d] for d in ds], "s-", color=C_PRED, label="(171,133), K = 7")
    style_axes(ax[0], "output weight d", "number of error events a_d", "Distance spectra")
    ax[1].semilogy(e, [bound(x) for x in e], "--", color=C_PRED, label="union bound (7,5)")
    ax[1].semilogy(list(sims), [v[0] for v in sims.values()], "o", color=C_MEAS, label="simulated, soft Viterbi")
    ax[1].semilogy(e, Q(np.sqrt(2 * 10 ** (e / 10))), ":", color="gray", label="uncoded BPSK")
    ax[1].set_ylim(1e-7, 1e-1)
    style_axes(ax[1], "Eb/N0 (dB)", "bit error rate", "Spectrum → performance")
    p.save(fig, "conv", "Distance spectra of the K = 3 and K = 7 codes and the (7,5) BER against its union bound.")
    p.discuss(f"""The trellis enumeration reproduces the closed-form spectrum of the (7,5) code term by term and the published values for the NASA K = 7 code
(d_free = 10 with 11 minimum-weight events, and no odd-weight events at all). Those few numbers predict performance: at 5 and 6 dB the simulated
BER sits on the union bound, while at 3 dB the bound overestimates ({bound(3.0):.1e} vs {sims[3.0][0]:.1e}) because overlapping error events are counted more than
once. The catastrophic example shows why generator choice is not just about distance: with g₁ and g₂ sharing the factor 1 + D, an input of 2000
ones encodes to a weight-{wc} sequence — a few channel errors could turn the all-zero message into all ones.""")
# tol-convention: relative tolerances are in percent
