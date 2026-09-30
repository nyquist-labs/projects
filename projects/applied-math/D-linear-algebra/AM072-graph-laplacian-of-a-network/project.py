from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-072", title="Resistor networks as graphs: Laplacian, effective resistance, Foster's theorem", level="H",
    tools="Weighted graph Laplacian, Moore–Penrose pseudoinverse, effective-resistance matrix, Foster's theorem, algebraic connectivity; verification with the MNA simulator",
    summary="Treat a resistor network as a weighted graph: compute every effective resistance from the Laplacian's pseudoinverse, verify them "
            "against circuit simulation, and confirm two graph-theory results — Foster's theorem and the link between algebraic connectivity and 'bottlenecks'.",
    problem="The nodal matrix of a resistor network is a graph Laplacian. What does spectral graph theory say about circuits?",
    theory=r"""L = D − W (conductance weights). $R_{ij}=(e_i-e_j)^TL^+(e_i-e_j)$. Foster's theorem: $\sum_{edges}g_eR_e = n-1$ for any connected network. The second-smallest eigenvalue λ₂ (Fiedler value) measures how well
connected the network is; cutting a network into two halves joined by a single resistor makes λ₂ small and the Fiedler vector changes sign across the cut. Cube of 1 Ω resistors: R between
opposite corners = 5/6 Ω, adjacent = 7/12 Ω.""",
    method="""(i) Unit-resistor cube. (ii) 100 random connected networks (8–30 nodes, 10 Ω–10 kΩ): all-pairs R_eff via L⁺ vs MNA (1 A between the pair). (iii) Foster's sum. (iv) Two 20-node random clusters joined by 1…5 bridge resistors: λ₂ and the Fiedler sign split.""",
)


def lap(n, edges):
    L = np.zeros((n, n))
    for a, b, g in edges:
        L[a, a] += g; L[b, b] += g; L[a, b] -= g; L[b, a] -= g
    return L


def reff(Lp, i, j):
    return Lp[i, i] + Lp[j, j] - 2 * Lp[i, j]


def run(p):
    cube = [(a, b, 1.0) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]
    Lp = np.linalg.pinv(lap(8, cube))
    p.compare("Cube: opposite corners", 5 / 6, reff(Lp, 0, 7), "Ω", tol=1e-10)
    p.compare("Cube: adjacent corners", 7 / 12, reff(Lp, 0, 1), "Ω", tol=1e-10)
    p.compare("Cube: face diagonal", 3 / 4, reff(Lp, 0, 3), "Ω", tol=1e-10)
    r = p.rng
    worst = 0; foster = []
    for _ in range(100):
        n = int(r.integers(8, 31)); edges = []
        for i in range(1, n):
            edges.append((i, int(r.integers(0, i)), 1 / float(10 ** r.uniform(1, 4))))
        for _ in range(n):
            a, b = r.choice(n, 2, replace=False); edges.append((int(a), int(b), 1 / float(10 ** r.uniform(1, 4))))
        Lp = np.linalg.pinv(lap(n, edges))
        i, j = r.choice(n, 2, replace=False)
        ck = Circuit("net")
        for k, (a, b, g) in enumerate(edges):
            ck.R(f"{k}", f"n{a}" if a else "0", f"n{b}" if b else "0", 1 / g)
        ni, nj = (f"n{i}" if i else "0"), (f"n{j}" if j else "0")
        ck.I("t", nj, ni, dc=1.0)
        o = ck.op()
        vd = (o.get(ni, 0.0) if ni != "0" else 0.0) - (o.get(nj, 0.0) if nj != "0" else 0.0)
        worst = max(worst, abs(vd / reff(Lp, i, j) - 1))
        foster.append(sum(g * reff(Lp, a, b) for a, b, g in edges) - (n - 1))
    p.compare("Effective resistance from L⁺ vs MNA simulation (100 random networks, worst relative)", 0, worst, "", kind="abs", tol=1e-9)
    p.compare("Foster's theorem Σ g_e R_e − (n − 1), worst over 100 networks", 0, max(abs(f) for f in foster), "", kind="abs", tol=1e-9)
    rows = []
    for nb in (1, 2, 3, 5, 10):
        n = 40; edges = []
        for c0 in (0, 20):
            for i in range(1, 20):
                edges.append((c0 + i, c0 + int(r.integers(0, i)), 1.0))
            for _ in range(40):
                a, b = r.choice(20, 2, replace=False); edges.append((c0 + int(a), c0 + int(b), 1.0))
        for _ in range(nb):
            edges.append((int(r.integers(0, 20)), 20 + int(r.integers(0, 20)), 1.0))
        L = lap(n, edges); w, V = np.linalg.eigh(L)
        fied = V[:, 1]
        split = max(np.mean(np.sign(fied[:20]) == np.sign(fied[0])) * np.mean(np.sign(fied[20:]) != np.sign(fied[0])), 0)
        rows.append((nb, w[1], split))
    rr = np.array(rows)
    p.compare("Fiedler vector separates the two clusters with 1 bridge (fraction correctly split)", 1.0, rr[0, 2], "", kind="abs", tol=0.05)
    p.compare("λ₂ grows with the number of bridges (monotone, 1 = yes)", 1, int(np.all(np.diff(rr[:, 1]) > 0)), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(rr[:, 0], rr[:, 1], "o-", color=C_MEAS)
    style_axes(ax[0], "bridging resistors between clusters", "algebraic connectivity λ₂", "Bottlenecks make λ₂ small", legend=False)
    n = 40; edges = []
    for c0 in (0, 20):
        for i in range(1, 20):
            edges.append((c0 + i, c0 + int(r.integers(0, i)), 1.0))
    edges.append((3, 25, 1.0))
    w, V = np.linalg.eigh(lap(n, edges))
    ax[1].bar(range(40), V[:, 1], color=[C_MEAS] * 20 + [C_PRED] * 20)
    style_axes(ax[1], "node (0–19 cluster A, 20–39 cluster B)", "Fiedler vector", "Sign of the Fiedler vector finds the cut", legend=False)
    p.save(fig, "laplacian", "Algebraic connectivity vs number of bridges, and the Fiedler vector of two weakly joined clusters.")
    p.discuss("""The Laplacian pseudoinverse gives every effective resistance at once — the cube's textbook 5/6, 7/12 and 3/4 Ω exactly — and agrees with direct
circuit simulation on 100 random networks. Foster's theorem holds to rounding error for every network: the conductance-weighted sum of edge
effective resistances always equals n − 1, a beautiful invariant with a simple proof via the trace of L L⁺. The spectral view also has an
engineering reading: the Fiedler value λ₂ is small when a network has a bottleneck, and the Fiedler vector's sign pattern locates the cut — the
basis of spectral partitioning used to split large circuits across processors in parallel simulation.""")
# tol-convention: relative tolerances are in percent
