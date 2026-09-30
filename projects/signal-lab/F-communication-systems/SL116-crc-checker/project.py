from eelab import *

META = dict(
    id="SL-116", title="CRC-32: what it catches and what it misses", level="M",
    tools="Own bitwise/table CRC-32 (IEEE 802.3), zlib cross-check, exhaustive and random error injection",
    summary="Implement CRC-32 two ways, check against zlib, then measure detection of 1-, 2-, 3-bit and burst errors in "
            "Ethernet-sized frames — and compare with a weak 8-bit additive checksum and CRC-8, where missed errors "
            "are frequent enough to count.",
    problem="Every Ethernet frame carries a 32-bit CRC. Which errors is it guaranteed to catch, and how often does a "
            "random corruption slip through?",
    theory=r"""A CRC with generator of degree r detects all bursts ≤ r bits, all odd-weight errors if (x+1) divides g(x), and for random
corruption misses a fraction ≈ $2^{-r}$. CRC-32 (0x04C11DB7) has Hamming distance 4 up to frames of 91,607 bits, so every 1-, 2- and
3-bit error in a 1,500-byte frame is caught; random garbage passes with probability 2⁻³² ≈ 2.3×10⁻¹⁰. For CRC-8 the miss rate
≈ 2⁻⁸ = 0.39 % is measurable.""",
    method="""1,500-byte random frames. Exhaustive-ish: 20,000 random single, double and triple bit flips; bursts of 2–32 bits. CRC-8 (0x07) and an
8-bit sum checksum on random multi-byte corruption (50,000 trials) to measure miss rates.""",
)

POLY = 0xEDB88320
TABLE = []
for i in range(256):
    c = i
    for _ in range(8):
        c = (c >> 1) ^ POLY if c & 1 else c >> 1
    TABLE.append(c)


def crc32_bitwise(data):
    c = 0xFFFFFFFF
    for byte in data:
        c ^= byte
        for _ in range(8):
            c = (c >> 1) ^ POLY if c & 1 else c >> 1
    return c ^ 0xFFFFFFFF


def crc32_table(data):
    c = 0xFFFFFFFF
    for byte in data:
        c = TABLE[(c ^ byte) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF


def crc8(data):
    c = 0
    for byte in data:
        c ^= byte
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c


def run(p):
    import zlib
    frame = bytes(p.rng.integers(0, 256, 1500, dtype=np.uint8))
    p.compare("Bitwise CRC-32 = zlib.crc32", zlib.crc32(frame), crc32_bitwise(frame), "", kind="abs")
    p.compare("Table CRC-32 = zlib.crc32", zlib.crc32(frame), crc32_table(frame), "", kind="abs")
    ref = zlib.crc32(frame)
    arr = np.frombuffer(frame, np.uint8)
    res = {}
    for nbits in (1, 2, 3):
        missed = 0
        for _ in range(20000 if nbits > 1 else 12000):
            a = arr.copy()
            for pos in p.rng.choice(12000, nbits, replace=False):
                a[pos // 8] ^= 1 << (pos % 8)
            missed += zlib.crc32(a.tobytes()) == ref
        res[nbits] = missed
        p.compare(f"{nbits}-bit errors missed by CRC-32", 0, missed, "", kind="abs")
    bm = 0
    for b in range(2, 33):
        for _ in range(300):
            bits = np.unpackbits(arr); st = int(p.rng.integers(0, len(bits) - b))
            bits[st] ^= 1; bits[st + b - 1] ^= 1
            bits[st + 1: st + b - 1] ^= p.rng.integers(0, 2, b - 2).astype(np.uint8)
            bm += zlib.crc32(np.packbits(bits).tobytes()) == ref
    p.compare("Bursts of 2–32 bits missed by CRC-32 (9,300 trials)", 0, bm, "", kind="abs")
    small = bytes(p.rng.integers(0, 256, 64, dtype=np.uint8)); s8 = crc8(small); ssum = sum(small) & 0xFF
    a0 = np.frombuffer(small, np.uint8)
    miss8 = misssum = 0
    T = 50000
    for _ in range(T):
        a = a0.copy(); k = int(p.rng.integers(2, 9))
        idx = p.rng.choice(64, k, replace=False); a[idx] = p.rng.integers(0, 256, k, dtype=np.uint8)
        if np.array_equal(a, a0):
            continue
        miss8 += crc8(a.tobytes()) == s8; misssum += (int(a.sum()) & 0xFF) == ssum
    p.compare("CRC-8 miss rate on random multi-byte corruption (2⁻⁸)", 2**-8, miss8 / T, "", tol=20)
    p.compare("8-bit sum checksum miss rate (also ≈ 2⁻⁸ for random data)", 2**-8, misssum / T, "", tol=20)
    fig, ax = p.fig()
    ax.bar(["CRC-8", "8-bit sum"], [miss8 / T * 100, misssum / T * 100], color=[C_MEAS, COLORS[1]])
    ax.axhline(100 * 2**-8, color=C_PRED, ls="--", label="2⁻⁸ = 0.39 %")
    style_axes(ax, None, "undetected corruptions (%)", "Random corruption: 8-bit checks miss ~1 in 256")
    p.save(fig, "miss_rates", "For random garbage every 8-bit check misses ~2⁻⁸; the CRC's advantage is its guarantees for structured errors.")
    p.discuss("""Both CRC-32 implementations match zlib bit-for-bit, and not a single 1-, 2- or 3-bit error or burst ≤ 32 bits escaped
detection, exactly as CRC theory guarantees. The 8-bit comparison makes the other half of the story measurable: for
*random* corruption any r-bit check misses ≈ 2⁻ʳ, so the CRC is no better than a simple sum there. The CRC earns its keep
on the error patterns real channels actually produce — few-bit errors and bursts — where the additive checksum has blind
spots (e.g. two compensating byte changes) and the CRC has none.""")
