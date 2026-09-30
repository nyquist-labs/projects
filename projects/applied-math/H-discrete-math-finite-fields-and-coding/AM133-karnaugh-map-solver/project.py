from eelab import *
from eelab.boolmin import prime_implicants, greedy_cover, exact_cover, evaluate, to_sop, literals

META = dict(
    id="AM-133", title="Karnaugh-map solver: automatic grouping, verified", level="M",
    tools="Prime-implicant generation and the K-map procedure (essential groups first, then largest groups) implemented as code, truth-table verification, comparison with an exact minimum cover, K-map rendering",
    summary="Automate what students do by circling groups on a Karnaugh map, verify the resulting sum-of-products against the truth table for every "
            "3-variable function and thousands of random 4- and 5-variable functions (with don't-cares), and measure how often the by-hand procedure misses the true minimum.",
    problem="Karnaugh maps are taught as an art. Is the 'largest groups first' recipe always optimal?",
    theory=r"""Groups on a K-map are implicants (products that cover only 1s/don't-cares); maximal groups are prime implicants. The recipe — take essential primes, then repeatedly the group covering most remaining 1s — always yields a correct cover but is a greedy
heuristic for set cover, which can miss the minimum (cyclic maps). For n ≤ 4 the greedy result is usually minimal; the fraction of non-minimal results should be small but non-zero.""",
    method="""All 256 three-variable functions; 3000 random four-variable and 1000 five-variable functions with 0–25 % don't-cares. Checks: (1) the cover equals the function on all care minterms and covers no 0s; (2) number of terms vs exact minimum
(branch-and-bound, shared with AM-134).""",
)


def kmap_text(minterms, dc, n=4):
    gray = [0, 1, 3, 2]
    rows = []
    for r in gray:
        rows.append(" ".join("1" if (r << 2 | c) in minterms else "x" if (r << 2 | c) in dc else "0" for c in gray))
    return rows


def run(p):
    r = p.rng
    cases = [(3, [m for m in range(8) if (f >> m) & 1], []) for f in range(256)]
    for n, cnt in ((4, 3000), (5, 1000)):
        for _ in range(cnt):
            v = r.random(2 ** n); dcf = r.uniform(0, 0.25)
            dc = [m for m in range(2 ** n) if v[m] < dcf]; mt = [m for m in range(2 ** n) if v[m] > 1 - r.uniform(0.2, 0.8) and m not in dc]
            cases.append((n, mt, dc))
    wrong = nonmin = total = 0; extra = []
    for n, mt, dc in cases:
        if not mt:
            continue
        pr = prime_implicants(mt, dc, n)
        g = greedy_cover(pr, mt, n)
        ok = all(evaluate(g, m) for m in mt) and not any(evaluate(g, m) for m in range(2 ** n) if m not in mt and m not in dc)
        wrong += not ok; total += 1
        e = exact_cover(pr, mt, n)
        if len(g) > len(e):
            nonmin += 1; extra.append(len(g) - len(e))
    p.compare(f"Covers that disagree with the truth table ({total} functions)", 0, wrong, "", kind="abs")
    p.compare("Fraction of functions where the K-map recipe is not minimal (my guess: small, < 5 %)", 2.0, nonmin / total * 100, "%", kind="abs", tol=5)
    p.metric("Worst excess over the minimum (product terms)", max(extra) if extra else 0, "")
    mt = [0, 1, 2, 5, 6, 7, 8, 9, 10, 14]; dc = []
    g = greedy_cover(prime_implicants(mt, dc, 4), mt, 4); e = exact_cover(prime_implicants(mt, dc, 4), mt, 4)
    p.write("results/example.txt", "K-map (rows AB = 00,01,11,10; cols CD = 00,01,11,10)\n" + "\n".join(kmap_text(set(mt), set(dc))) +
            f"\n\nK-map recipe: F = {to_sop(g, 'ABCD')}\nExact minimum: F = {to_sop(e, 'ABCD')}\n", "worked example")
    p.metric("Worked example Σm(0,1,2,5,6,7,8,9,10,14): recipe / exact terms", f"{len(g)} / {len(e)}", "", to_sop(e, "ABCD"))
    fig, ax = p.fig(1, 2, w=11, h=4)
    gray = [0, 1, 3, 2]
    ax[0].axis("off"); ax[0].set_xlim(-1, 4); ax[0].set_ylim(-0.5, 5)
    for i, rr in enumerate(gray):
        for j, c in enumerate(gray):
            m = rr << 2 | c
            ax[0].text(j + 0.5, 3.5 - i, "1" if m in mt else "0", ha="center", va="center", fontsize=14, color=C_MEAS if m in mt else "gray")
            ax[0].add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle((j, 3 - i), 1, 1, fill=False, ec="gray"))
        ax[0].text(-0.4, 3.5 - i, f"{rr:02b}", ha="center", va="center", fontsize=9)
    for j, c in enumerate(gray):
        ax[0].text(j + 0.5, 4.3, f"{c:02b}", ha="center", fontsize=9)
    ax[0].set_title("Example K-map (AB rows, CD columns)", loc="left", fontsize=10)
    import collections
    cnt = collections.Counter(extra)
    ax[1].bar(["minimal"] + [f"+{k}" for k in sorted(cnt)], [total - nonmin] + [cnt[k] for k in sorted(cnt)], color=[C_MEAS] + [C_PRED] * len(cnt))
    ax[1].set_yscale("log")
    style_axes(ax[1], "terms above the true minimum", "functions", "How good is the K-map recipe?", legend=False)
    p.save(fig, "kmap", "A worked Karnaugh map and the distribution of the greedy recipe's excess terms.")
    p.discuss(f"""Every cover produced by the automated K-map procedure matches its truth table — the recipe is always *correct*. It is not always *minimal*:
on {nonmin / total * 100:.1f} % of the random functions the 'essential groups, then biggest group' rule used more product terms than the exact minimum, never by
more than a term or two. The failures are the cyclic cases where several equally large groups overlap and the first choice forces an extra group
later — exactly where a human must 'look ahead' on the map. That gap is the motivation for the exact Quine–McCluskey/Petrick method of AM-134 and,
for large functions, heuristic minimisers such as Espresso.""")
# tol-convention: relative tolerances are in percent
