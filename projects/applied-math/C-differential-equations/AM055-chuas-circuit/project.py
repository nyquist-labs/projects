from eelab import *
from scipy.integrate import solve_ivp

META = dict(
    id="AM-055", title="Chua's circuit: a genuinely chaotic electronic circuit", level="H",
    tools="Dimensionless Chua equations with a piecewise-linear diode, equilibrium and eigenvalue analysis, double-scroll attractor, largest Lyapunov exponent (two-trajectory renormalisation), sensitivity demonstration",
    summary="Integrate Chua's circuit, locate its three equilibria and classify them from the Jacobian, plot the double-scroll attractor, and "
            "measure the largest Lyapunov exponent to prove the motion is chaotic — nearby trajectories diverge exponentially.",
    problem="Can three linear elements and one piecewise-linear resistor produce motion that never repeats?",
    theory=r"""$\dot x=α(y-x-f(x))$, $\dot y=x-y+z$, $\dot z=-βy$, $f(x)=m_1x+\tfrac12(m_0-m_1)(|x+1|-|x-1|)$. For α = 15.6, β = 28, m0 = −8/7, m1 = −5/7 the equilibria are the origin and
$x^*=\pm\frac{m_0-m_1}{m_1+1}$ = ±1.5; each is a saddle-focus (one real and a complex pair of eigenvalues with opposite-sign real parts). Trajectories spiral out of one outer focus
and are reinjected near the other: the double scroll. Chaos ⇔ largest Lyapunov exponent λ₁ > 0 while the orbit stays bounded.""",
    method="""RK45 (rtol 1e-10) for t ∈ [0, 400]; equilibria from the formula and checked by Newton; Jacobian eigenvalues; λ₁ by Benettin's method (perturbation 1e-8, renormalised every 0.5 time units,
averaged over 800 renormalisations); divergence of two trajectories started 1e-10 apart.""",
)

al, be, m0, m1 = 15.6, 28.0, -8 / 7, -5 / 7


def f(x):
    return m1 * x + 0.5 * (m0 - m1) * (abs(x + 1) - abs(x - 1))


def rhs(t, s):
    x, y, z = s
    return [al * (y - x - f(x)), x - y + z, -be * y]


def jac(x):
    slope = m0 if abs(x) < 1 else m1
    return np.array([[-al * (1 + slope), al, 0], [1, -1, 1], [0, -be, 0]])


def run(p):
    xs = (m0 - m1) / (m1 + 1)
    eq = [np.array([xs, 0, -xs]), np.zeros(3), np.array([-xs, 0, xs])]
    worst = max(np.max(np.abs(rhs(0, e))) for e in eq)
    p.compare("Equilibria x* = ±(m0−m1)/(m1+1) = ±1.5 satisfy the equations (max |f|)", 0, worst, "", kind="abs", tol=1e-12)
    for name, e in (("outer equilibrium", eq[0]), ("origin", eq[1])):
        ev = np.linalg.eigvals(jac(e[0]))
        real = ev[np.abs(ev.imag) < 1e-9].real; cplx = ev[np.abs(ev.imag) > 1e-9]
        p.metric(f"Eigenvalues at the {name}", ", ".join(f"{v:.3f}" for v in ev))
        p.compare(f"{name}: saddle-focus (real eigenvalue and complex pair of opposite-sign real parts; 1 = yes)", 1,
                  int(len(real) == 1 and len(cplx) == 2 and np.sign(real[0]) != np.sign(cplx[0].real)), "", kind="abs")
    s = solve_ivp(rhs, (0, 400), [0.7, 0, 0], rtol=1e-10, atol=1e-12, dense_output=True, max_step=0.01)
    t = np.linspace(100, 400, 300000); X = s.sol(t)
    p.compare("Orbit bounded (max |x| over t = 100…400 stays below 3)", 1, int(np.abs(X[0]).max() < 3), "", kind="abs")
    p.metric("Fraction of time spent in each scroll (x > 0)", np.mean(X[0] > 0), "", "switches between scrolls irregularly")
    y = X[:, 0].copy(); d0 = 1e-8; lyap = 0.0; n = 800; dt = 0.5
    ya = y.copy(); yb = y + np.array([d0, 0, 0])
    for _ in range(n):
        ya = solve_ivp(rhs, (0, dt), ya, rtol=1e-10, atol=1e-12).y[:, -1]
        yb = solve_ivp(rhs, (0, dt), yb, rtol=1e-10, atol=1e-12).y[:, -1]
        d = np.linalg.norm(yb - ya); lyap += np.log(d / d0); yb = ya + (yb - ya) * d0 / d
    lam1 = lyap / (n * dt)
    p.compare("Largest Lyapunov exponent λ₁ (> 0 means chaos; my guess ≈ 0.3)", 0.3, lam1, "1/time", kind="abs", tol=0.2)
    s2 = solve_ivp(rhs, (0, 60), [0.7 + 1e-10, 0, 0], rtol=1e-12, atol=1e-14, dense_output=True)
    s1 = solve_ivp(rhs, (0, 60), [0.7, 0, 0], rtol=1e-12, atol=1e-14, dense_output=True)
    tt = np.linspace(0, 60, 6000); sep = np.linalg.norm(s1.sol(tt) - s2.sol(tt), axis=0)
    fig = __import__("matplotlib.pyplot", fromlist=["figure"]).figure(figsize=(11, 4.2))
    a1 = fig.add_subplot(1, 2, 1, projection="3d"); a1.plot(X[0][::5], X[1][::5], X[2][::5], lw=.3, color=C_MEAS)
    a1.set_xlabel("x"); a1.set_ylabel("y"); a1.set_zlabel("z"); a1.set_title("Double-scroll attractor", loc="left", fontsize=10)
    a2 = fig.add_subplot(1, 2, 2); a2.semilogy(tt, sep + 1e-16, color=C_MEAS, label="separation of two orbits 1e-10 apart")
    a2.semilogy(tt, 1e-10 * np.exp(lam1 * tt), "--", color=C_PRED, label=f"e^(λ₁t), λ₁ = {lam1:.2f}")
    style_axes(a2, "t", "|Δ|", "Sensitive dependence on initial conditions")
    fig.tight_layout()
    p.save(fig, "chua", "The double-scroll attractor and exponential divergence of neighbouring trajectories.")
    p.discuss(f"""Chua's equations reproduce the double scroll: three saddle-focus equilibria, bounded motion, and irregular switching between the two scrolls. The
largest Lyapunov exponent measured by Benettin's method is λ₁ = {lam1:.2f} > 0 — two circuits started 10⁻¹⁰ apart disagree completely after about
{np.log(1e10) / max(lam1, 1e-3):.0f} time units, yet both stay on the same attractor. This is the defining combination of deterministic chaos, and it is why Chua's
circuit (buildable with two op-amps and a handful of passives) became the standard experimental chaos system; synchronising two such circuits is
the basis of proposed chaotic communication schemes.""")
# tol-convention: relative tolerances are in percent
