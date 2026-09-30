from eelab import *
from scipy import signal

META = dict(
    id="SL-187", title="Muscle fatigue: the EMG median-frequency shift", level="M",
    tools="Physiological surface-EMG synthesis (motor-unit action potentials with slowing conduction velocity), median/mean frequency estimation",
    summary="Show how slowing muscle-fibre conduction velocity during a sustained contraction compresses the EMG spectrum, predict the median-"
            "frequency decline from the velocity change, and measure the estimator's accuracy and variance on a synthetic 60-s contraction.",
    problem="Why does the EMG spectrum shift to lower frequencies as a muscle tires, and how precisely can the shift be tracked?",
    theory=r"""A motor-unit action potential travelling at conduction velocity v has a spectrum that scales with v: $S_v(f)=\frac{1}{v^2}\,S_1\!\left(\frac{f}{v}\right)$ (Lindström & Magnusson 1977).
Hence the median frequency is proportional to v: a 20 % fall in conduction velocity (typical over a fatiguing isometric contraction) lowers the median
frequency by 20 %. Spectral estimates from 1-s windows scatter by several percent.""",
    method="""Synthetic surface EMG (clearly labelled synthetic: no public dataset with ground-truth conduction velocity was available): 50 motor units, Poisson firing ~15 Hz,
tripolar MUAP shape whose time scale ∝ 1/v; v falls linearly from 4.5 to 3.6 m/s over 60 s; noise 20 dB below. Median frequency from Welch spectra in 1-s
windows (50 % overlap); linear regression of MDF(t).""",
    data="Synthetic (physiologically parameterised) — the ground-truth conduction velocity is known exactly.",
)


def run(p):
    fs, T = 2048, 60
    n = fs * T
    t = np.arange(n) / fs
    v = 4.5 - 0.9 * t / T
    x = np.zeros(n)
    rng_ = p.rng
    for mu in range(50):
        amp = rng_.uniform(0.3, 1.5); rate = rng_.uniform(10, 20)
        firings = np.cumsum(rng_.exponential(1 / rate, int(T * rate * 1.5)))
        firings = firings[firings < T - 0.05]
        for ft in firings:
            k = int(ft * fs)
            sc = 4.5 / v[k]
            tt = np.arange(-int(0.01 * fs * sc), int(0.01 * fs * sc)) / fs / (sc * 1e-3)
            muap = amp * (-tt * np.exp(-tt**2 / 2)) * (1 / sc)
            x[k: k + len(muap)] += muap[: max(0, min(len(muap), n - k))]
    x += rng_.normal(0, np.std(x) * 0.1, n)
    W = fs
    mdf, times = [], []
    for i in range(0, n - W, W // 2):
        f, P = signal.welch(x[i:i + W], fs, nperseg=256)
        c = np.cumsum(P); mdf.append(f[np.searchsorted(c, c[-1] / 2)]); times.append((i + W / 2) / fs)
    mdf, times = np.array(mdf), np.array(times)
    fit = np.polyfit(times, mdf, 1)
    m0, m1 = np.polyval(fit, 0), np.polyval(fit, T)
    p.compare("Relative median-frequency decline over 60 s (= relative velocity decline 20 %)", -20, (m1 - m0) / m0 * 100, "%", kind="abs")
    p.metric("Initial median frequency", m0, "Hz")
    resid = mdf - np.polyval(fit, times)
    p.metric("Scatter of 1-s MDF estimates about the trend", np.std(resid) / np.mean(mdf) * 100, "%")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(times, mdf, ".", color=C_MEAS, label="1-s MDF estimates"); ax[0].plot(times, np.polyval(fit, times), color=C_PRED, label="linear fit")
    ax[0].plot(times, m0 * (4.5 - 0.9 * times / T) / 4.5, "--", color="gray", label="∝ conduction velocity (truth)")
    style_axes(ax[0], "time (s)", "median frequency (Hz)", "Fatigue compresses the spectrum")
    for tt_, col in ((2, COLORS[0]), (58, COLORS[1])):
        f, P = signal.welch(x[int((tt_ - 1) * fs): int((tt_ + 1) * fs)], fs, nperseg=512)
        ax[1].plot(f, P / P.max(), color=col, label=f"t = {tt_} s")
    ax[1].set_xlim(0, 500)
    style_axes(ax[1], "frequency (Hz)", "normalised PSD", "Early vs late spectrum")
    p.save(fig, "fatigue", "As conduction velocity falls the whole spectrum slides to lower frequencies.")
    p.csv("mdf", t_s=times, mdf_hz=mdf)
    p.discuss("""The median frequency falls by the same fraction as the conduction velocity, confirming the spectral-scaling argument, and a regression over the
contraction recovers the ~20 % decline despite a few-percent scatter in each 1-s estimate. In real muscles the picture is complicated by
changing motor-unit recruitment and synchronisation, which also shift the spectrum — which is why MDF slope is used as a *relative* fatigue index
within one contraction, not an absolute measure between people. This project uses synthetic EMG deliberately, because it is the only way to know
the true conduction velocity.""")
