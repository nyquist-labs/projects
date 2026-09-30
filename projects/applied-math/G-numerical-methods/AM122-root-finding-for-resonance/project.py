from eelab import *

META = dict(
    id="AM-122", title="Root finding for resonance: bisection, secant and Newton", level="E",
    tools="Own bisection, secant, Newton and Brent-free comparison on the reactance of an LC network, convergence-order measurement from error sequences",
    summary="Find the series-resonance frequency of a two-tank network (a zero of its reactance) with three root finders, and measure their "
            "convergence orders — 1 (with factor ½), the golden ratio 1.618, and 2 — from the error sequences.",
    problem="Resonance is where reactance crosses zero. Which root finder should a filter-tuning script use?",
    theory=r"""Bisection halves the bracket: linear convergence, error ratio ½, guaranteed. Secant: order φ = (1+√5)/2 ≈ 1.618, one function evaluation per step. Newton: order 2 but needs the derivative (two evaluations per step for
reactance plus slope), so per *function evaluation* the secant method's efficiency index 1.618 beats Newton's √2 ≈ 1.414. Order estimated as $p ≈ \frac{\ln(e_{k+1}/e_k)}{\ln(e_k/e_{k-1})}$.""",
    method="""Network: L1 = 10 µH in series with (L2 = 4.7 µH ∥ C2 = 1 nF) in series with C1 = 470 pF — its reactance X(ω) has series-resonance zeros on either side of the parallel resonance (a pole) at 2.32 MHz. Reference root: closed form (a quadratic in ω²). The three methods search the upper zero from the bracket
[2.6, 4.0] MHz (Newton from 3.0 MHz); orders from the last three errors above round-off; evaluations to 1e-12 relative. A second bisection on [2, 3] MHz demonstrates the pole pitfall.""",
)

L1, L2, C2, C1 = 10e-6, 4.7e-6, 1e-9, 470e-12


def X(f):
    w = 2 * pi * f
    Zp = 1 / (1 / (1j * w * L2) + 1j * w * C2)
    return (1j * w * L1 + Zp + 1 / (1j * w * C1)).imag


def dX(f, h=1.0):
    return (X(f + h) - X(f - h)) / (2 * h)


def order_of(e, floor=1e-3):
    """Convergence order from the last three errors above the round-off floor (Hz)."""
    e = np.asarray(e); e = e[e > floor]
    return np.log(e[-1] / e[-2]) / np.log(e[-2] / e[-3])


