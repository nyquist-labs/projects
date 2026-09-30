from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="SL-090", title="AM demodulation from complex baseband (IQ)", level="M",
    tools="NumPy/SciPy: complex baseband model, envelope vs synchronous detection, SNR measurement",
    summary="Transmit a real speech clip with AM, receive it as IQ samples with frequency offset and noise, and "
            "compare envelope and synchronous detectors against the textbook output-SNR formulas, including "
            "the envelope detector's threshold.",
    problem="Why does an AM radio work with a single diode, and when does that simple envelope detector fail?",
    theory=r"""AM: $s(t)=A_c[1+m\,x(t)]$. With carrier-to-noise ratio CNR in the IF bandwidth 2W, coherent detection gives
$SNR_{out}=\frac{2m^2\overline{x^2}}{1+m^2\overline{x^2}}\,CNR$ (a factor ≤ ⅔ of the SSB/baseband figure). The envelope
detector matches it above threshold (CNR ≳ 10 dB) and collapses below, where the noise captures the envelope.""",
    method="""Message: the public-domain 'hello' clip, band-limited to 4 kHz, normalised to x² mean 0.1 (peaks < 1), m = 0.8, resampled to
48 kS/s complex baseband with a 150 Hz frequency offset and complex Gaussian noise for CNR 0–30 dB (in 8 kHz).
Envelope detector |r|; synchronous detector: carrier frequency from the FFT carrier line, then residual phase tracked by a
5 Hz low-pass of the de-rotated signal. Output SNR measured against the clean message after gain/delay alignment.""",
    data="Real speech message (public domain) over a simulated radio channel.",
)


def run(p):
    x, fs0 = speech_hello()
    fs = 48000
    x = signal.resample_poly(x, fs, int(fs0))
    b, a = signal.butter(6, 4000, fs=fs); x = signal.filtfilt(b, a, x)
    x = x / np.sqrt(np.mean(x**2)) * np.sqrt(0.1)
    x = np.clip(x, -1, 1)
    m = 0.8
    n = np.arange(len(x))
    tx = 1 + m * x
    k = m**2 * np.mean(x**2)
    res = []
    for cnr in np.arange(0, 31, 3):
        fo = 150.0
        Ps = np.mean(tx**2)
        N0 = Ps / (10 ** (cnr / 10) * 8000)
        noise = (p.rng.normal(size=len(x)) + 1j * p.rng.normal(size=len(x))) * np.sqrt(N0 * fs / 2)
        r = tx * np.exp(1j * (2 * pi * fo * n / fs + 0.7)) + noise
        r = signal.filtfilt(*signal.butter(6, 4000, fs=fs), r)
        env = np.abs(r)
        R = np.fft.fft(r); fq = np.fft.fftfreq(len(r), 1 / fs)
        near = np.abs(fq) < 500
        fo_est = fq[near][np.argmax(np.abs(R[near]))]                 # carrier line → frequency offset
        r2 = r * np.exp(-2j * pi * fo_est * n / fs)
        ph = np.unwrap(np.angle(signal.filtfilt(*signal.butter(2, 5, fs=fs), r2)))
        sync = np.real(r2 * np.exp(-1j * ph))
        out = []
        for y in (env, sync):
            y = y - y.mean()
            g = np.dot(y, x) / np.dot(x, x)
            out.append(10 * np.log10(np.mean((g * x) ** 2) / np.mean((y - g * x) ** 2)))
        pred = 10 * np.log10(2 * k / (1 + k)) + cnr
        res.append((cnr, out[0], out[1], pred))
    cnr_, env_, syn_, pred_ = map(np.array, zip(*res))
    for c in (15, 24):
        j = list(cnr_).index(c)
        p.compare(f"Synchronous detector SNR at CNR {c} dB", pred_[j], syn_[j], "dB", kind="abs")
        p.compare(f"Envelope detector SNR at CNR {c} dB", pred_[j], env_[j], "dB", kind="abs")
    j0 = list(cnr_).index(3)
    p.metric("Envelope-detector loss at CNR 3 dB (below threshold)", syn_[j0] - env_[j0], "dB")
    fig, ax = p.fig()
    ax.plot(cnr_, pred_, "--", color=C_PRED, label="theory: 2k/(1+k)·CNR")
    ax.plot(cnr_, syn_, "s-", color=C_MEAS, label="synchronous detector")
    ax.plot(cnr_, env_, "o-", color=COLORS[1], label="envelope detector")
    style_axes(ax, "CNR in 8 kHz (dB)", "output SNR (dB)", "AM detection of real speech")
    p.save(fig, "am_snr", "The envelope detector matches coherent detection above ~10 dB CNR, then falls off (threshold effect).")
    p.csv("am_snr", cnr_db=cnr_, envelope_snr_db=env_, synchronous_snr_db=syn_, theory_db=pred_)
    p.discuss("""Above threshold both detectors follow the textbook line, which sits well below CNR because most AM power is in the
carrier: with m = 0.8 and speech-like x only a small fraction of the transmitted power carries the message. Below
~10 dB CNR the envelope detector collapses faster than the synchronous one — the noise vector sometimes exceeds the
carrier, so |r| stops following 1 + m·x. That threshold is the price of the one-diode receiver.""")
