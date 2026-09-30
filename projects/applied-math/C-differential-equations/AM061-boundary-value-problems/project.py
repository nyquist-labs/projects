from eelab import *
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

META = dict(
    id="AM-061", title="Boundary-value problems: shooting vs relaxation", level="H",
    tools="Shooting method (RK45 + root finding on the missing slope), relaxation (finite differences + Newton iteration), analytic solutions of the Poisson and Poisson–Boltzmann equations",
    summary="Solve two field problems with boundary conditions at both ends — the potential in a uniformly charged region and the nonlinear "
            "Poisson–Boltzmann potential near a charged electrode — by shooting and by relaxation, against closed-form solutions.",
    problem="Initial-value solvers need all conditions at one point; field problems specify them at two boundaries. Which numerical strategy works better?",
    theory=r"""Linear: φ'' = −ρ/ε with φ(0) = φ(L) = 0 → parabola φ = ρx(L−x)/(2ε). Nonlinear (1-D Poisson–Boltzmann, electrolyte / depletion analogue, dimensionless): φ'' = sinh φ, φ(0) = φ0,
φ(∞) = 0 → Gouy–Chapman $φ=4\,\mathrm{artanh}\big(\tanh(φ_0/4)e^{-x}\big)$. Shooting guesses φ'(0) and integrates; it is exponentially sensitive for sinh-type problems (errors grow as e^{x}),
so it fails on long domains. Relaxation solves all points simultaneously with Newton and converges quadratically. Finite-difference error O(h²).""",
    method="""Linear case: shooting with brentq on φ'(0); relaxation with a tridiagonal solve. Poisson–Boltzmann: φ0 = 4, domain [0, X] with X = 5, 10, 20, 30 (φ(X) = analytic value); shooting with brentq over φ'(0);
relaxation with Newton on N = 100…3200 nodes (error and observed order).""",
)


def gc(x, phi0):
    return 4 * np.arctanh(np.tanh(phi0 / 4) * np.exp(-x))


def _blowup(t, y):
    return abs(y[0]) - 50.0          # stop once the shot has clearly diverged (sinh would overflow and stall the solver)


_blowup.terminal = True


def shoot_pb(phi0, X):
    target = gc(X, phi0)
    def miss(s):
        sol = solve_ivp(lambda t, y: [y[1], np.sinh(y[0])], (0, X), [phi0, s], rtol=1e-12, atol=1e-14, events=_blowup)
        return (sol.y[0, -1] if sol.status == 0 else np.sign(sol.y[0, -1]) * 1e6) - target
    s_true = -2 * np.sinh(phi0 / 2)
    try:
        s = brentq(miss, s_true * 1.2, s_true * 0.8, xtol=1e-15)
    except Exception:
        return None, s_true
    sol = solve_ivp(lambda t, y: [y[1], np.sinh(y[0])], (0, X), [phi0, s], rtol=1e-12, atol=1e-14, dense_output=True, events=_blowup)
    if sol.status != 0:
        return None, s_true
    xx = np.linspace(0, X, 400)
    return np.max(np.abs(sol.sol(xx)[0] - gc(xx, phi0))), s_true


def relax_pb(phi0, X, N):
    x = np.linspace(0, X, N + 1); h = x[1]
    u = phi0 * (1 - x / X) + gc(X, phi0) * x / X
    for it in range(50):
        F = np.zeros(N - 1); J = np.zeros((3, N - 1))
        F = (u[2:] - 2 * u[1:-1] + u[:-2]) / h ** 2 - np.sinh(u[1:-1])
        main = -2 / h ** 2 - np.cosh(u[1:-1]); off = np.full(N - 2, 1 / h ** 2)
        from scipy.linalg import solve_banded
        ab = np.zeros((3, N - 1)); ab[0, 1:] = off; ab[1] = main; ab[2, :-1] = off
        du = solve_banded((1, 1), ab, -F)
        u[1:-1] += du
        if np.max(np.abs(du)) < 1e-13:
            break
    return x, u, it + 1


