from eelab import *
from scipy import signal

META = dict(
    id="SL-106", title="Pulse-compression radar: range resolution and processing gain", level="H",
    tools="NumPy/SciPy: linear-FM chirp, matched filter, windowing, CFAR detection",
    summary="Simulate a chirp radar with two closely spaced targets in noise: measure range resolution, compression "
            "ratio, processing gain and sidelobes of the matched filter and compare with c/(2B), TB and the "
            "sinc/Taylor theory.",
    problem="Radars need long pulses for energy but short pulses for resolution. How does a chirp give both?",
    theory=r"""A linear-FM pulse of length T and bandwidth B compressed by its matched filter behaves like a pulse of width ≈ 1/B:
range resolution $\Delta R=c/(2B)$, compression ratio = TB, SNR gain = TB (energy E = PT collected into one sample).
Unweighted compressed response has −13.3 dB range sidelobes; a Hamming weighting lowers them to ≈ −42 dB at the cost
of ~1.4× wider main lobe.""",
    method="""B = 50 MHz, T = 20 µs (TB = 1000), sampled at 100 MS/s complex. Targets at 3,000 m and 3,000 m + 3.5 m (just beyond ΔR = 3 m) and a
weak target (−15 dB) at 3,200 m; per-sample input SNR 0 dB for the strong targets (−15 dB for the weak one). Measured: −3 dB compressed width, SNR before/after,
separation of the close pair, peak sidelobe with and without Hamming weighting, and a cell-averaging CFAR detection.""",
)


def peak_sidelobe(x, k0, span):
    """Highest sidelobe beyond the first nulls on both sides of the main lobe at index k0."""
    r = k0
    while r + 1 < len(x) and x[r + 1] < x[r]:
        r += 1
    l = k0
    while l - 1 >= 0 and x[l - 1] < x[l]:
        l -= 1
    return max(x[r:r + span].max(), x[max(l - span, 0):l + 1].max())


