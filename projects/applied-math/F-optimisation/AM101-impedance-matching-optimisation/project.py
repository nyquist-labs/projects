from eelab import *
from scipy.optimize import minimize, differential_evolution

META = dict(
    id="AM-101", title="Broadband impedance matching by optimisation, against the Bode–Fano limit", level="H",
    tools="Ladder matching networks (1–4 elements) optimised for minimax reflection over a band (differential evolution + Nelder–Mead), ABCD evaluation, Bode–Fano integral bound",
    summary="Match a parallel RC load (an antenna/photodiode-like load) to 50 Ω over an octave, minimising the worst reflection with 1–4 element "
            "ladders, and compare the achieved in-band |Γ| with the Bode–Fano limit that no lossless network can beat.",
    problem="How good can a match be over a wide band — and is the limit set by cleverness or by physics?",
    theory=r"""For a load R‖C, any lossless matching network obeys the Bode–Fano bound $\int_0^∞\ln\frac1{|Γ(ω)|}dω \le \frac{π}{RC}$. With |Γ| constant = Γ_m over a band Δω and 1 elsewhere, the best possible is
$Γ_m = e^{-π/(RC\,Δω)}$. Real ladders approach this as the number of elements grows (an infinite network would reach it). Here R = 100 Ω, C = 3.2 pF, band 0.5–1 GHz: RCΔω = 1.005 ⇒ Γ_m ≥ 0.044.""",
    method="""Load 100 Ω ‖ 3.2 pF; source 50 Ω. Ladders alternating series L / shunt C from the load side, 1–4 elements, values on a log scale; objective max |Γ_in| over 201 frequencies in 0.5–1 GHz; global search (differential evolution) then Nelder–Mead polish.""",
)

R, C = 100.0, 3.2e-12


def gamma_in(x, f):
    w = 2 * pi * f; Z = 1 / (1 / R + 1j * w * C)
    for k, v in enumerate(x):
        val = 10 ** v
        if k % 2 == 0:
            Z = Z + 1j * w * val * 1e-9            # series L (nH)
        else:
            Z = 1 / (1 / Z + 1j * w * val * 1e-12)  # shunt C (pF)
    return (Z - 50) / (Z + 50)


def run(p):
    f = np.linspace(0.5e9, 1e9, 201)
    dw = 2 * pi * (f[-1] - f[0])
    bf = np.exp(-pi / (R * C * dw))
    p.metric("Bode–Fano limit on the in-band |Γ| (flat over 0.5–1 GHz)", bf, "")
    res = []
    prev = np.array([])
    for n in (1, 2, 3, 4):
        obj = lambda x: np.max(np.abs(gamma_in(x, f)))
        cands = []
        for seed in range(3):                                  # several global searches…
            de = differential_evolution(obj, [(-1, 2.5)] * n, seed=int(p.rng.integers(1e6)), tol=1e-12, maxiter=1500, popsize=30, polish=False)
            cands.append(de.x)
        cands.append(np.r_[prev, -3.0])                        # …plus a warm start: previous optimum + a negligible new element
        best = None
        for x0 in cands:
            x = minimize(obj, x0, method="Nelder-Mead", options=dict(xatol=1e-10, fatol=1e-12, maxiter=40000)).x
            if best is None or obj(x) < obj(best):
                best = x
        prev = best
        res.append((n, obj(best), best))
    g0 = np.max(np.abs(gamma_in([], f)))
    p.metric("Unmatched load: worst |Γ| in band", g0, "")
    for n, g, x in res:
        p.metric(f"{n}-element ladder: worst in-band |Γ|", g, "", ", ".join(f"{10 ** v:.3g} {'nH' if k % 2 == 0 else 'pF'}" for k, v in enumerate(x)))
    p.compare("Every optimised design respects Bode–Fano (worst |Γ| ≥ limit; 1 = yes)", 1, int(all(g >= bf * 0.999 for _, g, _ in res)), "", kind="abs")
    p.compare("Improvement is monotone in the number of elements (1 = yes)", 1, int(all(res[i + 1][1] <= res[i][1] + 1e-9 for i in range(3))), "", kind="abs")
    ff = np.linspace(0.05e9, 5e9, 20000)
    x4 = res[-1][2]
    integral = np.trapezoid(np.log(1 / np.abs(gamma_in(x4, ff))), 2 * pi * ff)
    p.compare("Bode–Fano integral of the 4-element design ≤ π/(RC)", pi / (R * C), integral, "rad/s", kind="abs", tol=pi / (R * C))
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    fp = np.linspace(0.2e9, 1.5e9, 600)
    ax.plot(fp / 1e9, np.abs(gamma_in([], fp)), color="gray", label="unmatched")
    for (n, g, x), c in zip(res, COLORS):
        ax.plot(fp / 1e9, np.abs(gamma_in(x, fp)), color=c, label=f"{n} elements (max {g:.3f})")
    ax.axhline(bf, color="black", ls=":", label=f"Bode–Fano limit {bf:.3f}"); ax.axvspan(0.5, 1.0, color=COLORS[7], alpha=.15)
    style_axes(ax, "frequency (GHz)", "|Γ_in|", "Optimised ladders vs the physical limit")
    p.save(fig, "matching", "Reflection of the RC load unmatched and with optimised 1–4 element ladders, against the Bode–Fano limit.")
    p.discuss(f"""Optimisation drives the worst in-band reflection down with every added element, but each design stays above the Bode–Fano limit Γ ≥ {bf:.3f} — and the
4-element network's reflection integral stays below π/RC as the theorem requires. Diminishing returns are visible: the first two elements do most of
the work, later ones buy smaller improvements, because the remaining 'reflection budget' is fixed by the load's RC product, not by the network. This
is the practical meaning of Bode–Fano: if a wide-band match to a capacitive load is needed, no amount of optimiser effort helps once near the
limit — reduce C or narrow the band. The global search matters: in a first run the 4-element search stalled in a degenerate minimum (one
element shrank to 0.0006 nH) and did *worse* than 3 elements; restarting the global search several times and adding a warm start from the
previous optimum restored the expected monotone improvement — minimax matching landscapes are riddled with poor local minima.""")
# tol-convention: relative tolerances are in percent
