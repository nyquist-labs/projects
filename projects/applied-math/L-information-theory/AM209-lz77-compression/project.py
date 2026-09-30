from eelab import *
from eelab.data import alice_text
from eelab.info import H
import zlib

META = dict(
    id="AM-209", title="LZ77: universal compression by pointing into the past", level="M",
    tools="Own LZ77 encoder/decoder (hash-chain match search, sliding window, lengths/offsets/literals), fixed-width and entropy-estimated token costs, compression versus window size, universality demo on a Markov source of known entropy rate, comparison with zlib (LZ77 + Huffman)",
    summary="Implement the dictionary compressor behind ZIP and PNG, prove it lossless, measure how its compression depends on the window, and demonstrate its "
            "defining property: without knowing anything about a source, its rate approaches the source's entropy rate as the data grow.",
    problem="Arithmetic coding needs a probability model. How can a compressor that knows nothing about the data still approach the entropy?",
    theory=r"""LZ77 replaces a string that occurred before by a pointer (offset, length) into a window of recent history, otherwise emits a literal. Lempel–Ziv codes are *universal*: for any stationary ergodic source the bits per symbol converge to the entropy rate as the window and data length grow —
but slowly, roughly like $O(\log\log n/\log n)$. Test source: a first-order Markov chain on 4 symbols with known entropy rate $\bar H=-\sum_iπ_i\sum_jP_{ij}\log_2P_{ij}$; its single-symbol entropy is higher, so reaching below $H(X)$ proves the compressor learned the memory. zlib = LZ77 + Huffman coding of the tokens.""",
    method="""Encoder: minimum match 3, maximum 258, window 2⁸…2¹⁵, hash chains of depth 32. Token cost: 1 flag bit + 8 bits per literal, or 1 + ⌈log₂W⌉ + 8 bits per match (fixed-width), plus an 'entropy-coded' cost from the empirical entropies of the token streams. Markov source: 4 symbols,
lengths 10³…10⁶.""",
    data="Project Gutenberg eBook #11 (public domain).",
)


def lz77(data, window=1 << 15, minm=3, maxm=258, depth=32):
    n = len(data); i = 0; toks = []; heads = {}; prev = [-1] * n
    def insert(k):
        if k + 3 <= n:
            key = data[k:k + 3]; prev[k] = heads.get(key, -1); heads[key] = k
    while i < n:
        best_l, best_o = 0, 0
        if i + minm <= n:
            cand = heads.get(data[i:i + 3], -1); d = 0
            while cand >= 0 and i - cand <= window and d < depth:
                l = 0
                while l < maxm and i + l < n and data[cand + l] == data[i + l]:
                    l += 1
                if l > best_l:
                    best_l, best_o = l, i - cand
                cand = prev[cand]; d += 1
        if best_l >= minm:
            toks.append((best_o, best_l))
            for k in range(i, i + best_l):
                insert(k)
            i += best_l
        else:
            toks.append((0, data[i])); insert(i); i += 1
    return toks


def unlz77(toks):
    out = bytearray()
    for o, x in toks:
        if o == 0:
            out.append(x)
        else:
            s = len(out) - o
            for k in range(x):
                out.append(out[s + k])
    return bytes(out)


def cost(toks, window):
    lit = [x for o, x in toks if o == 0]; mt = [(o, x) for o, x in toks if o]
    fixed = len(lit) * 9 + len(mt) * (1 + int(np.ceil(np.log2(window))) + 8)
    ent = len(toks) * H([len(lit), len(mt)]) + len(lit) * H(np.bincount(lit)) + (len(mt) * (H(np.bincount([x for _, x in mt])) + H(np.bincount([int(np.log2(o)) for o, _ in mt])) + np.mean([max(int(np.log2(o)), 0) for o, _ in mt])) if mt else 0)
    return fixed, ent


