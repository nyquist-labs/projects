from eelab import *
from scipy.linalg import solve_discrete_are
from scipy.optimize import lsq_linear

META = dict(
    id="AM-168", title="Model predictive control: optimisation in the loop", level="H",
    tools="Condensed MPC formulation (prediction matrices), own box-constrained QP solver (accelerated projected gradient), reference solution by bounded least squares (scipy.optimize.lsq_linear, exact active-set BVLS), LQR equivalence for the unconstrained case, closed-loop comparison with a saturated LQR",
    summary="Build a linear MPC from scratch: predict over a horizon, minimise a quadratic cost subject to actuator limits, apply the first move, repeat. "
            "Verify the QP solver, show that without constraints MPC is exactly LQR, and measure what explicit constraint handling gains over simply clipping an LQR.",
    problem="LQR ignores actuator limits; clipping its output is not optimal and can misbehave. How does a controller plan *around* the limits?",
    theory=r"""Stack predictions $X=S_xx_0+S_uU$; cost $J=X^T\bar QX+U^T\bar RU=\tfrac12U^THU+f^TU+\text{const}$ with $H=2(S_u^T\bar QS_u+\bar R)$, $f=2S_u^T\bar QS_xx_0$, subject to $|u_k|\le u_{max}$. With terminal weight P from the Riccati equation and no
active constraints, the first move equals the LQR law −Kx for every horizon (dynamic programming). Box-constrained QPs are solved by projected gradient: $U\leftarrow\mathrm{clip}(V-\tfrac1L\nabla J(V))$ with Nesterov momentum, L = λ_max(H).
Receding-horizon cost with a long enough horizon approaches the infinite-horizon constrained optimum.""",
    method="""Double integrator sampled at 0.1 s, |u| ≤ 1, Q = diag(1, 0.1), R = 0.1, terminal weight P. QP check on 200 random states (N = 20). Closed loop from x₀ = (10, 0) for 150 steps: MPC with N = 3…40, saturated LQR, and a single open-loop QP
with N = 150 as the constrained optimum.""",
)

T = 0.1
A = np.array([[1, T], [0, 1.0]]); B = np.array([[T * T / 2], [T]]); Q = np.diag([1.0, 0.1]); R = np.array([[0.1]])
P = solve_discrete_are(A, B, Q, R); Klqr = np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)


def condensed(N):
    n = 2; Sx = np.zeros((n * N, n)); Su = np.zeros((n * N, N)); Ak = np.eye(n)
    for k in range(N):
        Ak = A @ Ak; Sx[n * k: n * k + n] = Ak
        for j in range(k + 1):
            Su[n * k: n * k + n, j: j + 1] = np.linalg.matrix_power(A, k - j) @ B
    Qb = np.kron(np.eye(N), Q); Qb[-n:, -n:] = P
    H = 2 * (Su.T @ Qb @ Su + R[0, 0] * np.eye(N)); F = 2 * Su.T @ Qb @ Sx
    return H, F, Sx, Su, Qb


def qp_box(H, f, umax, iters=20000, tol=1e-10):
    """min ½UᵀHU + fᵀU s.t. |U| ≤ umax — accelerated projected gradient with adaptive restart.
    Stops when U is a fixed point of a plain projected-gradient step (the KKT condition)."""
    L = np.linalg.eigvalsh(H)[-1]; U = np.zeros(len(f)); V = U.copy(); tk = 1.0
    for i in range(iters):
        Un = np.clip(V - (H @ V + f) / L, -umax, umax)
        if (V - Un) @ (Un - U) > 0:                              # momentum points uphill: restart
            tk = 1.0
        tn = (1 + np.sqrt(1 + 4 * tk * tk)) / 2
        V = Un + (tk - 1) / tn * (Un - U)
        U, tk = Un, tn
        if i % 5 == 4 and np.max(np.abs(np.clip(U - (H @ U + f) / L, -umax, umax) - U)) < tol:
            break
    return U, i + 1


