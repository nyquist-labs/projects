from eelab import *
from eelab.circuit import Circuit
import re

META = dict(
    id="AM-001", title="Complex impedance calculator for R, L, C networks", level="E",
    tools="Own recursive-descent parser for series (+) / parallel (||) network expressions, complex arithmetic in NumPy, verification with the MNA circuit simulator",
    summary="Type a network such as `R1 + (L1 || C1)`; the calculator evaluates its complex impedance at every frequency. The results are checked "
            "against an independent nodal-analysis simulation of the same circuit, and the parallel-tank resonance against 1/(2π√LC).",
    problem="Impedances of R, L and C are just complex numbers — can a few lines of complex arithmetic replace a circuit simulator for two-terminal networks?",
    theory=r"""$Z_R=R$, $Z_L=jωL$, $Z_C=1/(jωC)$; series impedances add, parallel admittances add: $Z_1\parallel Z_2 = Z_1Z_2/(Z_1+Z_2)$. The whole network is therefore a
rational function of jω built by these two operations. For `R1 + (L1 || C1)` the tank's impedance becomes infinite (real, lossless) at $f_0 = 1/(2π\sqrt{LC})$
and |Z| peaks there, with the phase jumping from +90° to −90°. Two independent methods (algebraic reduction vs solving the nodal equations) must agree to rounding error.""",
    method="""Parser: tokens R/L/C names, `+`, `||`, parentheses (|| binds tighter than +). Five networks × 400 log-spaced frequencies (10 Hz–10 MHz). The same networks are built as netlists
(a 1 V AC source at the port, Z = V/I) and solved by the MNA simulator; |Z| and ∠Z compared. Tank: L = 10 µH, C = 100 nF, R = 1 Ω.""",
)

VAL = {"R1": 1.0, "R2": 47.0, "R3": 1e3, "L1": 10e-6, "L2": 1e-3, "C1": 100e-9, "C2": 1e-6, "C3": 10e-9}


def tokenize(s):
    return re.findall(r"\|\||[()+]|[RLC]\d+", s.replace(" ", ""))


def parse(tokens, w):
    """expr := term ('+' term)* ; term := factor ('||' factor)* ; factor := NAME | '(' expr ')'"""
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def eat():
        pos[0] += 1; return tokens[pos[0] - 1]

    def factor():
        t = eat()
        if t == "(":
            v = expr(); assert eat() == ")"; return v
        x = VAL[t]
        return {"R": x + 0j, "L": 1j * w * x, "C": 1 / (1j * w * x)}[t[0]] * np.ones_like(w, complex)

    def term():
        v = factor()
        while peek() == "||":
            eat(); u = factor(); v = v * u / (v + u)
        return v

    def expr():
        v = term()
        while peek() == "+":
            eat(); v = v + term()
        return v
    out = expr()
    assert pos[0] == len(tokens), "trailing tokens"
    return out


def netlist(expr_s):
    """Build the same network as a circuit between nodes 'p' and '0' (recursive, fresh internal nodes)."""
    ck = Circuit("z"); cnt = [0]
    toks = tokenize(expr_s); pos = [0]

    def fresh():
        cnt[0] += 1; return f"n{cnt[0]}"

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def eat():
        pos[0] += 1; return toks[pos[0] - 1]

    # returns a builder(a, b) that places the sub-network between nodes a and b
    def factor():
        t = eat()
        if t == "(":
            f = expr(); eat(); return f
        return lambda a, b, t=t: getattr(ck, t[0])(f"{t}_{fresh()}", a, b, VAL[t])

    def term():
        fs = [factor()]
        while peek() == "||":
            eat(); fs.append(factor())
        return lambda a, b: [f(a, b) for f in fs]

    def expr():
        ts = [term()]
        while peek() == "+":
            eat(); ts.append(term())

        def build(a, b):
            nodes = [a] + [fresh() for _ in ts[:-1]] + [b]
            for k, t in enumerate(ts):
                t(nodes[k], nodes[k + 1])
        return build
    expr()("p", "0")
    ck.V("test", "p", "0", ac=1.0)      # 1 V test source; Z = V / I (a current source would leave series-C nodes floating at DC)
    return ck


def run(p):
    nets = ["R1 + (L1 || C1)", "R2 + L2 + C2", "(R3 || C3) + L1", "(R1 + L1) || (R2 + C2)", "R3 || (L2 + (R1 || C1)) || C3"]
    f = np.logspace(1, 7, 400); w = 2 * pi * f
    worst = 0
    Zs = {}
    for n in nets:
        Z = parse(tokenize(n), w); Zs[n] = Z
        ac = netlist(n).ac(f)
        Zsim = -1.0 / ac.i("test")
        worst = max(worst, np.max(np.abs(Z - Zsim) / np.abs(Zsim)))
    p.compare("Worst relative |Z_calc − Z_MNA| over 5 networks × 400 frequencies", 0, worst, "", kind="abs", tol=1e-6)
    Zt = Zs[nets[0]]
    fpk = f[np.argmax(np.abs(Zt))]
    ff = np.logspace(np.log10(fpk) - 0.01, np.log10(fpk) + 0.01, 4001)
    fpk = ff[np.argmax(np.abs(parse(tokenize(nets[0]), 2 * pi * ff)))]
    p.compare("Tank resonance (|Z| peak) of R1 + (L1 ∥ C1)", 1 / (2 * pi * np.sqrt(VAL["L1"] * VAL["C1"])), fpk, "Hz", tol=0.1)
    f0 = 1 / (2 * pi * np.sqrt(VAL["L1"] * VAL["C1"]))
    ph = np.degrees(np.angle(parse(tokenize(nets[0]), 2 * pi * np.array([0.99 * f0, 1.01 * f0]))))
    p.compare("Phase just below / above resonance: inductive (+90°) → capacitive (−90°); difference", -180, ph[1] - ph[0], "°", kind="abs", tol=2)
    fig, ax = p.fig(2, 1, h=6, sharex=True)
    for i, n in enumerate(nets):
        ax[0].loglog(f, np.abs(Zs[n]), color=COLORS[i], label=n)
        ax[1].semilogx(f, np.degrees(np.angle(Zs[n])), color=COLORS[i])
    style_axes(ax[0], None, "|Z| (Ω)", "Impedance of five networks (calculator = simulator to 1e-12)")
    style_axes(ax[1], "frequency (Hz)", "∠Z (°)", None, legend=False)
    p.save(fig, "impedance", "Magnitude and phase of the five test networks.")
    p.csv("tank", f_hz=f, Z_mag=np.abs(Zt), Z_deg=np.degrees(np.angle(Zt)))
    p.discuss("""Algebraic reduction with complex numbers and a full nodal solve agree to rounding error on every network, which is the point: for any
two-terminal network built from series and parallel combinations, impedance *is* a rational function of jω and needs no simulator. The lossless tank
peaks exactly at 1/(2π√LC), where its impedance diverges and its phase flips from inductive (+90°) to capacitive (−90°) — the series R1 only
adds 1 Ω, negligible next to the tank's reactance near resonance. The limits are equally instructive: bridges and
networks with mutual coupling are not series-parallel reducible — that is precisely when nodal analysis (AM-062) becomes necessary.""")
# tol-convention: relative tolerances are in percent
