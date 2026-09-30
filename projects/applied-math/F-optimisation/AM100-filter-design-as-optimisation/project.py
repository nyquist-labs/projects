from eelab import *
from scipy import signal
from scipy.optimize import minimize

META = dict(
    id="AM-100", title="Filter design as constrained optimisation", level="H",
    tools="Weighted least-squares FIR design written as normal equations (own), equality-constrained LS via KKT system, comparison with scipy.signal.firls, trade-off curve by weight sweep",
    summary="Formulate linear-phase FIR design as an explicit optimisation — minimise weighted squared error over pass- and stop-bands subject to "
            "exact constraints (unit DC gain, a forced null) — solve it in closed form via the KKT equations, and verify against SciPy and against the constraint values.",
    problem="'Design a low-pass filter' is vague. What exactly is being minimised, and how do hard requirements enter?",
    theory=r"""Type-I amplitude A(ω) = Σ a_k cos kω is linear in a. Weighted LS: minimise $\int W(ω)(A(ω)-D(ω))^2dω ≈ \|W^{1/2}(Ca-d)\|^2$ ⇒ normal equations $C^TWCa = C^TWd$. Equality constraints Ea = f (e.g. A(0) = 1, A(ω_n) = 0) via
Lagrange multipliers: $\begin{bmatrix}C^TWC & E^T\\E&0\end{bmatrix}\begin{bmatrix}a\\λ\end{bmatrix}=\begin{bmatrix}C^TWd\\f\end{bmatrix}$. Raising the stopband weight trades passband error for stopband energy along a convex curve.""",
    method="""N = 51 taps (L = 25), passband 0–0.2, stopband 0.26–0.5 (cycles/sample), dense grid of 2000 points. Unconstrained WLS vs scipy.signal.firls; constrained version with A(0) = 1 exactly and a null at 0.3; weight sweep 1…1000.""",
)


def design(N, W_s, constraints=()):
    L = (N - 1) // 2
    g = np.r_[np.linspace(0, 0.2, 800), np.linspace(0.26, 0.5, 1200)]
    w = 2 * pi * g; D = (g <= 0.2).astype(float); Wt = np.where(g <= 0.2, 1.0, W_s)
    C = np.cos(np.outer(w, np.arange(L + 1)))
    A = C.T @ (Wt[:, None] * C); b = C.T @ (Wt * D)
    if constraints:
        E = np.array([np.cos(2 * pi * f0 * np.arange(L + 1)) for f0, _ in constraints]); fv = np.array([v for _, v in constraints])
        K = np.block([[A, E.T], [E, np.zeros((len(fv), len(fv)))]])
        a = np.linalg.solve(K, np.r_[b, fv])[:L + 1]
    else:
        a = np.linalg.solve(A, b)
    h = np.r_[a[:0:-1] / 2, a[0], a[1:] / 2]
    return h, a


def run(p):
    N = 51
    h, a = design(N, 10.0)
    hs = signal.firls(N, [0, 0.2, 0.26, 0.5], [1, 1, 0, 0], weight=[1, 10], fs=1.0)
    p.compare("Own weighted LS vs scipy.signal.firls (max |Δh|; firls integrates exactly, own uses a dense grid)", 0, np.max(np.abs(h - hs)), "", kind="abs", tol=2e-3)
    hc, ac = design(N, 10.0, constraints=((0.0, 1.0), (0.3, 0.0)))
    w, H = signal.freqz(hc, worN=[0.0, 2 * pi * 0.3])
    p.compare("Constrained design: DC gain exactly 1", 1.0, abs(H[0]), "", tol=1e-10)
    p.compare("Constrained design: exact null at 0.3 cycles/sample", 0, abs(H[1]), "", kind="abs", tol=1e-12)
    wf, Hu = signal.freqz(h, worN=4096, fs=1.0); _, Hc = signal.freqz(hc, worN=4096, fs=1.0)
    pb = wf <= 0.2; sb = wf >= 0.26
    cost = lambda HH: (np.mean((np.abs(HH[pb]) - 1) ** 2), np.mean(np.abs(HH[sb]) ** 2))
    p.metric("Constraint cost: pass/stop MSE unconstrained vs constrained", f"{cost(Hu)[0]:.2e}/{cost(Hu)[1]:.2e} vs {cost(Hc)[0]:.2e}/{cost(Hc)[1]:.2e}")
    tr = []
    for Ws in np.logspace(0, 3, 13):
        hh, _ = design(N, Ws); _, HH = signal.freqz(hh, worN=4096, fs=1.0); tr.append(cost(HH))
    tr = np.array(tr)
    p.compare("Weight sweep traces a monotone trade-off (passband error ↑ as stopband energy ↓; 1 = yes)", 1, int(np.all(np.diff(tr[:, 0]) > 0) and np.all(np.diff(tr[:, 1]) < 0)), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(wf, db(np.abs(Hu) + 1e-12), color=C_MEAS, label="weighted LS"); ax[0].plot(wf, db(np.abs(Hc) + 1e-12), color=C_PRED, label="+ DC = 1, null at 0.3")
    ax[0].set_ylim(-90, 5)
    style_axes(ax[0], "frequency (cycles/sample)", "|H| (dB)", "Constraints enter through Lagrange multipliers")
    ax[1].loglog(tr[:, 1], tr[:, 0], "o-", color=C_MEAS)
    style_axes(ax[1], "stopband energy", "passband MSE", "Trade-off curve (stopband weight 1 → 1000)", legend=False)
    p.save(fig, "ls_fir", "Weighted-LS and constrained FIR responses, and the pass/stop trade-off curve.")
    p.discuss("""Written as an optimisation, FIR design is just weighted least squares: the self-built normal equations reproduce SciPy's firls (to the small
difference between a dense grid and exact band integrals). Hard requirements become linear equality constraints solved in the same KKT system:
the constrained filter has DC gain exactly 1 and an exact zero at 0.3 cycles/sample, paid for by a slightly higher squared error elsewhere. The
weight sweep traces the Pareto curve between passband error and stopband energy — there is no 'best' filter without a stated trade-off, which is
exactly what the weights (or, in AM-104, a minimax objective) encode.""")
# tol-convention: relative tolerances are in percent
