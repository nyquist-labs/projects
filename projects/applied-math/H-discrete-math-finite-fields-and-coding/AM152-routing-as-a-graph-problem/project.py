from eelab import *
import heapq, itertools
from collections import deque
import networkx as nx

META = dict(
    id="AM-152", title="Routing as a graph problem: Lee, A*, and Steiner trees", level="H",
    tools="Own Lee (breadth-first) and A* maze routers on an obstacle grid, networkx shortest paths as an independent reference, weighted-A* sub-optimality bound, exact rectilinear Steiner minimal trees via Hanan-grid enumeration vs minimum spanning trees, net-ordering experiment",
    summary="Treat PCB/IC routing as shortest paths and Steiner trees on a grid graph: prove the maze routers optimal against an independent solver, "
            "measure how much search A* saves, check the 3/2 bound between spanning and Steiner trees, and show why the order in which nets are routed matters.",
    problem="An autorouter must connect thousands of pins without crossings. Which graph problems is it really solving, and which of them are easy?",
    theory=r"""A two-pin connection on a grid with obstacles is a shortest-path problem: Lee's algorithm (BFS) is optimal; A* with the Manhattan distance (an admissible, consistent heuristic) is optimal while expanding fewer cells. Weighted A* (f = g + w·h) returns a path
at most w times longer. A multi-pin net wants a rectilinear Steiner minimal tree (NP-hard); Hanan showed the optimum uses only intersections of the pins' grid lines, and Hwang that MST ≤ 3/2 · RSMT. For 3 pins RSMT = half the bounding-box perimeter.
Routing many nets sequentially is order-dependent: earlier nets become obstacles for later ones.""",
    method="""200 random 40×40 grids with 25 % blocked cells, random pin pairs. Steiner: 300 random nets with 3 and 4 pins and 100 with 5 pins on a 20×20 lattice, exact by enumerating up to n − 2 Hanan points. Ordering: 10 two-pin nets on a 24×24 single-layer
grid, routed sequentially in 60 random orders.""",
)


def neighbours(c, free):
    x, y = c
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        q = (x + d[0], y + d[1])
        if 0 <= q[0] < free.shape[0] and 0 <= q[1] < free.shape[1] and free[q]:
            yield q


def lee(free, s, t):
    dist = {s: 0}; dq = deque([s]); exp = 0
    while dq:
        c = dq.popleft(); exp += 1
        if c == t:
            return dist[c], exp, None
        for q in neighbours(c, free):
            if q not in dist:
                dist[q] = dist[c] + 1; dq.append(q)
    return None, exp, None


def astar(free, s, t, w=1.0):
    h = lambda c: abs(c[0] - t[0]) + abs(c[1] - t[1])
    g = {s: 0}; par = {s: None}; pq = [(w * h(s), 0, s)]; closed = set(); exp = 0
    while pq:
        f, negg, c = heapq.heappop(pq)
        if c in closed:
            continue
        closed.add(c); exp += 1
        if c == t:
            path = []
            while c is not None:
                path.append(c); c = par[c]
            return g[t], exp, path
        for q in neighbours(c, free):
            ng = g[c] + 1
            if ng < g.get(q, 1e9):
                g[q] = ng; par[q] = c; heapq.heappush(pq, (ng + w * h(q), -ng, q))      # ties: prefer deeper nodes
    return None, exp, None


def mst_len(pts):
    n = len(pts); inT = [False] * n; d = [10 ** 9] * n; d[0] = 0; tot = 0
    for _ in range(n):
        i = min((j for j in range(n) if not inT[j]), key=lambda j: d[j]); inT[i] = True; tot += d[i]
        for j in range(n):
            if not inT[j]:
                dj = abs(pts[i][0] - pts[j][0]) + abs(pts[i][1] - pts[j][1])
                if dj < d[j]:
                    d[j] = dj
    return tot


def rsmt(pts):
    xs = sorted({q[0] for q in pts}); ys = sorted({q[1] for q in pts})
    hanan = [(x, y) for x in xs for y in ys if (x, y) not in pts]
    best = mst_len(pts)
    for k in range(1, len(pts) - 1):
        for sub in itertools.combinations(hanan, k):
            best = min(best, mst_len(list(pts) + list(sub)))
    return best


