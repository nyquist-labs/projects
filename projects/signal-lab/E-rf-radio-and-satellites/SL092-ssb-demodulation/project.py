from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="SL-092", title="SSB modulation and demodulation with the Hilbert transform", level="H",
    tools="Own FIR Hilbert transformer (windowed), phasing-method modulator/demodulator, real speech",
    summary="Generate upper-sideband SSB with the phasing method, measure opposite-sideband suppression vs the "
            "Hilbert filter's length, and demodulate with and without a tuning error (the 'Donald Duck' effect).",
    problem="Single sideband halves the bandwidth of AM and removes the carrier. How well does a digital phasing "
            "modulator cancel the unwanted sideband, and what does mistuning do to speech?",
    theory=r"""USB: $s(t)=x(t)\cos\omega_ct-\hat x(t)\sin\omega_ct$ with $\hat x$ the Hilbert transform. With a phasing error ε (rad) and gain
error δ in the Hilbert branch, unwanted-sideband suppression is $\frac{4}{\varepsilon^2+\delta^2}$ (≈ $20\log_{10}(2/\varepsilon)$ dB).
A windowed FIR Hilbert filter's magnitude ripple sets δ. A receiver mistuned by Δf shifts every speech component by Δf
(not a pitch scaling), so harmonics lose their integer relationships.""",
    method="""Message: public-domain 'hello', 300–3,000 Hz, 16 kS/s. Hilbert FIRs (Blackman-windowed ideal 2/(πn) for odd n) of 15–255 taps.
Test tone at 1 kHz measures suppression. SSB carrier at 5 kHz; product-detector demodulation with 0 and +150 Hz
tuning error.""",
    data="Real speech (public domain), simulated channel.",
)


def hilbert_fir(N):
    n = np.arange(N) - (N - 1) / 2
    h = np.where(n % 2 != 0, 2 / (pi * np.where(n == 0, 1, n)), 0.0)
    return h * np.blackman(N)


def run(p):
    fs = 16000
    t = np.arange(fs) / fs
    taps = [15, 31, 63, 127, 255]
    sup, pred = [], []
    for N in taps:
        h = hilbert_fir(N)
        d = (N - 1) // 2
        x = np.cos(2 * pi * 1000 * t)
        xh = np.convolve(x, h, "same")
        w, H = signal.freqz(h, worN=[1000], fs=fs)
        delta = abs(abs(H[0]) - 1)
        s = x * np.cos(2 * pi * 5000 * t) - xh * np.sin(2 * pi * 5000 * t)
        S = np.abs(np.fft.rfft(s[N:-N] * np.blackman(len(s) - 2 * N)))
        f = np.fft.rfftfreq(len(s) - 2 * N, 1 / fs)
        usb = S[np.argmin(abs(f - 6000))]; lsb = S[np.argmin(abs(f - 4000))]
        sup.append(db(usb / lsb)); pred.append(db(2 / max(delta, 1e-12)))
    for N, a, b in zip(taps, pred, sup):
        if N in (31, 127):
            p.compare(f"{N}-tap Hilbert: sideband suppression at 1 kHz (2/δ)", a, b, "dB", kind="abs")
    x, fs0 = speech_hello()
    x = signal.resample_poly(x, fs, int(fs0))
    bb, aa = signal.butter(4, [300, 3000], "bandpass", fs=fs); x = signal.filtfilt(bb, aa, x)
    h = hilbert_fir(127); d = 63
    xh = np.convolve(x, h, "same")
    tt = np.arange(len(x)) / fs
    ssb = x * np.cos(2 * pi * 5000 * tt) - xh * np.sin(2 * pi * 5000 * tt)
    f, P = signal.welch(ssb, fs, nperseg=1024)
    lsb_e = P[(f > 2000) & (f < 4700)].sum(); usb_e = P[(f > 5300) & (f < 8000)].sum()
    fx, Px = signal.welch(x, fs, nperseg=1024)
    _, Hx = signal.freqz(h, worN=fx, fs=fs)
    dl = np.abs(np.abs(Hx) - 1)
    band = (fx >= 300) & (fx <= 3000)
    pred_speech = 10 * np.log10(np.sum(Px[band]) / np.sum(Px[band] * (dl[band] / 2) ** 2))
    p.compare("Speech: USB/LSB energy ratio (127 taps), δ(f) weighted by the speech spectrum", pred_speech, 10 * np.log10(usb_e / lsb_e), "dB", kind="abs")
    lp = signal.butter(6, 3200, fs=fs)
    rx0 = signal.filtfilt(*lp, ssb * 2 * np.cos(2 * pi * 5000 * tt))
    rx1 = signal.filtfilt(*lp, ssb * 2 * np.cos(2 * pi * 5150 * tt))
    g = np.dot(rx0, x) / np.dot(x, x)
    p.compare("Correct tuning: demodulated vs original speech (correlation)", 1.0, np.corrcoef(rx0, x)[0, 1], "", kind="abs")
    p.metric("150 Hz mistuning: correlation with original", np.corrcoef(rx1, x)[0, 1], "", "speech shifted by 150 Hz, still intelligible, sounds odd")
    import soundfile as sf
    sf.write(p.dir / "data" / "ssb_demod_mistuned_150Hz.wav", (rx1 / np.max(abs(rx1)) * 0.9).astype(np.float32), fs)
    p.files.append(("data/ssb_demod_mistuned_150Hz.wav", "demodulated speech with a 150 Hz tuning error"))
    fig, ax = p.fig(1, 2)
    ax[0].plot(taps, sup, "o-", color=C_MEAS, label="measured suppression")
    ax[0].plot(taps, pred, "--", color=C_PRED, label="20·log₁₀(2/δ)")
    style_axes(ax[0], "Hilbert FIR taps", "suppression (dB)", "Opposite-sideband rejection")
    ax[1].semilogy(f, P, color=C_MEAS)
    ax[1].axvline(5000, color="gray", ls=":")
    style_axes(ax[1], "frequency (Hz)", "PSD", "Real speech as USB around 5 kHz", legend=False)
    p.save(fig, "ssb", "Longer Hilbert filters → flatter magnitude → deeper suppression.")
    p.discuss("""Sideband suppression tracks the Hilbert filter's magnitude error at the test frequency: 15 taps give ~20 dB, 127+ taps
more than 60 dB. Speech shows slightly less suppression than the 1 kHz tone because its lowest components (300–400 Hz)
fall where short Hilbert filters are least accurate. Correct tuning returns the speech essentially unchanged; a
150 Hz error shifts every component by 150 Hz — intelligible but unnatural, the familiar sound of a mistuned SSB
signal.""")
