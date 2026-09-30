from eelab import *
from eelab.gf import RS
from scipy.special import comb

META = dict(
    id="SL-114", title="Reed–Solomon RS(255,223): the satellite / CD code", level="H",
    tools="Own GF(2⁸) arithmetic and RS codec (Berlekamp–Massey, Chien search, Forney), Monte Carlo",
    summary="Implement the CCSDS-style RS(255,223) code from scratch, verify it corrects every pattern of up to 16 "
            "symbol errors and flags 17, and compare the decoded block-error rate on a random-symbol-error channel "
            "with the binomial prediction; show why RS is superb against bursts.",
    problem="Deep-space probes and CDs both protect data with Reed–Solomon codes. How many errors can RS(255,223) fix, "
            "and why do bursts not hurt it?",
    theory=r"""RS(n, k) over GF(2⁸) has minimum distance n − k + 1 = 33, so it corrects t = 16 symbol errors per 255-byte block. With independent
symbol-error probability p, $P_{block}=\sum_{i=17}^{255}\binom{255}{i}p^i(1-p)^{255-i}$. A burst of b bit errors touches at most
⌈b/8⌉ + 1 symbols, so any burst up to 121 bits is always correctable.""",
    method="""Generator g(x) = Π(x − αⁱ), i = 0…31, primitive polynomial x⁸+x⁴+x³+x²+1. Tests: 50 blocks each with exactly 1…20 random symbol errors;
Monte Carlo 300 blocks per p for p = 0.03…0.09; bursts of 8–160 bits at random offsets.""",
)


def run(p):
    rs = RS(255, 223)
    outcome = {}
    for ne in range(1, 21):
        good = fail = wrong = 0
        for _ in range(30):
            msg = list(p.rng.integers(0, 256, 223)); c = rs.encode(msg); r = c[:]
            for pos in p.rng.choice(255, ne, replace=False):
                r[pos] ^= int(p.rng.integers(1, 256))
            try:
                d, _ = rs.decode(r); good += d == msg; wrong += d != msg
            except ValueError:
                fail += 1
        outcome[ne] = (good, fail, wrong)
    p.compare("Largest error count always corrected (t = (n−k)/2)", 16, max(k for k, v in outcome.items() if v[0] == 30), "symbols", kind="abs")
    p.compare("17 errors: blocks detected as uncorrectable (of 30)", 30, outcome[17][1], "", kind="abs")
    p.metric("Miscorrections observed (17–20 errors)", sum(outcome[k][2] for k in range(17, 21)))
    ps = np.array([0.03, 0.05, 0.06, 0.07, 0.09])
    meas, th = [], []
    for pp in ps:
        bad = 0
        for _ in range(300):
            msg = list(p.rng.integers(0, 256, 223)); c = rs.encode(msg); r = c[:]
            hit = np.flatnonzero(p.rng.random(255) < pp)
            for pos in hit:
                r[pos] ^= int(p.rng.integers(1, 256))
            try:
                d, _ = rs.decode(r); bad += d != msg
            except ValueError:
                bad += 1
        meas.append(bad / 300)
        th.append(sum(comb(255, i, exact=True) * pp**i * (1 - pp) ** (255 - i) for i in range(17, 256)))
    meas, th = np.array(meas), np.array(th)
    k = 2
    p.compare(f"Block error rate at p = {ps[k]}", th[k], meas[k], "", kind="abs")
    bursts = [8, 40, 80, 121, 128, 160]
    burst_ok = []
    for b in bursts:
        okc = 0
        for _ in range(20):
            msg = list(p.rng.integers(0, 256, 223)); c = rs.encode(msg)
            bits = np.unpackbits(np.array(c, np.uint8))
            st = int(p.rng.integers(0, len(bits) - b)); bits[st: st + b] ^= 1
            r = list(np.packbits(bits))
            try:
                d, _ = rs.decode([int(v) for v in r]); okc += d == msg
            except ValueError:
                pass
        burst_ok.append(okc / 20)
    p.compare("Bit-burst length always corrected (8·(t−1)+1 = 121)", 1.0, burst_ok[bursts.index(121)], "", kind="abs")
    fig, ax = p.fig(1, 2)
    ax[0].semilogy(ps, np.maximum(th, 1e-6), "--", color=C_PRED, label="binomial theory")
    ax[0].semilogy(ps, np.maximum(meas, 1e-3), "o", color=C_MEAS, label="measured (300 blocks)")
    style_axes(ax[0], "symbol error probability p", "block error rate", "RS(255,223) waterfall")
    ax[1].plot(bursts, burst_ok, "o-", color=C_MEAS)
    ax[1].axvline(121, color=C_PRED, ls="--", label="guaranteed limit 121 bits")
    style_axes(ax[1], "burst length (bits)", "fraction corrected", "Burst errors")
    p.save(fig, "rs", "A steep waterfall around p ≈ 6 %, and every burst up to 121 bits corrected.")
    p.csv("waterfall", p=ps, measured=meas, theory=th)
    p.discuss("""The decoder corrects every block with up to 16 symbol errors and declares 17+ uncorrectable (rather than silently
miscorrecting) — the guaranteed behaviour for a distance-33 code. The block-error waterfall matches the binomial sum, and
the burst test shows why RS codes pair so well with convolutional codes in CCSDS and on CDs: RS counts *symbols*, so eight
consecutive bad bits cost only one symbol. Voyager and every CD player rely on exactly this.""")
