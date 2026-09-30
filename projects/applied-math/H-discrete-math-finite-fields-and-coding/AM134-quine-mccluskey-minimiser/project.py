from eelab import *
from eelab.boolmin import prime_implicants, exact_cover, greedy_cover, evaluate, to_sop
from eelab.hdl import synth
import time

META = dict(
    id="AM-134", title="Quine–McCluskey: exact two-level minimisation", level="H",
    tools="Own Quine–McCluskey prime-implicant generation and exact minimum cover by branch and bound (eelab.boolmin), truth-table verification, known-answer functions (parity, majority, prime detector), Yosys for a multi-level comparison, scaling measurements",
    summary="Implement the exact minimisation algorithm, verify it on functions whose minimum is known from theory, and measure how the number of "
            "prime implicants and the run time grow with the number of variables — the reason exact methods stop at ~10–12 variables.",
    problem="What is the provably smallest AND-OR circuit for a truth table — and how hard is it to find?",
    theory=r"""QM: repeatedly merge implicants differing in one variable; unmerged ones are prime. Minimum cover is NP-hard (set cover). Known minima: n-input parity has no mergeable pairs → exactly $2^{n-1}$ product terms of n literals; majority-of-n needs
$\binom{n}{\lceil n/2\rceil}$ terms; a function's number of primes can reach ~3ⁿ/n. Multi-level logic can be exponentially smaller (parity: n−1 XORs), which two-level minimisation cannot see.""",
    method="""Parity and majority for n = 3…7; 4-bit prime detector with and without don't-cares (BCD inputs); random functions for n = 4…8 (500 each up to n = 6, 80 and 40 for n = 7 and 8) verified against truth tables; timing and prime counts; parity in Yosys (multi-level) for contrast.""",
)


def run(p):
    for n in (3, 5, 7):
        mt = [m for m in range(2 ** n) if bin(m).count("1") % 2]
        c = exact_cover(prime_implicants(mt, [], n), mt, n)
        p.compare(f"Parity of {n} inputs: minimum product terms = 2^(n−1)", 2 ** (n - 1), len(c), "", kind="abs")
    from math import comb
    for n in (3, 5, 7):
        mt = [m for m in range(2 ** n) if bin(m).count("1") > n // 2]
        c = exact_cover(prime_implicants(mt, [], n), mt, n)
        p.compare(f"Majority of {n}: minimum terms = C(n, ⌈n/2⌉)", comb(n, (n + 1) // 2), len(c), "", kind="abs")
    pm = [2, 3, 5, 7, 11, 13]
    c1 = exact_cover(prime_implicants(pm, [], 4), pm, 4)
    bcd = [m for m in pm if m < 10]; dc = list(range(10, 16))
    c2 = exact_cover(prime_implicants(bcd, dc, 4), bcd, 4)
    p.metric("4-bit prime detector", to_sop(c1, "ABCD"), "", f"{len(c1)} terms")
    p.metric("… with BCD don't-cares (10–15)", to_sop(c2, "ABCD"), "", f"{len(c2)} terms")
    p.compare("Don't-cares never increase the minimum (terms with DC ≤ without; 1 = yes)", 1, int(len(c2) <= len(c1)), "", kind="abs")
    r = p.rng; rows = []; bad = 0
    for n in (4, 5, 6, 7, 8):
        t0 = time.perf_counter(); npr = []; saved = []
        for _ in range(500 if n <= 6 else 80 if n == 7 else 40):
            mt = [m for m in range(2 ** n) if r.random() < 0.4]
            if not mt:
                continue
            pr = prime_implicants(mt, [], n); c = exact_cover(pr, mt, n)
            bad += any(evaluate(c, x) != (x in set(mt)) for x in range(2 ** n))
            npr.append(len(pr)); saved.append(len(greedy_cover(pr, mt, n)) - len(c))
        rows.append((n, np.mean(npr), (time.perf_counter() - t0) / len(npr), np.mean(saved)))
    p.compare("Exact covers that disagree with their truth table (all random functions, n = 4…8)", 0, bad, "", kind="abs")
    rr = np.array(rows)
    p.metric("Mean primes per random function, n = 4 / 6 / 8", f"{rr[0, 1]:.0f} / {rr[2, 1]:.0f} / {rr[4, 1]:.0f}")
    p.metric("Mean solve time, n = 4 / 8", f"{rr[0, 2] * 1e3:.2f} ms / {rr[4, 2] * 1e3:.0f} ms")
    v = "module par(input [6:0] x, output y); assign y = ^x; endmodule"
    s = synth(p, {"par.v": v}, "par", gates="AND,OR,XOR,NAND,NOR,XNOR")
    p.compare("7-input parity as multi-level logic (Yosys): XOR gates = n − 1", 6, s["cells"], "", kind="abs")
    p.metric("… versus two-level: 64 seven-input ANDs + one 64-input OR", 64 * 7, "literals")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(rr[:, 0], rr[:, 1], "o-", color=C_MEAS, label="prime implicants (mean)"); ax[0].semilogy(rr[:, 0], 2.0 ** rr[:, 0] * 0.4, "--", color=C_PRED, label="minterms (40 % of 2ⁿ)")
    style_axes(ax[0], "variables n", "count", "Primes outnumber minterms as n grows")
    ax[1].semilogy(rr[:, 0], rr[:, 2], "o-", color=C_MEAS)
    style_axes(ax[1], "variables n", "exact solve time per function (s)", "Exact minimisation cost", legend=False)
    p.save(fig, "qm", "Growth of the number of prime implicants and of exact-minimisation time with the number of variables.")
    p.discuss("""The exact minimiser reproduces the theoretical minima — 2^{n−1} terms for parity (nothing can merge), C(n, ⌈n/2⌉) for majority — and every
random cover matches its truth table. Don't-cares help: restricting the prime detector to BCD inputs shortens the expression. The scaling plot
shows why exactness is limited to small functions: the number of primes grows faster than the number of minterms and the covering step is an
NP-hard search, so time rises steeply with n. The parity comparison makes the deeper point that two-level minimality is not circuit minimality:
the 'optimal' SOP for 7-input parity has 64 seven-literal terms, while six XOR gates do the same job — multi-level synthesis is a different and
richer problem.""")
# tol-convention: relative tolerances are in percent
