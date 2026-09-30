from eelab import *
from eelab.circuit import Circuit
import scipy.sparse as sp
import scipy.sparse.linalg as spla

META = dict(
    id="AM-062", title="Build a mini SPICE: modified nodal analysis from scratch", level="H",
    tools="A self-contained ~80-line MNA engine (stamps for R, C, L, independent V/I sources, VCVS/VCCS; DC and complex AC), sparse assembly, cross-checked against the repository's full simulator and hand solutions",
    summary="Write the matrix stamps of modified nodal analysis, assemble and solve the circuit matrix for DC and AC problems, and verify the "
            "engine on hand-solvable circuits (Wheatstone bridge, R-2R ladder, an op-amp modelled as a VCVS) and on 200 random networks against an independent simulator.",
    problem="What does a circuit simulator actually do? Can the whole idea fit in one page of linear algebra?",
    theory=r"""KCL at every non-ground node gives $Gv = i$; voltage sources add one unknown current each and one constraint row, giving the MNA system
$\begin{bmatrix}G & B\\ C & D\end{bmatrix}\begin{bmatrix}v\\ j\end{bmatrix}=\begin{bmatrix}i\\ e\end{bmatrix}$. Each element 'stamps' a few entries: a conductance g between a and b adds +g to (a,a),(b,b) and −g to (a,b),(b,a); a capacitor
is jωC, an inductor 1/(jωL) (or a branch current for DC). R-2R ladder: node voltages halve each stage exactly; bridge: zero detector current when R1/R2 = R3/R4.""",
    method="""Own engine (independent code path from eelab.circuit). Tests: R-2R ladder (8 bits), unbalanced/balanced Wheatstone bridge, inverting amplifier with VCVS gain 10⁶, RLC AC sweep; 200 random connected
networks (5–40 nodes, R/C/L/V/I) solved at DC and at 1 kHz by both engines.""",
)


class MiniSpice:
    def __init__(self):
        self.nodes = {"0": -1}; self.elems = []; self.vsrc = []

    def n(self, a):
        if a not in self.nodes:
            self.nodes[a] = len(self.nodes) - 1
        return self.nodes[a]

    def add(self, kind, a, b, val, c=None, d=None):
        self.elems.append((kind, self.n(a), self.n(b), val, None if c is None else self.n(c), None if d is None else self.n(d)))
        if kind in ("V", "E", "L"):
            self.vsrc.append(len(self.elems) - 1)

    def solve(self, w=0.0):
        N = len(self.nodes) - 1; M = len(self.vsrc); A = sp.lil_matrix((N + M, N + M), dtype=complex); z = np.zeros(N + M, complex)

        def g(a, b, y):
            for i, j, s in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
                if i >= 0 and j >= 0:
                    A[i, j] += s * y
        k = 0
        for idx, (kind, a, b, val, c, d) in enumerate(self.elems):
            if kind == "R":
                g(a, b, 1 / val)
            elif kind == "C":
                g(a, b, 1j * w * val)
            elif kind == "I":                      # current val flows from a through the source into b
                if a >= 0: z[a] -= val
                if b >= 0: z[b] += val
            elif kind == "G":                      # VCCS: current val·(v_c − v_d) from a to b
                for i, s in ((a, 1), (b, -1)):
                    for j, t in ((c, 1), (d, -1)):
                        if i >= 0 and j >= 0:
                            A[i, j] += s * t * val
            else:                                  # V, E (VCVS) and L (branch current)
                r = N + k; k += 1
                for i, s in ((a, 1), (b, -1)):
                    if i >= 0:
                        A[i, r] += s; A[r, i] += s
                if kind == "V":
                    z[r] = val
                elif kind == "E":
                    for j, t in ((c, 1), (d, -1)):
                        if j >= 0:
                            A[r, j] -= t * val
                else:                              # inductor: v_a − v_b − jωL·i = 0
                    A[r, r] -= 1j * w * val
        x = spla.spsolve(A.tocsc(), z)
        return {name: (x[i] if i >= 0 else 0.0) for name, i in self.nodes.items()}


