from eelab import *
from math import gcd

META = dict(
    id="AM-142", title="LFSRs and primitive polynomials", level="M",
    tools="Polynomial arithmetic over GF(2) with Python integers, exhaustive primitivity testing of every polynomial of degree 2–16, direct period measurement of simulated LFSRs, Berlekamp–Massey linear complexity, m-sequence balance/run/autocorrelation checks, Fibonacci vs Galois forms",
    summary="Find every primitive polynomial up to degree 16 by computing the multiplicative order of x, check the count against Euler's totient "
            "formula, and verify on simulated shift registers that primitive feedback gives the maximal period 2ⁿ − 1 with the classical pseudo-noise properties.",
    problem="Which feedback taps make a shift register cycle through every non-zero state — and why does the answer come from field theory?",
    theory=r"""An LFSR with characteristic polynomial f(x) of degree n steps its state by multiplication by x in GF(2)[x]/f. The period is the order of x, which is maximal ($2^n-1$) iff f is primitive. There are $\varphi(2^n-1)/n$ primitive polynomials of degree n.
An m-sequence has $2^{n-1}$ ones and $2^{n-1}-1$ zeros, half its runs have length 1, a quarter length 2, …; its ±1 autocorrelation is N at lag 0 and −1 elsewhere; its linear complexity is n; shift-and-add gives another shift of itself.""",
    method="""For n = 2…16 and every f with f(0) = 1: order of x from modular exponentiation and the prime factorisation of 2ⁿ − 1. Periods of simulated Galois LFSRs measured by stepping (n ≤ 12). Properties on the n = 10 sequence from x¹⁰ + x³ + 1.
Fibonacci and Galois registers compared for cyclic equivalence.""",
)


def pmulmod(a, b, f, n):
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1; a <<= 1
        if a >> n:
            a ^= f
    return r


def ppow(e, f, n):
    r, b = 1, 2
    while e:
        if e & 1:
            r = pmulmod(r, b, f, n)
        b = pmulmod(b, b, f, n); e >>= 1
    return r


def factors(m):
    out = []; d = 2
    while d * d <= m:
        if m % d == 0:
            out.append(d)
            while m % d == 0:
                m //= d
        d += 1
    if m > 1:
        out.append(m)
    return out


def phi(m):
    r = m
    for q in factors(m):
        r = r // q * (q - 1)
    return r


