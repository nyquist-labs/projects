from eelab import *
from scipy.linalg import solve_continuous_lyapunov
from scipy.integrate import solve_ivp

META = dict(
    id="AM-164", title="Lyapunov stability: proving convergence without solving the equations", level="H",
    tools="Own Lyapunov-equation solver (Kronecker form) vs SciPy, positive-definiteness test against eigenvalues on random matrices, monotone decrease of V along simulated trajectories, region-of-attraction estimate for a nonlinear system from a quadratic Lyapunov function, brute-force simulation of the true region",
    summary="Use energy-like functions to certify stability: for linear systems the Lyapunov equation has a positive-definite solution exactly when the "
            "system is stable; for a nonlinear oscillator a quadratic V gives a guaranteed — and measurably conservative — estimate of the region of attraction.",
    problem="How can we prove that every trajectory starting near an equilibrium converges to it, without computing a single trajectory?",
    theory=r"""If $V(x)>0$ and $\dot V(x)<0$ away from the origin, the origin is asymptotically stable. Linear: $V=x^TPx$ with $A^TP+PA=-Q$ (Q > 0) — a solution P > 0 exists iff A is Hurwitz; then $V(x(t))$ decreases monotonically and
$\dot V=-x^TQx$. Nonlinear: the time-reversed Van der Pol oscillator $\dot x_1=-x_2$, $\dot x_2=x_1-(1-x_1^2)x_2$ has a stable origin surrounded by an unstable limit cycle (the true boundary of the region of attraction). With P from the linearisation,
the largest level set $\{V<c\}$ on which $\dot V<0$ is a guaranteed subset of that region — never an overestimate.""",
    method="""2000 random 2–6-dimensional matrices (about half stable): P > 0 (Cholesky) vs eigenvalues. Own solver: vec form (I⊗Aᵀ + Aᵀ⊗I) vec P = −vec Q. Nonlinear: V̇ evaluated on level-set contours (720 points each) to find the largest certified c;
the true region from 3600 simulated initial conditions on a polar grid.""",
)


def lyap(A, Q):
    n = A.shape[0]
    M = np.kron(np.eye(n), A.T) + np.kron(A.T, np.eye(n))
    return np.linalg.solve(M, -Q.reshape(-1)).reshape(n, n)


def vdp(t, x):
    return [-x[1], x[0] - (1 - x[0] ** 2) * x[1]]


