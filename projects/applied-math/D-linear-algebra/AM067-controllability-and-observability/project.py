from eelab import *
import scipy.linalg as sla

META = dict(
    id="AM-067", title="Controllability and observability of a bridge circuit", level="H",
    tools="Controllability/observability matrices and their rank, Gramians via Lyapunov equations, singular values as a quantitative measure, pole-zero cancellation",
    summary="Build a symmetric RC bridge in which one internal mode cannot be driven from the input when the bridge is balanced; show the "
            "rank deficiency, the resulting pole-zero cancellation in the transfer function, and how a small imbalance restores full rank but leaves the mode 'nearly uncontrollable' (tiny Gramian singular value).",
    problem="Can a circuit have internal dynamics that no input can excite — and does that show up anywhere measurable?",
    theory=r"""Controllable iff rank [B, AB, …, A^{n−1}B] = n. In a symmetric circuit driven symmetrically, the antisymmetric mode (difference of the two capacitor voltages) obeys an equation with no input term, so it is
uncontrollable; its pole cancels in the transfer function to a symmetric output. Near balance (imbalance ε) the smallest singular value of the controllability Gramian $W_c$ (AW + WAᵀ + BBᵀ = 0) scales
like ε², a quantitative 'distance' from losing controllability.""",
    method="""Two RC branches (R1, C1) and (R2, C2) from the input to ground via a coupling resistor R_c between the capacitor nodes; states v1, v2; output (v1+v2)/2 or v1−v2. ε = (R2−R1)/R1 from 0 to 10 %.""",
)


def system(eps, R=1e3, C=1e-6, Rc=2e3):
    R1, R2 = R, R * (1 + eps)
    A = np.array([[-1 / (R1 * C) - 1 / (Rc * C), 1 / (Rc * C)], [1 / (Rc * C), -1 / (R2 * C) - 1 / (Rc * C)]])
    B = np.array([[1 / (R1 * C)], [1 / (R2 * C)]])
    return A, B


def run(p):
    A, B = system(0.0)
    Ctrb = np.c_[B, A @ B]
    p.compare("Balanced bridge: rank of the controllability matrix (n = 2)", 1, np.linalg.matrix_rank(Ctrb, tol=1e-9 * np.abs(Ctrb).max()), "", kind="abs")
    Cdiff = np.array([[1.0, -1.0]])
    Obs = np.r_[Cdiff, Cdiff @ A]
    p.metric("Balanced: observability rank from output v1 − v2", np.linalg.matrix_rank(Obs), "", "the difference mode is observable — but never excited")
    Csum = np.array([[0.5, 0.5]])
    s = 1j * 2 * pi * np.logspace(0, 4, 200)
    H = np.array([(Csum @ np.linalg.solve(si * np.eye(2) - A, B))[0, 0] for si in s])
    ev = np.linalg.eigvals(A)
    p.compare("Balanced: sum output behaves as a single RC (fit of |H| to 1/(1+sRC))", 0, np.max(np.abs(H - 1 / (1 + s * 1e3 * 1e-6))), "", kind="abs", tol=1e-9)
    p.metric("Eigenvalues (s⁻¹): symmetric mode / antisymmetric mode", f"{ev.max():.0f} / {ev.min():.0f}")
    rows = []
    for eps in (1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
        A, B = system(eps)
        W = sla.solve_continuous_lyapunov(A, -B @ B.T)
        sv = np.linalg.svd(W, compute_uv=False)
        rows.append((eps, sv.min() / sv.max(), np.linalg.matrix_rank(np.c_[B, A @ B])))
    r = np.array(rows)
    p.compare("Imbalanced bridge: full rank restored for every ε > 0", 2, int(r[:, 2].min()), "", kind="abs")
    sl = np.polyfit(np.log(r[:, 0]), np.log(r[:, 1]), 1)[0]
    p.compare("Gramian conditioning σ_min/σ_max ∝ ε^k (k = 2)", 2.0, sl, "", kind="abs", tol=0.15)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(r[:, 0], r[:, 1], "o-", color=C_MEAS, label="σ_min/σ_max of W_c"); ax[0].loglog(r[:, 0], r[0, 1] * (r[:, 0] / r[0, 0]) ** 2, "--", color=C_PRED, label="∝ ε²")
    style_axes(ax[0], "imbalance ε", "Gramian singular-value ratio", "How close to uncontrollable")
    from scipy.integrate import solve_ivp
    for eps, c in ((0.0, C_MEAS), (0.05, C_PRED)):
        A, B = system(eps)
        sol = solve_ivp(lambda t, x: A @ x + B[:, 0] * 1.0, (0, 0.01), [0, 0], max_step=1e-5)
        ax[1].plot(sol.t * 1e3, (sol.y[0] - sol.y[1]) * 1e3, color=c, label=f"ε = {eps}")
    style_axes(ax[1], "t (ms)", "v1 − v2 (mV)", "Step input: the difference mode stays silent when balanced")
    p.save(fig, "controllability", "Near-uncontrollability measured by the Gramian, and the antisymmetric mode's response to a step.")
    p.discuss(f"""The balanced bridge has a rank-1 controllability matrix: its antisymmetric mode (v1 − v2, with the faster eigenvalue set by the coupling
resistor) receives exactly zero input, so a step leaves v1 − v2 at zero forever and the transfer function to the symmetric output collapses to a
first-order RC — the second pole cancels. The rank test is binary, but reality is not: with 1 % imbalance the matrix is formally full rank, yet the
Gramian's singular-value ratio shows the mode is excited with energy ∝ ε² ({sl:.2f} measured). That is the engineering meaning of
controllability — bridge sensors, differential amplifiers and common-mode rejection all rely on symmetry making some mode (nearly) unreachable.""")
# tol-convention: relative tolerances are in percent
