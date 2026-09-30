from eelab import *
from scipy.linalg import solve_continuous_are, solve_continuous_lyapunov, expm

META = dict(
    id="AM-160", title="LQR: optimal state feedback from the Riccati equation", level="H",
    tools="Own algebraic-Riccati solver (stable invariant subspace of the Hamiltonian matrix), SciPy's solver as reference, closed-loop cost by Lyapunov equation and by time-domain integration, random gain perturbations, loop-gain robustness (Kalman inequality), Q/R trade-off curve",
    summary="Solve the continuous-time LQR problem from scratch, confirm that the predicted optimal cost x₀ᵀPx₀ is what a simulation accumulates, that "
            "no perturbed gain does better, and that the optimal loop has the guaranteed ≥ 60° phase margin; then trace the trade-off between regulation and effort.",
    problem="Pole placement asks where the poles should go. What if we instead state what we care about — error versus effort — and let the mathematics choose?",
    theory=r"""Minimise $J=\int_0^\infty(x^TQx+u^TRu)\,dt$ for $\dot x=Ax+Bu$: $u=-Kx$, $K=R^{-1}B^TP$, where P solves $A^TP+PA-PBR^{-1}B^TP+Q=0$; the optimal cost is $x_0^TPx_0$. P comes from the stable eigenvectors $[X_1;X_2]$ of the Hamiltonian
$\begin{bmatrix}A&-BR^{-1}B^T\\-Q&-A^T\end{bmatrix}$: $P=X_2X_1^{-1}$. For any stabilising gain the cost is $x_0^TSx_0$ with $(A-BK)^TS+S(A-BK)+Q+K^TRK=0$. Single-input LQR loops satisfy $|1+K(jωI-A)^{-1}B|\ge1$: the Nyquist curve avoids the unit disc
around −1, so PM ≥ 60° and the gain can be raised without limit or halved.""",
    method="""Plant: two masses coupled by a spring and damper, force on the first (4 states). Q = diag(10, 1, 10, 1), R = 1. Cost by integrating the simulated closed loop (matrix exponential steps, 2 ms, 60 s). 500 random gain perturbations of 1–20 %.
Return difference evaluated on 20 000 frequencies. Trade-off: R swept over 6 decades.""",
)


def care(A, B, Q, R):
    n = A.shape[0]; Ri = np.linalg.inv(R)
    Hm = np.block([[A, -B @ Ri @ B.T], [-Q, -A.T]])
    w, V = np.linalg.eig(Hm); V = V[:, w.real < 0]
    return np.real(V[n:] @ np.linalg.inv(V[:n]))


def cost_of(A, B, Q, R, K, x0):
    Acl = A - B @ K
    if np.max(np.linalg.eigvals(Acl).real) >= 0:
        return np.inf
    S = solve_continuous_lyapunov(Acl.T, -(Q + K.T @ R @ K))
    return float(x0 @ S @ x0)