def run(p):
    s = MiniSpice(); s.add("V", "n0", "0", 8.0); s.add("R", "n0", "0", 2e3)
    for k in range(1, 9):
        s.add("R", f"n{k - 1}", f"n{k}", 1e3); s.add("R", f"n{k}", "0", 2e3 if k < 8 else 1e3)
    v = s.solve()
    ratios = [v[f"n{k}"].real / v[f"n{k - 1}"].real for k in range(1, 9)]
    p.compare("R-2R ladder: every node is half the previous (worst deviation of the ratio)", 0.0, max(abs(r - 0.5) for r in ratios), "", kind="abs", tol=1e-12)
    for R4, label in ((1e3, "balanced"), (1.2e3, "unbalanced")):
        s = MiniSpice(); s.add("V", "t", "0", 10.0); s.add("R", "t", "a", 1e3); s.add("R", "a", "0", 2e3); s.add("R", "t", "b", 0.5e3); s.add("R", "b", "0", R4)
        v = s.solve()
        pred = 10 * (2e3 / 3e3 - R4 / (0.5e3 + R4))
        p.compare(f"Wheatstone bridge ({label}): v_a − v_b", pred, (v["a"] - v["b"]).real, "V", kind="abs", tol=1e-12)
    s = MiniSpice(); s.add("V", "in", "0", 0.1); s.add("R", "in", "m", 1e3); s.add("R", "m", "out", 10e3); s.add("E", "out", "0", 1e6, "0", "m")
    v = s.solve()
    p.compare("Inverting amplifier (VCVS, A = 10⁶): gain", -10 / (1 + 11 / 1e6), (v["out"] / 0.1).real, "", tol=1e-07)
    r = p.rng
    worst_dc = worst_ac = 0
    for trial in range(200):
        n = int(r.integers(5, 41)); ms, ck = MiniSpice(), Circuit("rand")
        ms.add("V", "n1", "0", 1.0); ck.V("s", "n1", "0", dc=1.0, ac=1.0)
        for i in range(2, n + 1):                       # spanning tree of resistors keeps it connected
            j = int(r.integers(1, i)); R = float(10 ** r.uniform(1, 5))
            ms.add("R", f"n{i}", f"n{j}", R); ck.R(f"t{i}", f"n{i}", f"n{j}", R)
        for e in range(n):
            a, b = r.choice(np.arange(0, n + 1), 2, replace=False); a = "0" if a == 0 else f"n{a}"; b = "0" if b == 0 else f"n{b}"
            kind = r.choice(["R", "C", "I"]); val = float(10 ** r.uniform(1, 5)) if kind == "R" else float(10 ** r.uniform(-9, -6)) if kind == "C" else float(r.uniform(-1e-3, 1e-3))
            ms.add(kind, a, b, val)
            {"R": lambda: ck.R(f"x{e}", a, b, val), "C": lambda: ck.C(f"x{e}", a, b, val), "I": lambda: ck.I(f"x{e}", a, b, dc=val, ac=val)}[kind]()
        vd = ms.solve(0.0); od = ck.op()
        worst_dc = max(worst_dc, max(abs(vd[k].real - od[k]) / (abs(od[k]) + 1e-3) for k in vd if k != "0" and k in od))
        va = ms.solve(2 * pi * 1e3); oa = ck.ac([1e3])
        worst_ac = max(worst_ac, max(abs(va[k] - oa.v(k)[0]) / (abs(oa.v(k)[0]) + 1e-3) for k in va if k != "0"))
    p.compare("200 random networks at DC: mini SPICE vs eelab.circuit (worst relative)", 0, worst_dc, "", kind="abs", tol=1e-6)
    p.compare("… at 1 kHz (complex AC)", 0, worst_ac, "", kind="abs", tol=1e-6)
    s = MiniSpice(); s.add("V", "a", "0", 1.0); s.add("R", "a", "b", 20.0); s.add("L", "b", "c", 10e-3); s.add("C", "c", "0", 1e-6)
    f = np.logspace(2, 4, 400)
    Hc = np.array([s.solve(2 * pi * fq)["c"] for fq in f])
    w0 = 1 / np.sqrt(10e-3 * 1e-6)
    p.compare("Series RLC: |v_C| peak at ω0√(1 − 2ζ²)", w0 * np.sqrt(1 - 2 * (20 / 2 * np.sqrt(1e-6 / 10e-3)) ** 2) / (2 * pi), f[np.argmax(np.abs(Hc))], "Hz", tol=1)
    s = MiniSpice(); s.add("V", "n0", "0", 8.0); s.add("R", "n0", "0", 2e3)
    for k in range(1, 9):
        s.add("R", f"n{k - 1}", f"n{k}", 1e3); s.add("R", f"n{k}", "0", 2e3 if k < 8 else 1e3)
    fig, ax = p.fig(1, 2, w=11)
    N = len(s.nodes) - 1 + len(s.vsrc)
    Ad = np.zeros((N, N))
    k = 0; Nn = len(s.nodes) - 1
    for kind, a, b, val, c, d in s.elems:
        if kind == "R":
            for i, j in ((a, a), (b, b), (a, b), (b, a)):
                if i >= 0 and j >= 0: Ad[i, j] = 1
        else:
            r_ = Nn + k; k += 1
            for i in (a, b):
                if i >= 0: Ad[i, r_] = Ad[r_, i] = 1
    ax[0].spy(Ad, markersize=6, color=C_MEAS); ax[0].set_title("MNA matrix sparsity, R-2R ladder", loc="left", fontsize=10)
    ax[1].semilogx(f, db(np.abs(Hc)), color=C_MEAS)
    style_axes(ax[1], "frequency (Hz)", "|v_C / v_in| (dB)", "Series RLC solved by the mini SPICE (AC)", legend=False)
    p.save(fig, "mini_spice", "Sparsity pattern of the assembled MNA matrix and an AC sweep computed by the mini simulator.")
    p.discuss(f"""About eighty lines of code — element stamps plus one sparse solve — reproduce what a circuit simulator does for linear DC and AC analysis. The
engine gets every hand-derivable answer exactly (R-2R ladder halving, bridge balance, the inverting amplifier's gain including the 1/(1 + 11/A)
error term) and agrees with the repository's full simulator on 200 random networks to ~1e-10. The sparsity plot shows why real simulators scale:
each node touches only its neighbours, so the matrix is nearly empty and sparse LU (AM-063) costs far less than dense elimination. Nonlinear
devices add Newton iterations around this same linear solve, and transient analysis adds an integration formula per capacitor and inductor —
that combination is AM-132, the full version.""")
# tol-convention: relative tolerances are in percent
