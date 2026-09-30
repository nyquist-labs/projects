from eelab import *

META = dict(
    id="AM-139", title="FSM state minimisation by partition refinement", level="H",
    tools="Own partition-refinement (Moore) minimiser, independent pair-marking (table-filling) implementation as a cross-check, machines inflated from known minimal machines, random-input equivalence testing, a worst-case machine for the number of refinement rounds",
    summary="Find and merge equivalent states of a finite-state machine. Verified three ways: recovering the known minimal size of deliberately "
            "inflated machines, agreeing with an independent table-filling algorithm, and proving behavioural equivalence on long random input sequences.",
    problem="A state diagram drawn by hand often has redundant states. How do we provably find the smallest equivalent machine?",
    theory=r"""Two states are equivalent iff no input sequence distinguishes their outputs. Start with the partition by output; repeatedly split blocks whose members go to different blocks under some input. The fixed point is the coarsest
consistent partition — the unique minimal machine (Myhill–Nerode). At most n − 2 splitting rounds are needed after the initial partition, and that bound is attained by a 'countdown' machine. Flip-flops saved: ⌈log₂n⌉ − ⌈log₂k⌉.""",
    method="""Mealy machines as tables next[s, x], out[s, x]. (1) 300 random minimal machines with k = 2…12 states, each inflated to up to 4k states by duplicating states (plus unreachable states); (2) a naive 8-state '1011' detector remembering
the last three bits; (3) a 20-state countdown machine. Cross-check by table-filling; equivalence by 20 000 random input symbols.""",
)


def reachable(nxt):
    seen = {0}; st = [0]
    while st:
        s = st.pop()
        for t in nxt[s]:
            if int(t) not in seen:
                seen.add(int(t)); st.append(int(t))
    return sorted(seen)


def minimise(nxt, out):
    keep = reachable(nxt); idx = {s: i for i, s in enumerate(keep)}
    nx = np.array([[idx[int(t)] for t in nxt[s]] for s in keep]); ou = out[keep]
    _, block = np.unique(ou, axis=0, return_inverse=True); block = block.ravel()
    rounds = 0
    while True:
        sig = np.column_stack([block, block[nx]])
        _, nb = np.unique(sig, axis=0, return_inverse=True); nb = nb.ravel()
        if nb.max() == block.max():
            break
        block = nb; rounds += 1
    k = block.max() + 1
    rep = [int(np.where(block == b)[0][0]) for b in range(k)]
    start = block[0]
    mn = np.array([[block[nx[r, x]] for x in range(nx.shape[1])] for r in rep]); mo = ou[rep]
    return mn, mo, int(start), rounds


def table_fill(nxt, out):
    keep = reachable(nxt); n = len(keep); idx = {s: i for i, s in enumerate(keep)}
    nx = np.array([[idx[int(t)] for t in nxt[s]] for s in keep]); ou = out[keep]
    D = (ou[:, None, :] != ou[None, :, :]).any(2)
    while True:
        new = D.copy()
        for x in range(nx.shape[1]):
            new |= D[nx[:, x][:, None], nx[:, x][None, :]]
        if (new == D).all():
            break
        D = new
    classes = 0; seen = np.zeros(n, bool)
    for s in range(n):
        if not seen[s]:
            classes += 1; seen |= ~D[s]
    return classes


def simulate(nxt, out, start, xs):
    s = start; ys = []
    for x in xs:
        ys.append(out[s, x]); s = nxt[s, x]
    return np.array(ys)


