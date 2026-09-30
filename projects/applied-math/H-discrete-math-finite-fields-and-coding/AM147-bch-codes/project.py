from eelab import *
from eelab.gf import GF
from itertools import combinations

META = dict(
    id="AM-147", title="BCH codes from cyclotomic cosets", level="H",
    tools="Cyclotomic cosets and minimal polynomials over GF(2ᵐ), generator construction, own algebraic decoder (syndromes, Berlekamp–Massey, Chien search), exhaustive weight enumeration and error-pattern tests, published (n, k, t) tables",
    summary="Construct binary BCH codes by requiring α, α², …, α²ᵗ to be roots of every codeword: derive the generators of the length-15 codes, reproduce "
            "the published (n, k, t) tables for n = 31 and 63 from the coset structure, confirm the BCH bound d ≥ 2t + 1, and decode every correctable error pattern.",
    problem="Hamming codes fix one error. How do you design a binary code to fix exactly t errors, for any t you choose?",
    theory=r"""Over GF(2), if β is a root of a binary polynomial so are β², β⁴, … — the cyclotomic coset. The generator is the LCM of the minimal polynomials of α¹…α²ᵗ, so n − k = total size of the distinct cosets hit. BCH bound: 2t consecutive roots ⇒ d ≥ 2t + 1.
Length 15: t = 1 → g = x⁴+x+1 (k = 11); t = 2 → x⁸+x⁷+x⁶+x⁴+1 (k = 7); t = 3 → x¹⁰+x⁸+x⁵+x⁴+x²+x+1 (k = 5). Tables: n = 31: k = 26, 21, 16, 11, 6 for t = 1, 2, 3, 5, 7; n = 63: k = 57, 51, 45, 39, 36, 30, 24 for t = 1…7.
Decoding: syndromes $S_i=r(\alpha^i)$, Berlekamp–Massey for the error locator, Chien search for its roots.""",
    method="""Generators built by multiplying minimal polynomials (coefficients must land in {0, 1}). (15,7) and (15,5): all codewords enumerated for the true minimum distance; every error pattern of weight ≤ t decoded. (63,45,t=3): 2000 random
patterns of weight ≤ 3 and weight 4.""",
)


def cosets(n):
    seen = set(); out = []
    for s in range(1, n):
        if s not in seen:
            c = []; x = s
            while x not in c:
                c.append(x); x = (2 * x) % n
            seen |= set(c); out.append(c)
    return out


def generator(gf, n, t):
    need = set(range(1, 2 * t + 1)); g = [1]; used = []
    for c in cosets(n):
        if need & set(c):
            used.append(c)
            for e in c:
                g = gf.poly_mul(g, [1, gf.pow(2, e)])
    assert set(g) <= {0, 1}, "minimal polynomials must have binary coefficients"
    return g, used                                             # highest degree first


def encode(msg, g, n):
    k = n - (len(g) - 1); rem = list(msg) + [0] * (n - k)
    for i in range(k):
        if rem[i]:
            for j in range(len(g)):
                rem[i + j] ^= g[j]
    return list(msg) + rem[k:]


def decode(gf, rx, n, t):
    rx = list(rx)
    S = [gf.poly_eval(rx, gf.pow(2, i)) for i in range(1, 2 * t + 1)]
    if not any(S):
        return rx, 0
    C, B, L, m, b = [1], [1], 0, 1, 1
    for i in range(2 * t):
        d = S[i]
        for j in range(1, L + 1):
            if j < len(C):
                d ^= gf.mul(C[j], S[i - j])
        if d == 0:
            m += 1; continue
        T = C[:]; coef = gf.div(d, b)
        C = C + [0] * max(0, len(B) + m - len(C))
        for j, bj in enumerate(B):
            C[j + m] ^= gf.mul(coef, bj)
        if 2 * L <= i:
            L, B, b, m = i + 1 - L, T, d, 1
        else:
            m += 1
    pos = []
    for j in range(n):                                          # error at coefficient x^j  ⇔  Λ(α^−j) = 0
        xi = gf.pow(2, (n - j) % n); v = 0
        for d_, c in enumerate(C[: L + 1]):
            v ^= gf.mul(c, gf.pow(xi, d_))
        if v == 0:
            pos.append(n - 1 - j)                               # list index (highest degree first)
    if len(pos) != L:
        return rx, -1
    for q in pos:
        rx[q] ^= 1
    return rx, L


