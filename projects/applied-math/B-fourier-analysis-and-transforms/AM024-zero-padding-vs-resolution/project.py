from eelab import *
from scipy import signal

META = dict(
    id="AM-024", title="Zero-padding vs resolution: what interpolation does not add", level="E",
    tools="FFT with and without zero-padding, two-tone resolution test, peak-dip criterion",
    summary="Show that zero-padding interpolates the spectrum (sharper-looking peaks, better frequency *estimates*) but cannot separate two tones "
            "closer than about 1/T — only a longer record can. The resolvability threshold is predicted and measured.",
    problem="Padding an FFT with zeros makes the spectrum look smoother. Does it improve resolution?",
    theory=r"""The spectrum of an N-sample record is the true spectrum convolved with the window's transform (mainlobe width ∝ 1/T). Zero-padding samples that same smooth function more
densely — it adds no information. Two equal tones produce two distinct peaks only when separated by more than ≈ 1/T (rectangular window) — and because coherent tones
interfere, whether a dip appears near that limit depends on their relative phase, so the test uses the median over phases. Frequency *estimation* of a single tone, however, improves with padding (peak-picking error ≤ half a bin → shrinks).""",
    method="""fs = 1 kHz, N = 100 (T = 0.1 s). Two unit tones at 100 Hz and 100 + Δf; Δf·T from 0.5 to 2.5; median dip depth over 24 relative phases, padding ×8 and ×64; also a record of N = 200.
Single-tone frequency estimate error vs padding.""",
)


def dip(x, pad, fs, f1, f2):
    T = len(x) / fs
    n = len(x) * pad
    X = np.abs(np.fft.rfft(x, n)); f = np.fft.rfftfreq(n, 1 / fs)
    band = (f > f1 - 0.3 / T) & (f < f2 + 0.3 / T)      # only the two mainlobes, never the sidelobes
    Xb, fb = X[band], f[band]
    pk, _ = signal.find_peaks(Xb)
    if len(pk) < 2:
        return 0.0
    top = pk[np.argsort(Xb[pk])[-2:]]; a, b = np.sort(top)
    return 1 - Xb[a:b + 1].min() / min(Xb[a], Xb[b])


def median_dip(N, pad, fs, rel_T, phases=24):
    """Median dip over relative tone phases (coherent tones interfere, so a single phase is not representative)."""
    T = N / fs; n = np.arange(N)
    out = []
    for r in rel_T:
        d = [dip(np.cos(2 * pi * 100 * n / fs) + np.cos(2 * pi * (100 + r / T) * n / fs + ph), pad, fs, 100, 100 + r / T)
             for ph in np.linspace(0, 2 * pi, phases, endpoint=False)]
        out.append(np.median(d))
    return np.array(out)


def run(p):
    fs, N = 1000, 100
    T = N / fs
    rel = np.linspace(0.5, 2.5, 41)
    res = {pad: median_dip(N, pad, fs, rel) for pad in (8, 64)}
    long = median_dip(2 * N, 64, fs, rel)                 # rel is Δf·T for the *long* record here
    thr = lambda d: rel[np.argmax(d > 0.05)]
    p.compare("Resolvable separation Δf·T with 64× padding (median dip > 5 % over phases)", 1.0, thr(res[64]), "", kind="abs", tol=0.2)
    p.compare("Same threshold with 8× padding (padding level does not matter)", thr(res[64]), thr(res[8]), "", kind="abs", tol=0.1)
    p.compare("Doubled record: threshold in units of its own T is unchanged, so Δf in Hz halves", thr(res[64]), thr(long), "", kind="abs", tol=0.1)
    r = p.rng
    errs = {}
    for pad in (1, 4, 16, 64):
        e = []
        for _ in range(300):
            f0 = r.uniform(80, 120)
            x = np.cos(2 * pi * f0 * np.arange(N) / fs + r.uniform(0, 2 * pi)) * np.hanning(N)
            X = np.abs(np.fft.rfft(x, N * pad)); f = np.fft.rfftfreq(N * pad, 1 / fs)
            e.append(f[np.argmax(X)] - f0)
        errs[pad] = np.sqrt(np.mean(np.square(e)))
    p.compare("Single-tone estimate RMS error without padding ≈ bin/√12", fs / N / np.sqrt(12), errs[1], "Hz", tol=20)
    p.metric("Single-tone RMS error with 64× padding", errs[64], "Hz", "interpolation *does* help estimation")
    fig, ax = p.fig(1, 2, w=11)
    for pad, c in zip((8, 64), COLORS):
        ax[0].plot(rel / T, res[pad] * 100, color=c, label=f"T = 0.1 s, pad ×{pad}")
    ax[0].plot(rel / (2 * T), long * 100, "--", color=C_PRED, label="T = 0.2 s (longer record)")
    style_axes(ax[0], "tone separation Δf (Hz)", "median dip between peaks (%)", "Only a longer record resolves closer tones")
    ax[1].loglog(list(errs), list(errs.values()), "o-", color=C_MEAS, label="measured")
    ax[1].loglog([1, 64], [fs / N / np.sqrt(12)] * 2, ":", color=C_PRED, label="bin/√12")
    style_axes(ax[1], "zero-padding factor", "RMS frequency error (Hz)", "But padding improves single-tone estimates")
    p.save(fig, "zeropad", "Two-tone resolvability vs separation for different padding factors and record lengths; single-tone estimation error vs padding.")
    p.discuss("""The dip that separates two equal tones appears at the same separation (≈ 1/T in the phase-median sense) whether the FFT is padded 8× or 64×,
and only doubling the actual record length halves that threshold in hertz. A first version used a single relative phase and got inconsistent
thresholds — near the resolution limit two coherent tones can cancel or reinforce between the peaks, which is itself a useful warning — zero-padding adds no information, it evaluates the same smeared spectrum on a
finer grid. That finer grid is still useful: for a single tone, the peak-picking error drops from bin/√12 (a uniform ±half-bin error) to the
limit set by the window and noise. Rule: pad to *locate* peaks, record longer to *separate* them.""")
# tol-convention: relative tolerances are in percent
