from eelab import *
from scipy.special import logsumexp

META = dict(
    id="AM-210", title="AWGN capacity and what real constellations can achieve", level="H",
    tools="Shannon capacity ½log₂(1 + SNR) per real dimension, Monte-Carlo mutual information of BPSK, 4-PAM, 8-PAM and 16-QAM inputs with Gaussian noise, the ultimate −1.59 dB limit in E_b/N₀, the 1.53 dB shaping gap at high SNR, required SNR for a target spectral efficiency",
    summary="Compute the capacity of the Gaussian channel and the information rates actually available with the finite, equally likely constellations used "
            "by modems, locate where each constellation stops being useful, and measure the two classic gaps — −1.59 dB at zero rate and 1.53 dB of shaping loss at high rate.",
    problem="Shannon's formula promises log₂(1 + SNR) bits. How much of it can a modem with a fixed constellation actually carry?",
    theory=r"""Real channel: $C=\tfrac12\log_2(1+\mathrm{SNR})$ bits per dimension, achieved by Gaussian inputs. With a discrete equiprobable constellation $\{a_i\}$, $I=\log_2M-E\left[\log_2\sum_j\exp\left(-\frac{(a_j-a_i)^2+2(a_j-a_i)n}{2σ^2}\right)\right]$. In energy per bit, reliable communication needs
$E_b/N_0\ge\frac{2^{2R}-1}{2R}$ (per real dimension), which tends to ln 2 = −1.59 dB as R → 0. At high SNR a uniform (square) constellation needs πe/6 = 1.53 dB more SNR than a Gaussian input for the same rate (shaping loss). 16-QAM = two independent 4-PAM.""",
    method="""Monte-Carlo expectation with 2×10⁵ noise samples per point, SNR −10 … 40 dB. Constellation-constrained Shannon limits: bisection on SNR for a target rate. Shaping gap: SNR needed for a given rate by an 8-PAM-like dense PAM (M = 64) vs Gaussian input at 4 bits/dimension.""",
)


def pam_mi(M, snr_db, n, rng):
    a = np.arange(M) * 2.0 - (M - 1); a /= np.sqrt(np.mean(a ** 2)); s2 = 10 ** (-snr_db / 10)
    i = rng.integers(0, M, n); z = rng.normal(0, np.sqrt(s2), n)
    d = a[None, :] - a[i][:, None]
    return np.log2(M) - np.mean(logsumexp(-(d ** 2 + 2 * d * z[:, None]) / (2 * s2), axis=1)) / np.log(2)


def run(p):
    r = p.rng; n = 200000
    snrs = np.arange(-10, 41, 2.0); C = 0.5 * np.log2(1 + 10 ** (snrs / 10))
    curves = {M: np.array([pam_mi(M, s, n if s < 25 else 50000, r) for s in snrs]) for M in (2, 4, 8)}
    p.compare("Every constellation rate stays below the Shannon capacity (violations beyond Monte-Carlo noise)", 0, int(sum(np.sum(v > C + 0.01) for v in curves.values())), "", kind="abs")
    p.compare("BPSK at high SNR saturates at log₂2 = 1 bit/dimension", 1.0, curves[2][-1], "bit", tol=0.1)
    p.compare("8-PAM at high SNR saturates at 3 bits/dimension", 3.0, curves[8][-1], "bit", tol=0.5)
    ebno = lambda R: (2 ** (2 * R) - 1) / (2 * R)
    p.compare("Ultimate limit: minimum E_b/N₀ as R → 0 is ln 2", 10 * np.log10(np.log(2)), 10 * np.log10(ebno(1e-6)), "dB", kind="abs", tol=0.01)
    from scipy.optimize import brentq
    snr_bpsk_half = brentq(lambda s: pam_mi(2, s, 400000, np.random.default_rng(1)) - 0.5, -10, 10)
    eb = snr_bpsk_half - 10 * np.log10(2 * 0.5)
    p.compare("BPSK at rate ½: minimum E_b/N₀ (known value 0.19 dB) from the constellation-constrained mutual information", 0.187, eb, "dB", kind="abs", tol=0.05)
    p.metric("Same rate with Gaussian inputs: minimum E_b/N₀", 10 * np.log10(ebno(0.5)), "dB", "restricting to ±1 costs about 0.2 dB at rate ½")
    gaps = {}
    for R in (2.0, 4.0, 6.0):
        snr_g = 10 * np.log10(2 ** (2 * R) - 1); M = int(2 ** (R + 2)); nn = 60000 if M <= 64 else 12000
        snr_pam = brentq(lambda s: pam_mi(M, s, nn, np.random.default_rng(2)) - R, snr_g, snr_g + 4); gaps[R] = snr_pam - snr_g
    p.compare("Shaping gap at 6 bits/dimension: extra SNR a uniform 256-PAM needs over a Gaussian input (asymptotically πe/6 = 1.53 dB)", 1.53, gaps[6.0], "dB", kind="abs", tol=0.15)
    p.metric("Shaping gap at 2 / 4 / 6 bits per dimension", " / ".join(f"{gaps[k]:.2f} dB" for k in (2.0, 4.0, 6.0)), "", "it approaches 1.53 dB only at high rate; my first check at 4 bits expected the asymptote and found 1.3 dB")
    q16 = 2 * np.interp(20, snrs, curves[4])
    p.metric("16-QAM (two 4-PAM) at 20 dB SNR: mutual information / 2-D capacity", f"{q16:.3f} / {2 * np.interp(20, snrs, C):.3f} bit per symbol")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(snrs, C, "k-", lw=2, label="capacity ½log₂(1+SNR)")
    for M, c in zip((2, 4, 8), (C_MEAS, C_PRED, COLORS[2])):
        ax[0].plot(snrs, curves[M], color=c, label=f"{M}-PAM")
    style_axes(ax[0], "SNR (dB)", "bits per dimension", "Constellation-constrained rates")
    Rs = np.linspace(0.01, 4, 200); ax[1].plot(10 * np.log10(ebno(Rs)), Rs, "k-", label="Shannon limit")
    ax[1].axvline(10 * np.log10(np.log(2)), color="gray", ls=":", label="−1.59 dB")
    for M, c in zip((2, 4, 8), (C_MEAS, C_PRED, COLORS[2])):
        ok = curves[M] > 0.02; ax[1].plot(snrs[ok] - 10 * np.log10(2 * curves[M][ok]), curves[M][ok], color=c, label=f"{M}-PAM")
    ax[1].set_xlim(-3, 25)
    style_axes(ax[1], "E_b/N₀ (dB)", "rate (bits per dimension)", "Energy per bit needed")
    p.save(fig, "awgn_capacity", "Mutual information of PAM constellations against the Gaussian-channel capacity, in SNR and in energy per bit.")
    p.discuss(f"""Every finite constellation tracks the Shannon curve at low SNR and then saturates at log₂M bits, so the choice of constellation is a choice of
operating range: BPSK is nearly optimal below 0 dB, 8-PAM wastes little until about 20 dB. Two famous numbers come out of the calculation. As the
rate goes to zero the energy per bit approaches ln 2 = −1.59 dB, below which no code works; and a rate-½ binary code cannot do better than
{eb:.2f} dB, the target that turbo and LDPC codes approach (AM-216). At high rate a uniform constellation needs {gaps[6.0]:.2f} dB more SNR than a Gaussian
input at 6 bits per dimension ({gaps[4.0]:.2f} dB at 4 bits) — approaching the asymptotic 1.53 dB shaping gap, which probabilistic shaping in modern optical and 5G systems recovers by using outer points less often.""")
# tol-convention: relative tolerances are in percent
