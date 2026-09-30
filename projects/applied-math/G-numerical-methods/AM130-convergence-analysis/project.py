from eelab import *
import scipy.sparse as sp
import scipy.sparse.linalg as spla

META = dict(
    id="AM-130", title="Verifying solvers: observed order of accuracy and manufactured solutions", level="H",
    tools="Method of manufactured solutions (MMS) for a 2-D Poisson solver and a heat-equation solver, grid refinement studies, observed order, Richardson extrapolation and the grid convergence index (GCI); deliberately injected bug detection",
    summary="Show how to *prove* a simulator is correct: choose an exact solution, derive the source term it requires, run the solver on refined grids, "
            "and confirm the observed order of accuracy — then plant a subtle bug and watch the order test catch it while a visual check does not.",
    problem="A solver produces plausible pictures. How do you know it solves the equations you think it does, to the accuracy you think it does?",
    theory=r"""MMS: pick u*(x,y) = sin(πx)sin(2πy)e^{x}, compute f = −∇²u*, solve −∇²u = f with u = u* on the boundary. A correct second-order scheme gives error ∝ h² (observed order p = log(e_h/e_{h/2})/log 2 → 2). Richardson: $u ≈ u_h + \frac{u_h-u_{2h}}{2^p-1}$;
GCI = 1.25|u_h − u_{2h}|/(2^p − 1) estimates the discretisation uncertainty without knowing the exact solution. A bug that makes the scheme first-order (e.g. a boundary treated with a one-sided formula, or an O(h) source error) changes p to 1 while the solution still looks right.""",
    method="""5-point Laplacian on N×N grids, N = 16…256. Correct solver vs one with a planted bug (source evaluated at cell corners shifted by h/2 in x). Heat equation u_t = u_xx with Crank–Nicolson (expected order 2 in time and space) vs backward Euler in time
(order 1 in Δt), refined together.""",
)


def uex(x, y):
    return np.sin(pi * x) * np.sin(2 * pi * y) * np.exp(x)


def src(x, y):
    # f = −∇²u for u = sin(πx) sin(2πy) e^x
    e = np.exp(x); s1, c1, s2 = np.sin(pi * x), np.cos(pi * x), np.sin(2 * pi * y)
    uxx = e * s2 * (s1 + 2 * pi * c1 - pi * pi * s1)
    uyy = -4 * pi * pi * e * s1 * s2
    return -(uxx + uyy)


