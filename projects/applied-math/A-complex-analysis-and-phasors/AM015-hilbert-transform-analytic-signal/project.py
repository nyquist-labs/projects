from eelab import *
from eelab.data import noaa_apt_audio
from scipy import signal

META = dict(
    id="AM-015", title="Hilbert transform and instantaneous frequency (with real satellite audio)", level="H",
    tools="FFT-based Hilbert transform (own implementation vs scipy.signal.hilbert), analytic signal, instantaneous frequency by phase differentiation; real NOAA-18 APT recording from SatNOGS",
    summary="Build the analytic signal by zeroing negative frequencies, extract instantaneous amplitude and frequency from a chirp, then use it on a "
            "real weather-satellite recording to recover the 2.4 kHz subcarrier frequency and the AM image envelope.",
    problem="A real signal has no 'instantaneous frequency' by itself. How does the Hilbert transform define one — and does it work on real data?",
    theory=r"""The analytic signal $z = x + j\mathcal{H}\{x\}$ has a one-sided spectrum (double the positive frequencies, zero the negative ones). For $x = A(t)\cos φ(t)$ with slowly varying A,
$z ≈ A e^{jφ}$, so |z| is the envelope and $f_i=\frac{1}{2π}\frac{dφ}{dt}$ the instantaneous frequency. For a linear chirp the estimate should follow the true sweep except near the
record ends (the FFT treats the record as periodic).""",
    method="""Chirp 200 → 2000 Hz in 1 s at 16 kHz: f_i vs truth. NOAA-18 APT audio (SatNOGS observation 11229309, 11025 Hz): band-pass 1.2–3.6 kHz, analytic signal, median instantaneous
frequency over the pass, compared with the FFT peak; envelope compared with the known 4160 samples/s line structure (2 lines/s).""",
    data="Real: SatNOGS network observation 11229309 (NOAA-18 APT), CC BY-SA 4.0.",
)


def hilbert_fft(x):
    N = len(x); X = np.fft.fft(x); h = np.zeros(N)
    h[0] = 1
    if N % 2 == 0:
        h[N // 2] = 1; h[1:N // 2] = 2
    else:
        h[1:(N + 1) // 2] = 2
    return np.fft.ifft(X * h)


def run(p):
    fs = 16000; t = np.arange(fs) / fs
    f0, f1 = 200, 2000
    x = np.cos(2 * pi * (f0 * t + (f1 - f0) / 2 * t * t))
    z = hilbert_fft(x)
    p.compare("Own FFT Hilbert vs scipy.signal.hilbert (worst)", 0, np.max(np.abs(z - signal.hilbert(x))), "", kind="abs", tol=1e-9)
    fi = np.diff(np.unwrap(np.angle(z))) * fs / (2 * pi)
    ftrue = f0 + (f1 - f0) * t[:-1] - 0 + (f1 - f0) / (2 * fs)
    core = slice(int(0.05 * fs), int(0.95 * fs))
    p.compare("Chirp: RMS instantaneous-frequency error (middle 90 %)", 0, np.sqrt(np.mean((fi[core] - ftrue[core]) ** 2)), "Hz", kind="abs", tol=1)
    p.metric("Chirp: worst error in the first/last 5 % (edge effect)", np.max(np.abs(fi - ftrue)), "Hz")
    audio, afs, _meta = noaa_apt_audio()
    audio = audio if audio.ndim == 1 else audio[:, 0]
    audio = audio[: int(afs * 120)]
    b, a = signal.butter(4, [1200, 3600], "bandpass", fs=afs)
    xa = signal.filtfilt(b, a, audio)
    za = hilbert_fft(xa)
    fia = np.diff(np.unwrap(np.angle(za))) * afs / (2 * pi)
    env = np.abs(za)
    good = env[1:] > np.percentile(env, 30)
    f_med = np.median(fia[good])
    F = np.abs(np.fft.rfft(xa * np.hanning(len(xa)))); ff = np.fft.rfftfreq(len(xa), 1 / afs)
    f_fft = ff[np.argmax(F)]
    p.compare("NOAA APT: median instantaneous frequency vs the carrier (FFT peak)", f_fft, f_med, "Hz", kind="abs", tol=5)
    wts = np.abs(za[1:]) ** 2
    f_w = np.sum(wts * fia) / np.sum(wts)
    Za = np.abs(np.fft.fft(za)) ** 2; fa_ = np.fft.fftfreq(len(za), 1 / afs)
    centroid = np.sum(Za * fa_) / np.sum(Za)
    p.compare("Identity: |z|²-weighted mean instantaneous frequency = spectral centroid of z", centroid, f_w, "Hz", tol=0.2)
    E = env - env.mean()
    fe = np.fft.rfftfreq(len(E), 1 / afs); Pe = np.abs(np.fft.rfft(E))
    band = (fe > 1) & (fe < 5)
    p.compare("Envelope line rate (APT sends 2 lines/s)", 2.0, fe[band][np.argmax(Pe[band])], "Hz", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    ax[0].plot(t[:-1], fi, color=C_MEAS, label="Hilbert estimate"); ax[0].plot(t[:-1], ftrue, "--", color=C_PRED, label="true sweep")
    style_axes(ax[0], "t (s)", "frequency (Hz)", "Chirp")
    ta = np.arange(len(fia)) / afs
    ax[1].plot(ta[: int(afs * 2)], fia[: int(afs * 2)], color=C_MEAS, lw=.4); ax[1].set_ylim(1500, 3300)
    style_axes(ax[1], "t (s)", "instantaneous frequency (Hz)", "APT audio (real)", legend=False)
    ax[2].plot(ta[: int(afs * 2)], env[1: int(afs * 2) + 1], color=C_MEAS, lw=.4)
    style_axes(ax[2], "t (s)", "envelope", "APT envelope = image lines", legend=False)
    p.save(fig, "hilbert", "Instantaneous frequency of a chirp and of real NOAA-18 APT audio, plus the recovered AM envelope.")
    p.discuss(f"""The FFT construction reproduces SciPy's Hilbert transform exactly and tracks the chirp to within a fraction of a hertz in the middle of the
record, with the expected errors at the ends where the implicit periodic extension joins 2000 Hz to 200 Hz. On the real satellite recording the
spectrum peaks at the {f_fft:.0f} Hz subcarrier and the envelope oscillates at exactly 2 Hz — the two image lines per second of the APT format. But
the median instantaneous frequency comes out {f_fft - f_med:.0f} Hz *low*, which I did not predict. The reason is Bedrosian's theorem: A·cos φ has
analytic signal A·e^(jφ) only if the envelope's spectrum lies below the carrier, and APT's image modulation (~2 kHz wide) nearly reaches the
2.4 kHz carrier, so the 'phase' absorbs part of the modulation. What does hold exactly is the identity that the power-weighted mean
instantaneous frequency equals the spectral centroid — confirmed here to 0.2 %. The instantaneous-frequency trace is noisy where
the envelope is small — dividing by a near-zero amplitude is the analytic signal's weak point, which is why the median over strong samples is used.""")
# tol-convention: relative tolerances are in percent
