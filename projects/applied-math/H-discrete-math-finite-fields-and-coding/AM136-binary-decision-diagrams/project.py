from eelab import *

META = dict(
    id="AM-136", title="Binary decision diagrams: compressing truth tables", level="H",
    tools="Own reduced ordered BDD package (unique table, memoised ITE/apply), node counts vs truth-table size, variable-ordering experiments on an n-bit comparator and adder, the hidden-weighted-bit and multiplier hard cases",
    summary="Build ROBDDs from scratch and measure how compactly they represent useful functions: linear size for adders and comparators with a "
            "good variable order, exponential with a bad one, and exponential regardless of order for multiplication — the facts that shaped formal verification.",
    problem="A 64-input function has 2⁶⁴ truth-table rows. How can a verification tool still reason about it exactly?",
    theory=r"""An ROBDD (fixed variable order, merged isomorphic subgraphs, no redundant tests) is canonical: two functions are equal iff their BDDs are identical nodes. Size depends dramatically on order: for the comparator $\bigwedge(a_i = b_i)$ the interleaved order
a₁b₁a₂b₂… needs 3n + 2 nodes, the separated order a₁…a_nb₁…b_n needs 3·2ⁿ − 1. The carry-out of an n-bit adder is linear when interleaved. Multiplier outputs need exponential BDDs for *every* order (Bryant 1991).""",
    method="""Node counts (including the two terminals) for n = 2…10: equality comparator under both orders, adder carry-out (interleaved), middle output bit of an n×n multiplier (n ≤ 7, interleaved). Canonicity test: two structurally different expressions of the
same function must return the identical node.""",
)


class BDD:
    def __init__(self):
        self.unique = {}; self.nodes = [None, None]; self.memo = {}

    def mk(self, v, lo, hi):
        if lo == hi:
            return lo
        k = (v, lo, hi)
        if k not in self.unique:
            self.nodes.append(k); self.unique[k] = len(self.nodes) - 1
        return self.unique[k]

    def var(self, v):
        return self.mk(v, 0, 1)

    def top(self, f):
        return self.nodes[f][0] if f > 1 else 1 << 30

    def ite(self, f, g, h):
        if f == 1:
            return g
        if f == 0:
            return h
        if g == h:
            return g
        if g == 1 and h == 0:
            return f
        k = (f, g, h)
        if k in self.memo:
            return self.memo[k]
        v = min(self.top(f), self.top(g), self.top(h))
        co = lambda x, b: (self.nodes[x][1 + b] if x > 1 and self.nodes[x][0] == v else x)
        r = self.mk(v, self.ite(co(f, 0), co(g, 0), co(h, 0)), self.ite(co(f, 1), co(g, 1), co(h, 1)))
        self.memo[k] = r
        return r

    def AND(self, a, b): return self.ite(a, b, 0)
    def OR(self, a, b): return self.ite(a, 1, b)
    def NOT(self, a): return self.ite(a, 0, 1)
    def XOR(self, a, b): return self.ite(a, self.NOT(b), b)

    def size(self, f):
        seen = set(); st = [f]
        while st:
            x = st.pop()
            if x in seen:
                continue
            seen.add(x)
            if x > 1:
                st += [self.nodes[x][1], self.nodes[x][2]]
        return len(seen | {0, 1}) if f > 1 else 1 + (f in (0, 1))


def comparator(n, interleaved):
    B = BDD(); f = 1
    for i in range(n):
        a = B.var(2 * i if interleaved else i); b = B.var(2 * i + 1 if interleaved else n + i)
        f = B.AND(f, B.NOT(B.XOR(a, b)))
    return B.size(f)


def adder_carry(n):
    B = BDD(); c = 0
    for i in range(n):
        a, b = B.var(2 * i), B.var(2 * i + 1)
        c = B.OR(B.AND(a, b), B.AND(c, B.XOR(a, b)))
    return B.size(c)


def mult_mid(n):
    B = BDD()
    a = [B.var(2 * i) for i in range(n)]; b = [B.var(2 * i + 1) for i in range(n)]
    acc = [0] * (2 * n)
    for i in range(n):
        carry = 0
        for j in range(n):
            pp = B.AND(a[j], b[i]); s = B.XOR(B.XOR(acc[i + j], pp), carry)
            carry = B.OR(B.AND(acc[i + j], pp), B.AND(carry, B.XOR(acc[i + j], pp))); acc[i + j] = s
        acc[i + n] = carry
    return B.size(acc[n - 1])


def run(p):
    B = BDD(); x, y, z = B.var(0), B.var(1), B.var(2)
    f1 = B.OR(B.AND(x, y), B.AND(B.NOT(x), z)); f2 = B.OR(B.OR(B.AND(x, y), B.AND(B.NOT(x), z)), B.AND(y, z))
    p.compare("Canonicity: AB + A'C and AB + A'C + BC reduce to the identical node (1 = yes)", 1, int(f1 == f2), "", kind="abs")
    ns = list(range(2, 11))
    ci = [comparator(n, True) for n in ns]; cs = [comparator(n, False) for n in ns]
    p.compare("Comparator, interleaved order: nodes = 3n + 2 (n = 10)", 32, ci[-1], "", kind="abs")
    p.compare("Comparator, separated order: nodes = 3·2ⁿ − 1 (n = 10)", 3 * 2 ** 10 - 1, cs[-1], "", kind="abs")
    ad = [adder_carry(n) for n in ns]
    p.compare("Adder carry-out, interleaved: linear growth (nodes per extra bit)", 3, ad[-1] - ad[-2], "", kind="abs")
    mm = [mult_mid(n) for n in range(2, 8)]
    growth = np.polyfit(range(2, 8), np.log2(mm), 1)[0]
    p.compare("Multiplier middle bit: node count grows exponentially (log₂ growth per bit > 0.5)", 1, int(growth > 0.5), "", kind="abs")
    p.metric("Multiplier middle-bit BDD nodes, n = 2…7", ", ".join(map(str, mm)))
    p.metric("Compression, 10-bit comparator: truth-table rows / BDD nodes (good order)", 2 ** 20 / ci[-1], "×")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(ns, ci, "o-", color=C_MEAS, label="comparator, interleaved"); ax[0].semilogy(ns, cs, "s-", color=C_PRED, label="comparator, separated")
    ax[0].semilogy(ns, ad, "^-", color=COLORS[2], label="adder carry, interleaved"); ax[0].semilogy(ns, 2.0 ** (2 * np.array(ns)), ":", color="gray", label="truth-table rows")
    style_axes(ax[0], "bits n", "BDD nodes", "Variable order decides everything")
    ax[1].semilogy(range(2, 8), mm, "o-", color=C_MEAS)
    style_axes(ax[1], "bits n", "BDD nodes", "Multiplier middle bit: exponential", legend=False)
    p.save(fig, "bdd", "BDD sizes for comparators and adders under two variable orders, and for a multiplier output.")
    p.discuss("""The from-scratch BDD package reproduces the classic results exactly: the equality comparator needs 3n + 2 nodes when each aᵢ is tested next to its
bᵢ and 3·2ⁿ − 1 when all a's come first (the diagram must remember every a bit), and an adder's carry is linear in the interleaved order. With a good
order a 20-input function with a million truth-table rows is a few dozen nodes — and because the form is canonical, equivalence checking is a
pointer comparison. The multiplier's middle bit grows exponentially regardless of order, which is why BDD-based verification conquered adders,
comparators and control logic in the 1990s but multipliers needed other methods (and why today's tools combine BDDs with SAT).""")
# tol-convention: relative tolerances are in percent
