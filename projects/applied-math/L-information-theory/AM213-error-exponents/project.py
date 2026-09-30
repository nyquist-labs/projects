from eelab import *
from eelab.info import h2

META = dict(
    id="AM-213", title="Error exponents: how fast block error falls with code length", level="H",
    tools="Gallager's random-coding exponent E_r(R) and the sphere-packing exponent for the BSC, exhaustive maximum-likelihood decoding of random linear codes of length 8–24, ensemble-average block-error rates, exponent estimated from the slope of log Pₑ versus n",
    summary="Below capacity the error probability of good codes falls exponentially with block length, Pₑ ≈ 2^(−n·E(R)). Compute the exponents from theory, "
            "then generate random linear codes, decode them by brute force and measure how fast their average block error actually falls.",
    problem="Shannon's theorem says error can be made arbitrarily small below capacity. How much longer must a code be to gain another decade?",
    theory=r"""BSC(p), rate R < C = 1 − H₂(p). Random-coding exponent $E_r(R)=\max_{0\leρ\le1}[E_0(ρ)-ρR]$ with $E_0(ρ)=ρ-(1+ρ)\log_2\left(p^{1/(1+ρ)}+(1-p)^{1/(1+ρ)}\right)$; the ensemble-average ML error satisfies $\bar P_e\le2^{-nE_r(R)}$. Sphere packing: no code does better than $2^{-nE_{sp}(R)}$
asymptotically, $E_{sp}(R)=D(δ\|p)$ with $H_2(δ)=1-R$ (in bits), equal to E_r above the critical rate. Finite lengths add polynomial prefactors, so a measured slope approaches the exponent from below only slowly.""",
    method="""BSC with p = 0.03 (C = 0.806). Rate ½ random linear codes (systematic, random parity part), n = 8, 12, 16, 20, 24; for each n, 40 random codes × 3000 transmissions of random messages, ML decoding by exhaustive nearest-codeword search (2^{n/2} codewords, bit-packed).
Exponent from the slope of log₂ Pₑ between n = 12 and 24.""",
)


def E0(rho, p):
    return rho - (1 + rho) * np.log2(p ** (1 / (1 + rho)) + (1 - p) ** (1 / (1 + rho)))


def Er(R, p):
    rhos = np.linspace(0, 1, 2001)
    return float(np.max(E0(rhos, p) - rhos * R))


def Esp(R, p):
    from scipy.optimize import brentq
    d = brentq(lambda x: h2(x) - (1 - R), p + 1e-12, 0.5)
    return float(d * np.log2(d / p) + (1 - d) * np.log2((1 - d) / (1 - p)))


def run(p):
    r = p.rng; pb = 0.03; R = 0.5
    C = 1 - h2(pb); er = Er(R, pb); es = Esp(R, pb)
    p.metric("BSC(0.03): capacity / E_r(½) / E_sp(½)", f"{C:.3f} bit / {er:.4f} / {es:.4f}", "", "exponents in bits per channel use")
    rhos = np.linspace(0, 1, 2001)
    p.compare("E_r at rate 0 equals E₀(1) (the cutoff rate R₀)", E0(1, pb), Er(0.0, pb), "bit", tol=1e-6)
    p.compare("E_r vanishes at capacity", 0.0, Er(C - 1e-6, pb), "bit", kind="abs", tol=1e-5)
    rows = []
    for n in (8, 12, 16, 20, 24):
        k = n // 2; msgs = (np.arange(2 ** k)[:, None] >> np.arange(k)) & 1; errs = 0; tot = 0
        for _ in range(40):
            Pm = r.integers(0, 2, (k, n - k)); G = np.hstack([np.eye(k, dtype=int), Pm]); CW = (msgs @ G) % 2
            cwi = CW @ (1 << np.arange(n))
            m = r.integers(0, 2 ** k, 3000); e = (r.random((3000, n)) < pb).astype(int) @ (1 << np.arange(n))
            rx = cwi[m] ^ e
            pc = np.array([bin(v).count("1") for v in range(1 << 12)])
            def wt(v):
                return pc[v & 4095] + pc[(v >> 12) & 4095]
            for s in range(0, 3000, 500):
                d = wt(rx[s:s + 500, None] ^ cwi[None, :]); dec = np.argmin(d, 1)
                errs += int(np.sum(cwi[dec] != cwi[m[s:s + 500]])); tot += len(dec)
        rows.append((n, errs / tot))
    rr = np.array(rows)
    p.compare("Average block error falls with n at fixed rate (violations of monotonic decrease)", 0, int(np.sum(np.diff(rr[:, 1]) > 0)), "", kind="abs")
    ok = all(rr[i, 1] <= 2 ** (-rr[i, 0] * er) for i in range(len(rr)))
    p.compare("Gallager's random-coding bound 2^(−n·E_r) holds for the measured ensemble average at every n (1 = yes)", 1, int(ok), "", kind="abs")
    slope = -np.polyfit(rr[1:, 0], np.log2(rr[1:, 1]), 1)[0]
    p.compare("Exponent measured from the slope (n = 12…24) vs E_r(½): same order of magnitude (ratio)", 1.0, slope / er, "", tol=60)
    p.metric("Block error rate at n = 8 / 12 / 16 / 20 / 24", " / ".join(f"{v:.2e}" for v in rr[:, 1]), "", f"measured slope {slope:.4f} bit per extra symbol")
    p.metric("Length needed for Pₑ = 10⁻⁶ at rate ½ by the random-coding bound", float(np.log2(1e6) / er), "symbols")
    Rs = np.linspace(0.01, C - 0.001, 200)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(Rs, [Er(x, pb) for x in Rs], color=C_MEAS, label="random coding E_r(R)"); ax[0].plot(Rs[Rs > 0.3], [Esp(x, pb) for x in Rs[Rs > 0.3]], "--", color=C_PRED, label="sphere packing E_sp(R)")
    ax[0].axvline(C, color="gray", ls=":", label="capacity")
    style_axes(ax[0], "rate R (bit/use)", "exponent (bit/use)", "BSC(0.03) error exponents")
    nn = np.arange(6, 30); ax[1].semilogy(rr[:, 0], rr[:, 1], "o-", color=C_MEAS, label="random linear codes, ML decoding"); ax[1].semilogy(nn, 2.0 ** (-nn * er), "--", color=C_PRED, label="2^(−n·E_r) bound")
    style_axes(ax[1], "block length n", "average block error", "Rate ½ on BSC(0.03)")
    p.save(fig, "error_exponents", "Error exponents of the BSC and the block error of random rate-½ codes versus length.")
    p.discuss(f"""Random linear codes decoded by exhaustive maximum likelihood behave as Gallager's theory says: their average block error falls steadily with
length and stays below the random-coding bound 2^(−n·E_r) at every length tested. The measured decay rate, {slope:.4f} bits of exponent per symbol between
n = 12 and 24, is of the same order as E_r(½) = {er:.4f}; at such short lengths the polynomial prefactors still bend the curve, so the asymptotic slope is only
approached, not reached. The exponent answers the practical question: halving the error rate costs about {1 / er:.0f} more symbols at this rate and
channel, and 10⁻⁶ needs of the order of {np.log2(1e6) / er:.0f} — which is why powerful codes are long, and why the exponent, not just capacity, sets latency.""")
# tol-convention: relative tolerances are in percent