def run(p):
    r = p.rng; N = 20; H, F, Sx, Su, Qb = condensed(N)
    Kmpc = np.linalg.solve(H, F)[0]
    p.compare("Unconstrained MPC (N = 20, Riccati terminal weight): first-move gain vs LQR gain (max difference)", 0.0, float(np.max(np.abs(Kmpc - Klqr[0]))), "", kind="abs", tol=1e-9)
    H3, F3, *_ = condensed(3)
    p.compare("… and for a horizon of only N = 3", 0.0, float(np.max(np.abs(np.linalg.solve(H3, F3)[0] - Klqr[0]))), "", kind="abs", tol=1e-9)
    G = np.linalg.cholesky(H / 2).T; worst = 0; its = []; act = 0
    for _ in range(200):
        x0 = r.uniform(-1, 1, 2) * np.array([8, 4]); f = F @ x0
        U, it = qp_box(H, f, 1.0); its.append(it)
        ref = lsq_linear(G, -np.linalg.solve(G.T, f / 2), bounds=(-1, 1), method="bvls", tol=1e-14).x
        worst = max(worst, float(np.max(np.abs(U - ref)))); act += np.any(np.abs(ref) > 1 - 1e-6)
    p.compare(f"Own projected-gradient QP vs scipy lsq_linear (BVLS) on 200 random states ({act} with active constraints): worst |ΔU|", 0.0, worst, "", kind="abs", tol=1e-5)
    p.metric("Median iterations of the QP solver", float(np.median(its)))
    x0 = np.array([10.0, 0.0]); steps = 150

    def closed_loop(ctrl):
        x = x0.copy(); J = 0; xs = [x.copy()]; us = []
        for _ in range(steps):
            u = ctrl(x); J += x @ Q @ x + R[0, 0] * u * u; x = A @ x + B[:, 0] * u; xs.append(x.copy()); us.append(u)
        return J + x @ P @ x, np.array(xs), np.array(us)
    res = {}
    for Nh in (3, 5, 10, 20, 40):
        Hh, Fh, *_ = condensed(Nh)
        res[Nh] = closed_loop(lambda x: qp_box(Hh, Fh @ x, 1.0)[0][0])
    res["sat"] = closed_loop(lambda x: float(np.clip(-(Klqr @ x)[0], -1, 1)))
    Hl, Fl, Sxl, Sul, Qbl = condensed(steps); Uo, _ = qp_box(Hl, Fl @ x0, 1.0, iters=200000, tol=1e-12)
    Xo = Sxl @ x0 + Sul @ Uo; Jopt = x0 @ Q @ x0 + Xo @ Qbl @ Xo + R[0, 0] * Uo @ Uo
    p.compare("Actuator limit respected by MPC at every step: max |u|", 1.0, float(np.max(np.abs(res[20][2]))), "", tol=1e-6)
    p.compare("Receding-horizon MPC (N = 40) cost vs the one-shot constrained optimum over the whole run", Jopt, res[40][0], "", tol=0.5)
    p.compare("MPC (N = 20) cost ≤ saturated-LQR cost (1 = yes)", 1, int(res[20][0] <= res["sat"][0] * (1 + 1e-9)), "", kind="abs")
    p.metric("Closed-loop cost: saturated LQR / MPC N = 3 / 5 / 10 / 20 / 40 / optimum", " / ".join(f"{v:.1f}" for v in [res["sat"][0]] + [res[k][0] for k in (3, 5, 10, 20, 40)] + [Jopt]))
    p.metric("Cost penalty of clipping an LQR instead of planning", (res["sat"][0] / Jopt - 1) * 100, "%")
    p.metric("Position overshoot: saturated LQR / MPC (N = 20)", f"{-res['sat'][1][:, 0].min():.2f} / {-res[20][1][:, 0].min():.2f}", "m", "starting 10 m from the target")
    p.compare("Short horizons cost more: closed-loop cost decreases as N grows from 3 to 40 (violations)", 0, int(sum(res[a_][0] < res[b_][0] * (1 - 1e-6) for a_, b_ in ((3, 5), (5, 10), (10, 20), (20, 40)))), "", kind="abs")
    t = np.arange(steps + 1) * T
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, res["sat"][1][:, 0], color=C_PRED, label="saturated LQR"); ax[0].plot(t, res[20][1][:, 0], color=C_MEAS, label="MPC, N = 20"); ax[0].plot(t, res[3][1][:, 0], color=COLORS[2], ls=":", label="MPC, N = 3")
    ax[0].axhline(0, color="gray", lw=.6)
    style_axes(ax[0], "time (s)", "position", "Regulation from 10 m with |u| ≤ 1")
    ax[1].step(t[:-1], res["sat"][2], where="post", color=C_PRED, label="saturated LQR"); ax[1].step(t[:-1], res[20][2], where="post", color=C_MEAS, label="MPC, N = 20")
    style_axes(ax[1], "time (s)", "control u", "MPC starts braking earlier")
    p.save(fig, "mpc", "Closed-loop position and control for a saturated LQR and for MPC with actuator constraints.")
    p.discuss(f"""Three checks pin down what MPC is. Without active constraints and with the Riccati terminal weight, its first move is the LQR law to round-off
for any horizon — MPC generalises LQR rather than replacing it. The home-made projected-gradient solver agrees with SciPy's bounded least-squares
on every test state — after one repair: my first stopping rule ('the iterate stopped changing') fired while the momentum term was holding every
input against its bound, returning a fully saturated plan that violated the optimality conditions; testing for a fixed point of a plain
projected-gradient step (the KKT condition) fixed it. And in closed loop the receding-horizon controller with N = 40 achieves the cost of the single optimisation over the entire
run, i.e. re-planning each step loses nothing. Against that benchmark, clipping the LQR output costs {(res['sat'][0] / Jopt - 1) * 100:.0f} % more: the LQR 'thinks' it can
brake as hard as it likes, accelerates too long and overshoots by {-res['sat'][1][:, 0].min():.1f} m, whereas MPC knows the limit and starts braking earlier. A horizon too
short to see the braking distance (N = 3) loses much of that advantage. The price is an optimisation at every sample —
{np.median(its):.0f} gradient iterations here — which is why MPC arrived first in slow process plants and only later in drives and power converters.""")
# tol-convention: relative tolerances are in percent
