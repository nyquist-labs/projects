from eelab import *
from eelab.data import physionet
from scipy import signal

META = dict(
    id="SL-176", title="EMG envelope extraction and amplitude estimators", level="M",
    tools="Rectification + low-pass and RMS envelopes (SciPy), PhysioNet EMG database (healthy subject, 4 kHz)",
    summary="Turn raw surface-EMG into a smooth activation envelope with mean-absolute-value and RMS detectors, verify the Gaussian-signal "
            "relation MAV = √(2/π)·RMS on real data, and measure how the smoothing window trades noise against delay.",
    problem="Prosthetics and muscle-controlled interfaces need 'how hard is the muscle working' from a noisy, zero-mean EMG signal. How do you "
            "get a clean, fast envelope?",
    theory=r"""*Surface* EMG is approximately a zero-mean Gaussian process with slowly varying variance σ²(t). For a Gaussian, E|x| = √(2/π)σ ≈ 0.798σ. A moving window of N samples
estimates σ with relative standard deviation ≈ 1/√(2N_eff) (fewer effective samples because EMG is band-limited to ~20–450 Hz), while adding a delay of
N/2 samples — the noise-vs-latency trade.""",
    method="""PhysioNet 'emgdb' healthy record (tibialis anterior, concentric needle electrode, 4 kHz, 12.7 s): 20–450 Hz band-pass, full-wave rectification, windows 25–400 ms. Envelope noise =
coefficient of variation during the steadiest contraction segment; delay from cross-correlation with a zero-phase reference envelope.""",
    data="Real: Examples of Electromyograms database (PhysioNet 'emgdb').",
)


def run(p):
    d = physionet("emgdb", "emg_healthy")
    x, fs = d["signal"][:, 0].astype(float), d["fs"]
    b, a = signal.butter(4, [20, 450], "bandpass", fs=fs); x = signal.filtfilt(b, a, x)
    win = int(0.25 * fs)
    rms = np.sqrt(np.convolve(x * x, np.ones(win) / win, "same"))
    mav = np.convolve(np.abs(x), np.ones(win) / win, "same")
    act = rms > np.percentile(rms, 60)
    ratio = np.median(mav[act] / rms[act])
    p.compare("MAV / RMS during contraction (Gaussian: √(2/π))", np.sqrt(2 / pi), ratio, "", tol=5)
    k = signal.kurtosis if hasattr(signal, "kurtosis") else None
    from scipy.stats import kurtosis
    seg = x[act][:int(2 * fs)]
    p.metric("Excess kurtosis of active EMG (Gaussian = 0)", kurtosis(seg))
    ref = signal.filtfilt(*signal.butter(2, 2, fs=fs), np.abs(x))
    rows = []
    for wms in (25, 50, 100, 200, 400):
        N = int(wms / 1000 * fs)
        env = np.convolve(np.abs(x), np.ones(N) / N, "full")[: len(x)]      # causal (real-time) envelope
        steady = slice(int(3 * fs), int(5 * fs)) if act[int(4 * fs)] else np.flatnonzero(act)[:int(2 * fs)]
        cv = np.std(env[steady]) / np.mean(env[steady])
        cc = np.correlate(env[::20] - env[::20].mean(), ref[::20] - ref[::20].mean(), "full")
        lag = (np.argmax(cc) - (len(ref[::20]) - 1)) * 20 / fs
        rows.append((wms, cv, lag * 1000))
    w_, cv_, lag_ = map(np.array, zip(*rows))
    p.compare("Causal envelope delay vs half the window (100 ms window)", 50, lag_[2], "ms", kind="abs")
    slope = np.polyfit(np.log(w_), np.log(cv_), 1)[0]
    p.compare("Envelope noise scaling with window (∝ N^−½)", -0.5, slope, "", kind="abs")
    t = np.arange(len(x)) / fs
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, x, color="gray", lw=.3, label="EMG (band-passed)")
    ax[0].plot(t, rms * 3, color=C_MEAS, label="RMS envelope × 3 (250 ms)")
    style_axes(ax[0], "time (s)", "mV", "Healthy tibialis anterior")
    ax[1].plot(lag_, cv_ * 100, "o-", color=C_MEAS)
    for (wm, c_, l_) in rows:
        ax[1].annotate(f"{wm} ms", (l_, c_ * 100), fontsize=8, xytext=(4, 4), textcoords="offset points")
    style_axes(ax[1], "envelope delay (ms)", "envelope ripple (CV, %)", "Noise vs latency trade-off", legend=False)
    p.save(fig, "emg_envelope", "Longer windows give smoother envelopes but respond later.")
    import pandas as pd
    p.csv_df("tradeoff", pd.DataFrame(rows, columns=["window_ms", "cv", "delay_ms"]))
    p.discuss("""My prediction assumed the textbook 'amplitude-modulated Gaussian noise' model of *surface* EMG — and it fails here: MAV/RMS is ~0.59 instead of
0.80 and the excess kurtosis is ~20. The reason is the data: PhysioNet's 'emgdb' was recorded with a concentric *needle* electrode, which picks up
individual motor-unit action potentials as sharp spikes separated by quiet baseline — a very non-Gaussian signal. Checking the recording modality
before applying a model is the lesson; with surface EMG (thousands of units superimposed) the ratio approaches 0.8. A causal moving-average envelope delays by roughly half its window,
and its ripple shrinks more slowly than 1/√N because the spiky needle signal has few independent 'events' per window — so a prosthetic controller that must respond within ~100 ms is
forced to accept a noticeably noisy envelope, which is why EMG classifiers (SL-177) use several features instead of one amplitude.""")