def run(p):
    g16 = GF(4, 0b10011)
    known = {1: 0b10011, 2: 0b111010001, 3: 0b10100110111}
    for t, kv in known.items():
        g, _ = generator(g16, 15, t)
        p.compare(f"n = 15, t = {t}: generator polynomial (as an integer) = {kv:#x}", kv, int("".join(map(str, g)), 2), "", kind="abs")
    tabs = {31: (GF(5, 0b100101), {1: 26, 2: 21, 3: 16, 5: 11, 7: 6}), 63: (GF(6, 0b1000011), {1: 57, 2: 51, 3: 45, 4: 39, 5: 36, 6: 30, 7: 24})}
    bad = 0; rows = []
    for n, (gf, tab) in tabs.items():
        for t, k in tab.items():
            g, used = generator(gf, n, t); rows.append((n, t, n - (len(g) - 1), k)); bad += (n - (len(g) - 1)) != k
    p.compare("Published (n, k, t) table entries for n = 31 and 63 not reproduced (12 entries)", 0, bad, "", kind="abs")
    for t, k in ((2, 7), (3, 5)):
        g, _ = generator(g16, 15, t)
        cws = np.array([encode([(m >> i) & 1 for i in range(k)], g, 15) for m in range(2 ** k)])
        w = cws.sum(1)
        p.compare(f"(15,{k}): true minimum distance vs BCH bound 2t + 1", 2 * t + 1, int(w[w > 0].min()), "", kind="abs")
        fail = 0; npat = 0
        for wt in range(1, t + 1):
            for pos in combinations(range(15), wt):
                c = list(cws[p.rng.integers(len(cws))]); rx = c[:]
                for q in pos:
                    rx[q] ^= 1
                npat += 1; fail += decode(g16, rx, 15, t)[0] != c
        p.compare(f"(15,{k}): error patterns of weight ≤ {t} not corrected (all {npat})", 0, fail, "", kind="abs")
    gf = tabs[63][0]; g, _ = generator(gf, 63, 3); r = p.rng; ok3 = 0; out4 = {"detected": 0, "miscorrected": 0}
    for _ in range(2000):
        c = encode(list(r.integers(0, 2, 45)), g, 63)
        rx = c[:]
        for q in r.choice(63, int(r.integers(1, 4)), replace=False):
            rx[q] ^= 1
        ok3 += decode(gf, rx, 63, 3)[0] == c
        rx = c[:]
        for q in r.choice(63, 4, replace=False):
            rx[q] ^= 1
        d, L = decode(gf, rx, 63, 3)
        out4["detected" if L < 0 else "miscorrected"] += 1
    p.compare("(63,45,t=3): random patterns of 1–3 errors corrected", 2000, ok3, "of 2000", kind="abs")
    p.metric("(63,45): 4 errors → decoder reports failure / mis-corrects", f"{out4['detected'] / 20:.0f} % / {out4['miscorrected'] / 20:.0f} %")
    p.section("Cyclotomic cosets mod 15", "\n".join(f"- {{{', '.join(map(str, c))}}} → minimal polynomial of degree {len(c)}" for c in cosets(15)))
    rr = np.array(rows)
    fig, ax = p.fig(1, 1, w=8, h=4.4)
    for n, col in ((31, C_MEAS), (63, C_PRED)):
        m_ = rr[rr[:, 0] == n]
        ax.plot(m_[:, 1] * 2 + 1, m_[:, 2] / n, "o-", color=col, label=f"n = {n}")
    style_axes(ax, "designed distance 2t + 1", "code rate k / n", "BCH codes: rate paid for each extra correctable error")
    p.save(fig, "bch", "Rate versus designed distance for the binary BCH codes of length 31 and 63 constructed here.")
    p.discuss(f"""Multiplying the minimal polynomials picked out by the cyclotomic cosets reproduces the textbook generators for length 15 and all twelve
published (n, k, t) entries for lengths 31 and 63 — the dimension of a BCH code is pure coset bookkeeping. The exhaustively measured minimum
distances equal the BCH bound 2t + 1, and the algebraic decoder (syndromes → Berlekamp–Massey → Chien search) corrects every error pattern up to t.
Beyond t it behaves honestly most of the time: with four errors in the t = 3 code it reports failure in {out4['detected'] / 20:.0f} % of trials and
mis-corrects in the rest. Note the uneven steps in rate: adding α⁵ to the required roots of the n = 15 code costs only two parity bits because its
coset {{5, 10}} is small — which is why some (n, k) combinations are bargains.""")
# tol-convention: relative tolerances are in percent
