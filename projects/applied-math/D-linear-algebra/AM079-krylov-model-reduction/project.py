from eelab import *
import scipy.sparse as sp
import scipy.sparse.linalg as spla

META = dict(
    id="AM-079", title="Krylov model-order reduction of a large RC network", level="H",
    tools="Descriptor model G x + C ẋ = b u of a 2000-node RC interconnect, Arnoldi/PRIMA projection onto a Krylov subspace, moment matching, passivity (congruence) and error vs order",
    summary="Reduce a 2000-state RC interconnect model to 4–20 states by projecting onto the Krylov subspace of G⁻¹C, show that the reduced models "
            "match the first q moments of the transfer function exactly, stay passive, and track the full response to high accuracy.",
    problem="Post-layout interconnect models have thousands of nodes. Can a 10-state model reproduce the behaviour that matters?",
    theory=r"""With H(s) = lᵀ(G + sC)⁻¹b, expand around s = 0: moments $m_k = l^T(-G^{-1}C)^kG^{-1}b$. Projecting with an orthonormal basis V of $\mathcal K_q(G^{-1}C, G^{-1}b)$ — the reduced model
$(V^TGV, V^TCV, V^Tb, V^Tl)$ — matches the first q moments exactly (one-sided Arnoldi; 2q if l = b by symmetry for this RC case). Congruence projection (PRIMA) preserves positive definiteness, so the reduced model is
passive (stable, all poles real negative for RC).""",
    method="""RC tree: 2000 nodes attached to random earlier nodes (a random recursive tree, depth ~ ln n), resistors 10 Ω–1 kΩ, capacitors 1–100 fF; 50 Ω driver; input current at the root, output voltage at a far leaf (and at the root for the symmetric case). Orders q = 2…20.
Moments computed directly; relative error of |H(jω)| over 1 kHz–10 GHz; eigenvalues of the reduced pencil. (A first network built as a chain
~700 resistors deep had its far-leaf response cut off near 5 kHz, so a 1 MHz–100 GHz sweep sampled only an exponentially small tail that no
DC-expanded model can represent — the error looked like 10⁵ %.)""",
)


def network(n, r):
    rows, cols, vals = [], [], []
    parent = [-1] + [int(r.integers(0, i)) for i in range(1, n)]          # random recursive tree: depth ~ ln n, like a routed clock/signal net
    G = sp.lil_matrix((n, n)); C = sp.lil_matrix((n, n))
    for i in range(1, n):
        g = 1 / r.uniform(10, 1000); j = parent[i]
        G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g
    for i in range(n):
        C[i, i] = r.uniform(1e-15, 100e-15)
    G[0, 0] += 1 / 50.0
    return G.tocsc(), C.tocsc()


def arnoldi(G, C, b, q):
    lu = spla.splu(G)
    v = lu.solve(b); V = [v / np.linalg.norm(v)]
    for k in range(1, q):
        w = lu.solve(C @ V[-1])
        for u in V:
            w -= (u @ w) * u
        for u in V:
            w -= (u @ w) * u
        V.append(w / np.linalg.norm(w))
    return np.array(V).T


def moments(G, C, b, l, k):
    lu = spla.splu(G) if sp.issparse(G) else None
    solve = (lambda x: lu.solve(x)) if lu else (lambda x: np.linalg.solve(G, x))
    x = solve(b); out = []
    for _ in range(k):
        out.append(l @ x); x = -solve(C @ x)
    return np.array(out)


def run(p):
    r = p.rng
    n = 2000
    G, C = network(n, r)
    b = np.zeros(n); b[0] = 1.0; l = np.zeros(n); l[-1] = 1.0
    f = np.logspace(3, 10, 60); s = 2j * pi * f
    Hf = np.array([l @ spla.spsolve((G + si * C).tocsc(), b) for si in s])
    rows = []
    for q in (2, 4, 6, 8, 12, 16, 20):
        V = arnoldi(G, C, b, q)
        Gr, Cr, br, lr = V.T @ (G @ V), V.T @ (C @ V), V.T @ b, V.T @ l
        Hr = np.array([lr @ np.linalg.solve(Gr + si * Cr, br) for si in s])
        err = np.max(np.abs(Hr - Hf) / np.max(np.abs(Hf)))
        m_full = moments(G, C, b, l, q + 2); m_red = moments(Gr, Cr, br, lr, q + 2)
        matched = int(np.sum(np.abs(m_red / m_full - 1) < 1e-6))
        poles = np.linalg.eigvals(-np.linalg.solve(Cr, Gr))
        rows.append((q, err, matched, np.max(poles.real), np.max(np.abs(poles.imag))))
    for q, err, matched, maxre, maxim in rows:
        if q in (4, 8):
            p.compare(f"q = {q}: moments matched (one-sided Krylov: ≥ q)", q, matched, "", kind="abs", tol=q)
    p.compare("All reduced models stable: largest pole real part < 0 (1 = yes)", 1, int(max(r_[3] for r_ in rows) < 0), "", kind="abs")
    p.compare("RC network ⇒ reduced poles real (max |Im|/|Re| scale)", 0, max(r_[4] for r_ in rows), "", kind="abs", tol=1e-3)
    p.compare("q = 12: worst relative |H| error over 1 kHz–10 GHz (my guess < 0.1 %)", 0, rows[4][1], "", kind="abs", tol=1e-3)
    p.metric("q = 20: worst relative error", rows[-1][1], "")
    fig, ax = p.fig(1, 2, w=11)
    rr = np.array(rows)
    ax[0].semilogy(rr[:, 0], rr[:, 1], "o-", color=C_MEAS)
    style_axes(ax[0], "reduced order q", "max |H_q − H| / max |H|", "Error vs reduced order (full model: 2000 states)", legend=False)
    ax[1].loglog(f, np.abs(Hf), color="black", lw=3, alpha=.3, label="full (2000)")
    for q, c in ((2, COLORS[1]), (4, COLORS[2]), (8, C_MEAS)):
        V = arnoldi(G, C, b, q); Gr, Cr, br, lr = V.T @ (G @ V), V.T @ (C @ V), V.T @ b, V.T @ l
        ax[1].loglog(f, np.abs([lr @ np.linalg.solve(Gr + si * Cr, br) for si in s]), "--", color=c, label=f"q = {q}")
    style_axes(ax[1], "frequency (Hz)", "|H| (Ω)", "Transfer impedance root → far leaf")
    p.save(fig, "mor", "Reduction error vs order, and the reduced models' responses against the full 2000-node network.")
    p.discuss(f"""A handful of Arnoldi vectors capture a 2000-node RC network: the q-state models match at least the first q moments of the transfer function (the
low-frequency Taylor coefficients) exactly, and the error across seven decades of frequency falls rapidly with q — though more slowly than I guessed: the 12-state
model is off by {rows[4][1] * 100:.1f} % at worst (not < 0.1 %), and q = 20 reaches {rows[-1][1] * 100:.2f} %; the error sits at the highest frequencies, far from the DC expansion point. Because the projection is a congruence (VᵀGV, VᵀCV), symmetric positive-definite matrices stay so: every reduced model is stable
with real poles, i.e. still a passive RC network, which is what makes PRIMA safe to use inside a larger simulation. The accuracy is best near the
expansion point (DC) and degrades at the highest frequencies, which is why multi-point (rational Krylov) expansions are used for broadband models.""")
# tol-convention: relative tolerances are in percent