def poisson(N, bug=False):
    h = 1.0 / N; x = np.linspace(0, 1, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    n = N - 1
    T = sp.diags([-np.ones(n - 1), 2 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1])
    A = (sp.kron(T, sp.eye(n)) + sp.kron(sp.eye(n), T)) / h ** 2
    Xi, Yi = X[1:-1, 1:-1], Y[1:-1, 1:-1]
    F = src(Xi + (h / 2 if bug else 0), Yi)
    U = uex(X, Y)
    b = F.copy()
    b[0, :] += U[0, 1:-1] / h ** 2; b[-1, :] += U[-1, 1:-1] / h ** 2; b[:, 0] += U[1:-1, 0] / h ** 2; b[:, -1] += U[1:-1, -1] / h ** 2
    u = spla.spsolve(A.tocsc(), b.ravel()).reshape(n, n)
    return np.max(np.abs(u - U[1:-1, 1:-1])), u[N // 4 - 1, N // 4 - 1]          # probe at (¼, ¼); the centre would be useless — the exact solution is zero there


def heat(N, scheme):
    x = np.linspace(0, 1, N + 1); h = x[1]; dt = h; steps = int(round(0.1 / dt))
    u = np.sin(pi * x)
    n = N - 1
    L = sp.diags([np.ones(n - 1), -2 * np.ones(n), np.ones(n - 1)], [-1, 0, 1]) / h ** 2
    I = sp.eye(n)
    if scheme == "CN":
        A = (I - dt / 2 * L).tocsc(); B = (I + dt / 2 * L)
    else:
        A = (I - dt * L).tocsc(); B = I
    lu = spla.splu(A); v = u[1:-1]
    for _ in range(steps):
        v = lu.solve(B @ v)
    return np.max(np.abs(v - np.exp(-pi * pi * 0.1) * np.sin(pi * x[1:-1])))


def run(p):
    Ns = [16, 32, 64, 128, 256]
    ok = [poisson(N)[0] for N in Ns]; bad = [poisson(N, bug=True)[0] for N in Ns]
    order = lambda e: np.log2(e[-2] / e[-1])
    p.compare("Correct Poisson solver: observed order (5-point stencil → 2)", 2.0, order(ok), "", kind="abs", tol=0.05)
    p.compare("Planted bug (source shifted by h/2): observed order drops to 1", 1.0, order(bad), "", kind="abs", tol=0.1)
    p.metric("Max error on the 64×64 grid: correct / buggy", f"{ok[2]:.2e} / {bad[2]:.2e}", "", "both 'look' right on a plot")
    e1, e2, e3 = [poisson(N)[1] for N in (64, 128, 256)]
    pobs = np.log(abs(e1 - e2) / abs(e2 - e3)) / np.log(2)
    gci = 1.25 * abs(e3 - e2) / (2 ** pobs - 1)
    p.compare("Richardson order from three grids at a probe point (no exact solution needed)", 2.0, pobs, "", kind="abs", tol=0.2)
    p.metric("Grid convergence index at the probe (256² grid)", gci, "")
    hcn = [heat(N, "CN") for N in (20, 40, 80, 160)]; hbe = [heat(N, "BE") for N in (20, 40, 80, 160)]
    p.compare("Heat equation, Crank–Nicolson with Δt ∝ h: observed order 2", 2.0, order(hcn), "", kind="abs", tol=0.15)
    p.compare("Heat equation, backward Euler with Δt ∝ h: observed order 1 (time error dominates)", 1.0, order(hbe), "", kind="abs", tol=0.15)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(1 / np.array(Ns), ok, "o-", color=C_MEAS, label="correct solver"); ax[0].loglog(1 / np.array(Ns), bad, "s-", color=C_PRED, label="with planted bug")
    ax[0].loglog(1 / np.array(Ns), ok[0] * (np.array(Ns[0]) / np.array(Ns)) ** 2, ":", color="gray", label="h²"); ax[0].loglog(1 / np.array(Ns), bad[0] * (np.array(Ns[0]) / np.array(Ns)), "--", color="gray", label="h")
    style_axes(ax[0], "grid spacing h", "max error", "MMS on 2-D Poisson")
    hh = 1 / np.array([20, 40, 80, 160])
    ax[1].loglog(hh, hcn, "o-", color=C_MEAS, label="Crank–Nicolson"); ax[1].loglog(hh, hbe, "s-", color=C_PRED, label="backward Euler")
    style_axes(ax[1], "h (Δt = h)", "max error at t = 0.1", "Heat equation")
    p.save(fig, "convergence", "Grid-refinement studies: a correct solver converges at order 2, a subtly buggy one at order 1.")
    p.discuss(f"""The manufactured-solution test is the strongest routine check a simulator can get: the correct 5-point Poisson solver converges at exactly order 2, and a planted
bug — evaluating the source half a cell off — drops the observed order to 1 while the solution plots still look fine and the error on a moderate grid
is merely 'a bit larger'. Without an exact solution, three-grid Richardson analysis still recovers the order (≈ {pobs:.2f}) and gives a grid convergence index
as an error bar. The same test distinguishes time integrators: refining space and time together, Crank–Nicolson shows order 2 and backward Euler
order 1. Every solver in this repository whose accuracy matters was checked this way (e.g. AM-047, AM-119, SL-125).""")
# tol-convention: relative tolerances are in percent
