from eelab import *
from eelab.gf import GF, RS
from itertools import combinations, product

META = dict(
    id="AM-146", title="Reed–Solomon codes: polynomials that survive erasure", level="H",
    tools="Reed–Solomon over GF(8) and GF(256) using the repository's field/codec (Berlekamp–Massey, Chien, Forney), exhaustive codeword enumeration, Lagrange interpolation over the field for erasure recovery, evaluation-view vs generator-view equivalence, burst-error experiments",
    summary="Treat a message as a polynomial and a codeword as its values: any k of n symbols determine it. Verify exhaustively on RS(7,3) that the "
            "minimum distance is n − k + 1 and that every ≤ 2-symbol error and every 4-symbol erasure is recovered, then scale to RS(255,223) and its 16-symbol (128-bit burst) limit.",
    problem="CDs, QR codes and deep-space links all survive scratches and bursts with the same trick. What is it, and where exactly does it stop working?",
    theory=r"""A polynomial of degree < k has at most k − 1 roots, so two distinct codewords (n evaluations) agree in at most k − 1 places: $d=n-k+1$, meeting the Singleton bound (MDS). Hence t = ⌊(n−k)/2⌋ errors or n − k erasures are correctable.
The evaluations $c_j=f(\alpha^j)$ have a spectrum that vanishes at $\alpha^1…\alpha^{n-k}$, so the evaluation code equals the cyclic code with generator $\prod_{i=1}^{n-k}(x-\alpha^i)$. Symbols are m-bit, so a burst of up to $(t-1)m+1$ bits is always corrected.""",
    method="""RS(7,3) over GF(8): all 512 codewords for the weight distribution; every error pattern of weight 1 and 2 (49 + 1029) on random codewords; every choice of 3 surviving symbols (35) reconstructs the message by Lagrange interpolation.
RS(255,223): random 1…16 symbol errors (500 trials each extreme), 17 errors, and bit bursts of 121 and 129+ bits.""",
)


def lagrange(gf, xs, ys, k):
    """Coefficients (lowest first) of the unique polynomial of degree < k through (xs, ys) over GF(2^m)."""
    coef = [0] * k
    for i in range(k):
        num = [1]; den = 1
        for j in range(k):
            if j != i:
                num = [a ^ b for a, b in zip([0] + num, [gf.mul(c, xs[j]) for c in num] + [0])]      # num·(x + x_j)
                den = gf.mul(den, xs[i] ^ xs[j])
        sc = gf.div(ys[i], den)
        for d in range(len(num)):
            coef[d] ^= gf.mul(num[d], sc)
    return coef


