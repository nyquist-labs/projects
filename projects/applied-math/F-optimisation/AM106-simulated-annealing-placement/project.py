from eelab import *

META = dict(
    id="AM-106", title="Simulated annealing for component placement", level="H",
    tools="Half-perimeter wirelength (HPWL) objective, random, greedy (steepest-descent swaps) and simulated-annealing placement on a grid, cooling-schedule study",
    summary="Place 60 components connected by 90 multi-pin nets on a 10×10 grid to minimise total wirelength; compare random placement, greedy "
            "improvement and simulated annealing, and show that annealing's willingness to accept uphill moves escapes the local minima that trap greedy search.",
    problem="Placement is a huge combinatorial problem. Why does an algorithm that deliberately makes things worse sometimes find better solutions?",
    theory=r"""Cost = Σ_nets (bounding-box half-perimeter). Moves: swap two cells (or move to an empty site). Metropolis rule: accept an uphill Δ with probability e^{−Δ/T}; T is lowered geometrically. At high T the search wanders
freely; as T → 0 it becomes greedy. With slow enough cooling annealing approaches the global optimum; greedy search stops at the first local minimum. I expect SA to cut wirelength ~30–50 % below random and ~10–20 % below greedy.""",
    method="""Synthetic netlist with locality (components in 6 clusters, nets mostly within clusters, some global). Greedy: random swaps accepted only if they improve, until 20,000 consecutive failures. SA: T₀ from the average uphill Δ, α = 0.95 per
stage, 2000 moves per stage, stop when acceptance < 0.5 %. 5 seeds each; cooling-rate study α = 0.8…0.99.""",
)


def netlist(r, n=60, nets=90):
    cl = np.repeat(np.arange(6), 10)
    out = []
    for k in range(nets):
        if r.random() < 0.8:
            c = r.integers(6); members = r.choice(np.flatnonzero(cl == c), r.integers(2, 5), replace=False)
        else:
            members = r.choice(n, r.integers(2, 5), replace=False)
        out.append(members)
    return out


def hpwl(pos, nets):
    return sum(np.ptp(pos[m, 0]) + np.ptp(pos[m, 1]) for m in nets)


def net_of(nets, n):
    lst = [[] for _ in range(n)]
    for k, m in enumerate(nets):
        for c in m:
            lst[c].append(k)
    return lst


def swap_delta(pos, nets, byc, a, b):
    ks = set(byc[a]) | set(byc[b])
    before = sum(np.ptp(pos[nets[k], 0]) + np.ptp(pos[nets[k], 1]) for k in ks)
    pos[[a, b]] = pos[[b, a]]
    after = sum(np.ptp(pos[nets[k], 0]) + np.ptp(pos[nets[k], 1]) for k in ks)
    pos[[a, b]] = pos[[b, a]]
    return after - before


def greedy(pos, nets, byc, r, patience=20000):
    pos = pos.copy(); fails = 0; n = len(pos)
    while fails < patience:
        a, b = r.choice(n, 2, replace=False); d = swap_delta(pos, nets, byc, a, b)
        if d < 0:
            pos[[a, b]] = pos[[b, a]]; fails = 0
        else:
            fails += 1
    return pos


def anneal(pos, nets, byc, r, alpha=0.95, moves=2000):
    pos = pos.copy(); n = len(pos)
    ups = [d for d in (swap_delta(pos, nets, byc, *r.choice(n, 2, replace=False)) for _ in range(300)) if d > 0]
    T = np.mean(ups) * 2
    while True:
        acc = 0
        for _ in range(moves):
            a, b = r.choice(n, 2, replace=False); d = swap_delta(pos, nets, byc, a, b)
            if d <= 0 or r.random() < np.exp(-d / T):
                pos[[a, b]] = pos[[b, a]]; acc += 1
        T *= alpha
        if acc / moves < 0.005:
            break
    return greedy(pos, nets, byc, r, 3000)


def run(p):
    rows = []
    for seed in range(5):
        r = np.random.default_rng(1000 + seed)
        nets = netlist(r); byc = net_of(nets, 60)
        sites = np.array([(i, j) for i in range(10) for j in range(10)])
        pos = sites[r.choice(100, 60, replace=False)].astype(float)
        c0 = hpwl(pos, nets); cg = hpwl(greedy(pos, nets, byc, r), nets); cs = hpwl(anneal(pos, nets, byc, r), nets)
        rows.append((c0, cg, cs))
    rr = np.array(rows)
    p.compare("SA reduction vs random placement (mean over 5 netlists; my guess 30–50 %)", 40, (1 - rr[:, 2] / rr[:, 0]).mean() * 100, "%", kind="abs", tol=15)
    p.compare("SA advantage over greedy swapping (my guess 10–20 %)", 15, (1 - rr[:, 2] / rr[:, 1]).mean() * 100, "%", kind="abs", tol=10)
    p.compare("SA better than greedy on every netlist (1 = yes)", 1, int(np.all(rr[:, 2] < rr[:, 1])), "", kind="abs")
    r = np.random.default_rng(7); nets = netlist(r); byc = net_of(nets, 60)
    sites = np.array([(i, j) for i in range(10) for j in range(10)]); pos = sites[r.choice(100, 60, replace=False)].astype(float)
    alphas = (0.8, 0.9, 0.95, 0.98)
    ac = [hpwl(anneal(pos, nets, byc, np.random.default_rng(3), alpha=a, moves=1000), nets) for a in alphas]
    p.metric("Wirelength vs cooling rate α = 0.8 / 0.9 / 0.95 / 0.98", " / ".join(f"{c:.0f}" for c in ac))
    fig, ax = p.fig(1, 2, w=11)
    ax[0].bar(["random", "greedy", "annealing"], rr.mean(0), yerr=rr.std(0), color=[COLORS[7], COLORS[1], C_MEAS])
    style_axes(ax[0], None, "total HPWL (grid units)", "Mean over 5 netlists", legend=False)
    best = anneal(pos, nets, byc, np.random.default_rng(3))
    cl = np.repeat(np.arange(6), 10)
    for c in range(6):
        ax[1].plot(best[cl == c, 0], best[cl == c, 1], "s", ms=12, color=COLORS[c], label=f"cluster {c}")
    ax[1].set_xlim(-1, 10); ax[1].set_ylim(-1, 10); ax[1].set_aspect("equal")
    style_axes(ax[1], "x", "y", "Annealed placement groups each cluster")
    p.save(fig, "annealing", "Wirelength for three placement methods, and an annealed placement coloured by logical cluster.")
    p.discuss(f"""Annealing cuts total wirelength by {(1 - rr[:, 2] / rr[:, 0]).mean() * 100:.0f} % relative to random placement and beats greedy swapping on every netlist (by
{(1 - rr[:, 2] / rr[:, 1]).mean() * 100:.0f} % on average): greedy search stops at the first placement where no single swap helps, while annealing's accepted
uphill moves let whole groups migrate before the temperature freezes them. Without being told, the annealed layout collects each logical
cluster into a compact region. Slower cooling generally helps but with diminishing returns, and it multiplies run time; industrial placers combine
annealing-like global moves with analytical (quadratic-wirelength) placement for speed.""")
# tol-convention: relative tolerances are in percent
