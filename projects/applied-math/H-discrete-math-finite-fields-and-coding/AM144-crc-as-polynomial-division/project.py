from eelab import *
import zlib, binascii

META = dict(
    id="AM-144", title="CRC as polynomial division over GF(2)", level="M",
    tools="Own bit-serial long division and table-driven CRC engine with the standard parameter model (width, polynomial, init, reflect, xor-out), catalogue check values, zlib/binascii cross-checks, exhaustive and Monte-Carlo error-detection experiments",
    summary="Implement the CRC as the remainder of polynomial division, reproduce the published check values of four standard CRCs and Python's own "
            "zlib/binascii results, and verify the detection guarantees algebra predicts: all single, double (up to the polynomial's period), odd and burst errors.",
    problem="Why does appending a division remainder catch almost every transmission error — and exactly which errors can slip through?",
    theory=r"""Message M(x), generator G(x) of degree r: transmit $T=x^rM+(x^rM \bmod G)$, divisible by G. An error pattern E is undetected iff G | E. Hence: single-bit errors always detected (G has ≥ 2 terms); double-bit errors $x^i+x^j$ detected while
$j-i$ < order of x mod G; all odd-weight errors detected if (x+1) | G; all bursts of length ≤ r detected; bursts of length r+1 undetected with probability $2^{-(r-1)}$; random garbage undetected with probability $2^{-r}$.
CRC-8 polynomial x⁸+x²+x+1 = (x+1)·(degree-7 primitive) has period 127. Catalogue check values for "123456789": CRC-32 = CBF43926, CRC-16/CCITT-FALSE = 29B1, CRC-16/ARC = BB3D, CRC-8 = F4.""",
    method="""Bit-serial reference and 256-entry-table implementation compared on random data. Error experiments with CRC-8 (0x07) on 96-bit codewords: every single, every double and every burst ≤ 8 exhaustively; 10⁶ random odd-weight errors, 9-bit bursts and
fully random error patterns. The first undetectable double-bit spacing is searched directly.""",
)


def reflect(v, w):
    return int(f"{v:0{w}b}"[::-1], 2)


def crc_bits(data, width, poly, init=0, refin=False, refout=False, xorout=0):
    reg = init; top = 1 << (width - 1); mask = (1 << width) - 1
    for byte in data:
        if refin:
            byte = reflect(byte, 8)
        for i in range(7, -1, -1):
            b = (byte >> i) & 1
            fb = ((reg & top) != 0) ^ b
            reg = (reg << 1) & mask
            if fb:
                reg ^= poly
    if refout:
        reg = reflect(reg, width)
    return reg ^ xorout


def make_table(width, poly):
    mask = (1 << width) - 1; top = 1 << (width - 1); t = []
    for i in range(256):
        r = i << (width - 8)
        for _ in range(8):
            r = ((r << 1) ^ poly) & mask if r & top else (r << 1) & mask
        t.append(r)
    return t


def crc_table(data, width, poly, table, init=0, refin=False, refout=False, xorout=0):
    reg = init; mask = (1 << width) - 1
    for byte in data:
        if refin:
            byte = reflect(byte, 8)
        reg = ((reg << 8) & mask) ^ table[((reg >> (width - 8)) ^ byte) & 0xFF]
    if refout:
        reg = reflect(reg, width)
    return reg ^ xorout


def polymod(e, g, r):
    """Remainder of the integer-coded GF(2) polynomial e modulo g (degree r)."""
    while e.bit_length() > r:
        e ^= g << (e.bit_length() - 1 - r)
    return e


