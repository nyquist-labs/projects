from eelab import *
from scipy.special import erfc, comb

META = dict(
    id="SL-113", title="Hamming (7,4) code: encode, corrupt, correct", level="M",
    tools="NumPy matrix encoder/syndrome decoder over GF(2), Monte Carlo on a binary symmetric channel",
    summary="Implement the (7,4) Hamming code with generator and parity-check matrices, verify it corrects every "
            "single-bit error, and compare block and bit error rates with the binomial prediction on a BSC.",
    problem="How can three parity bits locate and fix any single flipped bit in a 7-bit word?",
    theory=r"""Parity-check matrix H has the binary numbers 1…7 as columns, so a single error at position i gives syndrome = i. Block
error after decoding (BSC, crossover p): $P_{block}=1-(1-p)^7-7p(1-p)^6\approx21p^2$. Code rate 4/7.""",
    method="""G and H in systematic form; all 7 single-error patterns tested exhaustively; Monte Carlo 10⁶ blocks for p from 10⁻³ to 10⁻¹.""",
)


def run(p):
    Pm = np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]])
    G = np.hstack([np.eye(4, dtype=int), Pm])
    H = np.hstack([Pm.T, np.eye(3, dtype=int)])
    p.compare("G·Hᵀ = 0 (valid code)", 0, np.sum((G @ H.T) % 2), "", kind="abs")
    syn_table = {tuple(H[:, i]): i for i in range(7)}
    ok = 0
    for m in range(16):
        msg = np.array([(m >> k) & 1 for k in range(4)])
        c = msg @ G % 2
        for i in range(7):
            r = c.copy(); r[i] ^= 1
            s = tuple(H @ r % 2); r[syn_table[s]] ^= 1
            ok += np.array_equal(r[:4], msg)
    p.compare("Single-error patterns corrected (16 messages × 7 positions)", 112, ok, "", kind="abs")
    ps = np.logspace(-3, -1, 7)
    blk, bit = [], []
    for pp in ps:
        n = 10**6
        msg = p.rng.integers(0, 2, (n, 4))
        c = msg @ G % 2
        e = (p.rng.random((n, 7)) < pp).astype(int)
        r = (c + e) % 2
        s = r @ H.T % 2
        idx = s @ np.array([4, 2, 1])
        col = {int(np.array(H[:, i]) @ np.array([4, 2, 1])): i for i in range(7)}
        fix = np.array([col.get(v, -1) for v in range(8)])
        pos = fix[idx]
        rr = r.copy(); rows = np.flatnonzero(pos >= 0); rr[rows, pos[rows]] ^= 1
        blk.append(np.mean(np.any(rr[:, :4] != msg, axis=1))); bit.append(np.mean(rr[:, :4] != msg))
    blk = np.array(blk)
    th = 1 - (1 - ps) ** 7 - 7 * ps * (1 - ps) ** 6
    k = 3
    p.compare(f"Block error rate after decoding, p = {ps[k]:.3g}", th[k], blk[k], "", tol=10)
    p.compare("Block error rate at p = 0.01 vs 21p² approximation", 21 * 0.01**2, np.interp(0.01, ps, blk), "", tol=15)
    fig, ax = p.fig()
    ax.loglog(ps, ps, ":", color="gray", label="uncoded bit error = p")
    ax.loglog(ps, th, "--", color=C_PRED, label="block error theory")
    ax.loglog(ps, blk, "o", color=C_MEAS, label="block error (sim)")
    ax.loglog(ps, bit, "s", color=COLORS[2], ms=4, label="decoded bit error (sim)")
    style_axes(ax, "channel crossover probability p", "error rate", "Hamming (7,4) on a binary symmetric channel")
    p.save(fig, "hamming", "Errors fall from p to ~p²: the code trades 3/7 of the rate for quadratic error suppression.")
    p.section("Matrices", "G =\n```\n" + "\n".join(" ".join(map(str, r)) for r in G) + "\n```\nH =\n```\n" + "\n".join(" ".join(map(str, r)) for r in H) + "\n```")
    p.discuss("""All 112 single-error cases decode correctly, and block errors follow the binomial prediction (≈ 21p²) — the slope-2 line on
the log-log plot is the signature of a code with minimum distance 3. Whether this is a *gain* depends on the channel: the
extra 3 bits cost 10·log(7/4) = 2.4 dB of energy per information bit, so on AWGN the Hamming code helps only at moderate
SNR, which is why modern systems use longer codes (Reed–Solomon, LDPC).""")
