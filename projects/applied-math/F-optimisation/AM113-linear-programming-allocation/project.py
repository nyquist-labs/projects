from eelab import *
from scipy.optimize import linprog

META = dict(
    id="AM-113", title="Linear programming: allocating parts to board builds", level="M",
    tools="Own dense tableau simplex method (Bland's rule), scipy linprog/HiGHS for verification, dual prices (shadow values of scarce parts), sensitivity ranging by re-solving",
    summary="Decide how many of four board types to build from a limited component inventory to maximise profit, solve it with a self-written "
            "simplex and verify with HiGHS, read the shadow prices of the scarce parts, and check them by re-solving with one more unit of each part.",
    problem="A parts shortage limits production. Which boards should be built — and what is one more reel of a scarce chip worth?",
    theory=r"""max cᵀx s.t. Ax ≤ b, x ≥ 0. The optimum is at a vertex; simplex walks along edges improving the objective. Strong duality: the dual variables y (shadow prices) satisfy cᵀx* = bᵀy*, and $y_i = ∂(\text{profit})/∂b_i$ as long as the basis
does not change; parts with slack have price 0 (complementary slackness).""",
    method="""4 products, 5 resources (MCU, FPGA, DC/DC module, assembly hours, test hours) with a given bill of materials and profits. Own simplex vs HiGHS (primal and duals). Shadow prices checked by +1 unit finite differences; relaxing the most
valuable constraint.""",
)

A = np.array([[1, 1, 0, 2], [0, 1, 1, 0], [1, 2, 1, 2], [2, 3, 2, 4], [1, 2, 1, 1.5]], float)
B = np.array([400, 150, 700, 1200, 800.0])
C = np.array([30, 70, 40, 90.0])
NAMES = ["MCU", "FPGA", "DC/DC module", "assembly hours", "test hours"]


def simplex(c, A, b):
    m, n = A.shape
    T = np.zeros((m + 1, n + m + 1)); T[:m, :n] = A; T[:m, n:n + m] = np.eye(m); T[:m, -1] = b; T[-1, :n] = -c
    basis = list(range(n, n + m))
    while True:
        col = next((j for j in range(n + m) if T[-1, j] < -1e-12), None)       # Bland's rule: first improving column
        if col is None:
            break
        ratios = [(T[i, -1] / T[i, col], basis[i], i) for i in range(m) if T[i, col] > 1e-12]
        _, _, row = min(ratios)
        T[row] /= T[row, col]
        for i in range(m + 1):
            if i != row:
                T[i] -= T[i, col] * T[row]
        basis[row] = col
    x = np.zeros(n + m)
    for i, bi in enumerate(basis):
        x[bi] = T[i, -1]
    return x[:n], T[-1, -1], T[-1, n:n + m]


def run(p):
    x, z, y = simplex(C, A, B)
    res = linprog(-C, A_ub=A, b_ub=B, bounds=[(0, None)] * 4, method="highs")
    p.compare("Own simplex optimum profit vs HiGHS", -res.fun, z, "$", tol=1e-07)
    p.compare("Own simplex duals vs HiGHS marginals (max |Δ|)", 0, np.max(np.abs(y + res.ineqlin.marginals)), "$", kind="abs", tol=1e-9)
    p.compare("Strong duality: cᵀx* = bᵀy*", z, B @ y, "$", tol=1e-07)
    p.metric("Optimal build plan (boards A–D)", ", ".join(f"{v:.1f}" for v in x))
    fd = []
    for i in range(5):
        b2 = B.copy(); b2[i] += 1
        fd.append(-linprog(-C, A_ub=A, b_ub=b2, bounds=[(0, None)] * 4, method="highs").fun - z)
    p.compare("Shadow prices vs +1-unit re-solve (max |Δ|)", 0, np.max(np.abs(np.array(fd) - y)), "$", kind="abs", tol=1e-6)
    slack = B - A @ x
    p.compare("Complementary slackness: price × slack = 0 for every resource", 0, np.max(np.abs(y * slack)), "", kind="abs", tol=1e-9)
    for n_, yy, sl in zip(NAMES, y, slack):
        p.metric(f"{n_}: shadow price / slack", f"${yy:.2f} per unit / {sl:.1f} unused")
    k = int(np.argmax(y))
    gains = []
    for extra in (0, 20, 50, 100, 200):
        b2 = B.copy(); b2[k] += extra; gains.append(-linprog(-C, A_ub=A, b_ub=b2, bounds=[(0, None)] * 4, method="highs").fun)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].bar(NAMES, y, color=C_MEAS); ax[0].tick_params(axis="x", rotation=20)
    style_axes(ax[0], None, "shadow price ($ / unit)", "What one more unit is worth", legend=False)
    ax[1].plot([0, 20, 50, 100, 200], gains, "o-", color=C_MEAS, label="re-solved optimum"); ax[1].plot([0, 200], [z, z + 200 * y[k]], "--", color=C_PRED, label="shadow-price extrapolation")
    style_axes(ax[1], f"extra {NAMES[k]} units", "optimal profit ($)", "Shadow prices are local")
    p.save(fig, "lp", "Shadow prices of the five resources, and how the profit responds to more of the scarcest one.")
    p.discuss(f"""The self-written simplex reaches the same vertex, profit and dual prices as HiGHS, and strong duality holds to rounding. The duals are the
practical output: they say exactly what one more unit of each constrained resource is worth (confirmed by re-solving), and resources with spare
capacity are worth nothing at the margin (complementary slackness). The right-hand plot shows their limit — a shadow price is a derivative, valid
only until the optimal basis changes; buying many more {NAMES[k]} units eventually makes a different constraint binding and the marginal value drops.
That is the sensitivity analysis a planner needs before paying a broker premium for scarce parts.""")
# tol-convention: relative tolerances are in percent
