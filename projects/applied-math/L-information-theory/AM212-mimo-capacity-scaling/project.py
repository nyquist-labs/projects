from eelab import *

META = dict(
    id="AM-212", title="MIMO capacity scaling: why more antennas mean more bits", level="H",
    tools="Monte-Carlo ergodic capacity log₂det(I + (SNR/N_t)HHᴴ) of i.i.d. Rayleigh channels, high-SNR slope (multiplexing gain), large-system limit from the Marchenko–Pastur law, outage capacity and diversity, water-filling with channel knowledge, rank-deficient (keyhole-like) channels",
    summary="Measure how the capacity of multi-antenna links grows with the number of antennas and with SNR: slope min(N_t, N_r) per 3 dB, linear growth "
            "with antenna count predicted by random-matrix theory, the reliability gain seen in outage, and the collapse when the propagation offers only one path.",
    problem="Adding antennas at both ends of a radio link multiplies its capacity — under what conditions, and by how much?",
    theory=r"""Without channel knowledge at the transmitter $C=\log_2\det(I+\frac{ρ}{N_t}HH^H)$. At high SNR $C≈\min(N_t,N_r)\log_2ρ+$const: each doubling of SNR adds min(N_t, N_r) bits. For N_t = N_r = n → ∞ with i.i.d. entries, C/n converges to a deterministic limit given by the
Marchenko–Pastur eigenvalue law: $\frac Cn=2\log_2\left(1+ρ-\tfrac14F\right)-\frac{\log_2e}{4ρ}F$, $F=\left(\sqrt{4ρ+1}-1\right)^2$. Diversity: the 1 % outage capacity improves sharply with more antennas. A rank-1 channel (a single scatterer path) gives only $\log_2(1+ρ\,λ)$ — no multiplexing.""",
    method="""10 000 channel draws per point. n × n systems for n = 1…16 at 10 dB; slopes between 20 and 30 dB for 2×2, 4×4, 2×4; 1 % outage for 1×1, 2×2, 4×4; rank-one channel H = a bᴴ with Gaussian vectors.""",
)


def cap(H, rho):
    nt = H.shape[-1]; M = np.eye(H.shape[-2]) + rho / nt * H @ np.conj(np.swapaxes(H, -1, -2))
    return np.real(np.linalg.slogdet(M)[1]) / np.log(2)


def rayleigh(r, n, nr, nt):
    return (r.normal(size=(n, nr, nt)) + 1j * r.normal(size=(n, nr, nt))) / np.sqrt(2)


def mp_limit(rho):
    F = (np.sqrt(4 * rho + 1) - 1) ** 2
    return 2 * np.log2(1 + rho - F / 4) - np.log2(np.e) * F / (4 * rho)