def run(p):
    r = p.rng; bad = 0; diff = 0; nst = 0
    for _ in range(2000):
        n = int(r.integers(2, 7)); A = r.normal(size=(n, n)) - r.uniform(0, 2.2) * np.eye(n)
        stable = np.max(np.linalg.eigvals(A).real) < 0; nst += stable
        try:
            P = lyap(A, np.eye(n)); P = (P + P.T) / 2
            pd = np.all(np.linalg.eigvalsh(P) > 0)
            if stable:
                diff = max(diff, float(np.max(np.abs(P - solve_continuous_lyapunov(A.T, -np.eye(n)))) / np.max(np.abs(P))))
        except np.linalg.LinAlgError:
            pd = False
        bad += pd != stable
    p.compare(f"'P > 0' vs 'all eigenvalues in the left half-plane' on 2000 random matrices ({nst} stable): disagreements", 0, bad, "", kind="abs")
    p.compare("Own Kronecker-form solver vs scipy.linalg.solve_continuous_lyapunov (worst relative difference)", 0.0, diff, "", kind="abs", tol=1e-8)
    A = np.array([[0, 1.0], [-4, -0.4]]); Q = np.eye(2); P = lyap(A, Q)
    sol = solve_ivp(lambda t, x: A @ x, [0, 20], [1.0, 1.0], t_eval=np.linspace(0, 20, 4001), rtol=1e-10, atol=1e-12)
    V = np.einsum("it,ij,jt->t", sol.y, P, sol.y); E = 0.5 * sol.y[1] ** 2 + 2 * sol.y[0] ** 2
    p.compare("Lightly damped oscillator: V = xᵀPx never increases along the trajectory (largest upward step / V₀)", 0.0, float(max(0, np.max(np.diff(V)))) / V[0], "", kind="abs", tol=1e-9)
    Vd = np.gradient(V, sol.t); pred = -np.einsum("it,ij,jt->t", sol.y, Q, sol.y)
    p.compare("dV/dt measured along the trajectory vs −xᵀQx (worst relative error)", 0.0, float(np.max(np.abs(Vd[5:-5] - pred[5:-5])) / np.max(np.abs(pred))), "", kind="abs", tol=1e-3)
    p.metric("For comparison, the physical energy ½v² + 2x² has dE/dt = −0.4v² ≤ 0", "zero whenever v = 0", "", "non-increasing but not strictly decreasing: needs LaSalle; the Lyapunov-equation V avoids that")
    J = np.array([[0, -1.0], [1, -1.0]]); Pn = lyap(J, np.eye(2)); Pn = (Pn + Pn.T) / 2
    Lc = np.linalg.cholesky(Pn); th = np.linspace(0, 2 * pi, 720, endpoint=False); circ = np.vstack([np.cos(th), np.sin(th)])

    def vdot_max(c):
        X = np.linalg.solve(Lc.T, circ) * np.sqrt(c)                  # points with xᵀPx = c
        F = np.array([-X[1], X[0] - (1 - X[0] ** 2) * X[1]])
        return np.max(2 * np.einsum("it,ij,jt->t", X, Pn, F))
    lo, hi = 0.01, 20.0
    for _ in range(50):
        mid = (lo + hi) / 2
        ok = all(vdot_max(c) < 0 for c in np.linspace(mid / 40, mid, 40))
        (lo, hi) = (mid, hi) if ok else (lo, mid)
    cstar = lo

    def converges(x0):
        ev = lambda t, x: np.hypot(*x) - 8
        ev.terminal = True
        s = solve_ivp(vdp, [0, 60], x0, events=ev, rtol=1e-7, atol=1e-9)
        return s.status == 0 and np.hypot(*s.y[:, -1]) < 1e-2
    inside_fail = 0
    for a_ in np.linspace(0, 2 * pi, 60, endpoint=False):
        x0 = np.linalg.solve(Lc.T, np.array([np.cos(a_), np.sin(a_)])) * np.sqrt(0.98 * cstar)
        inside_fail += not converges(x0)
    p.compare("Initial conditions on the certified level set V = 0.98·c* that fail to converge (60 tested)", 0, inside_fail, "", kind="abs")
    radii = np.linspace(0.05, 4, 60); angs = np.linspace(0, 2 * pi, 60, endpoint=False); edge = []
    for a_ in angs:
        lo_r, hi_r = 0.05, 5.0
        for _ in range(14):
            mid = (lo_r + hi_r) / 2
            (lo_r, hi_r) = (mid, hi_r) if converges([mid * np.cos(a_), mid * np.sin(a_)]) else (lo_r, mid)
        edge.append(lo_r)
    edge = np.array(edge); area_true = 0.5 * np.sum(edge ** 2) * (angs[1] - angs[0])
    area_est = pi * cstar / np.sqrt(np.linalg.det(Pn))
    p.compare("The certified ellipse lies inside the true region of attraction (area ratio ≤ 1; 1 = yes)", 1, int(area_est < area_true), "", kind="abs")
    p.metric("Certified level c* / area of the estimate / true area", f"{cstar:.3f} / {area_est:.2f} / {area_true:.2f}", "", f"the quadratic estimate captures {area_est / area_true * 100:.0f} % of the true region")
    bt = solve_ivp(lambda t, x: [-v for v in vdp(t, x)], [0, 40], [2.0, 0.0], t_eval=np.linspace(25, 40, 1500), rtol=1e-9, atol=1e-11)
    p.compare("True boundary = the Van der Pol limit cycle (amplitude ≈ 2.0): largest |x₁| on the simulated boundary", float(np.max(np.abs(bt.y[0]))), float(np.max(np.abs(edge * np.cos(angs)))), "", tol=4)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(sol.t, V / V[0], color=C_MEAS, label="V = xᵀPx (Lyapunov equation)"); ax[0].semilogy(sol.t, E / E[0], color=C_PRED, ls="--", label="physical energy")
    style_axes(ax[0], "time (s)", "normalised value", "A strict Lyapunov function decreases at every instant")
    ax[1].plot(edge * np.cos(angs), edge * np.sin(angs), ".", color=C_MEAS, ms=4, label="true boundary (simulation)")
    ax[1].plot(bt.y[0], bt.y[1], color="gray", lw=0.8, label="limit cycle")
    el = np.linalg.solve(Lc.T, circ) * np.sqrt(cstar); ax[1].plot(el[0], el[1], color=C_PRED, lw=2, label="certified: V < c*")
    ax[1].set_aspect("equal")
    style_axes(ax[1], "x₁", "x₂", "Region of attraction: guaranteed vs actual")
    p.save(fig, "lyapunov", "A Lyapunov function along a trajectory, and the certified versus true region of attraction of a nonlinear oscillator.")
    p.discuss(f"""For linear systems the Lyapunov equation is a complete stability test: over 2000 random matrices 'P positive definite' and 'eigenvalues in
the left half-plane' never disagreed, and along a simulated trajectory V = xᵀPx falls at exactly −xᵀQx — strictly, at every instant, unlike the
physical energy, which stalls whenever the velocity is zero. For the nonlinear oscillator the same quadratic function certifies convergence
inside the level set V < {cstar:.2f}, and every tested initial condition on that set did converge. The certificate is safe but conservative: the
ellipse covers {area_est / area_true * 100:.0f} % of the true region of attraction, whose boundary is the unstable limit cycle. That gap is the general
experience with Lyapunov methods — a guarantee obtained without solving the equations, at the price of not being tight; better-shaped
functions (higher-order polynomials, sum-of-squares programming) shrink it.""")
# tol-convention: relative tolerances are in percent
