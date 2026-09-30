from eelab import *

META = dict(
    id="SL-075", title="Quantisation noise and the 6 dB-per-bit rule", level="M",
    tools="NumPy uniform quantiser, SINAD measurement, noise-spectrum analysis",
    summary="Quantise a full-scale sine at 2–20 bits, measure SNR, and verify SNR = 6.02·N + 1.76 dB, "
            "including where the rule breaks (low bits, and non-busy signals).",
    problem="Where does the famous 6.02 N + 1.76 dB come from, and when is the 'quantisation noise is white "
            "and uniform' assumption wrong?",
    theory=r"""A uniform quantiser with step Δ makes an error uniformly distributed in ±Δ/2 (if the signal is 'busy'), so
noise power = Δ²/12. A full-scale sine has power $(2^{N-1}\Delta)^2/2$, giving
$SNR = 10\log_{10}\frac{3}{2}2^{2N} = 6.02N+1.76$ dB. The assumption fails for very few bits (error correlated
with signal → harmonics) and for signals commensurate with the sample rate (periodic error).""",
    method="""Sine at 997 Hz (prime relative to f_s = 48 kHz) with amplitude just under full scale, 2¹⁶ samples; SNR = signal
power / (error power). Error spectrum and error histogram at 4 and 12 bits; a 1 kHz (commensurate) tone for
contrast.""",
)


def q(x, N):
    D = 2.0 / 2**N
    return np.clip(np.round(x / D) * D, -1, 1 - D)


def run(p):
    fs = 48000; n = np.arange(65536)
    x = 0.999 * np.sin(2 * pi * 997 * n / fs)
    bits = np.arange(2, 21)
    snr = np.array([10 * np.log10(np.mean(x**2) / np.mean((q(x, N) - x) ** 2)) for N in bits])
    pred = 6.02 * bits + 1.76 + 20 * np.log10(0.999)
    for N in (4, 8, 12, 16):
        p.compare(f"{N}-bit SNR", pred[N - 2], snr[N - 2], "dB", kind="abs")
    slope = np.polyfit(bits[4:], snr[4:], 1)[0]
    p.compare("Slope (dB per bit)", 6.02, slope, "dB/bit", kind="abs")
    xc = 0.999 * np.sin(2 * pi * 1000 * n / fs)
    fr = np.fft.rfftfreq(len(n), 1 / fs)
    def top_frac(sig):
        e = q(sig, 12) - sig
        P = np.abs(np.fft.rfft(e * np.hanning(len(e)))) ** 2
        return np.sort(P)[-60:].sum() / P.sum() * 100
    p.metric("Error power in the 60 strongest FFT bins, 997 Hz (busy)", top_frac(x), "%", "white-like: spread over all bins")
    p.metric("Error power in the 60 strongest FFT bins, 1000 Hz (commensurate)", top_frac(xc), "%", "periodic error: a few harmonic lines")
    fig, ax = p.fig(1, 2)
    ax[0].plot(bits, pred, "--", color=C_PRED, label="6.02N + 1.76")
    ax[0].plot(bits, snr, "o", color=C_MEAS, label="measured")
    style_axes(ax[0], "bits N", "SNR (dB)", "The 6 dB-per-bit rule")
    e4 = q(x, 4) - x; e12 = q(x, 12) - x
    ax[1].hist(e12 / (2 / 2**12), 60, density=True, color=C_MEAS, alpha=.8, label="12-bit error / Δ")
    ax[1].hist(e4 / (2 / 2**4), 60, density=True, color=COLORS[1], alpha=.5, label="4-bit error / Δ")
    ax[1].axhline(1, color=C_PRED, ls="--", lw=1, label="uniform ±½Δ")
    style_axes(ax[1], "error (steps)", "density", "Error distribution")
    p.save(fig, "snr_bits", "Uniform-error model holds from ~6 bits up; coarse quantisers have structured error.")
    fig, ax = p.fig()
    for i, (xx, lab) in enumerate(((x, "997 Hz (busy)"), (xc, "1000 Hz (commensurate)"))):
        ee = q(xx, 12) - xx
        EE = np.abs(np.fft.rfft(ee * np.hanning(len(ee))))
        ax.plot(fr / 1e3, db(EE / len(ee)), color=COLORS[i], lw=.6, label=lab)
    style_axes(ax, "frequency (kHz)", "error spectrum (dB)", "12-bit quantisation error spectrum")
    p.save(fig, "error_spectrum", "A commensurate tone turns 'noise' into discrete harmonic spurs.")
    p.csv("snr_vs_bits", bits=bits, snr_db=snr, predicted_db=pred)
    p.discuss("""Above ~6 bits the measured SNR sits on 6.02N + 1.76 within ~0.1 dB and the error histogram is flat, confirming
the uniform-noise model. At 2–4 bits the error is strongly correlated with the signal (histogram not uniform)
and the rule overestimates slightly. The commensurate-tone case shows why test tones are chosen 'prime': a
1 kHz tone at 48 kHz repeats every 48 samples, so the quantisation error repeats too and appears as harmonics
rather than noise — the problem dithering (SL-076) fixes.""")
