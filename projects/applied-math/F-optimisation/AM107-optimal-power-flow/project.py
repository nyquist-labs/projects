from eelab import *
from scipy.optimize import linprog

META = dict(
    id="AM-107", title="DC optimal power flow on a 5-bus network", level="H",
    tools="DC power-flow model (B-matrix, PTDFs), linear program for least-cost dispatch with line limits (HiGHS), locational marginal prices from dual variables, verification of KKT conditions and of prices by finite perturbation",
    summary="Dispatch three generators to serve load on a 5-bus transmission network at least cost, first ignoring and then enforcing line limits, "
            "and show that congestion creates different electricity prices at different buses — the LP's shadow prices.",
    problem="Why does electricity cost more at some locations of the grid than others, even with the same generators?",
    theory=r"""DC approximation: P = Bθ, line flow $F_ℓ = (θ_i-θ_j)/x_ℓ$, linear in injections via PTDFs. OPF: minimise Σc_gP_g subject to power balance, $|F_ℓ|≤F^{max}_ℓ$, generator limits — an LP. Without congestion one marginal generator sets a single
price everywhere; with a binding line limit, prices differ by bus: $LMP_i = λ − \sum_ℓ μ_ℓ\,PTDF_{ℓ,i}$ and each LMP equals the cost of serving 1 MW more load at that bus.""",
    method="""5 buses, 6 lines (reactances 0.03–0.1 p.u.), generators at buses 1, 3, 5 with costs 14, 30, 40 $/MWh and capacities 600/300/400 MW (a first version with capacities summing exactly to the load left only one, infeasible, dispatch); loads 300/300/400 MW at buses 2, 3, 4. Line 1–2 limit 280 MW (with this topology the flow on line 1–2 cannot go below ≈ 266 MW whatever the dispatch, so a first choice of 240 MW was infeasible, and 300 MW never bound).
LP solved with and without limits; LMPs from duals; each LMP checked by re-solving with +1 MW load at that bus.""",
)

LINES = [(0, 1, 0.03, 280), (0, 3, 0.03, 1e6), (0, 4, 0.065, 1e6), (1, 2, 0.1, 1e6), (2, 3, 0.03, 1e6), (3, 4, 0.03, 1e6)]
GEN = [(0, 14.0, 600), (2, 30.0, 300), (4, 40.0, 400)]
LOAD = np.array([0, 300.0, 300.0, 400.0, 0])


def ptdf():
    n = 5; B = np.zeros((n, n))
    for i, j, x, _ in LINES:
        B[i, i] += 1 / x; B[j, j] += 1 / x; B[i, j] -= 1 / x; B[j, i] -= 1 / x
    Bi = np.zeros((n, n)); Bi[1:, 1:] = np.linalg.inv(B[1:, 1:])
    return np.array([(Bi[i] - Bi[j]) / x for i, j, x, _ in LINES])


def opf(load, limits=True):
    H = ptdf(); ng = len(GEN)
    c = np.array([g[1] for g in GEN])
    Aeq = np.ones((1, ng)); beq = [load.sum()]
    G = np.zeros((5, ng))
    for k, (b, _, _) in enumerate(GEN):
        G[b, k] = 1
    Ahat = H @ G; fl = H @ load
    Aub, bub = [], []
    if limits:
        for l, (_, _, _, fmax) in enumerate(LINES):
            Aub.append(Ahat[l]); bub.append(fmax + fl[l]); Aub.append(-Ahat[l]); bub.append(fmax - fl[l])
    res = linprog(c, A_ub=np.array(Aub) if Aub else None, b_ub=bub if bub else None, A_eq=Aeq, b_eq=beq,
                  bounds=[(0, g[2]) for g in GEN], method="highs")
    flows = Ahat @ res.x - fl
    lam = res.eqlin.marginals[0]
    mu = res.ineqlin.marginals if limits else np.zeros(0)
    lmp = np.full(5, lam)
    if limits:
        for l in range(len(LINES)):
            lmp -= (mu[2 * l] - mu[2 * l + 1]) * H[l] * -1
    return res.fun, res.x, flows, lmp


def run(p):
    c0, P0, F0, _ = opf(LOAD, limits=False)
    c1, P1, F1, lmp = opf(LOAD, limits=True)
    p.metric("Unconstrained dispatch (MW) and flow on line 1–2", f"{P0.round(1)}, F12 = {F0[0]:.1f} MW (limit 280)")
    p.metric("Constrained dispatch (MW) and flow on line 1–2", f"{P1.round(1)}, F12 = {F1[0]:.1f} MW")
    p.compare("Line 1–2 limit binds in the constrained solution", 280, abs(F1[0]), "MW", tol=0.0001)
    p.compare("Power balance (generation − load)", 0, P1.sum() - LOAD.sum(), "MW", kind="abs", tol=1e-6)
    p.metric("Cost of congestion", c1 - c0, "$/h")
    fd = []
    for b in range(5):
        L2 = LOAD.copy(); L2[b] += 1.0
        fd.append(opf(L2, limits=True)[0] - c1)
    fd = np.array(fd)
    p.compare("LMPs from LP duals vs +1 MW finite-difference cost at each bus (max |Δ|)", 0, np.max(np.abs(lmp - fd)), "$/MWh", kind="abs", tol=0.05)
    p.metric("Locational marginal prices, buses 1–5", ", ".join(f"{v:.2f}" for v in fd), "$/MWh")
    p.compare("Congestion creates price differences (max − min LMP > 0)", 1, int(np.ptp(fd) > 1), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    xy = np.array([[0, 1], [1, 2], [2, 1], [1.5, 0], [0.2, -0.2]])
    for (i, j, x, fm), f_ in zip(LINES, F1):
        ax[0].plot(*xy[[i, j]].T, color=C_PRED if fm < 1e5 and abs(abs(f_) - fm) < 1e-3 else COLORS[7], lw=1 + abs(f_) / 60)
        m = xy[[i, j]].mean(0); ax[0].text(*m, f"{abs(f_):.0f}", fontsize=8)
    for b in range(5):
        ax[0].plot(*xy[b], "o", ms=18, color=C_MEAS); ax[0].text(*xy[b], f"{b + 1}", ha="center", va="center", color="white", fontsize=9)
        ax[0].text(xy[b, 0], xy[b, 1] - 0.22, f"${fd[b]:.1f}", ha="center", fontsize=8)
    ax[0].axis("off"); ax[0].set_title("Flows (MW) and LMPs; congested line in orange", loc="left", fontsize=10)
    ax[1].bar(np.arange(1, 6), fd, color=C_MEAS)
    style_axes(ax[1], "bus", "LMP ($/MWh)", "Prices differ only because of congestion", legend=False)
    p.save(fig, "opf", "Line flows and locational marginal prices in the congested dispatch.")
    p.discuss(f"""Without line limits the cheapest generator (bus 1, 14 $/MWh) would push {abs(F0[0]):.0f} MW through line 1–2, exceeding its 280 MW rating; the LP instead holds
that line exactly at its limit and dispatches more expensive generation elsewhere, costing {c1 - c0:.0f} $/h extra. The dual variables of the LP turn
into locational marginal prices, and each one is confirmed by brute force: adding 1 MW of load at a bus raises the optimal cost by exactly that
bus's LMP. The prices spread from ~14 to above 40 $/MWh — some buses even exceed the most expensive generator's cost, because serving load
there requires re-dispatching around the congested line (a classic counter-intuitive OPF result). This is how wholesale electricity markets
price transmission scarcity.""")
# tol-convention: relative tolerances are in percent