def run(p):
    L, rho = 1.0, 2.0
    target = 0.0
    def miss(s):
        return solve_ivp(lambda t, y: [y[1], -rho], (0, L), [0, s], rtol=1e-12, atol=1e-14).y[0, -1]
    s = brentq(miss, -10, 10)
    p.compare("Linear Poisson: shooting finds φ'(0) = ρL/2", rho * L / 2, s, "", tol=1e-07)
    N = 100; x = np.linspace(0, L, N + 1); h = x[1]
    A = np.diag(np.full(N - 1, -2.0)) + np.diag(np.ones(N - 2), 1) + np.diag(np.ones(N - 2), -1)
    u = np.r_[0, np.linalg.solve(A / h ** 2, -rho * np.ones(N - 1)), 0]
    p.compare("Linear Poisson: relaxation vs parabola (FD is exact for quadratics)", 0, np.max(np.abs(u - rho * x * (L - x) / 2)), "", kind="abs", tol=1e-12)
    phi0 = 4.0
    rows = []
    for X in (5, 10, 20, 30):
        e_s, s_true = shoot_pb(phi0, X)
        xx, uu, its = relax_pb(phi0, X, int(40 * X))
        rows.append((X, e_s, np.max(np.abs(uu - gc(xx, phi0))), its))
    for X, es, er, its in rows:
        p.metric(f"Poisson–Boltzmann on [0, {X}]: shooting error / relaxation error (Newton iterations)", f"{'fails' if es is None else f'{es:.1e}'} / {er:.1e} ({its})")
    p.compare("Shooting still succeeds on the short domain X = 5", 1, int(rows[0][1] is not None and rows[0][1] < 1e-6), "", kind="abs")
    p.compare("Shooting fails (no bracketed root / blow-up) on X = 30 while relaxation succeeds", 1, int((rows[-1][1] is None or rows[-1][1] > 1e-2) and rows[-1][2] < 1e-3), "", kind="abs")
    errs = []
    for Nn in (100, 200, 400, 800, 1600, 3200):
        xx, uu, _ = relax_pb(phi0, 10, Nn); errs.append(np.max(np.abs(uu - gc(xx, phi0))))
    order = np.polyfit(np.log(10 / np.array([100, 200, 400, 800, 1600, 3200])), np.log(errs), 1)[0]
    p.compare("Relaxation: observed order of accuracy (second-order FD)", 2.0, order, "", kind="abs", tol=0.1)
    fig, ax = p.fig(1, 2, w=11)
    xx, uu, _ = relax_pb(phi0, 10, 400)
    ax[0].plot(xx, uu, color=C_MEAS, lw=3, alpha=.5, label="relaxation"); ax[0].plot(xx, gc(xx, phi0), "--", color=C_PRED, label="Gouy–Chapman")
    style_axes(ax[0], "x (Debye lengths)", "φ (thermal voltages)", "Poisson–Boltzmann, φ0 = 4")
    s_true = -2 * np.sinh(phi0 / 2)
    for ds, c in ((1e-6, COLORS[0]), (-1e-6, COLORS[1]), (1e-10, COLORS[2])):
        sol = solve_ivp(lambda t, y: [y[1], np.sinh(y[0])], (0, 30), [phi0, s_true + ds], rtol=1e-12, atol=1e-14, dense_output=True, events=_blowup)
        tt = np.linspace(0, sol.t[-1], 400); ax[1].plot(tt, sol.sol(tt)[0], color=c, label=f"slope error {ds:+.0e}")
    ax[1].plot(xx, gc(xx, phi0), "--", color="black", lw=1)
    ax[1].set_ylim(-5, 6)
    style_axes(ax[1], "x", "φ", "Shooting: tiny slope errors explode as e^x")
    p.save(fig, "bvp", "Relaxation solution of the Poisson–Boltzmann problem, and why shooting fails on long domains.")
    p.discuss(f"""For the linear Poisson problem both methods are exact (the finite-difference Laplacian is exact on a parabola). The nonlinear Poisson–Boltzmann
problem separates them: its linearisation around the solution has growing solutions e^{{x}}, so a shooting error of 10⁻¹⁰ in the initial slope
is amplified by e^{{30}} ≈ 10¹³ across the domain — shooting works for X = 5 but cannot even bracket the root at X = 30. Relaxation treats all nodes
at once, sees both boundary conditions simultaneously and converges quadratically in a handful of Newton iterations, with the expected O(h²)
discretisation error (observed order {order:.2f}). This is why device simulators (Poisson with carrier densities that depend exponentially on φ)
are built on relaxation/Newton, not shooting.""")
# tol-convention: relative tolerances are in percent
