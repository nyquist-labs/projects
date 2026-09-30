from eelab import *

META = dict(
    id="AM-138", title="Carry-lookahead derived: from ripple to parallel prefix", level="M",
    tools="Own gate-level netlist builder (2-input gates with automatic level tracking, bit-parallel evaluation over 64-bit words), ripple, 4-bit-group lookahead and Kogge–Stone prefix adders, exhaustive/random functional verification, depth and gate counts against derived formulas",
    summary="Derive the generate/propagate carry recurrence, unroll it into lookahead equations, recognise the associative prefix operator that "
            "lets carries be computed in log₂n levels, and verify depth and size formulas for 4 to 64 bits on real gate netlists.",
    problem="A ripple adder waits for the carry to crawl across every bit. How does algebra make a 64-bit add as fast as a few gates?",
    theory=r"""$g_i=a_ib_i$, $p_i=a_i\oplus b_i$, $c_{i+1}=g_i+p_ic_i$. Unrolling: $c_4=g_3+p_3g_2+p_3p_2g_1+p_3p_2p_1g_0+p_3p_2p_1p_0c_0$ (two levels of wide gates). The pair operator $(G,P)\circ(G',P')=(G+PG',\,PP')$ is
associative, so all prefixes $(G_{i:0},P_{i:0})$ can be computed by a tree: Kogge–Stone uses $\log_2 n$ levels with $n\log_2n-n+1$ prefix cells. With 2-input gates and c₀ = 0: ripple depth $2n-1$; Kogge–Stone depth $2\log_2n+1$.
Both $p=a\oplus b$ and $p=a+b$ give the same carries (since $g$ absorbs the difference).""",
    method="""Netlists built from 2-input AND/OR/XOR; depth = longest gate path, size = gate count. Verification: exhaustive for n = 4 and 8, 10⁵ random vectors for n = 16…64 (bit-parallel). The unrolled c₄ equation is checked against the recurrence on all 512 inputs
for both definitions of p.""",
)


class Net:
    def __init__(self):
        self.ops = []; self.level = {}; self.n_in = 0

    def inp(self):
        k = ("in", self.n_in); self.n_in += 1; self.level[k] = 0
        return k

    def gate(self, op, a, b):
        k = ("g", len(self.ops)); self.ops.append((op, a, b, k)); self.level[k] = max(self.level[a], self.level[b]) + 1
        return k

    def run(self, inputs):
        v = {("in", i): x for i, x in enumerate(inputs)}
        for op, a, b, k in self.ops:
            v[k] = v[a] & v[b] if op == "and" else v[a] | v[b] if op == "or" else v[a] ^ v[b]
        return v


def ripple(n):
    N = Net(); a = [N.inp() for _ in range(n)]; b = [N.inp() for _ in range(n)]
    g = [N.gate("and", a[i], b[i]) for i in range(n)]; pp = [N.gate("xor", a[i], b[i]) for i in range(n)]
    c = [None, g[0]]; s = [pp[0]]
    for i in range(1, n):
        s.append(N.gate("xor", pp[i], c[i])); c.append(N.gate("or", g[i], N.gate("and", pp[i], c[i])))
    return N, s + [c[n]], 0


def kogge_stone(n):
    N = Net(); a = [N.inp() for _ in range(n)]; b = [N.inp() for _ in range(n)]
    G = [N.gate("and", a[i], b[i]) for i in range(n)]; P = [N.gate("xor", a[i], b[i]) for i in range(n)]; p0 = P[:]
    cells = 0; d = 1
    while d < n:
        G2, P2 = G[:], P[:]
        for i in range(d, n):
            G2[i] = N.gate("or", G[i], N.gate("and", P[i], G[i - d])); cells += 1
            if i - d >= d:                                   # P only needed while the prefix does not yet reach bit 0
                P2[i] = N.gate("and", P[i], P[i - d])
        G, P = G2, P2; d *= 2
    s = [p0[0]] + [N.gate("xor", p0[i], G[i - 1]) for i in range(1, n)]
    return N, s + [G[n - 1]], cells


def check(build, n, rng):
    N, outs, cells = build(n)
    if n <= 8:
        A, B = np.meshgrid(np.arange(2 ** n, dtype=np.uint64), np.arange(2 ** n, dtype=np.uint64)); A, B = A.ravel(), B.ravel()
    else:
        mask = np.uint64((1 << n) - 1)
        rnd = lambda: ((rng.integers(0, 2 ** 32, 100000, dtype=np.uint64) << np.uint64(32)) | rng.integers(0, 2 ** 32, 100000, dtype=np.uint64)) & mask
        A, B = rnd(), rnd()
    one = np.uint64(1)
    v = N.run([(A >> np.uint64(i)) & one for i in range(n)] + [(B >> np.uint64(i)) & one for i in range(n)])
    got = [v[o] for o in outs]
    low = np.zeros_like(A)
    for i in range(n):
        low |= got[i] << np.uint64(i)
    with np.errstate(over="ignore"):
        ssum = A + B
    if n < 64:
        ref_low = ssum & np.uint64((1 << n) - 1); ref_c = (ssum >> np.uint64(n)) & one
    else:
        ref_low = ssum; ref_c = (ssum < A).astype(np.uint64)
    bad = int(np.sum((low != ref_low) | (got[n] != ref_c)))
    depth = max(N.level[o] for o in outs)
    return bad, depth, len(N.ops), cells


