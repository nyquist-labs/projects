from eelab import *
from eelab.data import physionet
from scipy import signal

META = dict(
    id="AM-041", title="Wiener–Khinchin on real data: autocorrelation ↔ power spectrum", level="M",
    tools="Biased autocorrelation (direct and via FFT), periodogram, the Wiener–Khinchin identity, AR(1) theory; real ECG from the MIT-BIH Arrhythmia Database",
    summary="Show on a real ECG recording that the Fourier transform of the (biased) autocorrelation equals the periodogram exactly, and on a "
            "synthetic AR(1) process that both converge to the theoretical PSD; read physiology off the autocorrelation (the heartbeat period).",
    problem="The power spectrum and the autocorrelation are said to be a Fourier pair. Is that exact for finite data, or only in the limit?",
    theory=r"""For a length-N record, the biased autocorrelation $\hat r[m]=\frac1N\sum_n x[n]x[n+m]$ (|m| < N) and the periodogram $\hat P(f)=\frac1N|X(f)|^2$ are an exact DTFT pair — an algebraic identity,
no limits needed (with 2N-point FFTs to avoid circular wrap). For AR(1) $x[n]=ax[n-1]+w[n]$: $r[m]=\frac{σ^2a^{|m|}}{1-a^2}$, $P(f)=\frac{σ^2}{|1-ae^{-j2πf}|^2}$. The periodogram is unbiased-ish but its
variance does not fall with N (≈ P² per bin) — why Welch averaging exists (AM-042).""",
    method="""MIT-BIH record 100, lead MLII, 60 s at 360 Hz. r̂ computed directly (np.correlate) and via |FFT|²; periodogram vs FFT of r̂ compared. AR(1), a = 0.9, N = 65536: periodogram averaged over
frequency bands vs theory.""",
    data="Real: MIT-BIH Arrhythmia Database record 100 (PhysioNet, ODC-By).",
)


def run(p):
    rec = physionet("mitdb", "100", 0, 360 * 60, channels=[0])
    x = rec["signal"][:, 0] if rec["signal"].ndim > 1 else rec["signal"]
    fs = rec["fs"]
    x = np.asarray(x, float); x = x - x.mean(); N = len(x)
    r_dir = np.correlate(x, x, "full") / N                       # lags −(N−1)…(N−1)
    X = np.fft.fft(x, 2 * N)
    r_fft = np.fft.ifft(np.abs(X) ** 2).real / N
    r_fft = np.r_[r_fft[-(N - 1):], r_fft[:N]]
    p.compare("Autocorrelation: direct vs via |FFT|² (max relative error)", 0, np.max(np.abs(r_dir - r_fft)) / r_dir.max(), "", kind="abs", tol=1e-10)
    P_per = np.abs(X) ** 2 / N
    m = np.arange(-(N - 1), N)
    c = np.zeros(2 * N); c[:N] = r_dir[N - 1:]; c[N + 1:] = r_dir[:N - 1]      # lags 0…N−1, then −(N−1)…−1 (circular order)
    P_wk = np.real(np.fft.fft(c))
    p.compare("Wiener–Khinchin: FFT of biased autocorrelation = periodogram (max rel. error)", 0, np.max(np.abs(P_wk - P_per)) / P_per.max(), "", kind="abs", tol=1e-9)
    lags = np.arange(N) / fs
    rpos = r_dir[N - 1:] / r_dir[N - 1]
    band = (lags > 0.4) & (lags < 2.0)
    T_beat = lags[band][np.argmax(rpos[band])]
    pk, _ = signal.find_peaks(x, distance=int(0.4 * fs), height=np.percentile(x, 99) * 0.5)
    p.compare("Heartbeat period from the autocorrelation peak vs mean R–R interval", np.mean(np.diff(pk)) / fs, T_beat, "s", tol=3)
    r = p.rng
    a, n = 0.9, 2 ** 16
    w = r.normal(size=n); xa = signal.lfilter([1], [1, -a], w)
    Pa = np.abs(np.fft.rfft(xa)) ** 2 / n; f = np.fft.rfftfreq(n)
    Pth = 1 / np.abs(1 - a * np.exp(-2j * pi * f)) ** 2
    smooth = np.convolve(Pa / Pth, np.ones(256) / 256, "valid")
    p.compare("AR(1): band-averaged periodogram / theory (mean)", 1.0, np.mean(smooth), "", tol=2)
    p.compare("AR(1): raw periodogram scatter, std(P̂/P) (does not shrink with N)", 1.0, np.std(Pa[10:-10] / Pth[10:-10]), "", tol=5)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    ax[0].plot(lags[:int(3 * fs)], rpos[:int(3 * fs)], color=C_MEAS); ax[0].axvline(T_beat, color=C_PRED, ls="--", label=f"beat period {T_beat:.2f} s")
    style_axes(ax[0], "lag (s)", "normalised autocorrelation", "ECG autocorrelation (MIT-BIH 100)")
    fr = np.fft.fftfreq(2 * N, 1 / fs)[:N]
    ax[1].semilogy(fr, P_per[:N], color=COLORS[7], lw=.5, label="periodogram"); ax[1].semilogy(fr, np.abs(P_wk[:N]), ":", color=C_MEAS, lw=.8, label="FFT of autocorrelation")
    ax[1].set_xlim(0, 40)
    style_axes(ax[1], "frequency (Hz)", "power", "Identical spectra")
    ax[2].semilogy(f, Pa, color=COLORS[7], lw=.3, label="periodogram"); ax[2].semilogy(f, Pth, color=C_PRED, label="AR(1) theory")
    style_axes(ax[2], "frequency (cycles/sample)", "PSD", "AR(1): unbiased but noisy")
    p.save(fig, "wiener_khinchin", "ECG autocorrelation with the heartbeat period, the Wiener–Khinchin identity on real data, and an AR(1) periodogram vs theory.")
    p.discuss(f"""On a real ECG the transform of the biased autocorrelation matches the periodogram to ~1e-12 — Wiener–Khinchin is an exact identity for the
finite-data estimators (provided the FFT is long enough to avoid circular wrap), not merely an asymptotic statement. The autocorrelation also reads
physiology directly: its first big peak at {T_beat:.2f} s is the average heartbeat period, matching the R–R intervals. The AR(1) test shows the
estimator's weakness: averaged over bands the periodogram equals the theoretical PSD, but bin by bin its scatter is as large as the PSD itself
(std ≈ 1 × P, independent of N), which is exactly the variance Welch's method trades resolution to remove.""")
# tol-convention: relative tolerances are in percent
