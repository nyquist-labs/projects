from eelab import *

META = dict(
    id="AM-071", title="Matrix pencil: extracting damped exponentials from a transient", level="H",
    tools="Hua–Sarkar matrix pencil (Hankel matrices, SVD rank truncation, generalised eigenvalues), least-squares amplitudes, comparison with FFT peak picking",
    summary="Estimate the frequencies and damping factors of three closely spaced damped sinusoids in a noisy ringing transient with the matrix "
            "pencil method, show that it resolves modes an FFT cannot, and measure estimation error versus SNR.",
    problem="A ringing circuit's transient is a sum of damped exponentials. How do you recover each mode's frequency and decay, even when they overlap spectrally?",
    theory=r"""$x[n]=\sum_k c_kz_k^n$ with $z_k=e^{(-σ_k+jω_k)T}$. Hankel matrices Y₀ (rows 0…N−L−1) and Y₁ (shifted by one) satisfy Y₁ = Y₀·(something with eigenvalues z_k): the z_k are the non-zero eigenvalues of the pencil
$Y_0^+Y_1$ after truncating to the signal rank (2K for real signals). No frequency grid, so modes closer than the FFT's 1/T resolution are separable; errors grow as noise increases, approaching the Cramér–Rao
bound for moderate SNR.""",
    method="""fs = 1 MHz, N = 200 (T = 200 µs, FFT resolution 5 kHz). Modes: 100 kHz (σ = 5000 s⁻¹), 103 kHz (σ = 8000), 150 kHz (σ = 20000). SNR 10–60 dB, 100 trials each; pencil parameter L = N/3;
rank 6. Errors in frequency and damping.""",
)


def pencil(x, M, L=None):
    N = len(x); L = L or N // 3
    Y = np.array([x[i:i + L + 1] for i in range(N - L)])
    U, s, Vt = np.linalg.svd(Y, full_matrices=False)
    V = Vt[:M].conj().T
    V0, V1 = V[:-1], V[1:]
    z = np.linalg.eigvals(np.linalg.pinv(V0) @ V1)
    return z


def run(p):
    fs = 1e6; N = 200; n = np.arange(N); T = 1 / fs
    modes = [(100e3, 5000, 1.0), (103e3, 8000, 0.8), (150e3, 20000, 0.5)]
    x0 = sum(a * np.exp(-s_ * n * T) * np.cos(2 * pi * f * n * T) for f, s_, a in modes)
    z = pencil(x0, 6)
    est = sorted([(abs(np.angle(q)) / (2 * pi * T), -np.log(abs(q)) / T) for q in z if np.angle(q) > 0])
    worst_f = max(abs(e[0] - m[0]) for e, m in zip(est, modes)); worst_s = max(abs(e[1] - m[1]) / m[1] for e, m in zip(est, modes))
    p.compare("Noise-free: worst frequency error", 0, worst_f, "Hz", kind="abs", tol=1e-3)
    p.compare("Noise-free: worst relative damping error", 0, worst_s, "", kind="abs", tol=1e-6)
    X = np.abs(np.fft.rfft(x0 * np.hanning(N), 1 << 16)); ff = np.fft.rfftfreq(1 << 16, T)
    from scipy.signal import find_peaks
    pk, _ = find_peaks(X, prominence=X.max() * 0.05)
    p.compare("FFT peaks found near 100–103 kHz (the two modes 3 kHz apart are unresolved by 1/T = 5 kHz)", 1, int(np.sum((ff[pk] > 95e3) & (ff[pk] < 108e3))), "", kind="abs")
    r = p.rng
    rows = []
    for snr_db in (10, 20, 30, 40, 60):
        errs = []
        for _ in range(100):
            sig = np.sqrt(np.mean(x0 ** 2) / 10 ** (snr_db / 10))
            z = pencil(x0 + r.normal(0, sig, N), 6)
            est = sorted([(abs(np.angle(q)) / (2 * pi * T), -np.log(abs(q)) / T) for q in z if np.angle(q) > 0])
            if len(est) == 3:
                errs.append(abs(est[1][0] - 103e3))
        rows.append((snr_db, np.sqrt(np.mean(np.square(errs))) if errs else np.nan))
    rr = np.array(rows)
    sl = np.polyfit(rr[2:, 0], np.log10(rr[2:, 1]), 1)[0] * 20
    p.compare("High-SNR slope of frequency RMS error: −20 dB per 20 dB SNR (error ∝ noise amplitude)", -1.0, sl, "decades/decade", kind="abs", tol=0.2)
    p.metric("RMS error of the 103 kHz mode at 30 dB SNR", rr[2, 1], "Hz", "vs 5 kHz FFT resolution")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(ff / 1e3, X / X.max(), color=C_MEAS); ax[0].set_xlim(80, 170)
    for f, s_, a in modes:
        ax[0].axvline(f / 1e3, color=C_PRED, ls="--", lw=.8)
    style_axes(ax[0], "frequency (kHz)", "|X| (norm.)", "FFT (Hann): 100 and 103 kHz merge", legend=False)
    ax[1].semilogy(rr[:, 0], rr[:, 1], "o-", color=C_MEAS)
    style_axes(ax[1], "SNR (dB)", "RMS error of the 103 kHz estimate (Hz)", "Matrix pencil accuracy vs noise", legend=False)
    p.save(fig, "pencil", "The FFT cannot separate the close modes; the matrix pencil's error falls with SNR.")
    p.discuss(f"""On the clean transient the matrix pencil returns all three frequencies and damping factors to rounding error, including the 100/103 kHz pair
that a 200-sample FFT (resolution 5 kHz) shows as a single peak — the pencil fits a model instead of sampling a spectrum, so it has no grid-imposed
resolution limit. The price is noise sensitivity: the error falls in proportion to the noise amplitude at high SNR and grows sharply below ~20 dB,
where the rank-6 truncation can no longer separate signal from noise directions. That trade — model-based super-resolution in exchange for
knowing the model order and having decent SNR — is the defining property of all subspace methods.""")
# tol-convention: relative tolerances are in percent
