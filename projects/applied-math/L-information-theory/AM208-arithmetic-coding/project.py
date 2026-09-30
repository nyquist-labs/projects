from eelab import *
from eelab.data import alice_text
import zlib

META = dict(
    id="AM-208", title="Arithmetic coding: reaching the entropy bit by bit", level="H",
    tools="Own 32-bit integer arithmetic coder (interval renormalisation with pending-bit carry handling) and decoder, static and adaptive frequency models, order-0/1/2 context models on real text, comparison with ideal code length −Σlog₂p, Huffman and zlib",
    summary="Build a working arithmetic coder, prove it lossless on a whole book, show that its output is within a couple of bits of the model's ideal code "
            "length, beat Huffman where Huffman is weakest (skewed sources), and use context models to compress English far below its single-letter entropy.",
    problem="Huffman coding wastes up to one bit per symbol. How can a code spend fractional bits — and how close does it get to the entropy?",
    theory=r"""Arithmetic coding narrows an interval by each symbol's probability; the final interval has width $\prod p_i$, so about $-\sum\log_2p_i+2$ bits identify it. With finite-precision integers the interval is renormalised by shifting out settled bits, and 'underflow' (straddling the midpoint) is handled
by pending bits. The code length therefore equals the model's log-loss plus a constant, whatever the probabilities — including p = 0.99, where Huffman needs 1 bit/symbol against H = 0.081. Compression = modelling: an adaptive order-k context
model predicts each letter from the previous k and pays its conditional log-loss, approaching the conditional entropies of AM-204.""",
    method="""Coder: 32-bit range, frequencies up to 2¹⁶. Tests: round trip on the whole book for every model; code length vs Σ−log₂p of the model's own predictions; Bernoulli(0.01) source (10⁵ symbols) vs Huffman (1 bit/symbol) and H₂(0.01); adaptive order-0, 1, 2 models
(Laplace-smoothed counts, 256-symbol alphabet) on 'Alice'; zlib level 9 for reference.""",
    data="Project Gutenberg eBook #11 (public domain).",
)

TOP = (1 << 32) - 1; HALF = 1 << 31; QTR = 1 << 30


class Model:
    """Adaptive frequency model with a context of the previous `order` symbols."""
    def __init__(self, order, nsym=256):
        self.order, self.nsym, self.tab = order, nsym, {}

    def freqs(self, ctx):
        t = self.tab.get(ctx)
        if t is None:
            t = np.ones(self.nsym, np.int64); self.tab[ctx] = t
        return t

    def update(self, ctx, s):
        t = self.tab[ctx]; t[s] += 32
        if t.sum() > (1 << 16):
            t[:] = (t + 1) // 2


def encode(seq, model):
    lo, hi, pend = 0, TOP, 0; out = []; logloss = 0.0; hist = ()
    def emit(b):
        nonlocal pend
        out.append(b); out.extend([1 - b] * pend); pend = 0
    for s in seq:
        ctx = hist[-model.order:] if model.order else (); f = model.freqs(ctx); cum = np.concatenate([[0], np.cumsum(f)]); tot = int(cum[-1])
        logloss -= np.log2(f[s] / tot)
        rng = hi - lo + 1; hi = lo + rng * int(cum[s + 1]) // tot - 1; lo = lo + rng * int(cum[s]) // tot
        while True:
            if hi < HALF:
                emit(0)
            elif lo >= HALF:
                emit(1); lo -= HALF; hi -= HALF
            elif lo >= QTR and hi < 3 * QTR:
                pend += 1; lo -= QTR; hi -= QTR
            else:
                break
            lo, hi = 2 * lo, 2 * hi + 1
        model.update(ctx, s); hist = (hist + (s,))[-max(model.order, 1):]
    pend += 1; emit(0 if lo < QTR else 1)
    return out, logloss


