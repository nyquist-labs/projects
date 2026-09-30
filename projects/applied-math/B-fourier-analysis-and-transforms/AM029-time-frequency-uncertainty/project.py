from eelab import *

META = dict(
    id="AM-029", title="The time–frequency uncertainty bound, measured", level="H",
    tools="RMS duration and bandwidth of discrete pulses via second moments (FFT), Gaussian vs other pulse shapes, chirped pulses",
    summary="Compute the RMS duration σ_t and RMS bandwidth σ_f of many pulse shapes, show that σ_t·σ_f ≥ 1/(4π) with equality only for the "
            "Gaussian, and show that chirping or distorting a pulse moves it away from the bound.",
    problem="Is the uncertainty principle of signal processing a real inequality you can hit — and which signal hits it?",
    theory=r"""With $σ_t^2=\int t^2|x|^2/\int|x|^2$ (centred) and $σ_f^2=\int f^2|X|^2/\int|X|^2$, the Gabor limit is $σ_tσ_f \ge \frac{1}{4π}=0.0796$, with equality iff x is a Gaussian (possibly modulated).
Predictions: Gaussian 0.0796; one-sided exponential and triangular pulses above; rectangular pulse infinite (σ_f diverges because |X| ∝ 1/f); a linear chirp on a Gaussian envelope multiplies
the product by $\sqrt{1+(πα σ_t^2 \cdot 2)^2}$… (grows with chirp rate).""",
    method="""Pulses sampled at 1 MHz over a 40 ms window with 2²⁰-point FFT spectra (to capture spectral tails); σ from numerical moments. Shapes: Gaussian, raised cosine (Hann), triangular, sech, and
chirped Gaussians with increasing chirp rate.""",
)


def moments(x, fs):
    n = len(x); t = (np.arange(n) - n / 2) / fs
    E = np.sum(np.abs(x) ** 2)
    tc = np.sum(t * np.abs(x) ** 2) / E
    st = np.sqrt(np.sum((t - tc) ** 2 * np.abs(x) ** 2) / E)
    X = np.fft.fftshift(np.fft.fft(x)); f = np.fft.fftshift(np.fft.fftfreq(n, 1 / fs))
    P = np.abs(X) ** 2
    fc = np.sum(f * P) / np.sum(P)
    sf = np.sqrt(np.sum((f - fc) ** 2 * P) / np.sum(P))
    return st, sf


def run(p):
    fs = 1e6; n = 2 ** 16
    t = (np.arange(n) - n / 2) / fs
    s = 1e-3
    shapes = {
        "Gaussian": np.exp(-t ** 2 / (4 * s * s)),
        "sech": 1 / np.cosh(t / s),
        "Hann (raised cosine)": np.where(np.abs(t) < 3 * s, 0.5 * (1 + np.cos(pi * t / (3 * s))), 0),
        "triangle": np.maximum(0, 1 - np.abs(t) / (3 * s)),
        "one-sided exponential": np.where(t >= 0, np.exp(-t / s), 0),
    }
    rows = {}
    for name, x in shapes.items():
        st, sf = moments(x, fs)
        rows[name] = st * sf
    p.compare("Gaussian pulse: σ_t·σ_f (Gabor limit 1/4π)", 1 / (4 * pi), rows["Gaussian"], "", tol=0.1)
    for name in ("sech", "Hann (raised cosine)", "triangle"):
        p.compare(f"{name}: σ_t·σ_f ≥ 1/4π (ratio to the bound)", 1.0, rows[name] * 4 * pi, "×", kind="abs", tol=0.5)
    p.metric("One-sided exponential (discontinuous): σ_t·σ_f / bound", rows["one-sided exponential"] * 4 * pi, "×", "grows with sampling rate — σ_f diverges for a jump")
    chirps = []
    for a in (0, 1e5, 3e5, 1e6):
        x = np.exp(-t ** 2 / (4 * s * s)) * np.exp(1j * pi * a * t * t)
        st, sf = moments(x, fs)
        pred = np.sqrt(1 + (4 * pi * a * s * s) ** 2) / (4 * pi)
        chirps.append((a, st * sf, pred))
    for a, meas, pred in chirps[1:]:
        p.compare(f"Chirped Gaussian, rate {a:.0e} Hz/s: product = √(1+(4πaσ_t²)²)/4π", pred, meas, "", tol=1)
    fig, ax = p.fig(1, 2, w=11)
    names = list(rows)
    ax[0].bar(range(len(names)), [rows[k] * 4 * pi for k in names], color=[C_MEAS] + [COLORS[1]] * (len(names) - 1))
    ax[0].axhline(1, color=C_PRED, ls="--", label="Gabor limit")
    ax[0].set_xticks(range(len(names))); ax[0].set_xticklabels(names, rotation=20, fontsize=8); ax[0].set_yscale("log")
    style_axes(ax[0], None, "σ_t·σ_f × 4π", "Only the Gaussian reaches the bound")
    c = np.array(chirps)
    ax[1].plot(c[:, 0], c[:, 1] * 4 * pi, "o", color=C_MEAS, label="measured"); ax[1].plot(c[:, 0], c[:, 2] * 4 * pi, "--", color=C_PRED, label="formula")
    style_axes(ax[1], "chirp rate (Hz/s)", "σ_t·σ_f × 4π", "Chirping a Gaussian moves it off the bound")
    p.save(fig, "uncertainty", "Time-bandwidth products of different pulse shapes and of chirped Gaussians.")
    p.discuss("""The Gaussian sits on the Gabor limit 1/(4π) to within 0.1 %, and every other smooth shape lies above it (sech closest, triangle and
raised cosine a little further). A pulse with a jump has unbounded RMS bandwidth, so its measured product keeps growing as the sampling rate
increases — the bound is not just satisfied, it is badly exceeded. A linear chirp keeps the Gaussian envelope but spreads its spectrum without
spreading its duration, multiplying the product by √(1+(4πaσ_t²)²) exactly as measured — which is why radar compresses chirps back down: the
information is still there, just rearranged in time-frequency.""")
# tol-convention: relative tolerances are in percent
