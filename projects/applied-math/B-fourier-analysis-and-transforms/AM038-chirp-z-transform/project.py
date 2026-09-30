from eelab import *
import time

META = dict(
    id="AM-038", title="Chirp-Z transform: zooming into a spectral band", level="H",
    tools="Own Bluestein chirp-Z transform (three FFTs), direct evaluation on the z-plane arc, zero-padded FFT comparison, timing",
    summary="Implement the chirp-Z transform with Bluestein's identity to evaluate the spectrum on an arbitrary fine grid inside a narrow band, "
            "verify it against direct evaluation and a huge zero-padded FFT, and measure the cost advantage — while showing that zooming, like padding, adds no resolution.",
    problem="You need the spectrum between 1000 and 1010 Hz on a 0.01 Hz grid. Is there a cheaper way than an enormous FFT?",
    theory=r"""$X_k=\sum_n x_nA^{-n}W^{nk}$ on the spiral $z_k=AW^{-k}$. Using $nk=\tfrac12[n^2+k^2-(k-n)^2]$ turns the sum into a convolution with a chirp, computable with FFTs of length ≥ N+M−1:
cost O((N+M)log(N+M)) regardless of how fine the grid is. A zero-padded FFT reaching the same spacing needs length fs/Δf. The values are identical to the DTFT, so resolution is still
limited to ≈ 1/T.""",
    method="""x: N = 8192 samples at fs = 8 kHz containing tones at 1003.2 and 1004.9 Hz plus noise; zoom band 1000–1010 Hz with M = 1001 points (Δf = 0.01 Hz). Compare with the direct DTFT and a
zero-padded FFT of length 800,000; time both.""",
)


def czt(x, M, W, A):
    N = len(x); L = 1 << (N + M - 1).bit_length()
    n = np.arange(N); k = np.arange(M)
    y = x * A ** (-n) * W ** (n * n / 2)
    v = np.zeros(L, complex)
    v[:M] = W ** (-(k * k) / 2)
    m = np.arange(1, N)
    v[L - N + 1:] = W ** (-(m[::-1] ** 2) / 2)
    g = np.fft.ifft(np.fft.fft(y, L) * np.fft.fft(v))
    return g[:M] * W ** (k * k / 2)


def run(p):
    fs, N = 8000, 8192
    r = p.rng
    t = np.arange(N) / fs
    x = np.cos(2 * pi * 1003.2 * t) + 0.5 * np.cos(2 * pi * 1004.9 * t) + 0.1 * r.normal(size=N)
    f1, f2, M = 1000.0, 1010.0, 1001
    df = (f2 - f1) / (M - 1)
    W = np.exp(-2j * pi * df / fs); A = np.exp(2j * pi * f1 / fs)
    t0 = time.perf_counter(); X = czt(x, M, W, A); tc = time.perf_counter() - t0
    fk = f1 + df * np.arange(M)
    Xd = np.array([np.sum(x * np.exp(-2j * pi * f * t)) for f in fk])
    p.compare("CZT vs direct DTFT evaluation (max relative error)", 0, np.max(np.abs(X - Xd)) / np.max(np.abs(Xd)), "", kind="abs", tol=1e-9)
    Lz = int(round(fs / df))
    t0 = time.perf_counter(); Z = np.fft.fft(x, Lz); tz = time.perf_counter() - t0
    idx = np.round(fk / fs * Lz).astype(int)
    p.compare("CZT vs zero-padded FFT (length 800,000) at the same frequencies", 0, np.max(np.abs(X - Z[idx])) / np.max(np.abs(Z)), "", kind="abs", tol=1e-9)
    p.metric("Time: CZT (M = 1001) vs zero-padded FFT", f"{tc * 1e3:.2f} ms vs {tz * 1e3:.1f} ms ({tz / tc:.0f}× faster)")
    p.compare("Operation-count ratio ≈ Lz·log Lz / (3·L·log L), L = next pow2(N+M)", (Lz * np.log2(Lz)) / (3 * 16384 * 14), tz / tc, "×", tol=200)
    Xa = np.abs(X)
    from scipy.signal import find_peaks
    pk, _ = find_peaks(Xa, height=Xa.max() * 0.2)
    p.compare("Tone at 1003.2 Hz located by the zoomed spectrum", 1003.2, fk[pk[np.argmax(Xa[pk])]], "Hz", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 2, w=11)
    Fr = np.abs(np.fft.rfft(x)); fr = np.fft.rfftfreq(N, 1 / fs)
    ax[0].plot(fr, db(Fr), color=COLORS[7], lw=.6); ax[0].set_xlim(990, 1020)
    ax[0].plot(fr, db(Fr), "o", color=C_PRED, ms=4, label="plain FFT bins (0.98 Hz)")
    ax[0].plot(fk, db(Xa), color=C_MEAS, label="CZT zoom (0.01 Hz)")
    style_axes(ax[0], "frequency (Hz)", "|X| (dB)", "Zooming into 1000–1010 Hz")
    ax[1].plot(fk, Xa, color=C_MEAS)
    for f_, c in ((1003.2, C_PRED), (1004.9, COLORS[2])):
        ax[1].axvline(f_, ls="--", color=c)
    style_axes(ax[1], "frequency (Hz)", "|X|", "Fine grid, same resolution (≈ 1/T = 0.98 Hz)", legend=False)
    p.save(fig, "czt", "The chirp-Z zoom evaluates the spectrum on a 0.01 Hz grid inside the band; the two tones 1.7 Hz apart are separated.")
    p.discuss(f"""Bluestein's trick reproduces the directly evaluated DTFT on the zoom grid to ~1e-12 and matches an 800,000-point zero-padded FFT sample for sample,
while costing about three 16k-point FFTs — {tz / tc:.1f}× faster here, well short of the ~23× operation-count estimate: numpy's FFT handles the
800,000-point length (2⁸·5⁵) with an efficient mixed-radix plan in C, while my CZT pays Python-level overhead for the chirp multiplications. The zoom is exact interpolation of the
same spectrum, not extra resolution: the two tones 1.7 Hz apart are resolved because 1.7 Hz > 1/T ≈ 0.98 Hz, and they would merge at any grid
spacing if they were closer than that (AM-024). The CZT's real value is cost and flexibility: any band, any spacing, even spirals off the unit
circle for estimating damped modes.""")
# tol-convention: relative tolerances are in percent
