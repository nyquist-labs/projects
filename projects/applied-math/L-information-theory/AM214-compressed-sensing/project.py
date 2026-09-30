from eelab import *

META = dict(
    id="AM-214", title="Compressed sensing: recovering sparse signals from few measurements", level="H",
    tools="Own orthogonal matching pursuit and ISTA (ℓ₁-regularised least squares), Gaussian random measurement matrices, success-probability phase transition versus measurements and sparsity, comparison with the m ≈ 2k·ln(N/k) scaling, noise robustness, a multi-tone signal recovered from random time samples",
    summary="Reconstruct a length-N signal with only k non-zero coefficients from m ≪ N random linear measurements: map the sharp transition between "
            "failure and success, compare it with the theoretical scaling, check stability to noise, and recover a spectrally sparse signal sampled far below its Nyquist rate.",
    problem="The sampling theorem asks for 2B samples per second. If the signal is known to be sparse, how few measurements are really needed?",
    theory=r"""Measurements $y=Ax$, $A\in\mathbb R^{m\times N}$ Gaussian, x k-sparse. ℓ₁ minimisation and greedy methods such as OMP recover x exactly with high probability once $m\gtrsim Ck\ln(N/k)$ (C ≈ 2 for ℓ₁ in the Donoho–Tanner regime); below that, recovery fails abruptly — a phase transition.
With noise of norm ε the error scales like ε (stable recovery). A signal made of a few tones is sparse in the DFT basis, so random time samples at an average rate far below Nyquist suffice.""",
    method="""N = 256; k = 4…40; m = 10…200; 30 trials per cell; success = relative error < 10⁻⁴. OMP with least-squares refitting. FISTA (accelerated ISTA) with λ continuation and a least-squares debias for comparison at one point. Multi-tone: 5 tones on a 1024-point DFT grid, 80 random samples (Nyquist-rate sampling would need 1024),
recovered by OMP on a partial inverse-DFT dictionary.""",
)


def omp(A, y, k, tol=1e-10):
    r = y.copy(); S = []; x = np.zeros(A.shape[1], A.dtype)
    for _ in range(k):
        j = int(np.argmax(np.abs(A.conj().T @ r))); S.append(j)
        c, *_ = np.linalg.lstsq(A[:, S], y, rcond=None); r = y - A[:, S] @ c
        if np.linalg.norm(r) < tol * np.linalg.norm(y):
            break
    x[S] = c
    return x