def run(p):
    r = p.rng; mism = 0; rows = []; wviol = 0; wex = []
    for _ in range(200):
        free = r.random((40, 40)) > 0.25
        cells = np.argwhere(free); s = tuple(int(v) for v in cells[r.integers(len(cells))]); t = tuple(int(v) for v in cells[r.integers(len(cells))])
        G = nx.grid_2d_graph(40, 40); G.remove_nodes_from([tuple(int(v) for v in c) for c in np.argwhere(~free)])
        try:
            ref = nx.shortest_path_length(G, s, t)
        except nx.NetworkXNoPath:
            ref = None
        dl, el, _ = lee(free, s, t); da, ea, path = astar(free, s, t); dw, ew, _ = astar(free, s, t, w=2.0)
        mism += (dl != ref) + (da != ref)
        if ref:
            rows.append((ref, el, ea, ew)); wviol += dw > 2 * ref; wex.append(dw / ref)
            mism += len(path) - 1 != ref or any(not free[c] for c in path)
    rr = np.array(rows, float)
    p.compare(f"Lee and A* path length vs networkx shortest path (200 mazes, {len(rows)} routable): mismatches", 0, mism, "", kind="abs")
    p.metric("Cells expanded, A* / Lee (median over mazes)", float(np.median(rr[:, 2] / rr[:, 1])), "", "same optimal length, less search")
    p.compare("Weighted A* (w = 2): paths longer than 2× optimal", 0, wviol, "", kind="abs")
    p.metric("Weighted A* (w = 2): mean length penalty / expansions vs plain A*", f"{(np.mean(wex) - 1) * 100:.1f} % / {np.median(rr[:, 3] / rr[:, 2]):.2f}×")
    free = np.ones((40, 40), bool); _, e_l, _ = lee(free, (5, 5), (34, 30)); _, e_a, _ = astar(free, (5, 5), (34, 30))
    p.metric("Empty 40×40 grid, 54-step connection: cells expanded Lee / A*", f"{e_l} / {e_a}")
    ratios = {}; hp_bad = 0; hw_bad = 0
    for n, cnt in ((3, 300), (4, 300), (5, 100)):
        rat = []
        for _ in range(cnt):
            pts = set()
            while len(pts) < n:
                pts.add((int(r.integers(20)), int(r.integers(20))))
            pts = list(pts); st = rsmt(pts); ms = mst_len(pts); rat.append(st / ms)
            hw_bad += ms > 1.5 * st + 1e-9
            if n == 3:
                hp_bad += st != (max(q[0] for q in pts) - min(q[0] for q in pts)) + (max(q[1] for q in pts) - min(q[1] for q in pts))
        ratios[n] = np.array(rat)
    p.compare("3-pin nets: exact Steiner length ≠ half-perimeter of the bounding box (300 nets)", 0, hp_bad, "", kind="abs")
    p.compare("Hwang's bound MST ≤ 1.5 · RSMT violated (700 nets)", 0, hw_bad, "", kind="abs")
    p.metric("Mean wire saved by Steiner points vs MST: 3 / 4 / 5 pins", " / ".join(f"{(1 - ratios[n].mean()) * 100:.1f} %" for n in (3, 4, 5)))
    p.metric("Worst-case saving seen (bound: 33.3 %)", (1 - min(v.min() for v in ratios.values())) * 100, "%")
    # net ordering on a single layer
    N = 24; pins = []
    used = set()
    while len(pins) < 10:
        a = (int(r.integers(N)), int(r.integers(N))); b = (int(r.integers(N)), int(r.integers(N)))
        if a != b and a not in used and b not in used and abs(a[0] - b[0]) + abs(a[1] - b[1]) > 6:
            pins.append((a, b)); used |= {a, b}
    res = []
    for _ in range(60):
        order = r.permutation(10); free = np.ones((N, N), bool)
        for a, b in pins:
            free[a] = free[b] = False
        done = 0; length = 0
        for i in order:
            a, b = pins[i]; free[a] = free[b] = True
            d, _, path = astar(free, a, b)
            if d is not None:
                done += 1; length += d
                for c in path:
                    free[c] = False
            free[a] = free[b] = False
        res.append((done, length))
    res = np.array(res)
    p.compare("Net ordering matters: the number of nets completed differs between orders (1 = yes)", 1, int(res[:, 0].max() > res[:, 0].min()), "", kind="abs")
    p.metric("Nets completed (of 10) over 60 random orders: min / median / max", f"{res[:, 0].min()} / {np.median(res[:, 0]):.0f} / {res[:, 0].max()}")
    p.metric("Orders that complete every net", float(np.mean(res[:, 0] == 10)) * 100, "%")
    fig, ax = p.fig(1, 3, w=13, h=4.2)
    free = r.random((40, 40)) > 0.25; free[2, 2] = free[37, 36] = True
    d, e, path = astar(free, (2, 2), (37, 36))
    ax[0].imshow(~free.T, cmap="Greys", origin="lower", alpha=0.6)
    if path:
        pa = np.array(path); ax[0].plot(pa[:, 0], pa[:, 1], color=C_MEAS, lw=2)
    ax[0].set_title(f"A* route through a 25 % blocked grid ({d} steps)" if d else "no route", loc="left", fontsize=10); ax[0].grid(False)
    ax[1].hist([ratios[3], ratios[4], ratios[5]], bins=12, label=["3 pins", "4 pins", "5 pins"], color=[C_MEAS, C_PRED, COLORS[2]])
    ax[1].axvline(2 / 3, color="gray", ls=":", label="Hwang bound ⅔")
    style_axes(ax[1], "Steiner length / MST length", "nets", "How much Steiner points save")
    vals, cnts = np.unique(res[:, 0], return_counts=True)
    ax[2].bar(vals, cnts, color=C_MEAS)
    style_axes(ax[2], "nets completed (of 10)", "routing orders", "Same nets, different order", legend=False)
    p.save(fig, "routing", "An A* route, the distribution of Steiner/MST length ratios, and the effect of net ordering on completion.")
    p.discuss(f"""For a single connection the problem is easy and both routers are provably optimal — every length matches networkx's shortest path — but A*
gets there after expanding a fraction of the cells ({np.median(rr[:, 2] / rr[:, 1]):.2f} of Lee's in random mazes, {e_a} vs {e_l} on an empty board), and inflating the
heuristic trades a bounded length penalty for still less search. Multi-pin nets are where it gets hard: the exact Steiner tree (found here by
brute force over Hanan points, which is only feasible for a handful of pins) saves {(1 - ratios[4].mean()) * 100:.0f}–{(1 - ratios[5].mean()) * 100:.0f} % of wire over a spanning tree on
average and never more than a third, which is why practical routers use MST-based heuristics with local Steiner improvements. And the full problem
is harder again: routing the same ten nets in different orders completed between {res[:, 0].min()} and {res[:, 0].max()} of them, because each finished
net blocks the others — the reason real autorouters use rip-up-and-reroute or negotiated congestion instead of a single sequential pass.""")
# tol-convention: relative tolerances are in percent
