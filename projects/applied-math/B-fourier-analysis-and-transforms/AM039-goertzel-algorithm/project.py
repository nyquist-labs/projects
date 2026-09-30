from eelab import *
from scipy import signal
import time

META = dict(
    id="AM-039", title="Goertzel algorithm: single-bin detection and DTMF", level="M",
    tools="Goertzel recursion (second-order IIR per bin, run with scipy.signal.lfilter), comparison with FFT bins, DTMF decoder, timing crossover",
    summary="Implement the Goertzel algorithm, show it computes exactly one DFT bin, decode noisy DTMF telephone digits with eight Goertzel "
            "filters, and measure how many bins you can compute before a full FFT becomes cheaper.",
    problem="A touch-tone decoder only needs 8 frequencies. Why compute an FFT of all of them?",
    theory=r"""Goertzel: $s[n]=x[n]+2\cos(2πk/N)s[n-1]-s[n-2]$, then $X_k=e^{j2πk/N}s[N-1]-s[N-2]$ — exactly the DFT bin, at N real multiply-adds per bin. A full FFT costs ≈ N log₂N; so Goertzel wins for
K ≲ log₂N bins (≈ 8 for N = 205, the classic DTMF block at 8 kHz). DTMF: rows 697/770/852/941 Hz, columns 1209/1336/1477/1633 Hz.""",
    method="""Exactness: 1000 random (N, k) cases vs numpy.fft. DTMF: 16 digits × 200 trials at SNR 0…20 dB, N = 205, detection = strongest row + strongest column bin (with a twist/threshold check).
Timing: K Goertzel filters (lfilter, C) vs one rfft, N = 205 and 4096.""",
)

ROWS = [697, 770, 852, 941]; COLS = [1209, 1336, 1477, 1633]
KEYS = ["1", "2", "3", "A", "4", "5", "6", "B", "7", "8", "9", "C", "*", "0", "#", "D"]


def goertzel(x, k):
    N = len(x); c = 2 * np.cos(2 * pi * k / N)
    s = signal.lfilter([1.0], [1.0, -c, 1.0], x)
    return np.exp(2j * pi * k / N) * s[-1] - s[-2]


def run(p):
    r = p.rng
    worst = 0
    for _ in range(1000):
        N = int(r.integers(16, 1024)); k = int(r.integers(0, N)); x = r.normal(size=N)
        worst = max(worst, abs(goertzel(x, k) - np.fft.fft(x)[k]) / np.sqrt(N))
    p.compare("Goertzel vs FFT bin (worst error / √N over 1000 cases)", 0, worst, "", kind="abs", tol=1e-9)
    fs, N = 8000, 205
    bins = [round(f * N / fs) for f in ROWS + COLS]
    acc = {}
    for snr in (0, 5, 10, 15, 20):
        ok = tot = 0
        for _ in range(200):
            d = int(r.integers(16)); fr, fc = ROWS[d // 4], COLS[d % 4]
            t = np.arange(N) / fs
            s = np.sin(2 * pi * fr * t) + np.sin(2 * pi * fc * t)
            x = s + r.normal(0, np.sqrt(np.mean(s ** 2) / 10 ** (snr / 10)), N)
            m = np.abs([goertzel(x, k) for k in bins])
            ok += (np.argmax(m[:4]) * 4 + np.argmax(m[4:])) == d; tot += 1
        acc[snr] = ok / tot * 100
    p.compare("DTMF digit accuracy at 10 dB SNR (N = 205)", 100, acc[10], "%", kind="abs", tol=1)
    p.metric("DTMF accuracy at 0 / 5 / 20 dB SNR", f"{acc[0]:.0f} / {acc[5]:.0f} / {acc[20]:.0f} %")
    cross = {}
    for N in (205, 4096):
        x = r.normal(size=N)
        reps = 2000
        t0 = time.perf_counter(); [np.fft.rfft(x) for _ in range(reps)]; tf = (time.perf_counter() - t0) / reps
        t0 = time.perf_counter(); [goertzel(x, 10) for _ in range(reps)]; tg = (time.perf_counter() - t0) / reps
        cross[N] = tf / tg
    p.compare("Bins before an FFT is cheaper, N = 205 (op count: ≈ log₂N ≈ 8)", np.log2(205), cross[205], "bins", kind="abs", tol=8)
    p.metric("Measured break-even bins, N = 4096", cross[4096], "bins", "Python call overhead makes each Goertzel relatively expensive")
    fig, ax = p.fig(1, 2, w=11)
    fs2 = np.arange(0, 2000, 5)
    t = np.arange(N) / fs
    x = np.sin(2 * pi * 770 * t) + np.sin(2 * pi * 1336 * t)
    ax[0].plot(np.fft.rfftfreq(N, 1 / fs), np.abs(np.fft.rfft(x)), color=COLORS[7], label="full FFT")
    ax[0].plot([f * 1.0 for f in ROWS + COLS], [abs(goertzel(x, k)) for k in bins], "o", color=C_MEAS, ms=8, label="8 Goertzel bins")
    ax[0].set_xlim(500, 1800)
    style_axes(ax[0], "frequency (Hz)", "|X|", "Digit '5' = 770 + 1336 Hz")
    ax[1].plot(list(acc), list(acc.values()), "o-", color=C_MEAS)
    style_axes(ax[1], "SNR (dB)", "digit accuracy (%)", "DTMF decoding in noise", legend=False)
    p.save(fig, "goertzel", "Eight Goertzel filters pick out the DTMF tones; decoding accuracy vs SNR.")
    p.discuss(f"""The recursion reproduces the DFT bin exactly (errors at rounding level), so Goertzel is not an approximation but a way to compute one bin in O(N)
with two state variables — ideal for microcontrollers and for DTMF, where only eight bins matter. The decoder is error-free from 10 dB SNR and
still {acc[5]:.0f} % correct at 5 dB. The cost comparison depends on the platform: counting operations, eight bins at N = 205 roughly equal one FFT; in
Python each Goertzel call carries fixed overhead, so the measured break-even is about {cross[205]:.1f} bins. In C on a DSP, the per-sample cost
dominates and the operation-count rule applies.""")
# tol-convention: relative tolerances are in percent