def run(p):
    r = p.rng; N = 10000
    for (nr, nt) in ((2, 2), (4, 4), (4, 2)):
        H = rayleigh(r, N, nr, nt); c20 = cap(H, 100).mean(); c30 = cap(H, 1000).mean()
        p.compare(f"{nr}×{nt}: bits gained per 3 dB at high SNR = min(N_t, N_r)", min(nr, nt), (c30 - c20) / (10 / 3.0103), "bit", tol=5)
    rho = 10.0; ns = [1, 2, 4, 8, 16]; cn = [cap(rayleigh(r, 4000, n, n), rho).mean() / n for n in ns]
    p.compare("Large-system limit: C/n for 16×16 at 10 dB vs the Marchenko–Pastur formula", mp_limit(rho), cn[-1], "bit", tol=1)
    p.metric("Capacity per antenna pair at 10 dB, n = 1 / 2 / 4 / 8 / 16", " / ".join(f"{v:.2f}" for v in cn), "bit/s/Hz", f"limit {mp_limit(rho):.2f} — capacity grows linearly with n")
    out = {}
    for n in (1, 2, 4):
        c = cap(rayleigh(r, N, n, n), rho); out[n] = (np.percentile(c, 1), c.mean())
    p.compare("1 % outage capacity: 1×1 is far below its mean (deep fades), 4×4 close to its mean (diversity; ratio outage/mean > 0.7; 1 = yes)", 1, int(out[4][0] / out[4][1] > 0.7 and out[1][0] / out[1][1] < 0.1), "", kind="abs")
    p.metric("1 % outage / mean capacity at 10 dB: 1×1, 2×2, 4×4", " ; ".join(f"{out[n][0]:.2f} / {out[n][1]:.2f}" for n in (1, 2, 4)), "bit/s/Hz")
    a = (r.normal(size=(N, 4, 1)) + 1j * r.normal(size=(N, 4, 1))) / np.sqrt(2); b = (r.normal(size=(N, 1, 4)) + 1j * r.normal(size=(N, 1, 4))) / np.sqrt(2)
    Hk = a @ b / 1.0; ck = cap(Hk, 1000).mean() - cap(Hk, 100).mean()
    p.compare("Rank-one (keyhole) 4×4 channel: bits per 3 dB at high SNR = 1 (no multiplexing)", 1.0, ck / (10 / 3.0103), "bit", tol=5)
    H = rayleigh(r, 2000, 4, 4); gains = []
    for s_db in (-5, 20):
        rho_ = 10 ** (s_db / 10); cw = []
        for Hi in H:
            lam = np.linalg.eigvalsh(Hi @ Hi.conj().T); fl = 1 / np.maximum(lam, 1e-12); lo, hi = 0, fl.min() + rho_ + 1
            for _ in range(60):
                mu = (lo + hi) / 2; (lo, hi) = (mu, hi) if np.sum(np.maximum(mu - fl, 0)) < rho_ else (lo, mu)
            cw.append(np.sum(np.log2(1 + lam * np.maximum(mu - fl, 0))))
        gains.append(np.mean(cw) / cap(H, rho_).mean())
    p.metric("Gain from channel knowledge at the transmitter (water-filling over eigenmodes), −5 dB / 20 dB", f"{(gains[0] - 1) * 100:.0f} % / {(gains[1] - 1) * 100:.1f} %", "", "large at low SNR, negligible at high SNR (compare AM-211)")
    snrs = np.arange(-5, 31, 2.5)
    fig, ax = p.fig(1, 2, w=11)
    for (nr, nt), c in zip(((1, 1), (2, 2), (4, 4), (8, 8)), COLORS):
        Hs = rayleigh(r, 1500, nr, nt); ax[0].plot(snrs, [cap(Hs, 10 ** (s / 10)).mean() for s in snrs], color=c, label=f"{nr}×{nt}")
    ax[0].plot(snrs, [cap(a[:1500] @ b[:1500], 10 ** (s / 10)).mean() for s in snrs], "k--", label="4×4 keyhole")
    style_axes(ax[0], "SNR (dB)", "ergodic capacity (bit/s/Hz)", "Slope = number of spatial streams")
    ax[1].plot(ns, np.array(cn) * np.array(ns), "o-", color=C_MEAS, label="Monte Carlo"); ax[1].plot(ns, mp_limit(rho) * np.array(ns), "--", color=C_PRED, label="n × Marchenko–Pastur limit")
    style_axes(ax[1], "antennas per side n", "capacity at 10 dB (bit/s/Hz)", "Linear growth with antenna count")
    p.save(fig, "mimo", "Ergodic capacity of MIMO channels versus SNR and versus antenna count, with a rank-one channel for contrast.")
    p.discuss(f"""The measured slopes confirm the multiplexing law: each 3 dB adds two bits for 2×2 and four for 4×4, and a 4×2 link is limited by its two transmit
antennas. Capacity per antenna pair converges to the Marchenko–Pastur prediction ({mp_limit(rho):.2f} bit/s/Hz at 10 dB), so capacity grows *linearly* with the
number of antennas instead of logarithmically with power. Multiple antennas also buy reliability: the 1 % outage capacity of a single link is almost
zero because of deep fades, while for 4×4 it is {out[4][0] / out[4][1] * 100:.0f} % of the mean. All of this depends on rich scattering: in a keyhole channel with a single
propagation path, four antennas at each end give one stream (one bit per 3 dB). Knowing the channel at the transmitter matters at low SNR
(+{(gains[0] - 1) * 100:.0f} %) and hardly at high SNR.""")
# tol-convention: relative tolerances are in percent
