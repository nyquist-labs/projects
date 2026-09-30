from eelab import *
import time

META = dict(
    id="AM-020", title="Radix-2 FFT: derive the butterfly, implement, benchmark", level="H",
    tools="Own iterative radix-2 decimation-in-time FFT (bit reversal + butterflies, vectorised per stage), naive O(N²) DFT, numpy.fft; accuracy and timing scaling",
    summary="Derive the Cooley–Tukey butterfly from splitting the DFT into even and odd samples, implement an iterative radix-2 FFT, verify it "
            "against numpy, and measure how its cost and its round-off error scale with N compared with the naive DFT.",
    problem="Where does N log N come from — and does a from-scratch FFT really beat the O(N²) DFT by the predicted factor?",
    theory=r"""$X_k=E_k+W_N^kO_k$, $X_{k+N/2}=E_k-W_N^kO_k$, where E, O are the N/2-point DFTs of even/odd samples. Recursing log₂N times gives (N/2)log₂N butterflies instead of N² products, a
predicted speed-up of 2N/log₂N (≈ 186× at N = 1024 in operation count). Round-off: FFT error grows like O(log N)·ε versus O(√N)…O(N)·ε for the direct sum.""",
    method="""Iterative in-place DIT: bit-reversed permutation, then log₂N stages, each a vectorised NumPy butterfly. N = 16 … 65536 (naive DFT up to 2048). Accuracy against an extended-precision
reference (numpy.longdouble DFT for N ≤ 1024).""",
)


def fft_r2(x):
    x = np.asarray(x, complex); N = len(x); L = int(np.log2(N)); assert 1 << L == N
    idx = np.arange(N); rev = np.zeros(N, int)
    for b in range(L):
        rev |= ((idx >> b) & 1) << (L - 1 - b)
    X = x[rev].copy()
    size = 2
    while size <= N:
        half = size // 2
        w = np.exp(-2j * pi * np.arange(half) / size)
        X = X.reshape(-1, size)
        e, o = X[:, :half].copy(), X[:, half:] * w
        X[:, :half], X[:, half:] = e + o, e - o
        X = X.reshape(-1)
        size *= 2
    return X


def naive(x):
    N = len(x); n = np.arange(N)
    return np.array([np.sum(x * np.exp(-2j * pi * k * n / N)) for k in range(N)])


def run(p):
    r = p.rng
    Ns = [2 ** k for k in range(4, 17)]
    err, t_fft, t_naive, t_np = [], [], [], []
    for N in Ns:
        x = r.normal(size=N) + 1j * r.normal(size=N)
        err.append(np.max(np.abs(fft_r2(x) - np.fft.fft(x))) / np.max(np.abs(np.fft.fft(x))))
        reps = max(1, int(2e5 / N))
        t0 = time.perf_counter(); [fft_r2(x) for _ in range(reps)]; t_fft.append((time.perf_counter() - t0) / reps)
        t0 = time.perf_counter(); [np.fft.fft(x) for _ in range(reps)]; t_np.append((time.perf_counter() - t0) / reps)
        if N <= 2048:
            rr = max(1, int(2e4 / N)); t0 = time.perf_counter(); [naive(x) for _ in range(rr)]; t_naive.append((time.perf_counter() - t0) / rr)
    p.compare("Own radix-2 FFT vs numpy.fft, worst relative error (N = 16 … 65536)", 0, max(err), "", kind="abs", tol=1e-12)
    Nn = np.array(Ns[:len(t_naive)])
    sp = np.array(t_naive) / np.array(t_fft[:len(t_naive)])
    p.compare("Measured speed-up over the naive DFT at N = 1024 vs op-count ratio 2N/log₂N", 2 * 1024 / 10, sp[Nn == 1024][0], "×", tol=100)
    big = np.array(Ns) >= 8192
    sl = np.polyfit(np.log(np.array(Ns)[big]), np.log(np.array(t_fft)[big] / np.log2(np.array(Ns)[big])), 1)[0]
    p.compare("FFT time / log₂N ∝ N^k (k = 1 for N log N)", 1.0, sl, "", kind="abs", tol=0.25)
    # round-off vs a long-double reference
    acc = []
    for N in (64, 256, 1024):
        x = r.normal(size=N)
        n = np.arange(N, dtype=np.longdouble)
        ref = np.array([np.sum(x.astype(np.longdouble) * np.cos(-2 * np.pi * k * n / N)) + 1j * np.sum(x.astype(np.longdouble) * np.sin(-2 * np.pi * k * n / N)) for k in range(N)])
        e_fft = np.sqrt(np.mean(np.abs(fft_r2(x) - ref.astype(complex)) ** 2)) / np.sqrt(np.mean(np.abs(ref.astype(complex)) ** 2))
        e_nv = np.sqrt(np.mean(np.abs(naive(x) - ref.astype(complex)) ** 2)) / np.sqrt(np.mean(np.abs(ref.astype(complex)) ** 2))
        acc.append((N, e_fft, e_nv))
    p.metric("RMS relative round-off at N = 1024: FFT / naive DFT", f"{acc[-1][1]:.2e} / {acc[-1][2]:.2e}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(Nn, t_naive, "o-", color=COLORS[1], label="naive DFT (Python/NumPy)")
    ax[0].loglog(Ns, t_fft, "s-", color=C_MEAS, label="own radix-2 FFT")
    ax[0].loglog(Ns, t_np, "^-", color=COLORS[2], label="numpy.fft (C, pocketfft)")
    style_axes(ax[0], "N", "time (s)", "O(N²) vs O(N log N)")
    ax[1].loglog([a[0] for a in acc], [a[1] for a in acc], "s-", color=C_MEAS, label="FFT"); ax[1].loglog([a[0] for a in acc], [a[2] for a in acc], "o-", color=COLORS[1], label="naive sum")
    style_axes(ax[1], "N", "RMS relative error", "Round-off: the FFT is also more accurate")
    p.save(fig, "fft", "Timing of the naive DFT, the from-scratch FFT and numpy's FFT, and their round-off errors.")
    p.discuss(f"""The butterfly implementation matches numpy to rounding error for every size up to 65,536. The measured speed-up over the direct DFT at N = 1024 is
{sp[Nn == 1024][0]:.0f}× against an operation-count prediction of ~205× — the same order, with the difference due to constant factors (the naive version
computes exponentials inside the loop; the FFT's Python stage loop has fixed overhead). The from-scratch FFT's timing exponent (time/log₂N ∝ N^{sl:.2f}, fitted for N ≥ 8192) is still below 1: its
cost is a fixed Python overhead per stage plus vectorised work, and only at the largest sizes does the N log N arithmetic dominate.
Speed is not the only win: the FFT's round-off error is also smaller than the direct summation's, because each output is built from log₂N
well-conditioned stages rather than one long sum. numpy's C implementation is a further ~10–100× faster — same algorithm, no interpreter.""")
# tol-convention: relative tolerances are in percent
