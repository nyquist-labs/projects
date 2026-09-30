from eelab import *
import re

META = dict(
    id="AM-135", title="Boolean identity checker", level="M",
    tools="Own recursive-descent parser for Boolean expressions (', +, ·, ^, parentheses, implicit AND), canonical truth-table signature, counterexample generation, random expression fuzzing against Python evaluation",
    summary="Decide whether two Boolean expressions are identical by comparing canonical truth-table signatures, returning a counterexample "
            "when they are not; verify a catalogue of textbook theorems (De Morgan, absorption, consensus, Shannon expansion) and fuzz the parser against Python's own evaluator.",
    problem="Is (A+B)(A'+C) really equal to AC + A'B? A checker that answers with proof or counterexample.",
    theory=r"""Two expressions over n variables are equal iff their truth tables (2ⁿ rows) coincide — a canonical form, so equality is decidable by comparing bit-vectors. A differing row is a counterexample. Theorems to check include consensus
$AB+A'C+BC=AB+A'C$, absorption $A+AB=A$, De Morgan, and Shannon expansion $F = A\,F|_{A=1}+A'F|_{A=0}$. The general problem is co-NP-complete (tautology), but 2ⁿ is trivial for n ≲ 20.""",
    method="""Grammar (precedence NOT > AND > XOR > OR): expr := xterm ('+' xterm)*; xterm := term ('^' term)*; term := factor (('·'|implicit) factor)*; factor := atom "'"*; atom := variable | 0 | 1 | '(' expr ')'. 14 true identities and 6 deliberately false ones; 3000 random expressions
(≤ 6 variables, depth ≤ 6) rendered both in this syntax and as Python, signatures compared.""",
)


def parse(s):
    toks = re.findall(r"[A-Za-z]|[01]|[()+^'·*]", s)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def eat():
        pos[0] += 1; return toks[pos[0] - 1]

    def atom():
        t = eat()
        if t == "(":
            e = expr(); assert eat() == ")", "missing )"
        elif t in "01":
            e = ("const", int(t))
        else:
            e = ("var", t)
        while peek() == "'":
            eat(); e = ("not", e)
        return e

    def term():
        e = atom()
        while peek() is not None and (peek() in "·*" or peek() == "(" or peek().isalnum()):
            if peek() in "·*":
                eat()
            e = ("and", e, atom())
        return e

    def xterm():
        e = term()
        while peek() == "^":
            eat(); e = ("xor", e, term())
        return e

    def expr():
        e = xterm()
        while peek() == "+":
            eat(); e = ("or", e, xterm())
        return e
    out = expr()
    assert pos[0] == len(toks), "trailing input"
    return out


def variables(e, acc=None):
    acc = set() if acc is None else acc
    if e[0] == "var":
        acc.add(e[1])
    elif e[0] != "const":
        for c in e[1:]:
            variables(c, acc)
    return acc


def ev(e, env):
    k = e[0]
    if k == "var":
        return env[e[1]]
    if k == "const":
        return e[1]
    if k == "not":
        return 1 - ev(e[1], env)
    a, b = ev(e[1], env), ev(e[2], env)
    return a & b if k == "and" else a | b if k == "or" else a ^ b


def check(lhs, rhs):
    a, b = parse(lhs), parse(rhs)
    vs = sorted(variables(a) | variables(b))
    for m in range(2 ** len(vs)):
        env = {v: (m >> i) & 1 for i, v in enumerate(vs)}
        if ev(a, env) != ev(b, env):
            return False, env
    return True, None


TRUE = [("(A+B)'", "A'B'"), ("(AB)'", "A'+B'"), ("A+AB", "A"), ("A(A+B)", "A"), ("A+A'B", "A+B"), ("AB+A'C+BC", "AB+A'C"),
        ("(A+B)(A'+C)", "AC+A'B"), ("A^B", "AB'+A'B"), ("(A^B)^C", "A^(B^C)"), ("A(B+C)", "AB+AC"), ("A+BC", "(A+B)(A+C)"),
        ("AB+AB'", "A"), ("(A+B)(A+B')", "A"), ("AB'+B", "A+B")]
