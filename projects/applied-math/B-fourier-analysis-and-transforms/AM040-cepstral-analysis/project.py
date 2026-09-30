from eelab import *
from eelab.data import fsdd
from scipy import signal

META = dict(
    id="AM-040", title="Cepstral analysis: separating pitch from the vocal tract", level="H",
    tools="Real cepstrum (IFFT of log magnitude spectrum), liftering, cepstral pitch detection vs autocorrelation pitch; Free Spoken Digit Dataset (real speech)",
    summary="Use the cepstrum to separate the fast spectral ripple of the voice's pitch harmonics from the slow envelope of the vocal tract, "
            "estimate pitch on 3,000 real recordings from six speakers, and cross-check against an independent autocorrelation pitch estimator.",
    problem="Speech = glottal pulse train convolved with the vocal-tract filter. How can a convolution be undone without knowing either?",
    theory=r"""Log turns the convolution's product of spectra into a sum: $\log|S| = \log|E| + \log|H|$. The pitch harmonics make log|S| ripple with period F0 in frequency, i.e. a peak at quefrency
1/F0 in the cepstrum $c=\mathrm{IFFT}(\log|S|)$; the vocal-tract envelope lives at low quefrency. Low-time liftering (keep c below ~2 ms) recovers the smooth envelope (formants); the peak in
2.5–12.5 ms gives F0 (80–400 Hz). Two independent estimators (cepstrum, autocorrelation) should agree on voiced frames to within a few percent.""",
    method="""FSDD: 6 speakers × 10 digits × 50 recordings, 8 kHz. 40 ms Hann frames, energy-voiced frames only; cepstral pitch from the peak in 2.5–12.5 ms; autocorrelation pitch from the first
major peak of the normalised autocorrelation in the same lag range. Agreement = |Δ| < 5 %; octave errors counted separately.""",
    data="Real: Free Spoken Digit Dataset (CC BY-SA 4.0).",
)


def frames(x, fs, win=0.04, hop=0.02):
    n = int(win * fs); h = int(hop * fs)
    return np.array([x[i:i + n] * np.hanning(n) for i in range(0, len(x) - n, h)])


def cep_pitch(f, fs, nfft=1024):
    S = np.abs(np.fft.rfft(f, nfft)) + 1e-9
    c = np.fft.irfft(np.log(S))
    q = np.arange(len(c)) / fs
    band = (q >= 0.0025) & (q <= 0.0125)
    k = np.argmax(c[band])
    return 1 / q[band][k], c[band][k], c, q


def acf_pitch(f, fs):
    a = np.correlate(f, f, "full")[len(f) - 1:]; a /= a[0] + 1e-12
    lo, hi = int(fs / 400), int(fs / 80)
    k = lo + np.argmax(a[lo:hi])
    return fs / k, a[k]


def run(p):
    data = fsdd()
    rows = []
    for d, spk, i, x, fs in data:
        x = x.astype(float); x /= np.max(np.abs(x)) + 1e-9
        F = frames(x, fs)
        if len(F) == 0:
            continue
        e = np.sum(F ** 2, axis=1)
        for f in F[e > 0.3 * e.max()]:
            f0c, pk, _, _ = cep_pitch(f, fs)
            f0a, ra = acf_pitch(f, fs)
            if ra > 0.5:
                rows.append((spk, f0c, f0a))
    spk = np.array([r[0] for r in rows]); fc = np.array([r[1] for r in rows]); fa = np.array([r[2] for r in rows])
    rel = np.abs(fc / fa - 1)
    octave = np.minimum(np.abs(fc / fa - 2), np.abs(fc / fa - 0.5)) < 0.05
    p.compare("Voiced frames where cepstral and autocorrelation pitch agree within 5 %", 90, np.mean(rel < 0.05) * 100, "%", kind="abs", tol=10)
    p.metric("Octave errors (ratio ≈ 2 or ½)", np.mean(octave) * 100, "%", f"{len(rows)} voiced frames")
    per = {s: np.median(fa[spk == s]) for s in sorted(set(spk))}
    p.metric("Median pitch per speaker (autocorrelation)", ", ".join(f"{s}: {v:.0f} Hz" for s, v in per.items()))
    x, fs = next((x, fs) for d, s, i, x, fs in data if s == "jackson" and d == 7)
    x = x.astype(float); F = frames(x, fs); f = F[np.argmax(np.sum(F ** 2, axis=1))]
    f0, _, c, q = cep_pitch(f, fs)
    lift = c.copy(); lift[int(0.002 * fs):-int(0.002 * fs)] = 0
    env = np.exp(np.fft.rfft(lift).real)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    fr = np.fft.rfftfreq(1024, 1 / fs)
    ax[0].plot(fr, db(np.abs(np.fft.rfft(f, 1024)) + 1e-9), color=COLORS[7], lw=.8, label="spectrum")
    ax[0].plot(fr, db(env), color=C_MEAS, lw=2, label="liftered envelope")
    style_axes(ax[0], "frequency (Hz)", "dB", "Harmonics ride on the envelope")
    ax[1].plot(q[:len(q) // 2] * 1e3, c[:len(c) // 2], color=C_MEAS); ax[1].axvline(1e3 / f0, color=C_PRED, ls="--", label=f"pitch peak {f0:.0f} Hz")
    ax[1].set_xlim(0, 15); ax[1].set_ylim(-0.3, 0.5)
    style_axes(ax[1], "quefrency (ms)", "cepstrum", "Cepstrum of a voiced frame")
    ax[2].scatter(fa, fc, s=3, alpha=.3, color=C_MEAS); ax[2].plot([80, 400], [80, 400], "--", color=C_PRED)
    ax[2].set_xscale("log"); ax[2].set_yscale("log")
    style_axes(ax[2], "autocorrelation pitch (Hz)", "cepstral pitch (Hz)", "Two estimators on real speech", legend=False)
    p.save(fig, "cepstrum", "Spectrum and liftered envelope of a voiced frame, its cepstrum, and agreement of the two pitch estimators on FSDD.")
    p.discuss(f"""On {len(rows)} voiced frames of real speech the cepstral pitch agrees with an independent autocorrelation estimate within 5 % in
{np.mean(rel < 0.05) * 100:.0f} % of frames, and the per-speaker medians separate the lower- and higher-pitched voices as expected. The remaining disagreements are
dominated by octave errors ({np.mean(octave) * 100:.1f} %): the cepstrum sometimes locks onto a rahmonic (twice the period) and the autocorrelation onto a
sub-harmonic — the classic failure modes of both methods, usually fixed with continuity tracking across frames. The liftered cepstrum gives a
smooth vocal-tract envelope whose peaks are the formants: the log turned a convolution into an addition, which a simple 'low-quefrency' window
could split.""")
# tol-convention: relative tolerances are in percent