def is_primitive(f, n):
    N = 2 ** n - 1
    if ppow(N, f, n) != 1:
        return False
    return all(ppow(N // q, f, n) != 1 for q in factors(N))


def galois_period(f, n):
    s = 1; k = 0
    while True:
        s <<= 1
        if s >> n:
            s ^= f
        k += 1
        if s == 1:
            return k


def berlekamp_massey(s):
    n = len(s); c = [0] * n; b = [0] * n; c[0] = b[0] = 1; L, m = 0, -1
    for i in range(n):
        d = s[i]
        for j in range(1, L + 1):
            d ^= c[j] & s[i - j]
        if d:
            t = c[:]
            for j in range(n - i + m):
                c[i - m + j] ^= b[j]
            if 2 * L <= i:
                L, m, b = i + 1 - L, i, t
    return L


def run(p):
    rows = []; bad_period = 0; prim = {}
    for n in range(2, 17):
        pl = [f for f in range((1 << n) | 1, 1 << (n + 1), 2) if is_primitive(f, n)]
        prim[n] = pl; rows.append((n, len(pl), phi(2 ** n - 1) // n))
        if n <= 12:
            for f in pl[:: max(1, len(pl) // 12)]:
                bad_period += galois_period(f, n) != 2 ** n - 1
    rr = np.array(rows)
    p.compare("Degrees 2–16 where the count of primitive polynomials ≠ φ(2ⁿ − 1)/n", 0, int(np.sum(rr[:, 1] != rr[:, 2])), "", kind="abs")
    p.compare("Primitive polynomials of degree 8", 16, len(prim[8]), "", kind="abs")
    p.compare("Primitive polynomials of degree 16", 2048, len(prim[16]), "", kind="abs")
    p.compare("Simulated LFSRs with primitive feedback whose period ≠ 2ⁿ − 1", 0, bad_period, "", kind="abs")
    p.compare("x⁴+x³+x²+x+1 (irreducible, not primitive): period", 5, galois_period(0b11111, 4), "", kind="abs")
    p.compare("x⁴+x²+1 = (x²+x+1)²  (reducible): period", 6, galois_period(0b10101, 4), "", kind="abs")
    n = 10; f = (1 << 10) | (1 << 3) | 1; N = 2 ** n - 1
    p.compare("x¹⁰ + x³ + 1 is primitive (1 = yes)", 1, int(is_primitive(f, n)), "", kind="abs")
    # Fibonacci LFSR: s[k+10] = s[k+3] + s[k]
    s = [1] + [0] * 9
    for k in range(2 * N):
        s.append(s[k + 3] ^ s[k])
    seq = np.array(s[:N])
    p.compare("m-sequence (N = 1023): number of ones", 512, int(seq.sum()), "", kind="abs")
    d = np.flatnonzero(np.diff(np.r_[seq, seq[:1]]) != 0)
    runs = np.diff(np.r_[d, d[0] + N])
    p.compare("Total number of runs: 2^(n−1)", 512, len(runs), "", kind="abs")
    for L in (1, 2, 3):
        p.compare(f"Runs of length {L}: 2^(n−1−{L})", 2 ** (n - 1 - L), int(np.sum(runs == L)), "", kind="abs")
    x = 1 - 2.0 * seq
    ac = np.real(np.fft.ifft(np.abs(np.fft.fft(x)) ** 2))
    p.compare("Off-peak periodic autocorrelation (every lag): −1", -1.0, float(ac[1:].max()), "", kind="abs", tol=1e-6)
    p.compare("… and minimum", -1.0, float(ac[1:].min()), "", kind="abs", tol=1e-6)
    p.compare("Linear complexity (Berlekamp–Massey on 60 bits)", 10, berlekamp_massey(list(seq[:60])), "", kind="abs")
    sa = seq ^ np.roll(seq, 7)
    shifts = [k for k in range(N) if np.array_equal(sa, np.roll(seq, k))]
    p.compare("Shift-and-add: seq ⊕ (seq shifted by 7) is itself a shift of seq (matches found)", 1, len(shifts), "", kind="abs")
    # Galois form of the same polynomial: output MSB
    st = 1; g = []
    for _ in range(N):
        st <<= 1; o = st >> n
        if o:
            st ^= f
        g.append(o)
    g = np.array(g); dbl = np.r_[seq, seq]
    match = any(np.array_equal(dbl[k: k + N], g) for k in range(N)) or any(np.array_equal(dbl[k: k + N], g[::-1]) for k in range(N))
    p.compare("Galois and Fibonacci registers generate the same sequence up to a shift (1 = yes)", 1, int(match), "", kind="abs")
    p.write("results/primitive_polynomials.txt", "\n".join(f"n={k}: {len(v)} primitive; first few (hex, incl. x^n): " + " ".join(hex(f) for f in v[:8]) for k, v in prim.items()) + "\n",
            "counts and examples of primitive polynomials for degrees 2–16")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(rr[:, 0], rr[:, 1], "o", color=C_MEAS, label="found by search"); ax[0].semilogy(rr[:, 0], rr[:, 2], "--", color=C_PRED, label="φ(2ⁿ − 1)/n")
    ax[0].semilogy(rr[:, 0], 2.0 ** (rr[:, 0] - 1), ":", color="gray", label="candidates 2ⁿ⁻¹")
    style_axes(ax[0], "degree n", "count", "Primitive polynomials")
    lag = np.arange(-40, 41)
    ax[1].plot(lag, ac[lag % N], color=C_MEAS)
    style_axes(ax[1], "lag (chips)", "autocorrelation", "m-sequence: N at zero lag, −1 elsewhere", legend=False)
    p.save(fig, "lfsr", "Count of primitive polynomials versus the totient formula, and the two-valued autocorrelation of a 1023-chip m-sequence.")
    p.discuss("""The brute-force search finds exactly φ(2ⁿ − 1)/n primitive polynomials for every degree from 2 to 16 (16 of degree 8, 2048 of degree 16), and every
simulated register with primitive feedback walks through all 2ⁿ − 1 non-zero states, while irreducible-but-not-primitive and reducible polynomials
give short cycles. The degree-10 sequence has every textbook pseudo-noise property exactly: 512 ones, run lengths halving, a perfectly two-valued
autocorrelation, linear complexity 10 and the shift-and-add property. Those are the reasons m-sequences underlie scramblers, GPS C/A Gold codes,
BIST pattern generators and CRCs — and the low linear complexity is why a bare LFSR is useless as a cipher: 20 output bits reveal the whole sequence.""")
# tol-convention: relative tolerances are in percent
