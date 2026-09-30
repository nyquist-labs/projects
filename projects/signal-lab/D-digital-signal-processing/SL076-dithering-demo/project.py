from eelab import *

META = dict(
    id="SL-076", title="Dither: trading distortion for noise", level="M",
    tools="NumPy quantiser, RPDF/TPDF dither, harmonic analysis",
    summary="Quantise a very quiet tone (1–2 LSB) with no dither, RPDF and TPDF dither; measure harmonic "
            "distortion, noise floor and noise modulation to show why adding noise helps.",
    problem="Why do mastering engineers add noise to audio before reducing its bit depth?",
    theory=r"""Undithered, a signal of ~1 LSB turns into a square-ish wave: all error lands on odd harmonics (THD of tens of %).
Adding dither of variance σ² before quantising makes the error independent of the signal. RPDF (±½ LSB uniform)
decorrelates the *mean* error; TPDF (sum of two uniform, ±1 LSB) also makes the error *power* independent of the
signal (no noise modulation). Cost: total noise power rises from Δ²/12 to Δ²/12 + σ²_d:
+3.0 dB for RPDF, +4.8 dB for TPDF.""",
    method="""16-bit-scale quantiser (Δ = 1 LSB), tone of 1.3 LSB amplitude at 1 kHz, f_s = 48 kHz, 2¹⁷ samples. Measured:
THD (harmonics 2–15), total error power relative to Δ²/12, and noise modulation (error variance vs signal
level). Averaged power spectra over 16 segments.""",
)


def run(p):
    fs, Nn = 48000, 2**17
    n = np.arange(Nn)
    A = 1.3
    x = A * np.sin(2 * pi * 997 * n / fs)
    rng_ = p.rng
    variants = {"none": np.zeros(Nn), "RPDF": rng_.uniform(-.5, .5, Nn), "TPDF": rng_.uniform(-.5, .5, Nn) + rng_.uniform(-.5, .5, Nn)}
    fig, ax = p.fig()
    fr = np.fft.rfftfreq(8192, 1 / fs)
    for i, (nm, d) in enumerate(variants.items()):
        y = np.round(x + d)
        e = y - x
        pw = 10 * np.log10(np.mean(e**2) / (1 / 12))
        seg = y[: 16 * 8192].reshape(16, 8192) * np.hanning(8192)
        P = np.mean(np.abs(np.fft.rfft(seg, axis=1)) ** 2, axis=0)
        h = [P[np.argmin(abs(fr - k * 997))] for k in range(1, 16)]
        thd = 10 * np.log10(np.sum(h[1:]) / h[0])
        lvl = np.abs(x) < 0.25
        mod = np.var(e[lvl]) / np.var(e[~lvl])
        pred = {"none": 0.0, "RPDF": 3.01, "TPDF": 4.77}[nm]
        if nm != "none":
            p.compare(f"{nm}: total error power re Δ²/12", pred, pw, "dB", kind="abs")
        p.metric(f"{nm}: THD (harmonics 2–15)", thd, "dB")
        p.metric(f"{nm}: noise modulation (var near zero / var at peaks)", mod, "", "1.0 = no modulation")
        ax.plot(fr / 1e3, 10 * np.log10(P / P.max()), color=COLORS[i], lw=.8, label=f"{nm} (THD {thd:.0f} dB)")
        if nm == "TPDF":
            p.compare("TPDF: noise modulation ratio", 1.0, mod, "", kind="abs")
    ax.set_xlim(0, 12); ax.set_ylim(-110, 3)
    style_axes(ax, "frequency (kHz)", "relative power (dB)", "1.3-LSB tone quantised with and without dither")
    p.save(fig, "spectra", "Without dither: a comb of odd harmonics. With dither: a clean tone on a flat noise floor.")
    fig, ax = p.fig()
    k = slice(0, 200)
    ax.plot(n[k] / fs * 1e3, x[k], color="gray", lw=1, label="input (1.3 LSB)")
    ax.step(n[k] / fs * 1e3, np.round(x)[k], where="mid", color=COLORS[0], label="no dither")
    ax.step(n[k] / fs * 1e3, np.round(x + variants["TPDF"])[k], where="mid", color=COLORS[1], lw=.7, label="TPDF dither")
    style_axes(ax, "time (ms)", "LSB", "Time domain: dither turns a staircase into noise around the true signal")
    p.save(fig, "time_domain", "The dithered output averages to the input; the undithered one is a fixed distorted shape.")
    p.discuss("""Without dither the 1.3-LSB tone becomes a three-level staircase with strong odd harmonics. RPDF and TPDF dither
remove the harmonics entirely at the predicted noise costs (+3.0 dB, +4.8 dB over the bare Δ²/12). Only TPDF
makes the error power independent of the signal level (noise-modulation ratio ≈ 1) — RPDF still 'breathes'
with the music, which the ear notices on fade-outs. Hence TPDF is the standard when reducing to 16 bits.""")
