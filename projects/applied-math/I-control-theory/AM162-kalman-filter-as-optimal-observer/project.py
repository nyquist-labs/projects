from eelab import *
from eelab.control import zoh
from scipy.linalg import solve_discrete_are, solve_discrete_lyapunov

META = dict(
    id="AM-162", title="The Kalman filter as the optimal observer", level="H",
    tools="Riccati recursion iterated to steady state (own) vs scipy's DARE, error covariance of an arbitrary observer gain from a discrete Lyapunov equation, gain-scaling sweep and random gain perturbations, Monte-Carlo simulation, innovation whiteness test",
    summary="Among all observer gains, the steady-state Kalman gain minimises the estimation-error variance for given process and sensor noise. Show it: "
            "the Riccati recursion converges to the DARE solution, no perturbed gain gives a smaller error, simulation matches the predicted covariance, and only the optimal filter leaves a white innovation.",
    problem="An observer can be made fast (noisy) or slow (sluggish against disturbances). Is there a best gain — and how would we recognise it in data?",
    theory=r"""$x^+=Ax+w$, $y=Cx+v$, cov(w) = W, cov(v) = R. For a predictor-form observer with gain L the error covariance obeys $Σ=(A-LC)Σ(A-LC)^T+W+LRL^T$. Minimising trace Σ over L gives $L^*=APC^T(CPC^T+R)^{-1}$ where P solves the Riccati
equation $P=APA^T-APC^T(CPC^T+R)^{-1}CPA^T+W$; then Σ = P. The innovation $y-C\hat x$ is white iff the gain is optimal — any remaining correlation is information the filter failed to use.""",
    method="""Constant-acceleration-disturbance tracking model (position, velocity; 10 ms sample, random acceleration σ_a = 2 m/s², position sensor σ = 5 cm). Riccati recursion from P = I for 2000 steps. Sweep L = s·L* for s = 0.2…5 and 1000 random
perturbations. Monte-Carlo: 400 000 steps. Innovation autocorrelation at lags 1–5 for s = 0.3, 1, 3.""",
)


def sigma(A, C, W, R, L):
    F = A - L @ C
    if np.max(np.abs(np.linalg.eigvals(F))) >= 1:
        return None
    return solve_discrete_lyapunov(F, W + L @ R @ L.T)