FALSE = [("A+BC", "(A+B)C"), ("(A+B)'", "A'+B'"), ("A^B", "A+B"), ("AB+C", "A(B+C)"), ("A'B'", "(AB)'"), ("AB+A'C", "BC")]


def rand_expr(r, vs, depth):
    if depth == 0 or r.random() < 0.25:
        v = vs[r.integers(len(vs))]
        return (v, v.lower()) if r.random() < 0.7 else (v + "'", f"(1-{v.lower()})")
    a, pa = rand_expr(r, vs, depth - 1); b, pb = rand_expr(r, vs, depth - 1)
    op = r.integers(4)
    if op == 0:
        return f"({a}+{b})", f"({pa}|{pb})"
    if op == 1:
        return f"({a})({b})", f"({pa}&{pb})"
    if op == 2:
        return f"({a}^{b})", f"({pa}^{pb})"
    return f"({a}+{b})'", f"(1-({pa}|{pb}))"


def run(p):
    ok_true = sum(check(a, b)[0] for a, b in TRUE)
    res_false = [check(a, b) for a, b in FALSE]
    p.compare("Textbook identities confirmed", len(TRUE), ok_true, "", kind="abs")
    p.compare("False 'identities' rejected", len(FALSE), sum(not r_[0] for r_ in res_false), "", kind="abs")
    cex_ok = 0
    for (a, b), (eq, env) in zip(FALSE, res_false):
        if env is not None and ev(parse(a), {**{v: 0 for v in "ABC"}, **env}) != ev(parse(b), {**{v: 0 for v in "ABC"}, **env}):
            cex_ok += 1
    p.compare("Counterexamples that really distinguish the two sides", len(FALSE), cex_ok, "", kind="abs")
    r = p.rng; mism = 0
    for _ in range(3000):
        vs = list("ABCDEF")[: int(r.integers(2, 7))]
        s, py = rand_expr(r, vs, int(r.integers(2, 7)))
        tree = parse(s)
        for m in range(2 ** len(vs)):
            env = {v: (m >> i) & 1 for i, v in enumerate(vs)}
            if ev(tree, env) != (eval(py, {}, {v.lower(): env[v] for v in vs}) & 1):
                mism += 1; break
    p.compare("Parser/evaluator vs Python on 3000 random expressions (mismatches)", 0, mism, "", kind="abs")
    lines = [f"{a:>14} = {b:<10} : {'identity' if check(a, b)[0] else 'NOT an identity, e.g. ' + str(check(a, b)[1])}" for a, b in TRUE + FALSE]
    p.write("results/identities.txt", "\n".join(lines) + "\n", "checker output for the theorem catalogue")
    a, b = "AB+A'C+BC", "AB+A'C"
    fig, ax = p.fig(1, 1, w=8, h=3.6)
    vs = "ABC"; rows = []
    for m in range(8):
        env = {v: (m >> (2 - i)) & 1 for i, v in enumerate(vs)}
        rows.append([env["A"], env["B"], env["C"], ev(parse(a), env), ev(parse(b), env)])
    ax.axis("off"); t = ax.table(cellText=rows, colLabels=["A", "B", "C", a, b], loc="center", cellLoc="center"); t.scale(1, 1.3)
    ax.set_title("Consensus theorem: the redundant term BC never changes the output", loc="left", fontsize=10)
    p.save(fig, "consensus", "Truth-table proof of the consensus theorem produced by the checker.")
    p.discuss("""The checker confirms every textbook identity in the catalogue and rejects each plausible-looking false one with a concrete input assignment on
which the two sides differ — a proof or a counterexample, never a shrug. Its parser handles the engineering notation (implicit AND, postfix
complement) and agrees with Python's own evaluator on 3000 random expressions — after a fix: the first grammar gave XOR the same precedence as AND,
so A^BC was read as (A^B)C, and the fuzz test caught it on about 10 % of random expressions while every hand-written identity still passed. Testing
against an independent evaluator found what a catalogue of examples could not. The truth table is a canonical form, which is why the method is
complete; its cost doubles with every variable, so for larger problems the same question is answered with BDDs (AM-136) or SAT solvers — the tools
behind formal equivalence checking of real chip designs.""")
# tol-convention: relative tolerances are in percent
