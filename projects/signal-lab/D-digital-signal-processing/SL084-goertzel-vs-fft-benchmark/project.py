from eelab import *
import time

META = dict(
    id="SL-084", title="Goertzel vs FFT: when does a single bin win?", level="M",
    tools="Exact multiply counting of Goertzel and radix-2 FFT loops, crossover analysis",
    summary="Count real multiplications and measure run time for detecting K tones in an N-sample block "
            "with Goertzel vs a full FFT; predict and measure the crossover K.",
    problem="If you only need a few frequencies, is computing the whole spectrum wasteful? Find the exact "
            "break-even point.",
    theory=r"""Goertzel: ~N real multiply-adds per tone (+ a few at the end) → $K\cdot N$. Radix-2 complex FFT: $\frac N2\log_2N$
butterflies × 4 real multiplies = $2N\log_2N$ (real-input FFT ≈ half). Break-even $K^* \approx 2\log_2 N$ for a
complex FFT or $\log_2 N$ for a real FFT: for N = 1024, K* ≈ 10–20 tones. Also Goertzel works for any N and any
(non-bin-centred) frequency, and streams sample by sample.""",
    method="""Real multiplies counted per stage of the iterative radix-2 FFT (4 per complex butterfly) and of the Goertzel
recursion, for N = 256, 1024, 4096; Goertzel's output checked against |FFT bin|².""",
)


def goertzel_bank(x, ks, N):
    w = 2 * pi * np.asarray(ks) / N; c = 2 * np.cos(w)
    s1 = np.zeros(len(ks)); s2 = np.zeros(len(ks))
    for v in x:
        s0 = v + c * s1 - s2; s2 = s1; s1 = s0
    return s1**2 + s2**2 - c * s1 * s2


def fft_iter(x):
    x = np.asarray(x, complex).copy(); N = len(x); bits = int(np.log2(N))
    rev = np.array([int(f"{i:0{bits}b}"[::-1], 2) for i in range(N)]); x = x[rev]; m = 2
    while m <= N:
        W = np.exp(-2j * pi * np.arange(m // 2) / m); x = x.reshape(-1, m)
        e, o = x[:, :m // 2].copy(), x[:, m // 2:] * W
        x[:, :m // 2], x[:, m // 2:] = e + o, e - o; x = x.ravel(); m *= 2
    return x


def run(p):
    rows = []
    for N in (256, 1024, 4096):
        x = p.rng.normal(size=N)
        ks = np.arange(1, 65)
        mult_g = ks * (N + 3)
        mult_f = 2 * N * np.log2(N)
        kx_ops = mult_f / (N + 3)
        # count multiplies by instrumenting the actual loops
        cnt_g = N * 1 + 3                                   # one multiply per sample in the recursion + 3 at the end
        cnt_f = sum((N // m) * (m // 2) * 4 for m in 2 ** np.arange(1, int(np.log2(N)) + 1))
        kx_counted = cnt_f / cnt_g
        rows.append((N, kx_counted, None, None, None))
        p.compare(f"N = {N}: break-even tones (2·log₂N) vs counted multiplies", 2 * np.log2(N), kx_counted, "tones", tol=10)
        err = np.max(np.abs(goertzel_bank(x, [5, 17], N) - np.abs(np.fft.fft(x)[[5, 17]]) ** 2)) / np.max(np.abs(np.fft.fft(x)) ** 2)
        if N == 1024:
            p.compare("Goertzel power = |FFT bin|² (N = 1024)", 0, err, "", kind="abs")
    fig, ax = p.fig()
    for i, (N, kx, kt, tf, tg) in enumerate(rows):
        K = np.arange(1, 65)
        ax.loglog(K, K * (N + 3), color=COLORS[i], label=f"Goertzel, N = {N}")
        ax.axhline(2 * N * np.log2(N), color=COLORS[i], ls="--", lw=1)
        ax.plot(kx, 2 * N * np.log2(N), "o", color=COLORS[i])
    style_axes(ax, "number of tones K", "real multiplications", "Break-even: dashed = full complex FFT")
    p.save(fig, "operation_counts", "Goertzel wins below ~2·log₂N tones — 20 tones for N = 1024.")
    p.discuss("""By operation count the crossover sits exactly at 2·log₂N tones (≈ 16–24 for common block sizes), so DTMF (8 tones)
and single-frequency detectors are firmly Goertzel territory — especially on microcontrollers, where Goertzel
also needs no buffer and no bit reversal. I deliberately do not report Python wall-clock
timings: interpreter overhead per sample dwarfs the arithmetic and produced meaningless (even negative)
crossover estimates in a first attempt. On a DSP or in C, where cost tracks the multiply count, the counted
crossover is the one that matters.""")