def run(p):
    # analytic zeros: (uL1C1 − 1)(1 − uL2C2) + uL2C1 = 0 with u = ω²
    qa, qb, qc = -L1 * C1 * L2 * C2, L1 * C1 + L2 * C2 + L2 * C1, -1.0
    u = np.roots([qa, qb, qc]); fz = np.sort(np.sqrt(u.real)) / (2 * pi)
    fpole = 1 / (2 * pi * np.sqrt(L2 * C2))
    a, b = 2.6e6, 4.0e6
    lo, hi = a, b
    for _ in range(200):
        m = (lo + hi) / 2
        (lo, hi) = (m, hi) if np.sign(X(m)) == np.sign(X(lo)) else (lo, m)
    root = (lo + hi) / 2
    p.compare("Upper series resonance: bisection root vs closed form (quadratic in ω²)", fz[1], root, "Hz", tol=1e-07)
    p.metric("Lower series resonance / parallel resonance (pole)", f"{fz[0] / 1e6:.4f} MHz / {fpole / 1e6:.4f} MHz")
    # pitfall: a sign change across a pole also 'brackets'
    lo, hi = 2.0e6, 3.0e6
    for _ in range(200):
        m = (lo + hi) / 2
        (lo, hi) = (m, hi) if np.sign(X(m)) == np.sign(X(lo)) else (lo, m)
    trap = (lo + hi) / 2
    p.compare("Pitfall: bisection on [2, 3] MHz (sign change across a pole) converges to the parallel resonance 1/2π√(L₂C₂)", fpole, trap, "Hz", tol=0.0001)
    p.metric("|X| at that 'root'", abs(X(trap)), "Ω", "not a zero at all — always check the residual")
    seq = {}
    lo, hi = a, b; e = []; width = []
    for _ in range(45):
        m = (lo + hi) / 2; e.append(abs(m - root)); width.append(hi - lo); (lo, hi) = (m, hi) if np.sign(X(m)) == np.sign(X(lo)) else (lo, m)
    seq["bisection"] = np.array(e); width = np.array(width)
    x0, x1 = a, b; e = [abs(x0 - root), abs(x1 - root)]
    for _ in range(20):
        den = X(x1) - X(x0)
        if den == 0 or e[-1] < 1e-6:
            break
        x2 = x1 - X(x1) * (x1 - x0) / den; x0, x1 = x1, x2; e.append(abs(x1 - root))
    seq["secant"] = np.array(e)
    x = 3.0e6; e = [abs(x - root)]
    for _ in range(12):
        if e[-1] < 1e-6:
            break
        x = x - X(x) / dX(x); e.append(abs(x - root))
    seq["Newton"] = np.array(e)
    p.compare("Bisection: bracket (error bound) ratio per step (½)", 0.5, float(np.median(width[1:30] / width[:29])), "", tol=0.0001)
    p.compare("Bisection: midpoint error never exceeds half the bracket (violations)", 0, int(np.sum(seq["bisection"][:35] > width[:35] / 2 * (1 + 1e-9))), "", kind="abs")
    p.compare("Secant: convergence order (golden ratio 1.618)", 1.618, order_of(seq["secant"]), "", tol=20)
    p.compare("Newton: convergence order (2)", 2.0, order_of(seq["Newton"]), "", tol=15)
    ev = {"bisection": int(np.argmax(seq["bisection"] < root * 1e-12)) + 2, "secant": len(seq["secant"]), "Newton": 3 * (len(seq["Newton"]) - 1)}
    p.metric("Function evaluations to 1e-12 relative: bisection / secant / Newton (derivative by 2 extra evaluations)", " / ".join(f"{ev[k]}" for k in ev))
    seq = {k: (v, 0) for k, v in seq.items()}
    fig, ax = p.fig(1, 2, w=11)
    f = np.linspace(1e6, 5e6, 2000)
    ax[0].plot(f / 1e6, np.clip([X(q) for q in f], -2000, 2000), color=C_MEAS); ax[0].axhline(0, color="gray", lw=.6); ax[0].axvline(root / 1e6, color=C_PRED, ls="--")
    style_axes(ax[0], "frequency (MHz)", "reactance X (Ω)", "Reactance: zeros = series resonances, poles = parallel", legend=False)
    for (k, (e, _)), c in zip(seq.items(), (COLORS[1], COLORS[2], C_MEAS)):
        ax[1].semilogy(np.maximum(e / root, 1e-17), "o-", color=c, label=k)
    style_axes(ax[1], "iteration", "relative error", "Convergence")
    p.save(fig, "roots", "Reactance of the two-tank network and the error histories of three root finders.")
    p.discuss("""The measured orders match theory: bisection halves the error every step (slow but unconditionally safe once bracketed), the secant method converges
with order ≈ 1.62 and Newton with order 2. Counted in function evaluations — the real cost when each evaluation is a circuit simulation — the secant
method wins, because Newton's derivative costs extra evaluations here (finite differences). Reactance functions have poles between their zeros, and the first version of this
project fell into exactly that trap: the bracket [2, 3] MHz has a sign change, bisection converged beautifully — to the parallel resonance, where X
jumps from +∞ to −∞ and is nowhere near zero. A sign change is necessary for a root, not sufficient; checking the residual |X| exposes it at once.
Unbracketed Newton or secant can likewise jump across a pole to the wrong resonance; production code (Brent's method) combines the bracket of bisection with
the speed of secant/inverse-quadratic steps for exactly this reason.""")
# tol-convention: relative tolerances are in percent
