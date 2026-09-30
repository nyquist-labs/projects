from eelab import *
from eelab.data import alice_text
import heapq, zlib, itertools
from collections import Counter

META = dict(
    id="AM-151", title="Huffman coding: the optimal prefix code, built greedily", level="M",
    tools="Own heap-based Huffman construction, canonical code, bit-exact encoder/decoder, brute-force optimality check over all Kraft-tight length assignments, real English text (Project Gutenberg), comparison with Shannon code lengths, pair coding and zlib",
    summary="Build Huffman codes from scratch, prove on small alphabets that no prefix code does better, verify H ≤ L < H + 1 and Gallager's tighter "
            "redundancy bound on a real book, round-trip the whole text bit-exactly, and show where symbol-by-symbol coding stops: skewed sources and context.",
    problem="Morse gave 'e' a short code by intuition. What is the provably best variable-length code for a given set of symbol frequencies?",
    theory=r"""For symbol probabilities pᵢ the optimal prefix code merges the two least probable symbols repeatedly (greedy is optimal because the two rarest symbols can always be made siblings at maximum depth). Its mean length satisfies
$H\le L<H+1$ with $H=-\sum p_i\log_2p_i$; more tightly $L-H\le p_{max}+0.086$ (Gallager). Kraft: $\sum2^{-l_i}=1$ for a complete code. L = H exactly iff all pᵢ are powers of ½. Coding pairs of symbols reduces the per-symbol overhead and starts to exploit
correlation between neighbouring letters.""",
    method="""Data: the text of 'Alice's Adventures in Wonderland' (≈ 144 k characters). Optimality check: 300 random distributions on 3–6 symbols against exhaustive search over all length assignments with Kraft sum ≤ 1. Round trip of the entire text.
Pair (digram) Huffman; zlib level 9 for context.""",
    data="Project Gutenberg eBook #11 (public domain), fetched on first run and cached.",
)


def huffman_lengths(freq):
    """freq: dict symbol → weight. Returns dict symbol → code length."""
    if len(freq) == 1:
        return {s: 1 for s in freq}
    heap = [(w, i, (s,)) for i, (s, w) in enumerate(freq.items())]; heapq.heapify(heap)
    L = dict.fromkeys(freq, 0); tick = len(heap)
    while len(heap) > 1:
        w1, _, a = heapq.heappop(heap); w2, _, b = heapq.heappop(heap)
        for s in a + b:
            L[s] += 1
        heapq.heappush(heap, (w1 + w2, tick, a + b)); tick += 1
    return L


def canonical(L):
    code = {}; c = 0; prev = 0
    for s in sorted(L, key=lambda s: (L[s], str(s))):
        c <<= (L[s] - prev); code[s] = format(c, f"0{L[s]}b"); c += 1; prev = L[s]
    return code


def entropy(freq):
    w = np.array(list(freq.values()), float); q = w / w.sum()
    return float(-(q * np.log2(q)).sum())


def mean_len(freq, L):
    tot = sum(freq.values())
    return sum(freq[s] * L[s] for s in freq) / tot


