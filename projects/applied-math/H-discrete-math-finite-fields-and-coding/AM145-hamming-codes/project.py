from eelab import *
from math import comb

META = dict(
    id="AM-145", title="Hamming codes: perfect single-error correction", level="M",
    tools="Parity-check and generator matrices over GF(2) built from the definition, exhaustive weight enumeration, syndrome decoding, extended (SECDED) code, Monte-Carlo binary-symmetric-channel simulation against exact block-error formulas",
    summary="Construct Hamming codes for r = 3…6 from 'all non-zero columns', verify minimum distance 3 and the perfect sphere-packing identity, "
            "show that every single error is corrected and every double error is mis-corrected (unless an overall parity bit is added), and match simulated error rates to theory.",
    problem="How few parity bits can locate any single flipped bit — and what exactly happens when two bits flip?",
    theory=r"""H has all $2^r-1$ non-zero r-bit columns: $n=2^r-1$, $k=n-r$, $d_{min}=3$. The syndrome $s=Hr^T$ equals the column of the flipped bit. Perfect: $2^k(1+n)=2^n$ — every word is within distance 1 of exactly one codeword, so a double error
is *always* decoded to a wrong codeword (three bits wrong). (7,4) weight enumerator: $1+7x^3+7x^4+x^7$. Block error on a BSC(p): $1-(1-p)^n-np(1-p)^{n-1}$. Adding an overall parity bit gives d = 4 (SECDED): doubles are detected, not mis-corrected.""",
    method="""Systematic G from H; all 2ᵏ codewords enumerated for r = 3, 4 (weights); all single and double error patterns decoded for r = 3…6; BSC simulation of the (7,4) code, 10⁶ blocks per p; extended (8,4) code on all double errors.""",
)


def hamming(r):
    n = 2 ** r - 1
    cols = [c for c in range(1, n + 1) if c & (c - 1)] + [1 << i for i in range(r)]      # data columns first, then identity
    H = np.array([[(c >> i) & 1 for c in cols] for i in range(r)], np.uint8)
    k = n - r
    G = np.hstack([np.eye(k, dtype=np.uint8), H[:, :k].T])
    return G, H


def decode(H, rx):
    s = (rx @ H.T) % 2                                   # (N, r)
    key = s @ (1 << np.arange(H.shape[0]))
    colkey = H.T @ (1 << np.arange(H.shape[0]))
    lut = np.full(2 ** H.shape[0], -1); lut[colkey] = np.arange(H.shape[1])
    pos = lut[key]; out = rx.copy()
    idx = np.flatnonzero(pos >= 0)
    out[idx, pos[idx]] ^= 1
    return out


