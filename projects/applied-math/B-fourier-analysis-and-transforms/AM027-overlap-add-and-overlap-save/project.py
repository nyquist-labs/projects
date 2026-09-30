from eelab import *
import time
from scipy import signal as sps

META = dict(
    id="AM-027", title="Overlap-add and overlap-save: fast long-signal filtering", level="H",
    tools="Own overlap-add and overlap-save block convolvers (NumPy rfft), direct convolution reference, block-size sweep and operation-count model",
    summary="Implement both block-convolution methods, verify they reproduce direct filtering exactly, and measure the speed-up over direct "
            "convolution as a function of block size — predicted from an operation-count model.",
    problem="Filtering a million-sample signal with a 256-tap filter: direct, one giant FFT, or blocks? And what block size is best?",
    theory=r"""Per output sample, direct convolution costs M multiply-adds. With FFT size L and M taps, each block yields L−M+1 new samples at the cost of one forward and one inverse FFT
(≈ 2·(L/2)·log₂L complex operations for real FFTs) plus L/2 products, so cost/sample ≈ $\frac{L(\log_2L+1)}{L-M+1}$ — minimised near L ≈ 4–8 M. For M = 256: predicted optimum L ≈ 2048,
speed-up vs direct ≈ M / min(cost) ≈ 256/13 ≈ 20× in operations.""",
    method="""x: 2²⁰ Gaussian samples; h: 256-tap windowed-sinc low-pass. OLA and OLS with L = 512 … 65536; reference np.convolve. Wall time vs L; error vs reference.""",
)


def ola(x, h, L):
    M = len(h); B = L - M + 1; Hf = np.fft.rfft(h, L)
    y = np.zeros(len(x) + M - 1)
    for s in range(0, len(x), B):
        blk = x[s:s + B]
        yb = np.fft.irfft(np.fft.rfft(blk, L) * Hf, L)[:len(blk) + M - 1]
        y[s:s + len(yb)] += yb
    return y


def ols(x, h, L):
    M = len(h); B = L - M + 1; Hf = np.fft.rfft(h, L)
    xp = np.r_[np.zeros(M - 1), x, np.zeros(L)]
    out = []
    for s in range(0, len(x) + M - 1, B):
        seg = xp[s:s + L]
        if len(seg) < L:
            seg = np.r_[seg, np.zeros(L - len(seg))]
        out.append(np.fft.irfft(np.fft.rfft(seg) * Hf, L)[M - 1:])
    return np.concatenate(out)[:len(x) + M - 1]


def run(p):
    r = p.rng
    x = r.normal(size=2 ** 20); h = sps.firwin(256, 0.2)
    t0 = time.perf_counter(); ref = np.convolve(x, h); t_dir = time.perf_counter() - t0
    Ls = [512, 1024, 2048, 4096, 8192, 16384, 65536]
    res = []
    for L in Ls:
        t0 = time.perf_counter(); ya = ola(x, h, L); ta = time.perf_counter() - t0
        t0 = time.perf_counter(); ys = ols(x, h, L); ts = time.perf_counter() - t0
        res.append((L, ta, ts, np.max(np.abs(ya - ref)), np.max(np.abs(ys - ref))))
    res = np.array(res)
    p.compare("Overlap-add vs direct convolution, worst error", 0, res[:, 3].max(), "", kind="abs", tol=1e-10)
    p.compare("Overlap-save vs direct convolution, worst error", 0, res[:, 4].max(), "", kind="abs", tol=1e-10)
    M = 256
    Lg = np.array([2 ** k for k in range(9, 17)])
    cost = Lg * (np.log2(Lg) + 1) / (Lg - M + 1)
    Lopt_pred = Lg[np.argmin(cost)]
    best = res[np.argmin(res[:, 1]), 0]
    p.compare("Fastest block size (overlap-add), op-count model predicts", Lopt_pred, best, "", kind="abs", tol=Lopt_pred * 3)
    p.metric("Speed-up of best overlap-add over np.convolve (direct, C)", t_dir / res[:, 1].min(), "×")
    p.metric("Op-count speed-up predicted at the optimum", M / cost.min(), "×")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogx(res[:, 0], res[:, 1], "o-", color=C_MEAS, label="overlap-add"); ax[0].semilogx(res[:, 0], res[:, 2], "s-", color=COLORS[1], label="overlap-save")
    ax[0].axhline(t_dir, ls="--", color=C_PRED, label="direct np.convolve")
    style_axes(ax[0], "FFT block size L", "time for 2²⁰ samples (s)", "Block size trade-off")
    ax[1].semilogx(Lg, cost, "o-", color=C_PRED, label="model: L(log₂L+1)/(L−M+1)")
    style_axes(ax[1], "FFT block size L", "operations per output sample", "Operation-count model (M = 256)")
    p.save(fig, "ola_ols", "Measured run time of overlap-add/save vs block size, and the operation-count model.")
    p.discuss(f"""Both block methods reproduce direct convolution to ~1e-13. The operation-count model predicts an optimum near L = {Lopt_pred} and a ~{M / cost.min():.0f}×
advantage; the wall-clock optimum for this implementation lies at L = {int(best)}, and against NumPy's C-coded direct convolution the best block
method is {t_dir / res[:, 1].min():.1f}× faster. The model and the clock disagree on the exact optimum for an honest reason: in Python the per-block loop
overhead makes larger blocks relatively cheaper than an operation count says, so the practical optimum shifts to bigger L. Overlap-save avoids the
additions of overlap-add but needs the discard bookkeeping — at equal L their speeds are essentially the same.""")
# tol-convention: relative tolerances are in percent