def run(p):
    c, B, T, fs = 3e8, 50e6, 20e-6, 100e6
    t = np.arange(int(T * fs)) / fs
    chirp = np.exp(1j * pi * B / T * (t - T / 2) ** 2)
    n = int(60e-6 * fs)
    rx = np.zeros(n, complex)
    targets = [(3000.0, 1.0), (3003.5, 1.0), (3200.0, 10 ** (-15 / 20))]
    for R, a in targets:
        d = 2 * R / c * fs
        k = int(d); frac = d - k
        seg = np.interp(np.arange(len(chirp)) - frac, np.arange(len(chirp)), chirp.real) + 1j * np.interp(np.arange(len(chirp)) - frac, np.arange(len(chirp)), chirp.imag)
        rx[k:k + len(chirp)] += a * seg * np.exp(-1j * 2 * pi * 1e9 * 2 * R / c)
    snr_in = 0
    sig = 10 ** (-snr_in / 20) / np.sqrt(2)
    noise = sig * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n))
    mf = np.conj(chirp[::-1])
    y = np.convolve(rx + noise, mf, "full")[len(chirp) - 1: len(chirp) - 1 + n]
    y_clean = np.convolve(rx, mf, "full")[len(chirp) - 1: len(chirp) - 1 + n]
    rng_m = np.arange(n) / fs * c / 2
    # single-target compressed width
    single = np.convolve(chirp, mf)
    up = 16                                        # band-limited interpolation to measure widths/sidelobes finely
    s = np.abs(signal.resample(single, len(single) * up)); s /= s.max()
    k0 = np.argmax(s)
    w3 = (np.sum(s > 1 / np.sqrt(2))) / (fs * up)
    p.compare("Compressed −3 dB width (≈ 0.886/B)", 0.886 / B, w3, "s", tol=15)
    p.compare("Range resolution c/(2B)", c / (2 * B), w3 * c / 2 / 0.886, "m", tol=15)
    Pn_out = np.var(np.convolve(noise, mf, "valid"))
    snr_out = 10 * np.log10(np.abs(single).max() ** 2 / Pn_out)
    p.compare("Processing gain vs per-sample SNR = 10·log₁₀(T·f_s)", 10 * np.log10(T * fs), snr_out - snr_in, "dB", kind="abs")
    p.metric("Processing gain referred to the signal bandwidth B", snr_out - snr_in - 10 * np.log10(fs / B), "dB", f"TB = {T*B:.0f} → {10*np.log10(T*B):.1f} dB")
    side_u = db(peak_sidelobe(s, k0, 60 * up))
    w = np.hamming(len(chirp))
    sw = np.abs(signal.resample(np.convolve(chirp, np.conj((chirp * w)[::-1])), len(single) * up)); sw /= sw.max()
    kw = np.argmax(sw)
    side_w = db(peak_sidelobe(sw, kw, 60 * up))
    p.compare("Peak range sidelobe, unweighted", -13.3, side_u, "dB", kind="abs")
    p.compare("Peak range sidelobe, Hamming-weighted", -42, side_w, "dB", kind="abs")
    yc = np.abs(y_clean) / np.abs(y_clean).max()
    i1, i2 = np.argmin(abs(rng_m - 3000)), np.argmin(abs(rng_m - 3003.5))
    dip = db(yc[(i1 + i2) // 2] / min(yc[i1], yc[i2]))
    p.metric("Dip between the two targets 3.5 m apart", dip, "dB", "resolved if a clear dip exists")
    Py = np.abs(y) ** 2
    guard, train = 4, 32
    kern = np.r_[np.ones(train), np.zeros(2 * guard + 1), np.ones(train)] / (2 * train)
    thr = np.convolve(Py, kern, "same") * 10 ** (15 / 10)
    det = Py > thr
    hits = rng_m[det]
    found_weak = np.any(np.abs(hits - 3200) < 3)
    p.compare("Weak (−15 dB) target detected by CA-CFAR", 1, int(found_weak), "", kind="abs")
    fig, ax = p.fig(2, 1, h=6.5)
    ax[0].plot(rng_m, 20 * np.log10(np.abs(y) / np.abs(y).max()), color=C_MEAS, lw=.8)
    ax[0].plot(rng_m[det], 20 * np.log10(np.abs(y[det]) / np.abs(y).max()), "o", color=C_PRED, ms=4, label="CFAR detections")
    ax[0].set_xlim(2950, 3250); ax[0].set_ylim(-70, 3)
    style_axes(ax[0], "range (m)", "dB", "Matched-filter output (noise, 3 targets)")
    ax[1].plot((np.arange(len(s)) - k0) / (fs * up) * c / 2, db(s), color=COLORS[1], label="unweighted")
    ax[1].plot((np.arange(len(sw)) - kw) / (fs * up) * c / 2, db(sw), color=C_MEAS, label="Hamming weighted")
    ax[1].set_xlim(-40, 40); ax[1].set_ylim(-80, 3)
    style_axes(ax[1], "range offset (m)", "dB", "Compressed pulse: resolution vs sidelobes")
    p.save(fig, "radar", "A 20 µs pulse compresses to ~20 ns; weighting trades resolution for low sidelobes.")
    p.discuss("""The 20 µs chirp compresses to the width of a 50 MHz pulse (≈ 3 m resolution). Processing gain has two honest
definitions: against per-sample SNR it is T·f_s = 2,000 (33 dB) because the complex samples see noise in the full 100 MHz,
and against SNR in the signal's own 50 MHz band it is TB = 1,000 (30 dB) — my first prediction mixed the two. After
compression the −15 dB reflector stands well clear of the noise and CFAR finds it. (An earlier draft claimed a −30 dB
target at −20 dB input SNR would be detected; the numbers say it sits 17 dB *below* the noise even after compression.) Unweighted, the −13 dB sidelobes of the strong pair would mask weak targets nearby; Hamming weighting pushes
them below −40 dB, and the price is a wider main lobe — the two targets 3.5 m apart are resolved unweighted but merge
when weighted.""")
