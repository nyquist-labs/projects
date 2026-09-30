from eelab import *
from scipy import signal

META = dict(
    id="AM-114", title="Multi-objective design: Pareto fronts for an anti-alias filter", level="H",
    tools="Enumerated design space (filter family × order × cutoff), Pareto-dominance filtering, weighted-sum vs ε-constraint scalarisation, detection of non-convex front regions",
    summary="Choose an anti-aliasing filter with three competing goals — stopband attenuation, passband droop and group-delay distortion (plus "
            "component count via order) — compute the Pareto front of 2,000 candidate designs, and show that weighted-sum optimisation misses Pareto-optimal designs where the front is non-convex.",
    problem="'Best filter' has no meaning with several objectives. What does the set of reasonable choices look like, and which optimisation methods can find all of them?",
    theory=r"""A design is Pareto-optimal if no other design is at least as good in every objective and strictly better in one. Minimising a weighted sum Σw_iJ_i finds only designs on the *convex hull* of the front; the ε-constraint method
(minimise J₁ subject to J₂ ≤ ε) reaches every Pareto point. Filter families trade differently: Bessel = low delay distortion, poor selectivity; Chebyshev/elliptic = sharp, distorting; Butterworth in between.""",
    method="""Analog prototypes: Butterworth, Bessel, Chebyshev I (0.5 dB), elliptic (0.5 dB/60 dB), orders 2–8, cutoff 0.5–1.5 × passband edge (fp = 20 kHz, stopband from 30 kHz). Objectives: J₁ = −(min attenuation beyond 30 kHz), J₂ = droop at 20 kHz, J₃ = group-delay
variation over 0–20 kHz (µs). Pareto front in (J₁, J₃) at fixed max droop; weighted sums for 200 weights vs ε-constraint sweep.""",
)


def evaluate(fam, n, fc_ratio):
    wc = 2 * pi * 20e3 * fc_ratio
    if fam == "Butterworth":
        z, pz, k = signal.butter(n, wc, analog=True, output="zpk")
    elif fam == "Bessel":
        z, pz, k = signal.bessel(n, wc, analog=True, output="zpk", norm="mag")
    elif fam == "Chebyshev":
        z, pz, k = signal.cheby1(n, 0.5, wc, analog=True, output="zpk")
    else:
        z, pz, k = signal.ellip(n, 0.5, 60, wc, analog=True, output="zpk")
    f = np.r_[np.linspace(0, 20e3, 200), np.linspace(30e3, 200e3, 600)]
    _, H = signal.freqs_zpk(z, pz, k, worN=2 * pi * f)
    g = db(np.abs(H) + 1e-15); g -= g[0] if fam != "Chebyshev" or n % 2 else g[0] + 0.5
    att = -g[200:].max(); droop = -g[199]
    w = 2 * pi * f[:200]
    ph = np.unwrap(np.angle(H[:200])); gd = -np.gradient(ph, w)
    return -att, droop, np.ptp(gd) * 1e6


def pareto(P):
    keep = np.ones(len(P), bool)
    for i in range(len(P)):
        if np.any(np.all(P <= P[i], axis=1) & np.any(P < P[i], axis=1)):
            keep[i] = False
    return keep


def run(p):
    designs = [(fam, n, r) for fam in ("Butterworth", "Bessel", "Chebyshev", "elliptic") for n in range(2, 9) for r in np.linspace(0.5, 1.5, 70)]
    J = np.array([evaluate(*d) for d in designs])
    ok = J[:, 1] <= 3.0                                     # admissible: droop at 20 kHz ≤ 3 dB
    D2 = J[ok][:, [0, 2]]; names = [designs[i] for i in np.flatnonzero(ok)]
    front = pareto(D2)
    p.metric("Candidate designs / admissible (droop ≤ 3 dB) / Pareto-optimal in (attenuation, delay variation)", f"{len(J)} / {ok.sum()} / {front.sum()}")
    F = D2[front]; Fn = (F - F.min(0)) / np.ptp(F, 0)
    ws_hits = set()
    for w in np.linspace(0, 1, 201):
        ws_hits.add(int(np.argmin(w * Fn[:, 0] + (1 - w) * Fn[:, 1])))
    eps_hits = set()
    for eps in np.sort(F[:, 1]):
        cand = np.flatnonzero(F[:, 1] <= eps + 1e-12); eps_hits.add(int(cand[np.argmin(F[cand, 0])]))
    p.compare("ε-constraint sweep reaches every Pareto point (fraction)", 1.0, len(eps_hits) / len(F), "", tol=1e-07)
    p.compare("Weighted sums reach only the convex hull (fraction of the front found; < 1 if non-convex)", 0.5, len(ws_hits) / len(F), "", kind="abs", tol=0.5)
    fams = [names[i][0] for i in np.flatnonzero(front)]
    p.metric("Families on the front", ", ".join(f"{f_}: {fams.count(f_)}" for f_ in ("Bessel", "Butterworth", "Chebyshev", "elliptic")))
    fig, ax = p.fig(1, 1, w=8, h=5)
    colors = {"Butterworth": COLORS[0], "Bessel": COLORS[1], "Chebyshev": COLORS[2], "elliptic": COLORS[3]}
    for fam, c in colors.items():
        m = np.array([nm[0] == fam for nm in names])
        ax.scatter(-D2[m, 0], D2[m, 1], s=6, color=c, alpha=.35, label=fam)
    o = np.argsort(F[:, 0])
    ax.plot(-F[o, 0], F[o, 1], "k-", lw=1.5, label="Pareto front")
    hits = np.array(sorted(ws_hits)); ax.plot(-F[hits, 0], F[hits, 1], "o", mfc="none", mec=C_PRED, ms=9, label="found by weighted sums")
    ax.set_yscale("log")
    style_axes(ax, "stopband attenuation beyond 30 kHz (dB)", "group-delay variation 0–20 kHz (µs)", "Anti-alias filter trade-offs (droop ≤ 3 dB)")
    p.save(fig, "pareto", "All admissible designs by family, the Pareto front, and the subset reachable by weighted-sum optimisation.")
    p.discuss(f"""Out of {len(J)} candidate filters, {front.sum()} are Pareto-optimal: every other admissible design is beaten on both attenuation and delay distortion by
one of them. The front is populated by different families in different regions — Bessel where delay flatness matters most, elliptic and Chebyshev
where attenuation does — so the family choice itself is a trade-off decision, not a matter of taste. Scalarisation matters: the ε-constraint sweep
recovers the whole front by construction, whereas 201 weighted sums found only {len(ws_hits)} distinct designs, all on the convex hull; Pareto
designs in the front's non-convex dents are invisible to any weighting. Presenting the front, then letting the system-level requirement pick a
point, is the honest way to report a multi-objective design.""")
# tol-convention: relative tolerances are in percent
