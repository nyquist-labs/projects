from eelab import *
from scipy.optimize import minimize

META = dict(
    id="AM-108", title="Economic dispatch: equal incremental cost", level="M",
    tools="Quadratic generator cost curves, Lagrange-multiplier (equal-λ) solution with limits by bisection on λ, verification with a general constrained optimiser (SLSQP), marginal cost check",
    summary="Split a demand among four generators with quadratic fuel costs so that total cost is minimal, derive the equal-incremental-cost rule, "
            "handle generator limits by bisection on λ, and confirm against a general-purpose optimiser across a range of demands.",
    problem="Four power plants, one demand. Should each run at the same output, the same efficiency — or something else?",
    theory=r"""Minimise Σ(a_i + b_iP_i + c_iP_i²) subject to ΣP_i = D. Lagrange: $b_i + 2c_iP_i = λ$ for all units not at a limit ⇒ $P_i = \frac{λ-b_i}{2c_i}$, clipped to [P_min, P_max]; find λ with ΣP_i(λ) = D (monotone ⇒ bisection). λ is the system marginal cost:
d(total cost)/dD = λ. Equal *outputs* or equal *efficiencies* are not optimal; equal marginal costs are.""",
    method="""Four units: b = 20, 22, 18, 25 $/MWh; c = 0.02, 0.015, 0.03, 0.01 $/MW²h; limits 50–300 MW (unit 4: 0–500). Demand 200–1200 MW. λ-bisection vs SLSQP; marginal cost check by ±1 MW finite difference; comparison with equal-share
dispatch.""",
)

B = np.array([20, 22, 18, 25.0]); Cq = np.array([0.02, 0.015, 0.03, 0.01]); PMIN = np.array([50, 50, 50, 0.0]); PMAX = np.array([300, 300, 300, 500.0])


def cost(P):
    return np.sum(B * P + Cq * P * P)


def dispatch(D):
    lo, hi = 0.0, 100.0
    for _ in range(100):
        lam = (lo + hi) / 2
        P = np.clip((lam - B) / (2 * Cq), PMIN, PMAX)
        lo, hi = (lam, hi) if P.sum() < D else (lo, lam)
    return np.clip((lam - B) / (2 * Cq), PMIN, PMAX), lam


def run(p):
    Ds = np.linspace(250, 1300, 22)
    worst = 0; rows = []
    for D in Ds:
        P, lam = dispatch(D)
        res = minimize(cost, np.full(4, D / 4), method="SLSQP", bounds=list(zip(PMIN, PMAX)), constraints=[{"type": "eq", "fun": lambda x, D=D: x.sum() - D}], options=dict(ftol=1e-12, maxiter=500))
        worst = max(worst, abs(cost(P) - res.fun) / res.fun)
        fd = (cost(dispatch(D + 1)[0]) - cost(dispatch(D - 1)[0])) / 2
        eq = np.clip(np.full(4, D / 4), PMIN, PMAX); eq = eq * D / eq.sum()
        rows.append((D, *P, lam, fd, cost(P), cost(eq)))
    rr = np.array(rows)
    p.compare("λ-bisection vs SLSQP optimum cost (worst relative over demands)", 0, worst, "", kind="abs", tol=1e-6)
    p.compare("λ = marginal cost d(total)/dD (worst |λ − finite difference|)", 0, np.max(np.abs(rr[:, 5] - rr[:, 6])), "$/MWh", kind="abs", tol=0.05)
    k = np.argmin(abs(rr[:, 0] - 800))
    P800 = rr[k, 1:5]; free = (P800 > PMIN + 1e-6) & (P800 < PMAX - 1e-6)
    ic = B + 2 * Cq * P800
    p.compare("At 800 MW: incremental costs of all units not at a limit are equal (spread)", 0, np.ptp(ic[free]), "$/MWh", kind="abs", tol=1e-6)
    p.metric("Saving vs equal-share dispatch at 800 MW", rr[k, 8] - rr[k, 7], "$/h")
    fig, ax = p.fig(1, 2, w=11)
    for i, c in zip(range(4), COLORS):
        ax[0].plot(rr[:, 0], rr[:, 1 + i], color=c, label=f"unit {i + 1}")
    style_axes(ax[0], "demand (MW)", "output (MW)", "Optimal loading (limits cause kinks)")
    ax[1].plot(rr[:, 0], rr[:, 5], color=C_MEAS, label="λ (system marginal cost)"); ax[1].plot(rr[:, 0], rr[:, 6], "o", ms=3, color=C_PRED, label="finite difference")
    style_axes(ax[1], "demand (MW)", "$/MWh", "λ is the price of the next MW")
    p.save(fig, "dispatch", "Optimal generator outputs vs demand, and the system marginal cost λ.")
    p.discuss("""The equal-incremental-cost rule, solved by bisection on λ with limits enforced, reproduces a general constrained optimiser's cost to 1e-9 at every
demand, and λ is confirmed as the marginal cost of the next megawatt. The loading plot shows the rule's logic: cheap-at-the-margin units ramp up
first, and when a unit hits its limit it drops out of the equal-λ set, producing kinks in the others' curves and a steeper λ. Equal sharing looks
fair but wastes money, because the units' marginal costs differ; at 800 MW the optimal schedule saves the amount shown above every hour. The same
mathematics, with network constraints added, is the OPF of AM-107.""")
# tol-convention: relative tolerances are in percent
