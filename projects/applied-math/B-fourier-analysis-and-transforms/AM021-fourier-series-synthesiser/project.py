from eelab import *
from scipy.io import wavfile

META = dict(
    id="AM-021", title="Fourier-series synthesiser: square and sawtooth waves", level="E",
    tools="Analytic Fourier coefficients, partial-sum synthesis, RMS error predicted from the omitted harmonics (Parseval), audio (WAV) output",
    summary="Synthesise square and sawtooth waves from their harmonics, predict the mean-square error of every partial sum from the energy "
            "in the omitted terms, and render the results as audio so the harmonic build-up can be heard.",
    problem="How many harmonics does a square wave need — and can we predict the approximation error before computing it?",
    theory=r"""Square (±1): $\frac4π\sum_{k\,odd}\frac{\sin kωt}{k}$; sawtooth: $\frac2π\sum_k\frac{(-1)^{k+1}}{k}\sin kωt$. By Parseval the mean-square error of the N-harmonic partial sum equals the energy of the
omitted terms: square $\frac{8}{π^2}\sum_{k>N,\,odd}\frac1{k^2}$, sawtooth $\frac{2}{π^2}\sum_{k>N}\frac1{k^2}$ — both fall as 1/N, i.e. RMS error ∝ N^{−1/2}.""",
    method="""One period sampled at 2¹⁶ points; partial sums N = 1 … 200 harmonics; measured MSE vs the tail-sum prediction. 220 Hz tones with 1, 3, 9, 27 harmonics written to a 48 kHz WAV.""",
)


def run(p):
    M = 2 ** 16; t = np.arange(M) / M
    sq = np.sign(np.sin(2 * pi * t)); sq[sq == 0] = 1
    saw = 2 * ((t + 0.5) % 1) - 1
    Ns = np.arange(1, 201)
    k_all = np.arange(1, 200001)
    res = {"square": [], "sawtooth": []}
    ps, pw = 0 * sq, 0 * saw
    for N in Ns:
        if N % 2 == 1:
            ps = ps + 4 / pi * np.sin(2 * pi * N * t) / N
        pw = pw + 2 / pi * (-1) ** (N + 1) * np.sin(2 * pi * N * t) / N
        tail_sq = 8 / pi ** 2 * np.sum(1.0 / k_all[(k_all > N) & (k_all % 2 == 1)] ** 2)
        tail_sw = 2 / pi ** 2 * np.sum(1.0 / k_all[k_all > N] ** 2)
        res["square"].append((np.mean((ps - sq) ** 2), tail_sq)); res["sawtooth"].append((np.mean((pw - saw) ** 2), tail_sw))
    for name in res:
        a = np.array(res[name])
        rel = np.max(np.abs(a[:, 0] / a[:, 1] - 1))
        p.compare(f"{name}: worst |measured MSE / Parseval tail − 1| over N = 1…200", 0, rel, "", kind="abs", tol=0.01)
    a = np.array(res["square"])
    sl = np.polyfit(np.log(Ns[9:]), np.log(np.sqrt(a[9:, 0])), 1)[0]
    p.compare("Square wave: RMS error ∝ N^slope", -0.5, sl, "", kind="abs", tol=0.03)
    fs = 48000; tt = np.arange(int(fs * 0.6)) / fs
    parts = []
    for n in (1, 3, 9, 27):
        y = sum(4 / pi * np.sin(2 * pi * 220 * k * tt) / k for k in range(1, 2 * n, 2))
        parts.append(0.3 * y * np.minimum(1, np.minimum(tt, tt[-1] - tt) / 0.01))
    wav = np.concatenate(parts)
    (p.dir / "audio").mkdir(exist_ok=True)
    wavfile.write(p.dir / "audio" / "square_buildup.wav", fs, (wav / np.max(np.abs(wav)) * 0.8 * 32767).astype(np.int16))
    p.files.append(("audio/square_buildup.wav", "220 Hz square wave with 1, 3, 9 and 27 odd harmonics"))
    fig, ax = p.fig(1, 2, w=11)
    for n, c in zip((1, 3, 9, 27), COLORS):
        y = sum(4 / pi * np.sin(2 * pi * k * t) / k for k in range(1, 2 * n, 2))
        ax[0].plot(t, y, color=c, lw=1, label=f"{n} harmonics")
    ax[0].plot(t, sq, color="black", lw=.8)
    style_axes(ax[0], "t / T", "amplitude", "Square wave from odd harmonics")
    for name, c in (("square", C_MEAS), ("sawtooth", COLORS[1])):
        a = np.array(res[name])
        ax[1].loglog(Ns, a[:, 0], color=c, label=f"{name} measured MSE"); ax[1].loglog(Ns, a[:, 1], "--", color=C_PRED if name == "square" else COLORS[3], label=f"{name} Parseval tail")
    style_axes(ax[1], "harmonics N", "mean-square error", "Error = energy of the missing harmonics")
    p.save(fig, "synth", "Partial sums of the square wave, and measured vs predicted mean-square error.")
    p.discuss("""The measured mean-square error of every partial sum equals the energy of the omitted harmonics (Parseval) to within 1 %, so the
approximation error is fully predictable from the coefficients alone. Both waves converge slowly — RMS error ∝ N^{−1/2} — because a jump
forces coefficients that decay only as 1/k; smoother waves (triangle, 1/k²) converge much faster. The audio file makes the same point by ear:
one harmonic is a flute-like sine, 27 harmonics already sound like a buzzy square wave, and the remaining error is in the high harmonics near the
jumps (the Gibbs overshoot studied in AM-022), which barely changes the timbre.""")
# tol-convention: relative tolerances are in percent