def run(p):
    m1, m2, k, c = 1.0, 0.5, 4.0, 0.1
    A = np.array([[0, 1, 0, 0], [-k / m1, -c / m1, k / m1, c / m1], [0, 0, 0, 1], [k / m2, c / m2, -k / m2, -c / m2]])
    B = np.array([[0], [1 / m1], [0], [0.0]]); Q = np.diag([10.0, 1, 10, 1]); R = np.array([[1.0]])
    P = care(A, B, Q, R); Pref = solve_continuous_are(A, B, Q, R)
    p.compare("Own Hamiltonian-eigenvector Riccati solution vs scipy (max relative difference)", 0.0, float(np.max(np.abs(P - Pref)) / np.max(np.abs(Pref))), "", kind="abs", tol=1e-8)
    res = A.T @ P + P @ A - P @ B @ np.linalg.inv(R) @ B.T @ P + Q
    p.compare("Riccati residual ‖AᵀP + PA − PBR⁻¹BᵀP + Q‖ / ‖Q‖", 0.0, float(np.linalg.norm(res) / np.linalg.norm(Q)), "", kind="abs", tol=1e-8)
    K = np.linalg.solve(R, B.T @ P); x0 = np.array([1.0, 0, -0.5, 0])
    Jpred = float(x0 @ P @ x0)
    dt = 0.002; E = expm((A - B @ K) * dt); x = x0.copy(); J = 0.0; W = Q + K.T @ R @ K; xs = [x.copy()]
    for _ in range(int(60 / dt)):
        xn = E @ x; J += 0.5 * dt * (x @ W @ x + xn @ W @ xn); x = xn; xs.append(x.copy())
    p.compare("Cost accumulated by the simulated closed loop vs x₀ᵀPx₀", Jpred, J, "", tol=0.05)
    r = p.rng; better = 0; ratios = []
    for _ in range(500):
        Kp = K * (1 + r.uniform(0.01, 0.2) * r.normal(size=K.shape))
        Jp = cost_of(A, B, Q, R, Kp, x0); ratios.append(Jp / Jpred); better += Jp < Jpred * (1 - 1e-10)
    p.compare("Randomly perturbed gains (500) that achieve a lower cost than the LQR gain", 0, better, "", kind="abs")
    p.metric("Median cost penalty of a ~10 % gain error", (np.median(ratios) - 1) * 100, "%", "the optimum is flat: first-order insensitive to gain errors")
    w = np.logspace(-3, 3, 20000)
    Lw = np.array([(K @ np.linalg.solve(1j * x_ * np.eye(4) - A, B))[0, 0] for x_ in w])
    p.compare("Kalman inequality: min over ω of |1 + L(jω)| ≥ 1", 1.0, float(np.min(np.abs(1 + Lw))), "", tol=0.5)
    i = np.flatnonzero(np.diff(np.sign(np.abs(Lw) - 1)))
    pms = [180 + np.degrees(np.angle(Lw[j])) for j in i]; pms = [q if q <= 180 else q - 360 for q in pms]
    p.compare("Smallest phase margin over all gain crossovers ≥ 60° (1 = yes)", 1, int(min(abs(q) for q in pms) >= 60 - 0.5), "", kind="abs")
    p.metric("Phase margin(s) of the LQR loop", ", ".join(f"{q:.1f}°" for q in pms))
    for g, lab in ((0.51, "gain × 0.51"), (100.0, "gain × 100")):
        p.compare(f"Loop still stable with {lab} (1 = yes)", 1, int(np.max(np.linalg.eigvals(A - B @ (g * K)).real) < 0), "", kind="abs")
    Rs = np.logspace(-3, 3, 25); tr = []
    for rv in Rs:
        Pk = care(A, B, Q, np.array([[rv]])); Kk = B.T @ Pk / rv; Acl = A - B @ Kk
        Sx = solve_continuous_lyapunov(Acl.T, -Q); Su = solve_continuous_lyapunov(Acl.T, -(Kk.T @ Kk))
        tr.append((float(x0 @ Sx @ x0), float(x0 @ Su @ x0), np.max(np.linalg.eigvals(Acl).real)))
    tr = np.array(tr)
    p.compare("Trade-off curve is monotonic: cheaper control (smaller R) always gives lower state cost and higher effort (violations)", 0, int(np.sum(np.diff(tr[:, 0]) < 0) + np.sum(np.diff(tr[:, 1]) > 0)), "", kind="abs")
    xs = np.array(xs); t = np.arange(len(xs)) * dt
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].plot(t, xs[:, 0], color=C_MEAS, label="mass 1"); ax[0].plot(t, xs[:, 2], color=C_PRED, label="mass 2"); ax[0].set_xlim(0, 12)
    style_axes(ax[0], "time (s)", "position", "LQR regulation of two coupled masses")
    ax[1].plot(Lw.real, Lw.imag, color=C_MEAS); th = np.linspace(0, 2 * pi, 200); ax[1].plot(-1 + np.cos(th), np.sin(th), "--", color=C_PRED, label="forbidden disc |1 + L| < 1")
    ax[1].set_xlim(-3, 2); ax[1].set_ylim(-3, 2); ax[1].set_aspect("equal")
    style_axes(ax[1], "Re L", "Im L", "Nyquist curve stays out of the unit disc at −1")
    ax[2].loglog(tr[:, 1], tr[:, 0], "o-", color=C_MEAS, ms=3)
    style_axes(ax[2], "control effort ∫u² dt", "state cost ∫xᵀQx dt", "Pareto front traced by R", legend=False)
    p.save(fig, "lqr", "Closed-loop response, Nyquist plot of the LQR loop gain, and the regulation/effort trade-off.")
    p.discuss(f"""The Riccati solution built from the Hamiltonian's stable eigenvectors matches SciPy's to round-off, and the closed loop it defines accumulates
exactly the predicted cost x₀ᵀPx₀ = {Jpred:.3f}. None of 500 randomly perturbed gains did better, and a 10 % gain error costs only
{(np.median(ratios) - 1) * 100:.2f} % — the optimum is a flat minimum. The robustness guarantee is visible in the Nyquist plot: the loop never enters the unit
disc around −1, so the phase margin is at least 60° and the loop survives a 100-fold gain increase or a halving. Sweeping R traces the whole
Pareto front between regulation and effort — the designer picks a point on it instead of guessing pole locations. The guarantee holds only with
full state measurement; with an observer in the loop it can vanish (Doyle's 'guaranteed margins for LQG: there are none').""")
# tol-convention: relative tolerances are in percent
