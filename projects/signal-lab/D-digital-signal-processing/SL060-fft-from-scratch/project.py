from eelab import *
import time

META = dict(
    id="SL-060", title="FFT from scratch (DFT → radix-2)", level="M",
    tools="NumPy (reference), pure-Python/NumPy implementations, timing benchmark",
    summary="Implement the O(N²) DFT and a recursive and an iterative radix-2 FFT, verify them against "
            "NumPy to machine precision and measure how runtime scales with N.",
    problem="Why is the FFT fast? Build it from the definition and measure the N² → N log N gap.",
    theory=r"""$X[k]=\sum_{n=0}^{N-1}x[n]e^{-j2\pi kn/N}$ costs $N^2$ complex multiplies. Radix-2 decimation in time splits even
and odd samples: $X[k]=E[k]+W_N^kO[k]$, $X[k+N/2]=E[k]-W_N^kO[k]$, giving $\frac N2\log_2N$ butterflies.
Predicted runtime ratio DFT/FFT for N = 1024: $\frac{N^2}{(N/2)\log_2N} = 205$ (same constant factors).
Round-off error of a float64 FFT grows like $O(\varepsilon\log N)$ ≈ 10⁻¹⁵.""",
    method="""Three implementations: matrix DFT (NumPy vectorised, to be fair to the DFT), recursive radix-2 (vectorised
butterflies), iterative in-place with bit reversal. Random complex inputs N = 2⁴…2¹²; error vs `numpy.fft.fft`
(max abs error / max |X|); runtime is the median of 5 runs.""",
)


def dft(x):
    N = len(x); n = np.arange(N)
    return np.exp(-2j * pi * np.outer(n, n) / N) @ x


def fft_rec(x):
    N = len(x)
    if N == 1:
        return x.copy()
    E, O = fft_rec(x[0::2]), fft_rec(x[1::2])
    W = np.exp(-2j * pi * np.arange(N // 2) / N) * O
    return np.concatenate([E + W, E - W])


def fft_iter(x):
    x = np.asarray(x, complex).copy(); N = len(x); bits = int(np.log2(N))
    rev = np.array([int(f"{i:0{bits}b}"[::-1], 2) for i in range(N)])
    x = x[rev]
    m = 2
    while m <= N:
        W = np.exp(-2j * pi * np.arange(m // 2) / m)
        x = x.reshape(-1, m)
        e, o = x[:, :m // 2].copy(), x[:, m // 2:] * W
        x[:, :m // 2], x[:, m // 2:] = e + o, e - o
        x = x.ravel(); m *= 2
    return x


def bench(f, x, reps=5):
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); f(x); ts.append(time.perf_counter() - t)
    return np.median(ts)


def run(p):
    Ns = 2 ** np.arange(4, 13)
    rows = []
    for N in Ns:
        x = p.rng.normal(size=N) + 1j * p.rng.normal(size=N)
        ref = np.fft.fft(x)
        e_d = np.max(abs(dft(x) - ref)) / np.max(abs(ref)) if N <= 4096 else np.nan
        e_r = np.max(abs(fft_rec(x) - ref)) / np.max(abs(ref))
        e_i = np.max(abs(fft_iter(x) - ref)) / np.max(abs(ref))
        rows.append((N, bench(dft, x, 3), bench(fft_rec, x), bench(fft_iter, x), bench(np.fft.fft, x), e_d, e_r, e_i))
    N_, tdft, trec, tit, tnp, ed, er, ei = map(np.array, zip(*rows))
    k = list(Ns).index(1024)
    p.compare("Max relative error, iterative FFT (N = 4096)", 1e-15 * np.log2(4096), ei[-1], "", kind="abs")
    p.compare("DFT/FFT runtime ratio at N = 1024 (op-count prediction)", 1024**2 / (512 * 10), tdft[k] / tit[k], "×")
    slope_dft = np.polyfit(np.log(N_[3:]), np.log(tdft[3:]), 1)[0]
    slope_fft = np.polyfit(np.log(N_[3:]), np.log(tit[3:] / np.log2(N_[3:])), 1)[0]
    p.compare("DFT runtime exponent (t ∝ N^a)", 2.0, slope_dft, "", kind="abs")
    p.compare("FFT runtime exponent after dividing by log₂N", 1.0, slope_fft, "", kind="abs")
    p.metric("NumPy (pocketfft, C) vs my iterative FFT at N = 4096", tit[-1] / tnp[-1], "× slower")
    fig, ax = p.fig(1, 2)
    ax[0].loglog(N_, tdft * 1e3, "o-", label="DFT (matrix)")
    ax[0].loglog(N_, trec * 1e3, "o-", label="recursive radix-2")
    ax[0].loglog(N_, tit * 1e3, "o-", label="iterative radix-2")
    ax[0].loglog(N_, tnp * 1e3, "o-", label="numpy.fft")
    ax[0].loglog(N_, tit[3] * 1e3 * (N_ * np.log2(N_)) / (N_[3] * np.log2(N_[3])), "--", color="gray", lw=1, label="∝ N log N")
    style_axes(ax[0], "N", "runtime (ms)", "Runtime scaling")
    ax[1].loglog(N_, ed, "o-", label="DFT"); ax[1].loglog(N_, er, "o-", label="recursive"); ax[1].loglog(N_, ei, "o-", label="iterative")
    ax[1].loglog(N_, 1.1e-16 * np.log2(N_) * 3, "--", color="gray", lw=1, label="~ε·log N")
    style_axes(ax[1], "N", "max relative error", "Accuracy vs numpy.fft")
    p.save(fig, "benchmark", "The DFT grows as N², the FFT as N log N; errors stay near machine precision.")
    import pandas as pd
    p.csv_df("benchmark", pd.DataFrame(rows, columns=["N", "t_dft_s", "t_fft_recursive_s", "t_fft_iterative_s", "t_numpy_s", "err_dft", "err_rec", "err_iter"]))
    p.discuss("""Runtime exponents come out close to 2 for the DFT and 1 for the FFT once divided by log N. The measured
DFT/FFT ratio at N = 1024 differs from the pure operation-count prediction because the matrix DFT runs as a
single BLAS matrix-vector product (very efficient per operation) while my FFT spends much of its time in
Python-level loops and array reshapes — constant factors, not complexity. The DFT's error actually grows
faster (≈ N·ε) because each output sums N rounded products, while the FFT sums only log N stages.""")