def ista(A, y, lam, iters=3000):
    """FISTA for min ½‖Ax − y‖² + λ‖x‖₁ with continuation (λ decreased geometrically from ‖Aᵀy‖∞/2), then a least-squares debias on the support."""
    L = np.linalg.norm(A, 2) ** 2; x = np.zeros(A.shape[1]); z = x.copy(); t = 1.0
    for lam_k in np.geomspace(np.max(np.abs(A.T @ y)) / 2, lam, 12):
        for _ in range(iters // 12):
            v = z + A.T @ (y - A @ z) / L; xn = np.sign(v) * np.maximum(np.abs(v) - lam_k / L, 0)
            tn = (1 + np.sqrt(1 + 4 * t * t)) / 2; z = xn + (t - 1) / tn * (xn - x); x, t = xn, tn
    S = np.abs(x) > 1e-6 * np.abs(x).max(); c, *_ = np.linalg.lstsq(A[:, S], y, rcond=None); out = np.zeros_like(x); out[S] = c
    return out


def run(p):
    r = p.rng; N = 256; ks = np.arange(4, 41, 4); ms = np.arange(10, 201, 10); succ = np.zeros((len(ks), len(ms)))
    for a, k in enumerate(ks):
        for b, m in enumerate(ms):
            ok = 0
            for _ in range(30):
                A = r.normal(size=(m, N)) / np.sqrt(m); x = np.zeros(N); x[r.choice(N, k, replace=False)] = r.normal(size=k)
                xh = omp(A, A @ x, min(k, m)); ok += np.linalg.norm(xh - x) / np.linalg.norm(x) < 1e-4
            succ[a, b] = ok / 30
    m50 = np.array([ms[np.argmax(succ[a] >= 0.5)] if np.any(succ[a] >= 0.5) else np.nan for a in range(len(ks))])
    pred = 2 * ks * np.log(N / ks)
    ratio = m50 / pred
    p.compare("50 % success point of OMP vs 2k·ln(N/k): ratio, median over k = 4…40", 1.0, float(np.nanmedian(ratio)), "", tol=35)
    wdt = ms[np.argmax(succ[4] >= 0.9)] - ms[np.argmax(succ[4] >= 0.1)]
    p.compare("My expectation: at k = 20 the 10 % → 90 % success transition spans < 40 % of the 50 % point (1 = yes)", 1, int(wdt < 0.4 * m50[4]), "", kind="abs")
    p.metric("Transition width at k = 20 (10 % → 90 % success)", wdt, "measurements", f"50 % point at {m50[4]:.0f}; sharper for larger N, as the asymptotic theory is for N → ∞")
    p.metric("Measurements for 50 % success, k = 4 / 12 / 20 / 40 (N = 256)", " / ".join(f"{m50[list(ks).index(k)]:.0f}" for k in (4, 12, 20, 40)))
    k, m = 10, 80; A = r.normal(size=(m, N)) / np.sqrt(m); x = np.zeros(N); x[r.choice(N, k, replace=False)] = r.normal(size=k); errs = []
    for eps in (1e-4, 1e-3, 1e-2, 1e-1):
        e = r.normal(size=m); e *= eps * np.linalg.norm(A @ x) / np.linalg.norm(e); xh = omp(A, A @ x + e, k); errs.append(np.linalg.norm(xh - x) / np.linalg.norm(x))
    sl = np.polyfit(np.log10([1e-4, 1e-3, 1e-2, 1e-1]), np.log10(errs), 1)[0]
    p.compare("Stability: reconstruction error ∝ measurement noise (log–log slope)", 1.0, sl, "", kind="abs", tol=0.15)
    xi = ista(A, A @ x, 1e-4, 5000)
    p.compare("ℓ₁ (ISTA) recovers the same 10-sparse signal from 80 measurements (relative error)", 0.0, float(np.linalg.norm(xi - x) / np.linalg.norm(x)), "", kind="abs", tol=0.01)
    Nf = 1024; t = np.arange(Nf); freqs = r.choice(np.arange(20, 500), 5, replace=False); amps = r.uniform(0.5, 2, 5)
    sig = sum(a_ * np.cos(2 * pi * f_ * t / Nf + r.uniform(0, 2 * pi)) for a_, f_ in zip(amps, freqs))
    idx = np.sort(r.choice(Nf, 80, replace=False)); F = np.exp(2j * pi * np.outer(t, np.arange(Nf)) / Nf) / Nf
    c = omp(F[idx], sig[idx].astype(complex), 10); rec = np.real(F @ c)
    p.compare("5 tones from 80 random samples of 1024 (7.8 % of the Nyquist-rate samples): relative reconstruction error", 0.0, float(np.linalg.norm(rec - sig) / np.linalg.norm(sig)), "", kind="abs", tol=1e-6)
    fig, ax = p.fig(1, 2, w=11)
    im = ax[0].imshow(succ, origin="lower", aspect="auto", extent=[ms[0] - 5, ms[-1] + 5, ks[0] - 2, ks[-1] + 2], cmap="viridis"); fig.colorbar(im, ax=ax[0], label="success rate")
    ax[0].plot(pred, ks, "w--", label="2k·ln(N/k)"); ax[0].set_xlim(ms[0] - 5, ms[-1] + 5); ax[0].legend(loc="lower right"); ax[0].grid(False)
    ax[0].set_xlabel("measurements m"); ax[0].set_ylabel("sparsity k"); ax[0].set_title("OMP phase transition (N = 256)", loc="left", fontsize=10)
    ax[1].plot(t[:300], sig[:300], color="gray", lw=1, label="signal"); ax[1].plot(idx[idx < 300], sig[idx[idx < 300]], "o", color=C_PRED, label="random samples"); ax[1].plot(t[:300], rec[:300], "--", color=C_MEAS, lw=1, label="reconstruction")
    style_axes(ax[1], "sample", "amplitude", "Five tones from 80 of 1024 samples")
    p.save(fig, "compressed_sensing", "Success probability of sparse recovery versus measurements and sparsity, and a multi-tone signal rebuilt from random samples.")
    p.discuss(f"""Sparse recovery switches on over a band of measurement counts (at k = 20 from 10 % to 90 % success within {wdt} measurements — wider than I
expected at this small N; the transition sharpens only as N grows), and the 50 % point follows the 2k·ln(N/k) scaling (median ratio {np.nanmedian(ratio):.2f}) — 10-sparse signals of length 256 need about {m50[list(ks).index(12)]:.0f} random measurements rather
than 256. Recovery is stable (error proportional to noise, slope {sl:.2f}), and the convex ℓ₁ route reaches the same answer as the greedy one. The multi-tone
example connects to sampling theory: five tones on a 1024-point grid are reconstructed to machine precision from 80 randomly timed samples, 8 % of the
Nyquist-rate count. There is no contradiction with the sampling theorem — it assumes nothing but bandwidth, while compressed sensing trades that
generality for a sparsity assumption and randomised measurements.""")
# tol-convention: relative tolerances are in percent