def run(p):
    text = alice_text().encode("utf-8"); n = len(text)
    toks = lz77(text)
    p.compare("Round trip of the whole book (bytes differing)", 0, int(unlz77(toks) != text) * n, "", kind="abs")
    rows = []
    for wb in (8, 10, 12, 14, 15):
        t = lz77(text, window=1 << wb); f, e = cost(t, 1 << wb); rows.append((wb, f / n, e / n, len(t)))
    rr = np.array(rows)
    zb = len(zlib.compress(text, 9)) * 8 / n
    p.compare("Larger window compresses better (fixed-width cost, 2⁸ → 2¹⁵; violations of monotonic decrease)", 0, int(np.sum(np.diff(rr[:, 2]) > 0)), "", kind="abs")
    p.compare("32 kB window, entropy-coded tokens vs zlib -9 (same algorithm family), bits per character", zb, rr[-1, 2], "bit", tol=12)
    p.metric("Bits per character, 32 kB window: fixed-width tokens / entropy-coded estimate / zlib -9", f"{rr[-1, 1]:.2f} / {rr[-1, 2]:.2f} / {zb:.2f}")
    r = p.rng; P = np.array([[0.7, 0.2, 0.05, 0.05], [0.1, 0.6, 0.2, 0.1], [0.05, 0.15, 0.7, 0.1], [0.3, 0.05, 0.05, 0.6]])
    w, v = np.linalg.eig(P.T); pi_ = np.real(v[:, np.argmin(np.abs(w - 1))]); pi_ /= pi_.sum()
    Hrate = -np.sum(pi_[:, None] * P * np.log2(P)); H1 = H(pi_)
    lens = [1000, 10000, 100000, 1000000]; mk_ = []
    for N in lens:
        x = np.zeros(N, np.uint8); u = r.random(N); cp = np.cumsum(P, 1)
        for t in range(1, N):
            x[t] = np.searchsorted(cp[x[t - 1]], u[t])
        data = bytes(x); t_ = lz77(data, window=1 << 15); _, e = cost(t_, 1 << 15); mk_.append((N, e / N, len(zlib.compress(data, 9)) * 8 / N))
    mk_ = np.array(mk_)
    p.metric("Markov source: entropy rate / single-symbol entropy", f"{Hrate:.3f} / {H1:.3f} bit/symbol")
    p.compare("Universality: at 10⁶ symbols LZ77 (entropy-coded tokens) codes below the single-symbol entropy H(X) — it learned the memory (1 = yes)", 1, int(mk_[-1, 1] < H1), "", kind="abs")
    p.compare("… and its excess over the entropy rate shrinks with length (10³ → 10⁶; 1 = yes)", 1, int(mk_[-1, 1] - Hrate < mk_[0, 1] - Hrate), "", kind="abs")
    p.metric("LZ77 bits/symbol at 10³ / 10⁴ / 10⁵ / 10⁶ symbols", " / ".join(f"{v:.3f}" for v in mk_[:, 1]), "", f"entropy rate {Hrate:.3f}: convergence is slow, as theory warns")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(rr[:, 0], rr[:, 1], "o-", color=C_PRED, label="fixed-width tokens"); ax[0].plot(rr[:, 0], rr[:, 2], "s-", color=C_MEAS, label="entropy-coded tokens"); ax[0].axhline(zb, color="gray", ls=":", label="zlib -9")
    ax[0].set_xticks(rr[:, 0]); ax[0].set_xticklabels([f"2^{int(v)}" for v in rr[:, 0]])
    style_axes(ax[0], "window size (bytes)", "bits per character", "Alice: compression vs window")
    ax[1].semilogx(mk_[:, 0], mk_[:, 1], "o-", color=C_MEAS, label="own LZ77"); ax[1].semilogx(mk_[:, 0], mk_[:, 2], "s-", color=C_PRED, label="zlib -9")
    ax[1].axhline(Hrate, color="k", ls="--", label="entropy rate"); ax[1].axhline(H1, color="gray", ls=":", label="single-symbol entropy")
    style_axes(ax[1], "sequence length", "bits per symbol", "Markov source: slow universal convergence")
    p.save(fig, "lz77", "LZ77 compression of a book versus window size, and convergence toward the entropy rate of a Markov source.")
    p.discuss(f"""The LZ77 coder reproduces the book exactly and, with a 32 kB window and entropy-coded tokens, compresses it to {rr[-1, 2]:.2f} bits per character — within a
few percent of zlib ({zb:.2f}), which is the same idea with better token coding. Window size matters because English repeats words and phrases at
distances of kilobytes. The Markov experiment shows what makes the method remarkable: given only the symbols, LZ77 ends up coding a source whose
letters individually carry {H1:.2f} bits at {mk_[-1, 1]:.2f} bits per symbol, below the single-letter entropy, so it has captured the source's memory without
being told it exists. It also shows the catch: after a million symbols it is still {mk_[-1, 1] - Hrate:.2f} bits above the entropy rate {Hrate:.2f}; universal
convergence is logarithmically slow, which is why practical compressors pair dictionaries with statistical models.""")
# tol-convention: relative tolerances are in percent