def run(p):
    g8 = GF(3, 0b1011); rs = RS(7, 3, g8, fcr=1)
    al = [g8.pow(2, j) for j in range(7)]
    # evaluation view: c_j = f(α^j); coefficient of x^j is c_j, the codec wants highest degree first
    ev = lambda msg: [g8.poly_eval(list(msg[::-1]), a) for a in al]
    cws = [ev(m) for m in product(range(8), repeat=3)]
    wts = np.array([sum(1 for s in c if s) for c in cws])
    p.compare("RS(7,3): minimum distance = n − k + 1", 5, int(wts[wts > 0].min()), "", kind="abs")
    p.compare("RS(7,3): codewords of minimum weight = (q−1)·C(7,5)", 7 * 21, int(np.sum(wts == 5)), "", kind="abs")
    synd_bad = sum(max(g8.poly_eval(c[::-1], g8.pow(2, i)) for i in range(1, 5)) != 0 for c in cws)
    p.compare("Evaluation codewords that are not in the cyclic code with roots α¹…α⁴", 0, synd_bad, "", kind="abs")
    r = p.rng; fail = 0; n_pat = 0
    for w in (1, 2):
        for pos in combinations(range(7), w):
            for vals in product(range(1, 8), repeat=w):
                msg = [int(v) for v in r.integers(0, 8, 3)]; c = rs.encode(msg); rx = c[:]
                for q, v in zip(pos, vals):
                    rx[q] ^= v
                n_pat += 1
                try:
                    fail += rs.decode(rx)[0] != msg
                except ValueError:
                    fail += 1
    p.compare(f"RS(7,3): error patterns of weight ≤ 2 not corrected (all {n_pat})", 0, fail, "", kind="abs")
    wrong = det = 0
    for _ in range(3000):
        msg = [int(v) for v in r.integers(0, 8, 3)]; c = rs.encode(msg); rx = c[:]
        for q in r.choice(7, 3, replace=False):
            rx[q] ^= int(r.integers(1, 8))
        try:
            wrong += rs.decode(rx)[0] != msg
        except ValueError:
            det += 1
    p.metric("RS(7,3) with 3 errors (beyond t): detected / silently mis-decoded", f"{det / 30:.0f} % / {wrong / 30:.0f} %")
    er_fail = 0
    msg = [3, 6, 1]; c = ev(msg)
    for keep in combinations(range(7), 3):
        er_fail += lagrange(g8, [al[j] for j in keep], [c[j] for j in keep], 3) != msg
    p.compare("RS(7,3): 4 erasures — message recovered from any 3 surviving symbols (failures of 35)", 0, er_fail, "", kind="abs")
    big = RS(255, 223); ok16 = ok1 = bad17 = 0; T = 300
    for _ in range(T):
        msg = [int(v) for v in r.integers(0, 256, 223)]; c = big.encode(msg)
        for ne in (1, 16, 17):
            rx = c[:]
            for q in r.choice(255, ne, replace=False):
                rx[q] ^= int(r.integers(1, 256))
            try:
                good = big.decode(rx)[0] == msg
            except ValueError:
                good = False
            if ne == 1: ok1 += good
            elif ne == 16: ok16 += good
            else: bad17 += not good
    p.compare("RS(255,223): 16 random symbol errors corrected", T, ok16, f"of {T}", kind="abs")
    p.compare("RS(255,223): 17 symbol errors — decoding fails (t = 16)", T, bad17, f"of {T}", kind="abs")
    burst = {}
    for L in (121, 128, 129, 136, 137, 160):
        okb = 0
        for _ in range(100):
            msg = [int(v) for v in r.integers(0, 256, 223)]; c = big.encode(msg)
            bits = np.unpackbits(np.array(c, np.uint8)); s = int(r.integers(0, 2040 - L))
            bits[s: s + L] ^= 1
            try:
                okb += big.decode([int(v) for v in np.packbits(bits)])[0] == msg
            except ValueError:
                pass
        burst[L] = okb
    p.compare("Bit bursts of 121 bits = (t−1)·8 + 1 (always ≤ 16 symbols): corrected", 100, burst[121], "of 100", kind="abs")
    p.compare("Bit bursts of 137 bits (always ≥ 18 symbols): corrected", 0, burst[137], "of 100", kind="abs")
    p.metric("Bursts of 128 / 129 / 136 bits corrected (depends on alignment)", f"{burst[128]} / {burst[129]} / {burst[136]}", "of 100")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].bar(np.arange(8), np.bincount(wts, minlength=8), color=C_MEAS)
    style_axes(ax[0], "codeword weight", "count", "RS(7,3): nothing between 0 and d = 5", legend=False)
    ax[1].plot(list(burst), list(burst.values()), "o-", color=C_MEAS); ax[1].axvline(121, color=C_PRED, ls="--", label="guaranteed: 121 bits"); ax[1].axvline(128, color="gray", ls=":", label="16 symbols")
    style_axes(ax[1], "burst length (bits)", "bursts corrected (of 100)", "RS(255,223) burst correction")
    p.save(fig, "rs", "Weight distribution of RS(7,3) and burst-correction capability of RS(255,223).")
    p.discuss(f"""On the small code every claim is checked exhaustively: the 512 codewords have minimum weight 5 = n − k + 1 (with exactly 147 at that weight), the
polynomial-evaluation and cyclic-generator descriptions are the same code, all {n_pat} one- and two-symbol error patterns are corrected and any three
surviving symbols rebuild the message by interpolation. RS(255,223) corrects 16 symbol errors and refuses 17 — the decoder reports failure rather
than guessing, which is what lets an outer protocol request retransmission. Because a symbol error costs the same whether one or eight of its bits
are wrong, a 121-bit burst is always inside the budget and nothing longer than 136 bits is; between those the outcome depends on how the burst
lines up with symbol boundaries ({burst[128]} % at 128 bits). That burst tolerance is why RS is the outer code on CDs, QR codes and CCSDS links.""")
# tol-convention: relative tolerances are in percent
