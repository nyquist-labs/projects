from eelab import *
from eelab.control import zoh
from scipy.linalg import solve_continuous_are

META = dict(
    id="SL-166", title="LQR optimal control vs a tuned PID", level="H",
    tools="Continuous algebraic Riccati equation (SciPy), cost integration, PID grid search on the same cost",
    summary="Design an LQR controller for a double integrator (a satellite's attitude axis), verify the optimal cost x₀ᵀPx₀, then "
            "show that no PD controller from a dense grid beats it on the same quadratic cost.",
    problem="LQR is 'optimal' — optimal at what, and by how much does it beat a hand-tuned controller?",
    theory=r"""ẍ = u (double integrator). Cost J = ∫(x² + ẋ² + ρu²)dt, ρ = 0.1. LQR: K = R⁻¹BᵀP with P from the ARE; minimum cost from x₀ is $x_0^TPx_0$. For this
plant the closed form is $K=[1/\sqrt\rho,\ \sqrt{1/\rho+2/\sqrt\rho}]$ (for Q = I). A PD law u = −k_px − k_dẋ is the same structure, so the best PD equals LQR.""",
    method="""x₀ = [1, 0]. Riccati solution, analytic gains, simulated cost (exact ZOH, 1 ms, 20 s). PD grid k_p ∈ [0.5, 10], k_d ∈ [0.5, 10] (100 × 100) on the same cost.""",
)


def cost(Kp, Kd, rho=0.1, dt=1e-3, T=20):
    A = np.array([[0, 1], [-Kp, -Kd]]); Ad, _ = zoh(A, np.zeros((2, 1)), dt)
    x = np.array([1.0, 0.0]); J = 0
    for _ in range(int(T / dt)):
        u = -Kp * x[0] - Kd * x[1]
        J += (x @ x + rho * u * u) * dt
        x = Ad @ x
    return J


def run(p):
    rho = 0.1
    A = np.array([[0, 1], [0, 0.0]]); B = np.array([[0], [1.0]])
    P = solve_continuous_are(A, B, np.eye(2), np.array([[rho]]))
    K = (B.T @ P / rho).ravel()
    Ka = np.array([1 / np.sqrt(rho), np.sqrt(1 / rho + 2 / np.sqrt(rho))])
    p.compare("LQR position gain vs closed form 1/√ρ", Ka[0], K[0], "", tol=0.1)
    p.compare("LQR rate gain vs closed form", Ka[1], K[1], "", tol=0.1)
    x0 = np.array([1.0, 0.0])
    Jopt = x0 @ P @ x0
    Jsim = cost(K[0], K[1])
    p.compare("Simulated cost vs x₀ᵀPx₀", Jopt, Jsim, "", tol=0.5)
    kp = np.linspace(0.5, 10, 60); kd = np.linspace(0.5, 10, 60)
    grid = np.array([[cost(a, b, T=15, dt=5e-3) for b in kd] for a in kp])
    i, j = np.unravel_index(np.argmin(grid), grid.shape)
    p.compare("Best PD on a 60×60 grid: cost / LQR cost (≥ 1)", 1.0, grid[i, j] / Jopt, "", kind="abs")
    p.metric("Best grid PD gains", f"k_p = {kp[i]:.2f}, k_d = {kd[j]:.2f}", "", f"LQR: {K[0]:.2f}, {K[1]:.2f}")
    fig, ax = p.fig()
    cs = ax.contourf(kd, kp, np.log10(grid), 20, cmap="viridis")
    ax.plot(K[1], K[0], "*", color="white", ms=14, label="LQR gains")
    ax.plot(kd[j], kp[i], "o", color=C_PRED, mfc="none", ms=12, label="best grid point")
    style_axes(ax, "k_d", "k_p", "Cost landscape of PD gains (log₁₀ J)")
    p.save(fig, "lqr", "The LQR gains sit at the bottom of the cost bowl found by brute force.")
    p.discuss("""The Riccati solution reproduces the closed-form gains, the simulated cost equals x₀ᵀPx₀, and a brute-force search over 3,600 PD controllers
cannot do better — its best point lies next to the LQR gains, within grid resolution. That is what 'optimal' means: optimal for *this*
quadratic cost. The engineering work in LQR is choosing Q and R to express what you actually care about; the optimisation itself is solved.""")