def run(p):
    T = 0.01; A = np.array([[1, T], [0, 1.0]]); G = np.array([[T * T / 2], [T]]); C = np.array([[1.0, 0]])
    W = G @ G.T * 2.0 ** 2; R = np.array([[0.05 ** 2]])
    P = np.eye(2)
    for _ in range(2000):
        S_ = C @ P @ C.T + R; P = A @ P @ A.T - A @ P @ C.T @ np.linalg.solve(S_, C @ P @ A.T) + W
    Pref = solve_discrete_are(A.T, C.T, W, R)
    p.compare("Riccati recursion iterated to steady state vs scipy DARE (max relative difference)", 0.0, float(np.max(np.abs(P - Pref) / np.abs(Pref))), "", kind="abs", tol=1e-8)
    Ls = A @ P @ C.T @ np.linalg.inv(C @ P @ C.T + R)
    p.compare("Lyapunov covariance of the observer with gain L* equals the Riccati solution (trace ratio)", 1.0, np.trace(sigma(A, C, W, R, Ls)) / np.trace(P), "", tol=1e-6)
    scales = np.logspace(np.log10(0.2), np.log10(5), 61); tr = []
    for s in scales:
        S_ = sigma(A, C, W, R, s * Ls); tr.append(np.trace(S_) if S_ is not None else np.nan)
    tr = np.array(tr)
    p.compare("Gain scale s that minimises trace Σ(s·L*)", 1.0, scales[np.nanargmin(tr)], "", tol=4)
    r = p.rng; better = 0
    for _ in range(1000):
        Lp = Ls * (1 + 0.3 * r.normal(size=Ls.shape)); S_ = sigma(A, C, W, R, Lp)
        if S_ is None:
            continue
        better += (S_[0, 0] < P[0, 0] * (1 - 1e-9)) or (S_[1, 1] < P[1, 1] * (1 - 1e-9))
    p.compare("Random gain perturbations (1000) giving a smaller position or velocity error variance", 0, better, "", kind="abs")
    N = 400_000; acc = r.normal(0, 2.0, N); v = r.normal(0, 0.05, N)
    res = {}
    for s in (0.3, 1.0, 3.0):
        L = s * Ls; x = np.zeros(2); xh = np.zeros(2); e2 = np.zeros(2); inn = np.zeros(N)
        l0, l1 = L[0, 0], L[1, 0]; g0, g1 = G[0, 0], G[1, 0]
        x0 = x1 = h0 = h1 = 0.0
        for k in range(N):
            y = x0 + v[k]; iv = y - h0; inn[k] = iv
            if k > 5000:
                e2[0] += (x0 - h0) ** 2; e2[1] += (x1 - h1) ** 2
            h0, h1 = h0 + T * h1 + l0 * iv, h1 + l1 * iv
            x0, x1 = x0 + T * x1 + g0 * acc[k], x1 + g1 * acc[k]
        i_ = inn[5000:] - inn[5000:].mean(); ac = [float(np.mean(i_[:-j] * i_[j:]) / np.var(i_)) for j in range(1, 6)]
        res[s] = (e2 / (N - 5001), ac)
    p.compare("Monte-Carlo position-error variance with the Kalman gain vs P₁₁", P[0, 0], res[1.0][0][0], "m²", tol=5)
    p.compare("Monte-Carlo velocity-error variance with the Kalman gain vs P₂₂", P[1, 1], res[1.0][0][1], "(m/s)²", tol=6)
    p.compare("Innovation lag-1 autocorrelation with the Kalman gain (white ⇒ 0)", 0.0, res[1.0][1][0], "", kind="abs", tol=0.01)
    p.compare("Sub-optimal gains leave a coloured innovation: |lag-1 autocorrelation| > 0.05 for s = 0.3 and s = 3 (1 = yes)", 1, int(abs(res[0.3][1][0]) > 0.05 and abs(res[3.0][1][0]) > 0.05), "", kind="abs")
    p.metric("Innovation lag-1 autocorrelation, s = 0.3 / 1 / 3", " / ".join(f"{res[s][1][0]:+.3f}" for s in (0.3, 1.0, 3.0)), "", "positive: filter too slow; negative: too fast")
    p.metric("rms position error: raw sensor / Kalman estimate", f"{0.05 * 100:.1f} cm / {np.sqrt(res[1.0][0][0]) * 100:.2f} cm")
    p.metric("Kalman gain L* and observer pole radius", f"[{Ls[0, 0]:.4f}, {Ls[1, 0]:.3f}], |z| = {np.max(np.abs(np.linalg.eigvals(A - Ls @ C))):.4f}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(scales, tr / np.trace(P), color=C_MEAS); ax[0].axvline(1, color=C_PRED, ls="--", label="Kalman gain")
    ax[0].plot([0.3, 1, 3], [(res[s][0].sum()) / np.trace(P) for s in (0.3, 1.0, 3.0)], "o", color=COLORS[2], label="Monte-Carlo")
    style_axes(ax[0], "gain scale s (L = s·L*)", "trace Σ / trace P", "Error variance is minimised at the Kalman gain")
    lags = np.arange(1, 6)
    for s, c in ((0.3, COLORS[1]), (1.0, C_MEAS), (3.0, COLORS[2])):
        ax[1].plot(lags, res[s][1], "o-", color=c, label=f"s = {s:g}")
    ax[1].axhline(0, color="gray", lw=.6)
    style_axes(ax[1], "lag (samples)", "innovation autocorrelation", "Only the optimal filter's innovation is white")
    p.save(fig, "kalman_observer", "Estimation-error variance versus observer gain, and innovation autocorrelation for three gains.")
    p.discuss(f"""The steady-state Kalman gain is simply the best observer gain for the stated noise levels. Iterating the Riccati recursion lands on SciPy's DARE
solution; the Lyapunov covariance of an observer using that gain equals the Riccati P; scaling the gain either way, or perturbing it at random a
thousand times, never reduced the error; and a 400 000-step simulation reproduces the predicted variances. The estimate is
{0.05 / np.sqrt(res[1.0][0][0]):.1f}× better than the raw sensor. The innovation test is the practical pay-off: a filter that is too slow leaves positively
correlated innovations (it keeps being surprised in the same direction), one that is too fast leaves negatively correlated ones (it chases noise),
and only the optimal gain leaves them white. On real data, where W and R are never known exactly, that is how a Kalman filter is tuned.""")
# tol-convention: relative tolerances are in percent