def run(p):
    for r_ in (3, 4, 5, 6):
        G, H = hamming(r_); n = 2 ** r_ - 1; k = n - r_
        assert not ((G @ H.T) % 2).any()
        if r_ in (3, 6):
            p.compare(f"({n},{k}) sphere packing: 2ᵏ(1 + n) / 2ⁿ", 1.0, 2.0 ** k * (1 + n) / 2.0 ** n, "")
    G, H = hamming(3)
    msgs = np.array([[(m >> i) & 1 for i in range(4)] for m in range(16)], np.uint8)
    cw = (msgs @ G) % 2; w = cw.sum(1)
    p.compare("(7,4) minimum distance", 3, int(w[w > 0].min()), "", kind="abs")
    for wt, cnt in ((3, 7), (4, 7), (7, 1)):
        p.compare(f"(7,4) codewords of weight {wt}", cnt, int(np.sum(w == wt)), "", kind="abs")
    G4, H4 = hamming(4)
    m4 = np.array([[(m >> i) & 1 for i in range(11)] for m in range(2048)], np.uint8); w4 = ((m4 @ G4) % 2).sum(1)
    p.compare("(15,11) minimum distance", 3, int(w4[w4 > 0].min()), "", kind="abs")
    p.compare("(15,11) number of weight-3 codewords: n(n−1)/6", 35, int(np.sum(w4 == 3)), "", kind="abs")
    s_fail = d_ok = d_w3 = d_tot = 0
    for r_ in (3, 4, 5, 6):
        G, H = hamming(r_); n = 2 ** r_ - 1
        c = (p.rng.integers(0, 2, (1, n - r_), dtype=np.uint8) @ G) % 2
        e1 = np.eye(n, dtype=np.uint8)
        s_fail += int(np.any(decode(H, c ^ e1) != c, axis=1).sum())
        ii, jj = np.triu_indices(n, 1); e2 = np.zeros((len(ii), n), np.uint8); e2[np.arange(len(ii)), ii] = 1; e2[np.arange(len(ii)), jj] = 1
        dec = decode(H, c ^ e2)
        d_tot += len(ii); d_ok += int(np.all(dec == c, axis=1).sum()); d_w3 += int(((dec ^ c).sum(1) == 3).sum())
    p.compare("Single errors not corrected (all positions, r = 3…6)", 0, s_fail, "", kind="abs")
    p.compare(f"Double errors decoded to a wrong codeword at distance 3 (all {d_tot} patterns)", d_tot, d_w3, "", kind="abs")
    # extended (8,4)
    G, H = hamming(3)
    Ge = np.hstack([G, G.sum(1, keepdims=True) % 2])
    c = (np.array([[1, 0, 1, 1]], np.uint8) @ Ge) % 2
    ii, jj = np.triu_indices(8, 1); det = 0
    for i, j in zip(ii, jj):
        rx = c.copy(); rx[0, i] ^= 1; rx[0, j] ^= 1
        synd = (rx[:, :7] @ H.T) % 2; par = rx.sum() % 2
        det += int(synd.any() and par == 0)              # non-zero syndrome with even overall parity ⇒ two errors
    p.compare("Extended (8,4) SECDED: double errors flagged as uncorrectable (of 28)", 28, det, "", kind="abs")
    ps = np.array([0.003, 0.01, 0.03, 0.1]); N = 1_000_000; sim = []; ber = []
    for pr in ps:
        m = p.rng.integers(0, 2, (N, 4), dtype=np.uint8); c = (m @ G) % 2
        rx = c ^ (p.rng.random((N, 7)) < pr).astype(np.uint8); dec = decode(H, rx)
        sim.append(np.mean(np.any(dec != c, axis=1))); ber.append(np.mean(dec[:, :4] != m))
    th = 1 - (1 - ps) ** 7 - 7 * ps * (1 - ps) ** 6
    for i in (1, 3):
        p.compare(f"(7,4) block error rate on BSC(p = {ps[i]})", th[i], sim[i], "", tol=5)
    p.metric("Decoded bit error rate at p = 0.01", ber[1], "", f"vs raw 0.01 — {0.01 / ber[1]:.0f}× better at rate 4/7")
    fig, ax = p.fig(1, 2, w=11)
    pp = np.logspace(-3, -0.7, 60)
    ax[0].loglog(pp, 1 - (1 - pp) ** 7 - 7 * pp * (1 - pp) ** 6, "--", color=C_PRED, label="theory (7,4)"); ax[0].loglog(ps, sim, "o", color=C_MEAS, label="simulated")
    ax[0].loglog(pp, 1 - (1 - pp) ** 4, ":", color="gray", label="uncoded 4 bits")
    style_axes(ax[0], "channel bit error probability p", "block error rate", "Hamming (7,4) on a binary symmetric channel")
    ax[1].bar(np.arange(8), np.bincount(w, minlength=8), color=C_MEAS)
    style_axes(ax[1], "codeword weight", "count", "(7,4) weight enumerator 1 + 7x³ + 7x⁴ + x⁷", legend=False)
    p.save(fig, "hamming", "Block error rate of the (7,4) Hamming code versus theory, and its weight distribution.")
    p.discuss("""Everything the construction promises holds exactly: the codes have minimum distance 3, their decoding spheres tile the whole space (perfect
codes), and syndrome decoding repairs every single-bit error for r = 3…6. The flip side of perfection is visible in the double-error test: there is no
'unused' syndrome, so *every* double error is confidently decoded to the wrong codeword, leaving three bits wrong. One extra overall parity bit
fixes that — the (8,4) code flags all 28 double errors — which is the SECDED scheme in ECC memory. Simulated block error rates match
1 − (1−p)⁷ − 7p(1−p)⁶ within Monte-Carlo noise.""")
# tol-convention: relative tolerances are in percent
