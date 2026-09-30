from eelab import *
from scipy import signal

META = dict(
    id="AM-016", title="Complex baseband: why IQ sampling needs half the rate", level="H",
    tools="Complex envelope, quadrature down-conversion, band-limited reconstruction, aliasing measurement vs sample rate",
    summary="Represent a band-pass signal by its complex envelope, show that complex (IQ) samples at rate B capture a bandwidth-B signal that real "
            "samples need 2B to capture, and measure reconstruction error versus sampling rate for both.",
    problem="Software-defined radios sample I and Q. Why two channels — and why is that no more data than one real channel at twice the rate?",
    theory=r"""A real band-pass signal $x(t)=\mathrm{Re}\{\tilde x(t)e^{j2πf_ct}\}$ occupying $f_c\pm B/2$ is fully described by its complex envelope $\tilde x$, whose spectrum occupies $[-B/2, B/2]$ and is
not symmetric. Complex samples need rate ≥ B (the spectrum is one-sided: no mirror image to alias onto); a real baseband signal of the same bandwidth occupies
$[-B, B]$ symmetrically and needs ≥ 2B real samples. Same number of real numbers per second — 2 per complex sample at B vs 1 per real sample at 2B.""",
    method="""Random band-limited complex envelope, B = 10 kHz (asymmetric spectrum), carrier 100 kHz, simulated at 2 MHz. (i) IQ: mix down, low-pass, resample at rate r, band-limited
interpolation back, compare with truth. (ii) Real: the envelope's real part shifted to 0…B baseband sampled at r. Reconstruction SNR vs r/B.""",
)


def bandlimited(n, fs, B, r, asym=True):
    X = np.zeros(n, complex); f = np.fft.fftfreq(n, 1 / fs)
    m = (f >= -B / 2) & (f <= B / 2)
    X[m] = (r.normal(size=m.sum()) + 1j * r.normal(size=m.sum())) * (1 + 0.8 * np.tanh(f[m] / (B / 8)) if asym else 1)
    return np.fft.ifft(X)


def resample_err(xc, fs, rate):
    """sample x (complex or real) at `rate` by FFT-domain band-limiting to ±rate/2, return reconstruction SNR (dB)."""
    n = len(xc); X = np.fft.fft(xc); f = np.fft.fftfreq(n, 1 / fs)
    # ideal sampling at `rate` = periodise the spectrum with period `rate`, then ideal low-pass ±rate/2
    Y = np.zeros(n, complex)
    k = np.round(f / rate).astype(int)
    fold = f - k * rate                     # where each component lands after sampling
    idx = np.round(fold / (fs / n)).astype(int) % n
    np.add.at(Y, idx, X)
    Y[np.abs(f) > rate / 2] = 0
    y = np.fft.ifft(Y)
    return 10 * np.log10(np.sum(np.abs(xc) ** 2) / np.sum(np.abs(y - xc) ** 2))


def run(p):
    r = p.rng
    fs, n, B, fc = 2e6, 2 ** 16, 10e3, 100e3
    env = bandlimited(n, fs, B, r)
    t = np.arange(n) / fs
    x = (env * np.exp(2j * pi * fc * t)).real                 # the real RF signal
    # quadrature down-conversion
    bb = x * np.exp(-2j * pi * fc * t) * 2
    sos = signal.butter(8, 3 * B, fs=fs, output="sos")
    bb = signal.sosfiltfilt(sos, bb.real) + 1j * signal.sosfiltfilt(sos, bb.imag)
    core = slice(n // 10, -n // 10)                       # exclude filter start-up/end transients
    snr_dc = 10 * np.log10(np.sum(np.abs(env[core]) ** 2) / np.sum(np.abs(bb[core] - env[core]) ** 2))
    p.compare("Quadrature down-conversion recovers the complex envelope (SNR, my guess ≥ 40 dB)", 40, snr_dc, "dB", kind="abs", tol=100)
    real_bb = bandlimited(n, fs, 2 * B, r, asym=False).real       # a real baseband signal of the same bandwidth B (occupies −B…B)
    ratios = np.array([0.6, 0.8, 0.9, 0.95, 1.0, 1.05, 1.2, 1.5, 1.9, 2.0, 2.1, 2.5])
    snr_iq = np.array([resample_err(env, fs, k * B) for k in ratios])
    snr_re = np.array([resample_err(real_bb, fs, k * B) for k in ratios])
    thr = 40
    need_iq = ratios[np.argmax(snr_iq > thr)]; need_re = ratios[np.argmax(snr_re > thr)]
    p.compare("Complex (IQ) samples: minimum rate for > 40 dB reconstruction (× B)", 1.0, need_iq, "× B", kind="abs", tol=0.06)
    p.compare("Real samples, same bandwidth: minimum rate (× B)", 2.0, need_re, "× B", kind="abs", tol=0.11)
    p.compare("Real numbers per second needed: IQ vs real (ratio)", 1.0, (2 * need_iq) / need_re, "", tol=6)
    fig, ax = p.fig(1, 2, w=11)
    F = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs)) / 1e3
    ax[0].plot(F, db(np.fft.fftshift(np.abs(np.fft.fft(env))) + 1e-9), color=C_MEAS, lw=.6, label="complex envelope (one-sided, asymmetric)")
    ax[0].plot(F, db(np.fft.fftshift(np.abs(np.fft.fft(real_bb))) + 1e-9), color=C_PRED, lw=.6, alpha=.7, label="real signal (mirror-symmetric)")
    ax[0].set_xlim(-30, 30); ax[0].set_ylim(0, 80)
    style_axes(ax[0], "frequency (kHz)", "|X| (dB)", "Spectra")
    ax[1].plot(ratios, snr_iq, "o-", color=C_MEAS, label="IQ (complex) sampling"); ax[1].plot(ratios, snr_re, "s-", color=C_PRED, label="real sampling")
    ax[1].axvline(1, color=C_MEAS, ls=":"); ax[1].axvline(2, color=C_PRED, ls=":")
    style_axes(ax[1], "sample rate / B", "reconstruction SNR (dB)", "Aliasing sets in below B (IQ) or 2B (real)")
    p.save(fig, "iq", "Spectra of a complex envelope and a real signal of equal bandwidth, and reconstruction quality vs sample rate.")
    p.discuss("""The measured thresholds sit exactly where the theory says: complex samples reconstruct the envelope perfectly once the rate reaches B, real samples
of a signal with the same bandwidth need 2B. Counting real numbers, IQ sampling at B and real sampling at 2B cost the same — the saving is not in
data but in *analog* bandwidth: each ADC in an IQ receiver runs at half the rate and sees only half the bandwidth, which is why SDRs quote a
complex sample rate equal to their usable bandwidth. The asymmetric spectrum is the key: a complex envelope carries independent information at
+f and −f, which a real signal cannot.""")
# tol-convention: relative tolerances are in percent