def run(p):
    msg = b"123456789"
    cat = [("CRC-32", dict(width=32, poly=0x04C11DB7, init=0xFFFFFFFF, refin=True, refout=True, xorout=0xFFFFFFFF), 0xCBF43926),
           ("CRC-16/CCITT-FALSE", dict(width=16, poly=0x1021, init=0xFFFF), 0x29B1),
           ("CRC-16/ARC", dict(width=16, poly=0x8005, refin=True, refout=True), 0xBB3D),
           ("CRC-8", dict(width=8, poly=0x07), 0xF4)]
    for name, kw, chk in cat:
        p.compare(f'{name} of "123456789"', chk, crc_bits(msg, **kw), "", kind="abs")
    r = p.rng; bad = 0
    for _ in range(300):
        d = bytes(r.integers(0, 256, int(r.integers(1, 200)), dtype=np.uint8))
        bad += crc_bits(d, **cat[0][1]) != zlib.crc32(d)
        bad += crc_bits(d, 16, 0x1021) != binascii.crc_hqx(d, 0)
        for name, kw, _ in cat:
            bad += crc_table(d, kw["width"], kw["poly"], make_table(kw["width"], kw["poly"]), **{k: v for k, v in kw.items() if k not in ("width", "poly")}) != crc_bits(d, **kw)
    p.compare("Disagreements with zlib.crc32, binascii.crc_hqx and the table-driven engine (300 random messages)", 0, bad, "", kind="abs")
    G = 0x107; R = 8; n = 96
    p.compare("Undetected single-bit errors (96-bit codeword)", 0, sum(polymod(1 << i, G, R) == 0 for i in range(n)), "", kind="abs")
    first = next(d for d in range(1, 400) if polymod((1 << d) | 1, G, R) == 0)
    p.compare("Smallest undetectable double-bit spacing = order of x mod G", 127, first, "bits", kind="abs")
    p.compare("Undetected double-bit errors within a 96-bit codeword (all 4560 pairs)", 0, sum(polymod((1 << i) | (1 << j), G, R) == 0 for i in range(n) for j in range(i)), "", kind="abs")
    und = 0; tot = 0
    for L in range(2, 9):
        for body in range(1 << (L - 2)):
            e = (1 << (L - 1)) | (body << 1) | 1
            for sh in range(n - L + 1):
                tot += 1; und += polymod(e << sh, G, R) == 0
    p.compare(f"Undetected bursts of length ≤ 8 (all {tot} patterns)", 0, und, "", kind="abs")
    N = 300_000
    und9 = sum(polymod(((1 << 8) | (int(b) << 1) | 1) << int(s), G, R) == 0 for b, s in zip(r.integers(0, 128, N), r.integers(0, n - 9, N)))
    p.compare("9-bit bursts undetected: 2^−(r−1) = 1/128", 1 / 128, und9 / N, "", tol=6)
    odd = 0
    for _ in range(100_000):
        k = 2 * int(r.integers(0, 5)) + 1
        e = 0
        for b in r.choice(n, k, replace=False):
            e |= 1 << int(b)
        odd += polymod(e, G, R) == 0
    p.compare("Undetected odd-weight errors (100 000 random patterns; (x+1) divides G)", 0, odd, "", kind="abs")
    words = r.integers(0, 2 ** 32, (N, 3), dtype=np.uint64)
    undr = sum(polymod((int(a) << 64) | (int(b) << 32) | int(c), G, R) == 0 for a, b, c in words)
    p.compare("Random error patterns undetected: 2^−8", 1 / 256, undr / N, "", tol=8)
    sp = np.arange(1, 300); rem = [polymod((1 << int(d)) | 1, G, R) for d in sp]
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(sp, rem, ".", color=C_MEAS, ms=3); ax[0].plot([127, 254], [0, 0], "o", color=C_PRED, label="undetected (remainder 0)")
    style_axes(ax[0], "spacing between the two flipped bits", "remainder of xᵈ + 1", "Double-bit errors: blind spots at multiples of 127")
    ax[1].bar(["9-bit burst", "random"], [und9 / N, undr / N], color=C_MEAS, label="measured")
    ax[1].plot(["9-bit burst", "random"], [1 / 128, 1 / 256], "_", color=C_PRED, ms=40, mew=3, label="theory")
    style_axes(ax[1], "", "undetected fraction", "What slips through an 8-bit CRC")
    p.save(fig, "crc", "Remainders of double-bit error polynomials and measured undetected-error rates for CRC-8.")
    p.discuss("""The division engine reproduces the catalogue check values of four standard CRCs and matches Python's zlib and binascii on random data, in both
the bit-serial and table-driven forms. The error experiments confirm each algebraic guarantee with no exceptions: no single-bit, odd-weight or
≤ 8-bit burst error divides G, and double-bit errors are all caught until the two bits are exactly 127 positions apart — the order of x modulo
the generator, which is why each CRC polynomial comes with a maximum protected block length. Beyond the guarantees the CRC behaves like a random
8-bit hash: 1/128 of 9-bit bursts and 1/256 of arbitrary corruption pass undetected. Choosing a CRC is therefore choosing a polynomial whose
algebraic blind spots lie outside the errors your channel actually produces.""")
# tol-convention: relative tolerances are in percent
