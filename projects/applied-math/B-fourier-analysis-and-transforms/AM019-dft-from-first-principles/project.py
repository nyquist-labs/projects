from eelab import *
import time

META = dict(
    id="AM-019", title="The DFT as a matrix-vector product", level="M",
    tools="Explicit DFT matrix W_N, unitary-matrix checks, comparison with numpy.fft, operation-count and timing scaling",
    summary="Build the N×N DFT matrix, show its rows are sampled complex exponentials (the Fourier basis), verify orthogonality and Parseval, "
            "match numpy's FFT to rounding error, and measure the O(N²) cost that motivates the FFT.",
    problem="What exactly does the DFT compute — and why is it a change of basis?",
    theory=r"""$X = W x$ with $W_{kn}=e^{-j2πkn/N}$. Rows are orthogonal: $W^HW = N I$, so $W/\sqrt N$ is unitary — the DFT is a rotation of the coordinate system into the Fourier basis, and energy is
preserved (Parseval: $\sum|x|^2=\frac1N\sum|X|^2$). Inverse: $x = \frac1N W^H X$. Cost: N² complex multiply-adds, so doubling N quadruples the time.""",
    method="""N = 8 … 2048: W built explicitly; ‖W^HW − NI‖, ‖Wx − fft(x)‖, Parseval error; matrix-vector time vs N fitted on log-log axes.""",
)


def dft_matrix(N):
    n = np.arange(N)
    return np.exp(-2j * pi * np.outer(n, n) / N)


def run(p):
    r = p.rng
    Ns = [8, 16, 32, 64, 128, 256, 512, 1024, 2048]
    orth, match, pars, times = [], [], [], []
    for N in Ns:
        W = dft_matrix(N)
        x = r.normal(size=N) + 1j * r.normal(size=N)
        orth.append(np.max(np.abs(W.conj().T @ W - N * np.eye(N))) / N)
        X = W @ x
        match.append(np.max(np.abs(X - np.fft.fft(x))) / np.max(np.abs(X)))
        pars.append(abs(np.sum(abs(x) ** 2) - np.sum(abs(X) ** 2) / N) / np.sum(abs(x) ** 2))
        reps = max(1, int(2e6 / N ** 2))
        t0 = time.perf_counter()
        for _ in range(reps):
            W @ x
        times.append((time.perf_counter() - t0) / reps)
    p.compare("Orthogonality: max |WᴴW − NI| / N over all N", 0, max(orth), "", kind="abs", tol=1e-10)
    p.compare("W·x vs numpy.fft.fft, worst relative error", 0, max(match), "", kind="abs", tol=1e-10)
    p.compare("Parseval's theorem, worst relative error", 0, max(pars), "", kind="abs", tol=1e-12)
    sl = np.polyfit(np.log(Ns[3:]), np.log(times[3:]), 1)[0]
    p.compare("Matrix-vector DFT time exponent (∝ N^k)", 2.0, sl, "", kind="abs", tol=0.3)
    x = np.zeros(64); x[5] = 1
    p.compare("DFT of a delayed impulse = row of W (|X| flat, phase slope −2π·5/N)", -2 * pi * 5 / 64, np.polyfit(np.arange(64), np.unwrap(np.angle(np.fft.fft(x))), 1)[0], "rad/bin", tol=1e-07)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    W = dft_matrix(32)
    ax[0].imshow(W.real, cmap="RdBu", vmin=-1, vmax=1); ax[0].set_title("Re W (N = 32)", loc="left", fontsize=10); ax[0].grid(False)
    ax[0].set_xlabel("n"); ax[0].set_ylabel("k")
    for k, c in zip((0, 1, 3), COLORS):
        ax[1].plot(W[k].real, "o-", ms=3, color=c, label=f"row k = {k}")
    style_axes(ax[1], "n", "Re W_kn", "Rows are sampled cosines/sines")
    ax[2].loglog(Ns, times, "o-", color=C_MEAS, label="measured")
    ax[2].loglog(Ns, times[-1] * (np.array(Ns) / Ns[-1]) ** 2, "--", color=C_PRED, label="∝ N²")
    style_axes(ax[2], "N", "time per transform (s)", "Cost of the matrix DFT")
    p.save(fig, "dft_matrix", "The DFT matrix, its rows as basis functions, and the quadratic cost of computing it directly.")
    p.discuss(f"""Written as a matrix, the DFT hides nothing: its rows are sampled complex sinusoids, they are orthogonal to machine precision, and W·x equals
numpy's FFT to ~1e-13, so the FFT is merely a fast way of doing this product. Parseval holds because W/√N is unitary — the transform is a rotation
of coordinates, not a lossy operation. Timing grows with exponent {sl:.2f} (≈ 2; below 2 for small N where overheads dominate and BLAS
vectorises well): at N = 2048 the matrix already has 4 million entries, which is why the O(N log N) factorisation in AM-020 matters.""")
# tol-convention: relative tolerances are in percent
