from eelab import *
from scipy import signal

META = dict(
    id="AM-042", title="Welch's method: trading resolution for variance", level="M",
    tools="Own Welch PSD estimator (segmenting, Hann windows, overlap, averaging), variance and resolution measurements, comparison with scipy.signal.welch",
    summary="Implement Welch's averaged periodogram, predict how the relative variance falls with the number of segments (including the effect of "
            "50 % overlap) and how the resolution (ENBW) grows, and verify both on white noise and closely spaced tones.",
    problem="A raw periodogram is as noisy as the spectrum it estimates. How much does averaging help, and what does it cost?",
    theory=r"""Averaging K independent periodograms divides the relative variance by K. With a Hann window and 50 % overlap segments are correlated: the effective number is $K_{eff}=K/(1+2c^2)$ with
c = 0.167 (Hann at 50 %) → K_eff ≈ 0.95K — overlap buys ~2× more segments for almost the same independence. Resolution: equivalent noise bandwidth $1.5f_s/L$ for a Hann segment of
length L, so halving L doubles the averaging and doubles the smearing.""",
    method="""White noise, N = 2¹⁸: relative variance var(P̂)/E(P̂)² per bin vs K for non-overlapping (L = N/K) and 50 %-overlap segments. Two tones 20 Hz apart at fs = 8 kHz: minimum L that resolves them.
Own implementation vs scipy.signal.welch.""",
)


def welch(x, L, overlap=0.5, fs=1.0):
    step = int(L * (1 - overlap)); w = np.hanning(L); U = np.sum(w ** 2)
    segs = [x[i:i + L] * w for i in range(0, len(x) - L + 1, step)]
    P = np.mean([np.abs(np.fft.rfft(s)) ** 2 for s in segs], axis=0) / (fs * U)
    P[1:-1] *= 2
    return np.fft.rfftfreq(L, 1 / fs), P, len(segs)


def run(p):
    r = p.rng
    x = r.normal(size=2 ** 18)
    rows = []
    for K in (1, 2, 4, 8, 16, 32, 64, 128):
        L = 2 ** 18 // K
        _, P0, k0 = welch(x, L, 0.0)
        _, P5, k5 = welch(x, L, 0.5)
        rows.append((K, k0, np.var(P0[5:-5]) / np.mean(P0[5:-5]) ** 2, k5, np.var(P5[5:-5]) / np.mean(P5[5:-5]) ** 2))
    rows = np.array(rows)
    for K, k0, v0, k5, v5 in rows[[2, 5]]:
        p.compare(f"No overlap, K = {int(k0)} segments: relative variance = 1/K", 1 / k0, v0, "", tol=10)
        p.compare(f"50 % overlap, {int(k5)} segments: relative variance = (1+2c²)/K, c = 0.167", (1 + 2 * 0.167 ** 2) / k5, v5, "", tol=12)
    f1, Pm, _ = welch(x, 4096, 0.5, fs=8000.0)
    f2, Ps = signal.welch(x, fs=8000.0, window="hann", nperseg=4096, noverlap=2048, detrend=False)
    p.compare("Own Welch vs scipy.signal.welch (max relative difference)", 0, np.max(np.abs(Pm - Ps) / Ps), "", kind="abs", tol=1e-6)
    fs = 8000.0; t = np.arange(2 ** 16) / fs
    y = np.sin(2 * pi * 1000 * t) + np.sin(2 * pi * 1020 * t) + 0.5 * r.normal(size=len(t))
    res_L = None
    for L in (128, 256, 512, 1024, 2048, 4096):
        f, P, _ = welch(y, L, 0.5, fs)
        band = (f > 990) & (f < 1030)
        pk, _ = signal.find_peaks(P[band])
        if len(pk) >= 2 and np.sort(P[band][pk])[-2] > 3 * P[band].min():
            res_L = L; break
    Lpred = 2 * 1.5 * fs / 20
    p.compare("Shortest power-of-two Hann segment resolving tones 20 Hz apart (prediction L ≳ 2·1.5·fs/Δf = 1200 → 2048)", 1 << int(np.ceil(np.log2(Lpred))), res_L, "samples", kind="abs", tol=0)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(rows[:, 1], rows[:, 2], "o-", color=C_MEAS, label="no overlap"); ax[0].loglog(rows[:, 3], rows[:, 4], "s-", color=COLORS[1], label="50 % overlap")
    ax[0].loglog(rows[:, 1], 1 / rows[:, 1], "--", color=C_PRED, label="1/K")
    style_axes(ax[0], "number of segments", "relative variance of P̂", "Variance falls as 1/K")
    for L, c in ((256, COLORS[0]), (1024, COLORS[1]), (8192, COLORS[2])):
        f, P, K = welch(y, L, 0.5, fs)
        ax[1].semilogy(f, P, color=c, lw=1, label=f"L = {L} ({K} segments)")
    ax[1].set_xlim(900, 1120)
    style_axes(ax[1], "frequency (Hz)", "PSD", "Resolution vs smoothness")
    p.save(fig, "welch", "Relative variance vs number of segments, and the resolution trade-off on two close tones.")
    p.discuss(f"""The relative variance of the averaged periodogram falls as 1/K for independent segments, and with 50 % Hann overlap it stays within a few
percent of (1+2c²)/K — so overlapping nearly doubles the number of useful averages for free, which is why 50 % is the default. The price of
short segments is resolution: two tones 20 Hz apart only separate once the segment is long enough (here L = {res_L} samples), consistent with the
Hann ENBW of 1.5 fs/L. Welch's method is the practical answer to AM-041's problem: choose L for the resolution you need, then let the record length
decide how much variance you remove.""")
# tol-convention: relative tolerances are in percent