def decode(bits, n, model):
    lo, hi, val = 0, TOP, 0; pos = 0; hist = (); out = []
    for _ in range(32):
        val = (val << 1) | (bits[pos] if pos < len(bits) else 0); pos += 1
    for _ in range(n):
        ctx = hist[-model.order:] if model.order else (); f = model.freqs(ctx); cum = np.concatenate([[0], np.cumsum(f)]); tot = int(cum[-1])
        rng = hi - lo + 1; tgt = ((val - lo + 1) * tot - 1) // rng; s = int(np.searchsorted(cum, tgt, side="right") - 1)
        out.append(s); hi = lo + rng * int(cum[s + 1]) // tot - 1; lo = lo + rng * int(cum[s]) // tot
        while True:
            if hi < HALF:
                pass
            elif lo >= HALF:
                lo -= HALF; hi -= HALF; val -= HALF
            elif lo >= QTR and hi < 3 * QTR:
                lo -= QTR; hi -= QTR; val -= QTR
            else:
                break
            lo, hi = 2 * lo, 2 * hi + 1; val = (val << 1) | (bits[pos] if pos < len(bits) else 0); pos += 1
        model.update(ctx, s); hist = (hist + (s,))[-max(model.order, 1):]
    return out


class Fixed:
    def __init__(self, f):
        self.f, self.order = np.array(f, np.int64), 0

    def freqs(self, ctx):
        return self.f

    def update(self, ctx, s):
        pass


def run(p):
    r = p.rng
    src = (r.random(100000) < 0.01).astype(int)
    bits, ll = encode(src, Fixed([990, 10]))
    p.compare("Bernoulli(0.01), 10⁵ symbols: code length vs the model's ideal −Σlog₂p", ll, len(bits), "bit", kind="abs", tol=3)
    p.compare("… bits per symbol vs the entropy H₂(0.01) = 0.081 (Huffman: 1.000)", 0.0808, len(bits) / len(src), "bit", tol=4)
    p.compare("… decodes back exactly (symbol errors)", 0, int(np.sum(np.array(decode(bits, len(src), Fixed([990, 10]))) != src)), "", kind="abs")
    text = alice_text().encode("utf-8"); data = list(text); n = len(data)
    rows = []
    for order in (0, 1, 2):
        bits, ll = encode(data, Model(order)); ok = decode(bits, n, Model(order)) == data
        rows.append((order, len(bits) / n, ll / n, ok))
    for order, bpc, llc, ok in rows:
        p.compare(f"Order-{order} adaptive model on the book: lossless round trip (1 = yes)", 1, int(ok), "", kind="abs")
    p.compare("Order-2 model: arithmetic-code length vs the model's log-loss (bits per character)", rows[2][2], rows[2][1], "bit", tol=0.1)
    zb = len(zlib.compress(text, 9)) * 8 / n
    p.compare("My expectation: the order-2 context model beats zlib -9 on English text (1 = yes)", 1, int(rows[2][1] < zb), "", kind="abs")
    p.metric("Bits per character: order-0 / order-1 / order-2 arithmetic coding / zlib -9", " / ".join(f"{v[1]:.3f}" for v in rows) + f" / {zb:.3f}", "", f"{n} bytes; Huffman on single characters (AM-151): 4.60")
    fig, ax = p.fig(1, 1, w=7.5, h=4.2)
    names = ["Huffman\n(order 0)", "arith.\norder 0", "arith.\norder 1", "arith.\norder 2", "zlib -9"]; vals = [4.603, rows[0][1], rows[1][1], rows[2][1], zb]
    ax.bar(names, vals, color=[COLORS[7], C_MEAS, C_MEAS, C_MEAS, C_PRED])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center")
    style_axes(ax, "", "bits per character", "Compressing 'Alice in Wonderland'", legend=False)
    p.save(fig, "arithmetic", "Bits per character of the book with Huffman, arithmetic coding under three context models, and zlib.")
    p.discuss(f"""The coder is exact — every model decodes the whole book back byte for byte — and efficient in the sense that matters: its output is within a
few bits of the model's own log-loss, so the coding step costs essentially nothing and all compression is decided by the probabilities. That removes
Huffman's one-bit floor on skewed sources (0.083 bit/symbol for a Bernoulli(0.01) source, against Huffman's 1.00). On English the gain comes from
modelling: order-0 arithmetic coding matches single-letter Huffman performance ({rows[0][1]:.2f} bit/char), and predicting each letter from the previous one or
two brings it to {rows[1][1]:.2f} and {rows[2][1]:.2f}. I expected the order-2 model to beat zlib; it lands just above it ({zb:.2f}), because zlib's long-range matching
finds repeated words and phrases (character names, 'said the') that a two-letter context cannot see. Better models — longer contexts, mixtures —
are how modern compressors reach ≈ 2 bits/char on such text; the arithmetic coder underneath stays the same.""")
# tol-convention: relative tolerances are in percent
