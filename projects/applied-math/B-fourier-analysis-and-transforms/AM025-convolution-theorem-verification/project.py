from eelab import *
import time

META = dict(
    id="AM-025", title="The convolution theorem, verified numerically", level="M",
    tools="Direct O(NM) convolution, FFT-based convolution with sufficient zero-padding, error analysis, timing crossover",
    summary="Prove numerically that linear convolution equals the inverse FFT of the product of zero-padded spectra, measure the rounding error of "
            "both methods against exact integer arithmetic, and find the length at which FFT convolution becomes faster.",
    problem="'Convolution in time is multiplication in frequency' — how exactly, how accurately, and when is it worth it?",
    theory=r"""For sequences of length N and M, $y = x*h$ has length N+M−1 and $Y = XH$ for DFTs of any length L ≥ N+M−1. Cost: direct NM multiply-adds vs ≈ 3·L log₂L for three FFTs, so FFT
convolution wins once M ≳ a few × log₂L (tens of taps). Error: with integer inputs the exact result is known; FFT round-off ~ ε·‖x‖‖h‖·log L, direct summation is exact for small integers.""",
    method="""Random integer sequences (|value| ≤ 100) so the exact convolution is known; lengths N = M from 8 to 16384; np.convolve (direct) vs rfft-based; max absolute error vs exact; timings.""",
)


def fftconv(x, h):
    L = len(x) + len(h) - 1
    n = 1 << (L - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(h, n), n)[:L]


def run(p):
    r = p.rng
    Ns = [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384]
    err_f, t_d, t_f = [], [], []
    for N in Ns:
        x = r.integers(-100, 101, N).astype(float); h = r.integers(-100, 101, N).astype(float)
        exact = np.convolve(x.astype(np.int64), h.astype(np.int64))
        yf = fftconv(x, h)
        err_f.append(np.max(np.abs(yf - exact)))
        reps = max(1, int(3e5 / (N * np.log2(N + 2))))
        t0 = time.perf_counter(); [np.convolve(x, h) for _ in range(reps)]; t_d.append((time.perf_counter() - t0) / reps)
        t0 = time.perf_counter(); [fftconv(x, h) for _ in range(reps)]; t_f.append((time.perf_counter() - t0) / reps)
    p.compare("FFT convolution vs exact integer result, worst absolute error (N = M = 16384)", 0, err_f[-1], "", kind="abs", tol=1e-6)
    cross = Ns[int(np.argmax(np.array(t_f) < np.array(t_d)))]
    p.compare("Crossover length where FFT convolution becomes faster (my guess: ~100 samples)", 100, cross, "samples", kind="abs", tol=200)
    p.metric("Speed-up at N = M = 16384", t_d[-1] / t_f[-1], "×")
    x = np.array([1.0, 2, 3]); h = np.array([0, 1, 0.5])
    p.compare("Hand example [1,2,3]*[0,1,0.5] = [0,1,2.5,4,1.5]", 0, np.max(np.abs(fftconv(x, h) - np.array([0, 1, 2.5, 4, 1.5]))), "", kind="abs", tol=1e-12)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(Ns, t_d, "o-", color=COLORS[1], label="direct (np.convolve)"); ax[0].loglog(Ns, t_f, "s-", color=C_MEAS, label="FFT convolution")
    style_axes(ax[0], "N = M", "time (s)", "Direct O(NM) vs FFT O(L log L)")
    ax[1].loglog(Ns, np.maximum(err_f, 1e-17), "s-", color=C_MEAS, label="FFT method, max |error|")
    ax[1].loglog(Ns, 1e-16 * 100 * 100 * np.array(Ns) * np.log2(Ns) / 50, ":", color=C_PRED, label="∝ ε·|x||h|·N log N (scaled)")
    style_axes(ax[1], "N = M", "max absolute error", "Round-off of FFT convolution")
    p.save(fig, "convolution", "Timing and accuracy of direct vs FFT-based linear convolution.")
    p.discuss(f"""With enough zero-padding (L ≥ N+M−1) the inverse FFT of the product equals the linear convolution — the worst error at 16,384 × 16,384 is
{err_f[-1]:.1e} on outputs of order 10⁷, so rounding recovers the exact integers. The FFT method's error grows slowly with size (round-off accumulated
through log L stages), while the direct sum on these small integers is exact. FFT convolution overtook the direct method only at N = M ≈ {cross} —
later than my ~100 guess, because numpy's direct convolution is tight compiled code while the FFT path pays for three transforms and padding
to a power of two — and is ~{t_d[-1] / t_f[-1]:.0f}× faster at 16k. For a short filter against a long signal the right tool is block convolution
(overlap-add/save, AM-027), which keeps the FFT size near a few × the filter length.""")
# tol-convention: relative tolerances are in percent
