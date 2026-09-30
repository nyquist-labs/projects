from eelab import *

META = dict(
    id="SL-079", title="Wavelet multi-resolution analysis of a transient", level="H",
    tools="Own Haar and Daubechies-4 discrete wavelet transform (lifting-free filter-bank form), NumPy",
    summary="Implement a DWT filter bank, verify perfect reconstruction, and compare wavelets with the FFT "
            "at localising a short transient and compacting a signal's energy into few coefficients.",
    problem="The FFT says *which* frequencies are present but not *when*. Can wavelets locate a 5 ms click "
            "inside a second of signal, and represent it with far fewer coefficients?",
    theory=r"""A DWT splits a signal with a low-pass/high-pass quadrature-mirror pair and downsamples by 2, repeating on the
low band: level j has time resolution $2^j$ samples. Orthogonal wavelets (Haar, db4) conserve energy
(Parseval) and reconstruct perfectly. A transient of duration T appears as large coefficients only at levels
whose scale ≈ T and only at its location, so its energy compacts into ~log levels × few coefficients, whereas
the FFT spreads it over all bins.""",
    method="""Signal: 1 s at 4096 Hz: two sines (40, 120 Hz) + a 5 ms decaying 600 Hz click at t = 0.62 s + white noise (σ = 0.05).
db4 filters from the published coefficients. 6-level decomposition, reconstruction error, location of the largest
detail coefficient at the click's scale, and the number of coefficients holding 99 % of the click's energy in
the DWT vs FFT domain.""",
)

DB4 = np.array([0.48296291314469025, 0.83651630373746899, 0.22414386804185735, -0.12940952255092145])


def filters(name):
    h = np.array([1, 1]) / np.sqrt(2) if name == "haar" else DB4
    g = h[::-1] * (-1) ** np.arange(len(h))
    return h, g


def dwt(x, h, g):
    N = len(x); L = len(h)
    idx = (np.arange(0, N, 2)[:, None] + np.arange(L)[None, :]) % N
    return x[idx] @ h, x[idx] @ g


def idwt(a, d, h, g):
    N = 2 * len(a); L = len(h); x = np.zeros(N)
    for k in range(len(a)):
        for m in range(L):
            x[(2 * k + m) % N] += a[k] * h[m] + d[k] * g[m]
    return x


def wavedec(x, name, levels):
    h, g = filters(name); ds = []; a = x
    for _ in range(levels):
        a, d = dwt(a, h, g); ds.append(d)
    return a, ds


def waverec(a, ds, name):
    h, g = filters(name)
    for d in ds[::-1]:
        a = idwt(a, d, h, g)
    return a


def run(p):
    fs, N = 4096, 4096
    t = np.arange(N) / fs
    click = np.where((t >= 0.62) & (t < 0.625), np.exp(-(t - 0.62) / 0.0015) * np.sin(2 * pi * 600 * (t - 0.62)), 0) * 2
    base = np.sin(2 * pi * 40 * t) + 0.5 * np.sin(2 * pi * 120 * t)
    x = base + click + 0.05 * p.rng.normal(size=N)
    for name in ("haar", "db4"):
        a, ds = wavedec(x, name, 6)
        xr = waverec(a, ds, name)
        p.compare(f"{name}: perfect reconstruction error (max |Δ|)", 0, np.max(abs(xr - x)), "", kind="abs")
        e = np.sum(a**2) + sum(np.sum(d**2) for d in ds)
        p.compare(f"{name}: energy conservation (Parseval)", np.sum(x**2), e, "", tol=1e-6)
    a, ds = wavedec(x, "db4", 6)
    lvl = 2   # scale 2^2..2^3 samples ≈ 600 Hz band (512–1024 Hz at fs=4096)
    k = np.argmax(np.abs(ds[lvl]))
    t_loc = (k * 2 ** (lvl + 1)) / fs
    p.compare("Click location from largest level-3 detail coefficient", 0.62, t_loc, "s", kind="abs",
              note=f"resolution {2**(lvl+1)/fs*1e3:.1f} ms")
    ac, dc = wavedec(click, "db4", 6)
    coefs = np.sort(np.abs(np.r_[ac, np.concatenate(dc)]))[::-1] ** 2
    n99w = np.argmax(np.cumsum(coefs) >= 0.99 * coefs.sum()) + 1
    F = np.sort(np.abs(np.fft.fft(click)) ** 2)[::-1]
    n99f = np.argmax(np.cumsum(F) >= 0.99 * F.sum()) + 1
    p.metric("Coefficients for 99 % of click energy: db4 DWT", n99w)
    p.metric("Coefficients for 99 % of click energy: FFT", n99f)
    p.metric("Compaction advantage of DWT over FFT for the click", n99f / n99w, "×")
    fig, ax = p.fig(8, 1, w=8, h=9, sharex=True)
    ax[0].plot(t, x, color="gray", lw=.5); ax[0].set_ylabel("x", rotation=0, labelpad=15)
    for j, d in enumerate(ds):
        tt = (np.arange(len(d)) + 0.5) * 2 ** (j + 1) / fs
        ax[j + 1].plot(tt, d, color=COLORS[j % 8], lw=.8)
        ax[j + 1].set_ylabel(f"d{j+1}", rotation=0, labelpad=15)
        ax[j + 1].axvline(0.62, color=C_PRED, lw=.6, ls=":")
    ax[7].plot((np.arange(len(a)) + 0.5) * 2**6 / fs, a, color="black", lw=.8); ax[7].set_ylabel("a6", rotation=0, labelpad=15)
    ax[7].set_xlabel("time (s)")
    ax[0].set_title("db4 wavelet decomposition: the click lights up at t = 0.62 s in the fine levels", loc="left")
    p.save(fig, "decomposition", "Fine detail levels are quiet except at the click; the sines live in the coarse approximation.")
    fig, ax = p.fig()
    ax.semilogy(np.arange(1, 400), coefs[:399] / coefs.sum(), color=C_MEAS, label="db4 DWT coefficients")
    ax.semilogy(np.arange(1, 400), F[:399] / F.sum(), color=COLORS[1], label="FFT bins")
    style_axes(ax, "rank", "fraction of click energy", "Energy compaction of a transient")
    p.save(fig, "compaction", "The DWT packs the click into a few dozen coefficients; the FFT needs hundreds.")
    p.discuss("""Both wavelets reconstruct the signal to machine precision and conserve energy, as orthogonal filter banks must.
The click, invisible in the FFT's global view, is located to within one coefficient of level 3 (2 ms). Its energy
compacts into a few dozen DWT coefficients versus hundreds of FFT bins — the property behind wavelet compression
(JPEG 2000) and wavelet denoising: keep the few big coefficients, zero the rest.""")
