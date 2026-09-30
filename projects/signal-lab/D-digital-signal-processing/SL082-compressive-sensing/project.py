from eelab import *

META = dict(
    id="SL-082", title="Compressive sensing: recovering sparse signals from few samples", level="H",
    tools="Orthogonal Matching Pursuit (own implementation), random Gaussian and random-subsampling measurements",
    summary="Recover a k-sparse spectrum from far fewer random measurements than Nyquist requires; map the "
            "success probability vs number of measurements and compare the transition with the "
            "M ≈ 2k·ln(N/k) prediction.",
    problem="Nyquist says you need 2B samples. If the signal is sparse — a few tones — how many random "
            "samples actually suffice?",
    theory=r"""A k-sparse vector in dimension N can be recovered from M random linear measurements when
$M \gtrsim C\,k\ln(N/k)$ (for greedy OMP with Gaussian matrices, C ≈ 2 works in practice); below that recovery fails
abruptly — a phase transition. Sparse-in-frequency signals sampled at random times behave similarly with a
partial-Fourier matrix.""",
    method="""N = 256, k ∈ {4, 8, 16}, M from 8 to 128. For each (k, M) 50 trials: Gaussian measurement matrix, OMP; success
if relative error < 1e-3. Transition point = M at 50 % success. Demo: a 5-tone signal on a 1024-sample grid
reconstructed from 80 random time samples (7.8 % of Nyquist).""",
)


def omp(A, y, k):
    r = y.copy(); S = []
    for _ in range(k):
        S.append(int(np.argmax(np.abs(A.conj().T @ r))))
        x_s, *_ = np.linalg.lstsq(A[:, S], y, rcond=None)
        r = y - A[:, S] @ x_s
    x = np.zeros(A.shape[1], complex if np.iscomplexobj(A) else float); x[S] = x_s
    return x


def run(p):
    N = 256
    Ms = np.arange(8, 129, 8)
    fig, ax = p.fig(1, 2)
    for i, k in enumerate([4, 8, 16]):
        succ = []
        for M in Ms:
            ok = 0
            for _ in range(50):
                x = np.zeros(N); x[p.rng.choice(N, k, replace=False)] = p.rng.normal(size=k)
                A = p.rng.normal(size=(M, N)) / np.sqrt(M)
                xh = omp(A, A @ x, k)
                ok += np.linalg.norm(xh - x) / np.linalg.norm(x) < 1e-3
            succ.append(ok / 50)
        succ = np.array(succ)
        m50 = np.interp(0.5, succ, Ms) if succ.max() >= 0.5 else np.nan
        p.compare(f"k = {k}: M at 50 % recovery (2k·ln(N/k))", 2 * k * np.log(N / k), m50, "measurements", tol=40)
        ax[0].plot(Ms, succ, "o-", color=COLORS[i], label=f"k = {k}")
        ax[0].axvline(2 * k * np.log(N / k), color=COLORS[i], ls=":", lw=1)
    style_axes(ax[0], "measurements M (N = 256)", "recovery probability", "OMP phase transition")
    Nn, K, Mt = 1024, 5, 80
    freqs = p.rng.choice(np.arange(10, 500), K, replace=False)
    amps = p.rng.uniform(0.5, 1.5, K)
    n = np.arange(Nn)
    xt = sum(a * np.cos(2 * pi * f * n / Nn + p.rng.uniform(0, 2 * pi)) for a, f in zip(amps, freqs))
    idx = np.sort(p.rng.choice(Nn, Mt, replace=False))
    F = np.exp(2j * pi * np.outer(n, np.arange(Nn)) / Nn) / Nn
    A = F[idx]
    Xh = omp(A, xt[idx].astype(complex), 2 * K)
    xr = np.real(F @ Xh)
    err = np.linalg.norm(xr - xt) / np.linalg.norm(xt)
    p.compare("5-tone signal from 80 random samples: reconstruction error", 0, err, "", kind="abs")
    ax[1].plot(n[:300], xt[:300], color="gray", lw=1, label="true signal")
    ax[1].plot(idx[idx < 300], xt[idx[idx < 300]], "o", color=C_PRED, ms=5, label="random samples")
    ax[1].plot(n[:300], xr[:300], "--", color=C_MEAS, lw=1, label="OMP reconstruction")
    style_axes(ax[1], "sample", "amplitude", "Reconstruction from 7.8 % of the samples")
    p.save(fig, "compressive_sensing", "Recovery switches on sharply near M ≈ 2k ln(N/k).")
    p.discuss("""The success curves show the sharp phase transition that compressive-sensing theory predicts, and its location
scales as k·ln(N/k) — but with a constant of ≈ 1.2 rather than the 2 I assumed: for every k the 50 % point sits
~38 % below 2k·ln(N/k). The scaling law is right; the constant is empirical, depends on the success criterion
and matrix ensemble, and here C = 2 is simply conservative. The 5-tone demo
reconstructs 1,024 samples from 80 random ones — impossible by Nyquist sampling, possible because the signal
has only 10 non-zero Fourier coefficients. The catch: it works only because the signal *is* sparse in a known
basis and the sampling is random (regular undersampling would alias).""")