def run(p):
    bad = 0
    for pdef in ("xor", "or"):
        for m in range(512):
            a = [(m >> i) & 1 for i in range(4)]; b = [(m >> (4 + i)) & 1 for i in range(4)]; c0 = m >> 8
            g = [x & y for x, y in zip(a, b)]; pr = [(x ^ y) if pdef == "xor" else (x | y) for x, y in zip(a, b)]
            c = c0
            for i in range(4):
                c = g[i] | (pr[i] & c)
            c4 = g[3] | pr[3] & g[2] | pr[3] & pr[2] & g[1] | pr[3] & pr[2] & pr[1] & g[0] | pr[3] & pr[2] & pr[1] & pr[0] & c0
            bad += (c != c4) or (c != ((sum(a[i] << i for i in range(4)) + sum(b[i] << i for i in range(4)) + c0) >> 4))
    p.compare("Unrolled c₄ equation vs recurrence vs true carry (512 inputs × both definitions of p)", 0, bad, "mismatches", kind="abs")
    ns = [4, 8, 16, 32, 64]; rows = []
    for n in ns:
        br, dr, gr, _ = check(ripple, n, p.rng); bk, dk, gk, ck = check(kogge_stone, n, p.rng)
        rows.append((n, br + bk, dr, dk, gr, gk, ck))
    rr = np.array(rows)
    p.compare("Functional mismatches, both adders, n = 4…64", 0, int(rr[:, 1].sum()), "", kind="abs")
    p.compare("Ripple depth at n = 64: 2n − 1", 127, rr[-1, 2], "gate delays", kind="abs")
    p.compare("Kogge–Stone depth = 2·log₂n + 1 for every n = 4…64 (mismatches)", 0, int(np.sum(rr[:, 3] != 2 * np.log2(rr[:, 0]) + 1)), "", kind="abs")
    p.compare("Kogge–Stone depth at n = 64", 13, rr[-1, 3], "gate delays", kind="abs")
    p.compare("Kogge–Stone prefix cells at n = 64: n·log₂n − n + 1", 64 * 6 - 63, rr[-1, 6], "", kind="abs")
    p.metric("Speed-up at 64 bits (depth ratio)", rr[-1, 2] / rr[-1, 3], "×")
    p.metric("Area cost at 64 bits (gate ratio)", rr[-1, 5] / rr[-1, 4], "×", f"{int(rr[-1, 5])} vs {int(rr[-1, 4])} gates")
    p.csv("adders", n=rr[:, 0], ripple_depth=rr[:, 2], ks_depth=rr[:, 3], ripple_gates=rr[:, 4], ks_gates=rr[:, 5])
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(ns, rr[:, 2], "o-", color=C_PRED, label="ripple (2n − 1)", base=2); ax[0].loglog(ns, rr[:, 3], "s-", color=C_MEAS, label="Kogge–Stone (2log₂n + 1)", base=2)
    style_axes(ax[0], "bits n", "depth (gate delays)", "Delay: linear vs logarithmic")
    ax[1].loglog(ns, rr[:, 4], "o-", color=C_PRED, label="ripple", base=2); ax[1].loglog(ns, rr[:, 5], "s-", color=C_MEAS, label="Kogge–Stone", base=2)
    style_axes(ax[1], "bits n", "two-input gates", "Area: n vs n·log n")
    p.save(fig, "cla", "Depth and gate count of ripple and Kogge–Stone adders built from the derived equations.")
    p.discuss(f"""The unrolled lookahead equation agrees with the recurrence on every input for both definitions of propagate, and both netlists add correctly at
every width. Depth follows 2n − 1 for ripple and 2·log₂n + 1 for the prefix tree. (I first derived 2·log₂n + 2 — one level for g/p, two per
prefix level, one for the sum XOR — and the netlist came out one level faster: the carry into the top bit is a prefix over only n − 1 bits, whose last
cell combines with a partner that is one gate shallower, so the final XOR is not on a longer path than the carry-out.) At 64 bits the prefix adder is
{rr[-1, 2] / rr[-1, 3]:.0f}× faster in gate delays, at {rr[-1, 5] / rr[-1, 4]:.1f}× the gates (and, in silicon, a lot of wiring that this count ignores). The key algebraic step is
noticing that (G, P) pairs combine associatively: once carries are a prefix computation, any parallel-prefix network (Kogge–Stone, Brent–Kung,
Sklansky) trades depth, area and fan-out — the design space every fast adder since the 1970s lives in.""")
# tol-convention: relative tolerances are in percent
