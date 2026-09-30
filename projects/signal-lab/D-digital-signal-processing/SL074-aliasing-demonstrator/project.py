from eelab import *

META = dict(
    id="SL-074", title="Aliasing demonstrator (Nyquist in action)", level="E",
    tools="NumPy sampling + FFT peak finding",
    summary="Sample sinusoids from 0 to 3·f_s and measure the apparent frequency, reproducing the folding "
            "saw-tooth predicted by f_alias = |f − k·f_s|; show a wagon-wheel style visual example.",
    problem="What frequency do you *see* when you sample a signal faster than half your sampling rate?",
    theory=r"""Samples of $\cos(2\pi f n/f_s)$ are identical for $f$ and $f \pm kf_s$ and for $-f$. The apparent frequency is
$f_a = |f - f_s\,\mathrm{round}(f/f_s)|$ ∈ [0, f_s/2] — a triangle wave in f with period f_s. Nyquist: frequencies
below f_s/2 are recovered exactly.""",
    method="""f_s = 1000 Hz, 1-s records, 301 test frequencies from 0 to 3000 Hz; apparent frequency from the FFT peak with
parabolic interpolation. Visual: a 1030 Hz sine sampled at 1 kHz looks like a 30 Hz sine.""",
)


def run(p):
    fs = 1000.0
    n = np.arange(int(fs))
    fr = np.linspace(0, 3000, 301)
    meas = []
    for f in fr:
        x = np.cos(2 * pi * f * n / fs + 0.3)
        X = np.abs(np.fft.rfft(x * np.hanning(len(x)), 8 * len(x)))
        k = np.argmax(X)
        if 0 < k < len(X) - 1:
            a, b, c = np.log(X[k - 1:k + 2] + 1e-12); k = k + 0.5 * (a - c) / (a - 2 * b + c)
        meas.append(k * fs / (8 * len(x)))
    meas = np.array(meas)
    pred = np.abs(fr - fs * np.round(fr / fs))
    err = np.max(np.abs(meas - pred)[(pred > 5) & (pred < fs / 2 - 5)])
    p.compare("Max |apparent − predicted| over 301 tones (away from 0 and f_s/2)", 0, err, "Hz", kind="abs")
    for f in (300, 700, 2480):
        p.compare(f"Apparent frequency of {f} Hz", float(abs(f - fs * round(f / fs))), float(meas[np.argmin(abs(fr - f))]), "Hz", kind="abs")
    x = np.cos(2 * pi * 1030 * n / fs + 0.3)
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), 8 * len(x))); fa = np.argmax(X) * fs / (8 * len(x))
    p.compare("Apparent frequency of 1030 Hz", 30, fa, "Hz", kind="abs")
    fig, ax = p.fig(1, 2)
    ax[0].plot(fr, pred, "--", color=C_PRED, label="|f − f_s·round(f/f_s)|")
    ax[0].plot(fr, meas, ".", color=C_MEAS, ms=4, label="measured FFT peak")
    ax[0].axhline(fs / 2, color="gray", ls=":", lw=1)
    style_axes(ax[0], "true frequency (Hz)", "apparent frequency (Hz)", "Frequency folding")
    tt = np.linspace(0, 0.05, 5000)
    ax[1].plot(tt * 1e3, np.cos(2 * pi * 1030 * tt + 0.3), color="gray", lw=.6, label="1030 Hz signal")
    ns = np.arange(0, 51)
    ax[1].plot(ns, np.cos(2 * pi * 1030 * ns / fs + 0.3), "o", color=C_MEAS, ms=4, label="samples at 1 kHz")
    ax[1].plot(tt * 1e3, np.cos(2 * pi * 30 * tt + 0.3), "--", color=C_PRED, label="30 Hz alias")
    style_axes(ax[1], "time (ms)", "amplitude", "Sampling a 1030 Hz tone at 1 kHz")
    p.save(fig, "aliasing", "The measured apparent frequency traces the predicted triangle exactly.")
    p.csv("folding", true_hz=fr, apparent_hz=meas, predicted_hz=pred)
    p.discuss("""The measured apparent frequency lies on the predicted folding triangle for all 301 tones (errors only at
the fold points 0 and f_s/2, where a tone and its mirror image merge into one peak). The 1030 Hz example is the
wagon-wheel effect: the samples fit a 30 Hz cosine perfectly, so after sampling no algorithm can tell the two
apart — which is why the anti-aliasing filter must come *before* the ADC.""")
