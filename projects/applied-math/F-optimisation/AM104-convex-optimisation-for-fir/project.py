from eelab import *
from scipy import signal
from scipy.optimize import linprog

META = dict(
    id="AM-104", title="Minimax FIR design as a linear program", level="H",
    tools="Chebyshev (minimax) FIR design posed as an LP (scipy linprog/HiGHS), comparison with Parks–McClellan, extra convex constraints (peak stopband limit, exact DC gain) that Remez cannot handle",
    summary="Formulate equiripple FIR design as a linear program — minimise δ subject to |A(ω) − D(ω)| ≤ δ on a grid — confirm it reproduces "
            "Parks–McClellan, then add constraints the exchange algorithm cannot express (a hard −60 dB stopband ceiling while minimising passband ripple, and an exact DC gain).",
    problem="Remez gives the optimal equiripple filter. What if the specification is not 'equiripple with weights' but a set of hard limits?",
    theory=r"""A(ω) = Σ a_k cos kω is linear in a, so the constraints $-δ ≤ W(ω)(A(ω)-D(ω)) ≤ δ$ at grid points are linear inequalities, and minimising δ is an LP; its optimum equals the Chebyshev/Remez solution on the same grid.
Convexity makes adding constraints free of local minima: e.g. minimise passband ripple subject to |A| ≤ 10^{−60/20} in the stopband, or A(0) = 1. The answer is globally optimal by construction.""",
    method="""N = 41, passband 0–0.2, stopband 0.25–0.5; 500 grid points per band. LP with 21 coefficients + δ; HiGHS solver. (1) weighted minimax vs scipy.signal.remez; (2) passband ripple minimised with a −60 dB stopband ceiling (N increased until feasible);
(3) exact A(0) = 1.""",
)


def lp_design(N, fp, fs_, Wstop=1.0, stop_ceiling=None, dc_exact=False, grid=500):
    L = (N - 1) // 2
    g1 = np.linspace(0, fp, grid); g2 = np.linspace(fs_, 0.5, grid)
    C1 = np.cos(2 * pi * np.outer(g1, np.arange(L + 1))); C2 = np.cos(2 * pi * np.outer(g2, np.arange(L + 1)))
    nv = L + 2
    c = np.zeros(nv); c[-1] = 1
    rows, rhs = [], []
    for C, D, W in ((C1, 1.0, 1.0), (C2, 0.0, Wstop)):
        if stop_ceiling is not None and D == 0.0:
            rows += [np.r_[C[i], 0] for i in range(len(C))] + [np.r_[-C[i], 0] for i in range(len(C))]; rhs += [stop_ceiling] * (2 * len(C))
            continue
        rows += [np.r_[W * C[i], -1] for i in range(len(C))]; rhs += [W * D] * len(C)
        rows += [np.r_[-W * C[i], -1] for i in range(len(C))]; rhs += [-W * D] * len(C)
    Aeq = beq = None
    if dc_exact:
        Aeq = [np.r_[np.ones(L + 1), 0]]; beq = [1.0]
    res = linprog(c, A_ub=np.array(rows), b_ub=np.array(rhs), A_eq=Aeq, b_eq=beq, bounds=[(None, None)] * nv, method="highs")
    if res.status != 0:
        return None, None
    a = res.x[:L + 1]
    return np.r_[a[:0:-1] / 2, a[0], a[1:] / 2], res.x[-1]


def run(p):
    N = 41
    h, d = lp_design(N, 0.2, 0.25)
    hr = signal.remez(N, [0, 0.2, 0.25, 0.5], [1, 0], fs=1.0)
    w, H = signal.freqz(h, worN=2 ** 14, fs=1.0); _, Hr = signal.freqz(hr, worN=2 ** 14, fs=1.0)
    rip = lambda HH: max(np.max(np.abs(np.abs(HH[w <= 0.2]) - 1)), np.max(np.abs(HH[w >= 0.25])))
    p.compare("LP minimax vs Parks–McClellan: peak error (relative difference)", rip(Hr), rip(H), "", tol=2)
    p.compare("LP vs remez coefficients (max |Δh|)", 0, np.max(np.abs(h - hr)), "", kind="abs", tol=2e-3)
    ceiling = 10 ** (-60 / 20)
    Nf = None
    for Nc in range(41, 121, 2):
        hc, dc = lp_design(Nc, 0.2, 0.25, stop_ceiling=ceiling)
        if hc is not None and dc < 0.01:
            Nf = Nc; break
    wc, Hc = signal.freqz(hc, worN=2 ** 14, fs=1.0)
    p.compare("Hard −60 dB stopband ceiling respected (max stopband level)", -60, db(np.max(np.abs(Hc[wc >= 0.25]))), "dB", kind="abs", tol=0.2)
    p.metric("Shortest filter meeting −60 dB stopband with passband ripple < 1 %", Nf, "taps")
    hd, _ = lp_design(N, 0.2, 0.25, dc_exact=True)
    p.compare("Exact DC gain constraint A(0) = 1", 1.0, np.sum(hd), "", tol=1e-07)
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    ax.plot(w, db(np.abs(H) + 1e-12), color=C_MEAS, lw=2.5, alpha=.6, label="LP minimax (N = 41)"); ax.plot(w, db(np.abs(Hr) + 1e-12), "--", color=C_PRED, label="Parks–McClellan (N = 41)")
    ax.plot(wc, db(np.abs(Hc) + 1e-12), color=COLORS[2], label=f"LP with −60 dB ceiling (N = {Nf})"); ax.axhline(-60, color="gray", ls=":")
    ax.set_ylim(-100, 5)
    style_axes(ax, "frequency (cycles/sample)", "|H| (dB)", "Minimax FIR by linear programming")
    p.save(fig, "lp_fir", "The LP minimax design matches Parks–McClellan; hard constraints are added without changing the method.")
    p.discuss(f"""Posed as a linear program, minimax FIR design returns the same filter as Parks–McClellan (same peak error, coefficients equal to the grid
tolerance) — the exchange algorithm is a specialised solver for this particular LP. What the LP formulation adds is flexibility with guaranteed
global optimality: a hard −60 dB stopband ceiling (with passband ripple minimised) is just a different set of inequalities, and it tells us the
shortest filter meeting both specs is {Nf} taps; an exact DC gain is one equality. Remez can only trade weights and cannot express a hard limit
directly. The cost is speed — thousands of constraints instead of a few exchange iterations — irrelevant at these sizes.""")
# tol-convention: relative tolerances are in percent
