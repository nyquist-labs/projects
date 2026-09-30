from eelab import *
from eelab.boolmin import prime_implicants, exact_cover, evaluate, literals
from itertools import permutations

META = dict(
    id="AM-140", title="State encoding optimisation: every assignment of a 5-state FSM", level="H",
    tools="Exhaustive enumeration of all 6720 three-bit state assignments, exact two-level minimisation of every next-state and output function (eelab.boolmin) with unused codes as don't-cares, one-hot encoding for comparison, simulation of the encoded logic against the behavioural FSM",
    summary="The same state machine costs very different amounts of logic depending on which binary code each state gets. Enumerate every possible "
            "3-bit assignment for a '1101' sequence detector, minimise the logic exactly for each, and see where the naive binary, Gray and one-hot choices rank.",
    problem="State names are arbitrary; their codes are not. How much logic does a good assignment save, and how good are the default choices?",
    theory=r"""With s states in b bits there are $2^b!/(2^b-s)!$ assignments (6720 for s = 5, b = 3; 1120 distinct up to renaming the flip-flops). Each gives next-state functions $D_i(q, x)$ and output $z(q)$; cost here = total literals + product terms of the exact minimum
SOP forms (unused codes are don't-cares). No closed form predicts the best assignment — the problem is NP-hard — which is why tools use heuristics (adjacent codes for states sharing successors) or one-hot (s flip-flops, very simple
per-flip-flop logic). My guess before running: a 2× spread between best and worst, with plain binary somewhere in the middle.""",
    method="""Moore '1101' detector (overlapping), states S0…S4, output in S4. All injective maps state → {0…7}; per assignment minimise D2, D1, D0 (4 variables) and z (3 variables). One-hot: 6 variables, non-one-hot codes as don't-cares.
The best assignment's equations are simulated on 5000 random bits against the state table.""",
)

NXT = [(0, 1), (0, 2), (3, 2), (0, 4), (0, 2)]           # next state for x = 0, 1
Z = [0, 0, 0, 0, 1]


def cost_of(codes, nbits):
    """codes[s] = integer code. Returns (cost, covers) with covers = list of (cover, nvars)."""
    nv = nbits + 1; used = set(codes)
    dc_next = [(c << 1) | x for c in range(2 ** nbits) if c not in used for x in (0, 1)]
    total = 0; covs = []
    for bit in range(nbits):
        mt = [(codes[s] << 1) | x for s in range(5) for x in (0, 1) if (codes[NXT[s][x]] >> bit) & 1]
        cv = exact_cover(prime_implicants(mt, dc_next, nv), mt, nv) if mt else []
        total += sum(literals(c, nv) for c in cv) + len(cv); covs.append((cv, nv))
    mt = [codes[s] for s in range(5) if Z[s]]
    cv = exact_cover(prime_implicants(mt, [c for c in range(2 ** nbits) if c not in used], nbits), mt, nbits)
    total += sum(literals(c, nbits) for c in cv) + len(cv); covs.append((cv, nbits))
    return total, covs


def run_encoded(codes, covs, nbits, xs):
    q = codes[0]; out = []
    for x in xs:
        out.append(int(evaluate(covs[-1][0], q)))
        v = (q << 1) | int(x)
        q = sum(int(evaluate(covs[b][0], v)) << b for b in range(nbits))
    return out


def run(p):
    costs = {}
    for codes in permutations(range(8), 5):
        costs[codes] = cost_of(codes, 3)[0]
    c = np.array(list(costs.values()))
    p.compare("Assignments enumerated: 8!/3!", 6720, len(c), "", kind="abs")
    best = min(costs, key=costs.get); worst = max(costs, key=costs.get)
    binary = (0, 1, 2, 3, 4); gray = (0, 1, 3, 2, 6)
    p.metric("Best assignment (S0…S4)", " ".join(f"{x:03b}" for x in best), "", f"cost {costs[best]}")
    p.metric("Worst assignment", " ".join(f"{x:03b}" for x in worst), "", f"cost {costs[worst]}")
    p.compare("Worst / best cost ratio (my guess: about 2×)", 2.0, costs[worst] / costs[best], "×", tol=35)
    pct = lambda k: float(np.mean(c <= costs[k]) * 100)
    p.metric("Plain binary 000,001,010,011,100: cost", costs[binary], "", f"better than or equal to {100 - pct(binary) + np.mean(c == costs[binary]) * 100:.0f} % of assignments")
    p.metric("Gray order 000,001,011,010,110: cost", costs[gray], "", f"better than or equal to {100 - pct(gray) + np.mean(c == costs[gray]) * 100:.0f} % of assignments")
    onehot = tuple(1 << i for i in range(5))
    oh_cost, _ = cost_of(onehot, 5)
    p.metric("One-hot (5 flip-flops): logic cost", oh_cost, "", "vs 3 flip-flops for the binary encodings")
    p.compare("Distinct costs are invariant under flip-flop renaming (6720 / 6 classes have equal cost; violations)", 0,
              sum(costs[tuple(sum(((cd >> b) & 1) << pm[b] for b in range(3)) for cd in best)] != costs[best] for pm in permutations(range(3))), "", kind="abs")
    xs = p.rng.integers(0, 2, 5000)
    s = 0; ref = []
    for x in xs:
        ref.append(Z[s]); s = NXT[s][x]
    bad = 0
    for codes, nb in ((best, 3), (binary, 3), (onehot, 5)):
        _, covs = cost_of(codes, nb)
        bad += int(np.sum(np.array(run_encoded(codes, covs, nb, xs)) != np.array(ref)))
    p.compare("Encoded logic vs behavioural FSM on 5000 random bits (best, binary, one-hot; mismatches)", 0, bad, "", kind="abs")
    xs_s = "".join(map(str, xs[:-1])); occ = sum(xs_s.startswith("1101", i) for i in range(len(xs_s) - 3))
    p.compare("Detections by the FSM vs occurrences of '1101' counted directly in the input", occ, int(np.sum(ref)), "", kind="abs")
    fig, ax = p.fig(1, 1, w=8, h=4.2)
    vals, cnt = np.unique(c, return_counts=True)
    ax.bar(vals, cnt, color=C_MEAS, width=0.8)
    for k, nm, col in ((binary, "binary", C_PRED), (gray, "Gray", COLORS[2]), (best, "best", COLORS[3])):
        ax.axvline(costs[k], color=col, ls="--", lw=1.5, label=f"{nm} ({costs[k]})")
    style_axes(ax, "logic cost (literals + product terms)", "number of assignments", "All 6720 state assignments of the '1101' detector")
    p.save(fig, "encodings", "Distribution of exact two-level logic cost over every possible 3-bit state assignment.")
    p.discuss(f"""Exhaustive search shows how much the arbitrary-looking choice of state codes matters: the worst assignment costs
{costs[worst] / costs[best]:.1f}× the best ({costs[worst]} vs {costs[best]}), and the two 'obvious' choices — counting in binary ({costs[binary]}) or Gray order ({costs[gray]}) — are
not optimal. Every encoded version, including the best one found, reproduces the behavioural machine exactly on random input. One-hot spends two
extra flip-flops to get next-state equations that read directly off the state diagram (cost {oh_cost}); in FPGAs, where flip-flops are free and wide
gates are not, that trade is often right — which is why synthesis tools choose encodings automatically rather than trusting the designer's numbering.
For larger machines the search space explodes (16 states: 16! ≈ 2×10¹³), so heuristics replace enumeration.""")
# tol-convention: relative tolerances are in percent