def run(p):
    r = p.rng; worse = 0; tested = 0
    for _ in range(300):
        n = int(r.integers(3, 7)); pr = r.dirichlet(np.ones(n) * r.uniform(0.3, 3))
        Lh = huffman_lengths({i: float(x) for i, x in enumerate(pr)})
        best = min(sum(pr[i] * l[i] for i in range(n)) for l in itertools.product(range(1, n), repeat=n) if sum(2.0 ** -x for x in l) <= 1 + 1e-12)
        tested += 1; worse += sum(pr[i] * Lh[i] for i in range(n)) > best + 1e-12
    p.compare(f"Huffman worse than the best prefix code found by exhaustive search ({tested} random sources, 3–6 symbols)", 0, worse, "", kind="abs")
    dy = {"a": 0.5, "b": 0.25, "c": 0.125, "d": 0.0625, "e": 0.0625}
    p.compare("Dyadic source (½, ¼, ⅛, 1/16, 1/16): L = H exactly", entropy(dy), mean_len(dy, huffman_lengths(dy)), "bit")
    text = alice_text(); freq = Counter(text)
    L = huffman_lengths(freq); code = canonical(L); Hx = entropy(freq); Lbar = mean_len(freq, L)
    p.metric("Text length / alphabet size", f"{len(text)} characters / {len(freq)} symbols")
    p.compare("Kraft sum Σ2^(−lᵢ) of the Huffman code", 1.0, sum(2.0 ** -l for l in L.values()), "", tol=1e-9)
    p.compare("Source coding bound: H ≤ L < H + 1 (1 = holds)", 1, int(Hx <= Lbar < Hx + 1), "", kind="abs")
    pmax = max(freq.values()) / len(text)
    p.compare("Gallager bound: L − H ≤ p_max + 0.086 (1 = holds)", 1, int(Lbar - Hx <= pmax + 0.086), "", kind="abs")
    p.metric("Entropy H / Huffman L / redundancy", f"{Hx:.4f} / {Lbar:.4f} / {Lbar - Hx:.4f} bit per character", "", f"p_max = {pmax:.3f} (space)")
    bits = "".join(code[ch] for ch in text)
    inv = {v: k for k, v in code.items()}; out = []; cur = ""
    for b in bits:
        cur += b
        if cur in inv:
            out.append(inv[cur]); cur = ""
    p.compare("Encode → decode of the whole book: characters that differ", 0, int("".join(out) != text) * len(text), "", kind="abs")
    p.compare("Encoded size = Σ fᵢ·lᵢ", Lbar * len(text), len(bits), "bit", tol=1e-9)
    codes = list(code.values())
    p.compare("Prefix-free: codewords that are a prefix of another", 0, sum(a != b and b.startswith(a) for a in codes for b in codes), "", kind="abs")
    Ls = {s: int(np.ceil(-np.log2(freq[s] / len(text)))) for s in freq}
    p.metric("Shannon code lengths ⌈−log₂p⌉: mean", mean_len(freq, Ls), "bit/char", "valid but wasteful — Huffman is never worse")
    p.metric("Fixed-length code", int(np.ceil(np.log2(len(freq)))), "bit/char")
    pairs = Counter(text[i: i + 2] for i in range(0, len(text) - 1, 2))
    L2 = mean_len(pairs, huffman_lengths(pairs)) / 2; H2 = entropy(pairs) / 2
    p.compare("Pair (digram) Huffman: bits per character beats single-symbol Huffman (1 = yes)", 1, int(L2 < Lbar), "", kind="abs")
    p.metric("Digram Huffman / digram entropy per character", f"{L2:.4f} / {H2:.4f} bit")
    zb = len(zlib.compress(text.encode("utf-8"), 9)) * 8 / len(text)
    p.metric("zlib -9 (LZ77 + Huffman, long contexts)", zb, "bit/char")
    sk = {"0": 0.99, "1": 0.01}
    p.compare("Skewed binary source (0.99, 0.01): Huffman cannot go below 1 bit/symbol", 1.0, mean_len(sk, huffman_lengths(sk)), "bit")
    p.metric("… while its entropy is", entropy(sk), "bit", "the gap arithmetic coding closes (AM-208)")
    top = sorted(freq, key=freq.get, reverse=True)[:12]
    p.section("Most frequent symbols", "| symbol | probability | −log₂p | code length | codeword |\n|---|---|---|---|---|\n" + "\n".join(
        f"| {repr(s)} | {freq[s] / len(text):.4f} | {-np.log2(freq[s] / len(text)):.2f} | {L[s]} | `{code[s]}` |" for s in top))
    fig, ax = p.fig(1, 2, w=11)
    pr = np.array([freq[s] / len(text) for s in freq]); ll = np.array([L[s] for s in freq])
    ax[0].semilogx(pr, ll, "o", color=C_MEAS, ms=4, label="Huffman length"); q = np.logspace(np.log10(pr.min()), 0, 50); ax[0].semilogx(q, -np.log2(q), "--", color=C_PRED, label="ideal −log₂p")
    style_axes(ax[0], "symbol probability", "code length (bits)", "Huffman lengths track −log₂p")
    names = ["fixed", "Shannon\ncode", "Huffman", "entropy\nH", "digram\nHuffman", "zlib"]
    vals = [np.ceil(np.log2(len(freq))), mean_len(freq, Ls), Lbar, Hx, L2, zb]
    ax[1].bar(names, vals, color=[COLORS[7], COLORS[1], C_MEAS, C_PRED, COLORS[2], COLORS[3]])
    style_axes(ax[1], "", "bits per character", "Alice in Wonderland", legend=False)
    p.save(fig, "huffman", "Huffman code lengths against the ideal −log₂p, and compression of a real text by several methods.")
    p.discuss(f"""The greedy merge is optimal: in 300 random small sources no exhaustive search found a better prefix code, and for a dyadic source the code
meets the entropy exactly. On a real book the Huffman code needs {Lbar:.3f} bits per character against an entropy of {Hx:.3f} — a redundancy of only
{Lbar - Hx:.3f} bit, inside Gallager's bound — and the whole text round-trips bit-exactly. Two limits show where Huffman stops. First, a code
word is at least one bit, so a very skewed source (0.99/0.01) is coded at 1 bit/symbol against an entropy of 0.08 — the motivation for arithmetic
coding. Second, the entropy of single letters is not the entropy of English: coding letter pairs already gets to {L2:.2f} bits per character and
zlib, which models long repeats, reaches {zb:.2f}. Huffman is optimal for the model it is given; better compression comes from better models.""")
# tol-convention: relative tolerances are in percent
