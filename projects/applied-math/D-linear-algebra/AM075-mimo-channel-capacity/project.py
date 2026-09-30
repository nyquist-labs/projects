from eelab import *

META = dict(
    id="AM-075", title="MIMO capacity from singular values", level="H",
    tools="SVD of random Rayleigh channel matrices, parallel-channel decomposition, equal-power and water-filling capacity, Monte-Carlo ergodic capacity, high-SNR slope",
    summary="Show that a MIMO channel H = UΣVᴴ is a set of min(Nt, Nr) parallel scalar channels, compute capacity from the singular values, and "
            "verify that ergodic capacity grows linearly with min(Nt, Nr) — about min(Nt,Nr) × log₂(SNR) bits at high SNR.",
    problem="Adding antennas at both ends of a link multiplies its capacity. Why — and by exactly how much?",
    theory=r"""Precoding with V and receiving with Uᴴ turns y = Hx + n into y'_i = σ_i x'_i + n'_i. With equal power per transmit antenna, $C=\log_2\det(I+\frac{ρ}{N_t}HH^H)=\sum_i\log_2(1+\frac{ρ}{N_t}σ_i^2)$ bits/s/Hz.
At high SNR each non-zero σ_i adds log₂ρ: capacity slope = min(Nt, Nr) bits per 3 dB. For Rayleigh fading (i.i.d. CN(0,1) entries) the channel has full rank almost surely.""",
    method="""10,000 channel draws per configuration (1×1, 2×2, 4×4, 8×8, 4×2); SNR 0–30 dB. det formula vs Σ log(1+σ²) (must agree), SVD pre/post-coding verified on a random draw (off-diagonal leakage),
high-SNR slope from 20–30 dB.""",
)


def cap(H, rho):
    Nt = H.shape[1]; s = np.linalg.svd(H, compute_uv=False)
    return np.sum(np.log2(1 + rho / Nt * s ** 2))


def run(p):
    r = p.rng
    H = (r.normal(size=(4, 4)) + 1j * r.normal(size=(4, 4))) / np.sqrt(2)
    U, s, Vh = np.linalg.svd(H)
    D = U.conj().T @ H @ Vh.conj().T
    p.compare("SVD precoding diagonalises H: max off-diagonal |UᴴHV|", 0, np.max(np.abs(D - np.diag(np.diag(D)))), "", kind="abs", tol=1e-12)
    rho = 10.0
    det_form = np.log2(np.real(np.linalg.det(np.eye(4) + rho / 4 * H @ H.conj().T)))
    p.compare("log₂det(I + ρ/Nt·HHᴴ) = Σ log₂(1 + ρσ²/Nt)", det_form, cap(H, rho), "bit/s/Hz", tol=1e-10)
    snr_db = np.arange(0, 31, 2); res = {}
    for nt, nr in ((1, 1), (2, 2), (4, 4), (8, 8), (2, 4)):
        C = []
        for sd in snr_db:
            rho = 10 ** (sd / 10)
            Hs = (r.normal(size=(2000, nr, nt)) + 1j * r.normal(size=(2000, nr, nt))) / np.sqrt(2)
            sv = np.linalg.svd(Hs, compute_uv=False)
            C.append(np.mean(np.sum(np.log2(1 + rho / nt * sv ** 2), axis=1)))
        res[(nt, nr)] = np.array(C)
    for (nt, nr), C in res.items():
        slope = (C[-1] - C[-6]) / (snr_db[-1] - snr_db[-6]) * 10 * np.log10(2)
        p.compare(f"{nt}×{nr}: high-SNR slope (bits per 3 dB) = min(Nt, Nr)", min(nt, nr), slope, "bit/3 dB", kind="abs", tol=0.15)
    p.compare("4×4 vs 1×1 ergodic capacity at 30 dB (≈ 4×)", 4, res[(4, 4)][-1] / res[(1, 1)][-1], "×", kind="abs", tol=0.6)
    fig, ax = p.fig(1, 2, w=11)
    for (k, C), c in zip(res.items(), COLORS):
        ax[0].plot(snr_db, C, "o-", ms=3, color=c, label=f"{k[0]}×{k[1]}")
    style_axes(ax[0], "SNR (dB)", "ergodic capacity (bit/s/Hz)", "Capacity grows with min(Nt, Nr)")
    sv = np.linalg.svd((r.normal(size=(5000, 4, 4)) + 1j * r.normal(size=(5000, 4, 4))) / np.sqrt(2), compute_uv=False)
    for i, c in zip(range(4), COLORS):
        ax[1].hist(sv[:, i] ** 2, bins=80, density=True, alpha=.6, color=c, label=f"σ²_{i + 1}")
    ax[1].set_xlim(0, 15)
    style_axes(ax[1], "eigen-channel gain σ²", "density", "4×4: four parallel channels of unequal strength")
    p.save(fig, "mimo", "Ergodic capacity vs SNR for several array sizes, and the distribution of the four eigen-channel gains.")
    p.discuss("""The SVD literally turns the matrix channel into independent scalar channels (off-diagonal leakage at rounding level), and the capacity formula
log det(I + ρ/Nt·HHᴴ) is just the sum of their Shannon capacities. The measured high-SNR slopes equal min(Nt, Nr) — 1, 2, 4, 8 bits per 3 dB — and a 2×4
link behaves like 2 streams: the extra receive antennas add array gain (a vertical shift), not new streams. The eigen-channels are very unequal
(the weakest 4×4 mode is often near zero), which is why at low SNR it pays to put power only on the strong modes — water-filling, AM-211.""")
# tol-convention: relative tolerances are in percent
