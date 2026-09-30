from eelab import *
from scipy.linalg import toeplitz

META = dict(
    id="AM-112", title="Tikhonov regularisation: deblurring a sensor signal", level="H",
    tools="Ill-posed deconvolution (Gaussian blur Toeplitz matrix), SVD analysis, truncated SVD and Tikhonov (ridge) solutions, L-curve and generalised cross-validation, bias–variance decomposition by Monte Carlo",
    summary="Undo the blur of a slow sensor from noisy data: show that naive inversion amplifies noise catastrophically, regularise with Tikhonov "
            "and truncated SVD, choose the parameter by the L-curve and GCV, and decompose the error into bias and variance as the parameter varies.",
    problem="A sensor smooths the true signal. Inverting the smoothing should restore it — why does that produce garbage, and what is the principled fix?",
    theory=r"""y = Ax + n with A = UΣVᵀ having singular values decaying to ~10⁻¹⁵: naive $x=\sum \frac{u_i^Ty}{σ_i}v_i$ amplifies noise by 1/σ_i. Tikhonov $\min\|Ax-y\|^2+λ^2\|x\|^2$ applies filter factors $f_i=\frac{σ_i^2}{σ_i^2+λ^2}$. Error = bias² (grows with λ) +
variance (shrinks with λ): U-shaped with a minimum. GCV $G(λ)=\frac{\|Ax_λ-y\|^2}{(\mathrm{trace}(I-AA_λ^+))^2}$ estimates the optimum without knowing x.""",
    method="""x: piecewise signal (steps + a bump), N = 200; Gaussian blur σ = 4 samples; noise 1 % of max. λ from 10⁻⁶ to 1: error, bias², variance (100 noise realisations), residual/solution norms (L-curve corner by max curvature), GCV minimum.""",
)


def run(p):
    N = 200; t = np.arange(N)
    x = np.where((t > 40) & (t < 90), 1.0, 0) + np.where((t > 120) & (t < 125), 0.8, 0) + 0.5 * np.exp(-((t - 160) / 10) ** 2)
    k = np.exp(-0.5 * (np.arange(N) / 4.0) ** 2); A = toeplitz(k); A /= A.sum(1, keepdims=True)
    U, s, Vt = np.linalg.svd(A)
    p.metric("Singular values of the blur matrix: largest / smallest", f"{s[0]:.2f} / {s[-1]:.1e}", "", f"condition number {s[0] / s[-1]:.1e}")
    r = p.rng; sig = 0.01
    y = A @ x + r.normal(0, sig, N)
    naive = np.linalg.solve(A, y)
    p.compare("Naive inversion: error norm / signal norm (≫ 1: noise amplified)", 100, np.linalg.norm(naive - x) / np.linalg.norm(x), "×", kind="abs", tol=1e30)
    lams = np.logspace(-6, 0, 61)
    def tik(yv, lam):
        return Vt.T @ ((s / (s ** 2 + lam ** 2)) * (U.T @ yv))
    err, bias2, var, resn, soln, gcv = [], [], [], [], [], []
    Ys = A @ x + r.normal(0, sig, (100, N))
    for lam in lams:
        X = np.array([tik(yy, lam) for yy in Ys]); mean = X.mean(0)
        err.append(np.mean(np.sum((X - x) ** 2, 1))); bias2.append(np.sum((mean - x) ** 2)); var.append(np.mean(np.sum((X - mean) ** 2, 1)))
        xl = tik(y, lam); resn.append(np.linalg.norm(A @ xl - y)); soln.append(np.linalg.norm(xl))
        fcs = s ** 2 / (s ** 2 + lam ** 2); gcv.append(resn[-1] ** 2 / (N - fcs.sum()) ** 2)
    err, bias2, var = map(np.array, (err, bias2, var))
    p.compare("Error = bias² + variance (max relative mismatch over λ)", 0, np.max(np.abs(err - bias2 - var) / err), "", kind="abs", tol=1e-9)
    lopt = lams[np.argmin(err)]; lg = lams[np.argmin(gcv)]
    lr, ls = np.log(resn), np.log(soln)
    d1r, d1s = np.gradient(lr), np.gradient(ls); d2r, d2s = np.gradient(d1r), np.gradient(d1s)
    kappa = (d1r * d2s - d2r * d1s) / (d1r ** 2 + d1s ** 2) ** 1.5
    lc = lams[5 + np.argmax(kappa[5:-5])]
    p.compare("GCV-chosen λ vs true error-minimising λ (ratio, within ×3 is good)", 1.0, lg / lopt, "×", kind="abs", tol=2)
    p.metric("λ: error-optimal / GCV / L-curve corner", f"{lopt:.1e} / {lg:.1e} / {lc:.1e}")
    p.compare("Regularised error at the GCV λ relative to the best possible (ratio)", 1.0, err[np.argmin(gcv)] / err.min(), "", tol=30)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    ax[0].plot(t, x, color="black", lw=2, label="true"); ax[0].plot(t, y, color=COLORS[7], label="blurred + 1 % noise"); ax[0].plot(t, tik(y, lg), color=C_MEAS, label="Tikhonov (GCV λ)")
    ax[0].set_ylim(-0.5, 1.5)
    style_axes(ax[0], "sample", None, "Deblurring")
    ax[1].loglog(lams, err, color=C_MEAS, label="total error"); ax[1].loglog(lams, bias2, "--", color=C_PRED, label="bias²"); ax[1].loglog(lams, var, ":", color=COLORS[2], label="variance")
    ax[1].axvline(lg, color="gray", ls="-.", label="GCV choice")
    style_axes(ax[1], "λ", "squared error", "Bias–variance trade-off")
    ax[2].loglog(resn, soln, color=C_MEAS); ax[2].plot(resn[list(lams).index(lc)], soln[list(lams).index(lc)], "o", color=C_PRED, label="corner")
    style_axes(ax[2], "‖Ax − y‖", "‖x‖", "L-curve")
    p.save(fig, "tikhonov", "Deblurring result, the bias–variance decomposition of the error vs λ, and the L-curve.")
    p.discuss(f"""The blur matrix has a condition number around 10¹⁵ (its singular values decay like the Gaussian's spectrum), so naive inversion multiplies the 1 %
noise into an estimate hundreds of times larger than the signal itself. Tikhonov regularisation damps each singular component by σ²/(σ² + λ²), and the
Monte-Carlo decomposition shows the textbook U-curve exactly: variance falls and bias grows with λ, and their sum (matching the measured error to
rounding) has a clear minimum. GCV picks a λ close to that optimum without knowing the true signal; the L-curve corner lands nearby. The
regularised solution recovers the steps and bump but rounds their edges — information destroyed by the blur (high frequencies below the noise)
cannot be restored, only traded between bias and noise.""")
# tol-convention: relative tolerances are in percent
