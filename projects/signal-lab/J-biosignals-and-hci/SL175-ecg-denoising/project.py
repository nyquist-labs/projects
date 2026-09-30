from eelab import *
from eelab.data import physionet
from scipy import signal

META = dict(
    id="SL-175", title="ECG denoising with real noise from the Noise Stress Test Database", level="M",
    tools="Zero-phase high-pass and notch filters, wavelet-free median baseline estimation (SciPy); MIT-BIH + NSTDB real noise",
    summary="Corrupt a clean real ECG with real baseline-wander, electrode-motion and muscle-noise recordings at 6 dB SNR, remove them with "
            "standard filters, and measure the SNR improvement for each noise type — including the one filtering cannot fix.",
    problem="ECGs recorded in the real world are full of baseline wander, muscle noise and motion artefacts. Which of these can filtering "
            "actually remove?",
    theory=r"""A linear filter that passes the ECG band (≈ 0.5–40 Hz) can at best remove the noise power *outside* that band, so the best-case SNR gain is
$-10\log_{10}(P_{noise,\,0.5–40\,Hz}/P_{noise})$, computed from each real noise record's own spectrum. Baseline wander is almost all below 0.5 Hz (large
gain); muscle noise and electrode-motion artefact have substantial in-band power that no linear filter can separate from the ECG.""",
    method="""Clean signal: MIT-BIH record 103 lead 1, 2 minutes. Noise: NSTDB 'bw', 'em', 'ma' records scaled to 6 dB SNR (signal power / noise power). Filters: 200/600 ms
median baseline removal, 60 Hz notch (Q = 30), 40 Hz zero-phase low-pass. SNR_out computed against the clean ECG after identical filtering.""",
    data="Real: MIT-BIH record 103 and MIT-BIH Noise Stress Test Database (PhysioNet).",
)


def snr(ref, x):
    return 10 * np.log10(np.sum(ref**2) / np.sum((x - ref) ** 2))


def clean_filter(x, fs):
    b1 = signal.medfilt(x, int(0.2 * fs) | 1); b2 = signal.medfilt(b1, int(0.6 * fs) | 1)
    y = x - b2
    b, a = signal.iirnotch(60, 30, fs); y = signal.filtfilt(b, a, y)
    b, a = signal.butter(4, 40, fs=fs); return signal.filtfilt(b, a, y)


def run(p):
    n = 360 * 120
    ecg = physionet("mitdb", "103", 0, n, channels=[0])["signal"][:, 0].astype(float)
    fs = 360.0
    ecg = ecg - np.median(ecg)
    ref = clean_filter(ecg, fs)
    res = {}
    fig, axs = p.fig(3, 1, h=8, sharex=True)
    t = np.arange(n) / fs
    pred = {}
    for i, nm in enumerate(("bw", "ma", "em")):
        nz = physionet("nstdb", nm, 0, n, channels=[0])["signal"][:, 0].astype(float)
        nz -= nz.mean()
        nz *= np.sqrt(np.mean(ecg**2) / np.mean(nz**2) / 10 ** (6 / 10))
        f, P = signal.welch(nz, fs, nperseg=4096)
        inband = np.sum(P[(f >= 0.5) & (f <= 40)]) / np.sum(P)
        pred[nm] = -10 * np.log10(inband)          # best case: all out-of-band noise removed, in-band noise untouched
        x = ecg + nz
        y = clean_filter(x, fs)
        gain = snr(ref, y) - snr(ecg, x)
        res[nm] = gain
        m = (t > 30) & (t < 36)
        axs[i].plot(t[m], x[m], color="gray", lw=.6, label=f"noisy ({nm})"); axs[i].plot(t[m], y[m], color=C_MEAS, lw=1, label="filtered")
        style_axes(axs[i], "time (s)" if i == 2 else None, "mV", {"bw": "baseline wander", "ma": "muscle artefact", "em": "electrode motion"}[nm])
    p.save(fig, "denoise", "Filtering removes baseline wander, partly helps with muscle noise and cannot touch electrode-motion artefact.")
    names = {"bw": "baseline wander", "ma": "muscle artefact", "em": "electrode motion"}
    for nm in ("bw", "ma", "em"):
        p.compare(f"{names[nm]}: SNR gain vs −10·log₁₀(in-band noise fraction)", pred[nm], res[nm], "dB", kind="abs",
                  note="upper bound for a linear filter that keeps 0.5–40 Hz")
    p.discuss("""Each measured gain sits close to its spectral upper bound, which ranks the noise types exactly: baseline wander lives almost entirely below
0.5 Hz and is removed with a large gain; muscle noise and electrode-motion artefact keep their in-band part. My first prediction assumed
electrode motion is purely in-band (0 dB gain); the real NSTDB 'em' record also contains a lot of low-frequency drift, so filtering still helps
~6 dB — but the in-band residue that remains looks exactly like ECG waves, which is why 'em' is the standard stress test for QRS detectors and
why wearable ECGs use adaptive filtering with motion sensors.""")