def run(p):
    r = p.rng; fail_size = fail_tab = fail_eq = 0; trials = 0; infl = []
    for _ in range(300):
        k = int(r.integers(2, 13)); m = int(r.integers(2, 4))
        while True:
            bn = r.integers(0, k, (k, m)); bo = r.integers(0, 2, (k, m))
            mn, mo, st, _ = minimise(bn, bo)
            if len(mn) == k:                                   # keep only base machines that are reachable and minimal
                break
        copies = [int(r.integers(1, 5)) for _ in range(k)]
        ids = [[] for _ in range(k)]; c = 0
        for s in range(k):
            for _ in range(copies[s]):
                ids[s].append(c); c += 1
        extra = int(r.integers(0, 4)); n = c + extra
        nxt = np.zeros((n, m), int); out = np.zeros((n, m), int)
        for s in range(k):
            for q in ids[s]:
                for x in range(m):
                    nxt[q, x] = ids[bn[s, x]][r.integers(copies[bn[s, x]])]; out[q, x] = bo[s, x]
        for q in range(c, n):
            nxt[q] = r.integers(0, n, m); out[q] = r.integers(0, 2, m)
        mn, mo, st, _ = minimise(nxt, out)
        trials += 1; infl.append(n / k)
        fail_size += len(mn) != k
        fail_tab += table_fill(nxt, out) != len(mn)
        xs = r.integers(0, m, 2000)
        fail_eq += not np.array_equal(simulate(nxt, out, 0, xs), simulate(mn, mo, st, xs))
    p.compare(f"Inflated machines reduced to exactly the known minimal size ({trials} machines, mean inflation {np.mean(infl):.1f}×)", 0, fail_size, "failures", kind="abs")
    p.compare("Disagreements with the independent table-filling algorithm", 0, fail_tab, "", kind="abs")
    p.compare("Machines whose minimised version behaves differently on 2000 random inputs", 0, fail_eq, "", kind="abs")
    # naive 1011 detector: state = last three bits
    nxt = np.zeros((8, 2), int); out = np.zeros((8, 2), int)
    for s in range(8):
        for x in (0, 1):
            nxt[s, x] = ((s << 1) | x) & 7; out[s, x] = int(s == 0b101 and x == 1)
    mn, mo, st, rd = minimise(nxt, out)
    p.compare("'1011' detector drawn with 8 states (last three bits): minimal states", 4, len(mn), "", kind="abs")
    xs = r.integers(0, 2, 20000)
    p.compare("… outputs identical on 20 000 random bits (mismatches)", 0, int(np.sum(simulate(nxt, out, 0, xs) != simulate(mn, mo, st, xs))), "", kind="abs")
    p.metric("Flip-flops: before → after", f"{int(np.ceil(np.log2(8)))} → {int(np.ceil(np.log2(len(mn))))}")
    n = 20
    nxt = np.array([[min(s + 1, n - 1)] * 2 for s in range(n)]); out = np.array([[int(s == n - 1)] * 2 for s in range(n)])
    mn2, _, _, rounds = minimise(nxt, out)
    p.compare("Countdown machine (n = 20): refinement rounds = n − 2", n - 2, rounds, "", kind="abs")
    p.compare("… and it is already minimal (states)", n, len(mn2), "", kind="abs")
    tbl = "| state | next (x=0) | next (x=1) | out (x=0) | out (x=1) |\n|---|---|---|---|---|\n" + "\n".join(
        f"| {'→ ' if i == st else ''}S{i} | S{mn[i, 0]} | S{mn[i, 1]} | {mo[i, 0]} | {mo[i, 1]} |" for i in range(len(mn)))
    p.section("Minimised '1011' detector", tbl)
    fig, ax = p.fig(1, 1, w=7, h=4)
    ax.scatter(np.array(infl) * 0 + r.uniform(-0.1, 0.1, len(infl)) + 1, infl, s=8, color=C_MEAS, alpha=0.5)
    ax.set_xlim(0, 2); ax.set_xticks([1]); ax.set_xticklabels(["300 random machines"])
    style_axes(ax, "", "states before / states after", "Redundancy removed by minimisation", legend=False)
    p.save(fig, "minimise", "State-count reduction achieved on the randomly inflated machines.")
    p.discuss("""Partition refinement recovered the minimal machine in every trial: inflated machines collapsed back to their known size, the independent
pair-marking algorithm always agreed on the number of classes, and minimised machines were indistinguishable from the originals on long random
inputs. The naive eight-state '1011' detector needs only four states — two flip-flops instead of three — because remembering the last three bits
stores more than the detector needs (only the longest matched prefix matters). The countdown machine shows the worst case: each round can peel off
only one state, so n − 2 rounds are required; Hopcroft's algorithm gets the total work down to O(n log n) by always refining with the smaller half.""")
# tol-convention: relative tolerances are in percent
