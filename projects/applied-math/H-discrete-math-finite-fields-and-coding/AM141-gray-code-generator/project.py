from eelab import *

META = dict(
    id="AM-141", title="Gray codes: one bit at a time", level="E",
    tools="Binary↔Gray conversion by XOR and prefix-XOR, reflected construction, exhaustive property checks up to 16 bits, Monte-Carlo model of sampling a counter whose bits switch with random skew (asynchronous FIFO pointer / rotary encoder)",
    summary="Generate n-bit Gray codes three ways, prove the single-bit-change property exhaustively, and quantify why it matters: sampling a binary "
            "counter mid-transition can return a wildly wrong value, while a Gray counter is never off by more than one count.",
    problem="An encoder disc or a clock-domain-crossing pointer is read while it changes. How do we make a half-changed value harmless?",
    theory=r"""$g=b\oplus(b\gg1)$; inverse $b_i=\bigoplus_{j\ge i}g_j$ (prefix XOR). Successive codes differ in exactly one bit, including wrap-around (cyclic). Average bit flips per increment: Gray = 1; binary = $2-2^{1-n}$.
If bits change at slightly different instants, a binary transition k→k+1 that flips m bits can be read as any of $2^m$ mixtures — worst case 0111→1000 reads anything from 0 to 15 — whereas Gray can only read k or k+1: error ≤ 1 count.""",
    method="""Exhaustive checks for n = 1…16. Skew model: each changing bit switches at an independent random time inside the transition window; the counter is sampled at a uniformly random instant (10⁶ samples, n = 10).
Error = |decoded value − nearest true value|.""",
)


def to_gray(b):
    return b ^ (b >> 1)


def from_gray(g, n):
    b = g.copy()
    s = 1
    while s < n:
        b ^= b >> s; s *= 2
    return b


def reflected(n):
    c = [0]
    for i in range(n):
        c = c + [x | (1 << i) for x in reversed(c)]
    return np.array(c)


def run(p):
    bad_adj = bad_inv = bad_ref = 0
    for n in range(1, 17):
        b = np.arange(2 ** n); g = to_gray(b)
        d = g ^ np.roll(g, -1)
        bad_adj += int(np.sum((d & (d - 1)) != 0) + np.sum(d == 0))
        bad_inv += int(np.sum(from_gray(g, n) != b))
        bad_ref += int(np.sum(reflected(n) != g))
        bad_adj += len(np.unique(g)) != 2 ** n
    p.compare("Adjacent codes (incl. wrap-around) not differing in exactly one bit, n = 1…16", 0, bad_adj, "", kind="abs")
    p.compare("Round-trip binary → Gray → binary failures", 0, bad_inv, "", kind="abs")
    p.compare("XOR formula vs reflect-and-prefix construction (differences)", 0, bad_ref, "", kind="abs")
    n = 10; b = np.arange(2 ** n)
    flips_b = np.array([bin(int(x)).count("1") for x in b ^ np.roll(b, -1)])
    p.compare("Mean bit flips per increment, binary (n = 10): 2 − 2^(1−n)", 2 - 2 ** (1 - n), flips_b.mean(), "")
    p.compare("Mean bit flips per increment, Gray", 1.0, float(np.mean([bin(int(x)).count("1") for x in to_gray(b) ^ np.roll(to_gray(b), -1)])), "")
    r = p.rng; M = 1_000_000
    k = r.integers(0, 2 ** n - 1, M)
    res = {}
    for name, enc, dec in (("binary", lambda v: v, lambda v: v), ("Gray", to_gray, lambda v: from_gray(v, n))):
        old, new = enc(k), enc(k + 1); diff = old ^ new
        read = old.copy(); ts = r.random(M)                   # sampling instant inside the transition window
        for bit in range(n):
            ch = ((diff >> bit) & 1).astype(bool)
            switched = r.random(M) < ts                        # this bit's own switching instant, uniform in the window
            read = np.where(ch & switched, read ^ (1 << bit), read)
        val = dec(read)
        err = np.minimum(np.abs(val - k), np.abs(val - (k + 1)))
        res[name] = err
    p.compare("Gray counter sampled mid-transition: worst error", 0, int(res["Gray"].max()), "counts", kind="abs")
    p.compare("Binary counter sampled mid-transition: worst error (2^(n−1) − 1 at the MSB carry, n = 10)", 2 ** (n - 1) - 1, int(res["binary"].max()), "counts", tol=2)
    p.metric("Binary: fraction of samples that are wrong (neither k nor k+1)", float(np.mean(res["binary"] > 0)) * 100, "%")
    p.metric("Binary: RMS error when sampled mid-transition", float(np.sqrt(np.mean(res["binary"].astype(float) ** 2))), "counts")
    p.write("results/gray4.txt", "\n".join(f"{i:2d}  {i:04b}  {int(to_gray(np.array(i))):04b}" for i in range(16)) + "\n", "4-bit table: index, binary, Gray")
    fig, ax = p.fig(1, 2, w=11)
    g4 = to_gray(np.arange(16))
    for bit in range(4):
        ax[0].step(np.arange(17), np.r_[(g4 >> bit) & 1, (g4[0] >> bit) & 1] * 0.7 + bit, where="post", color=C_MEAS)
        ax[0].step(np.arange(17), np.r_[(np.arange(16) >> bit) & 1, 0] * 0.7 + bit + 4.5, where="post", color=C_PRED)
    ax[0].set_yticks([1.5, 6]); ax[0].set_yticklabels(["Gray", "binary"])
    style_axes(ax[0], "count", "", "4-bit waveforms: one edge per step (Gray) vs many (binary)", legend=False)
    e = res["binary"]; h = np.bincount(e[e > 0])
    ax[1].semilogy(np.nonzero(h)[0], h[np.nonzero(h)[0]] / M, ".", color=C_PRED, label="binary")
    ax[1].axvline(1, color=C_MEAS, lw=0); ax[1].plot([0], [1e-7], "o", color=C_MEAS, label="Gray: always 0")
    style_axes(ax[1], "read error (counts)", "probability", "Error when read during a transition (n = 10)")
    p.save(fig, "gray", "Gray versus binary counter waveforms and the distribution of mid-transition read errors.")
    p.discuss(f"""All three constructions agree and every adjacent pair — including the wrap from the last code back to the first — differs in exactly one
bit for n up to 16. That single property makes a mid-transition read harmless: the Gray counter was never wrong in a million skewed samples, while
the binary counter returned a value that was neither the old nor the new count in {np.mean(res['binary'] > 0) * 100:.0f} % of samples, with a worst error of
{int(res['binary'].max())} counts at the MSB carry (0111111111 → 1000000000, where a partial read can even return 0 or 1023). This is exactly why
asynchronous FIFO pointers and absolute rotary encoders use Gray code. It also halves switching activity ({flips_b.mean():.2f} → 1 flips per count).""")
# tol-convention: relative tolerances are in percent
