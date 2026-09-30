from eelab import *
import scipy.linalg as sla

META = dict(
    id="AM-078", title="Condition numbers: when linear algebra lies", level="M",
    tools="Hilbert and Vandermonde matrices, polynomial fitting in monomial vs Chebyshev bases, nodal matrices with extreme resistor ratios, forward error vs κ·ε_mach",
    summary="Measure how the relative error of computed solutions tracks κ(A)·ε_mach across ill-conditioned problems: Hilbert systems, "
            "high-degree polynomial fits (and how a better basis fixes them), and circuits mixing milliohm and gigaohm resistors.",
    problem="A backward-stable solver can still return garbage. When — and how do you tell in advance?",
    theory=r"""Backward stability gives $\frac{\|x̂-x\|}{\|x\|}\lesssim κ(A)\,ε_{mach}$, κ = ‖A‖‖A⁻¹‖. Hilbert matrices have κ ≈ e^{3.5n}; the monomial Vandermonde matrix on [−1, 1] grows exponentially with degree,
while a Chebyshev basis stays well conditioned. A nodal matrix's κ is roughly the ratio of largest to smallest conductance — and the error concentrates in the node voltages set by the weak links.""",
    method="""Hilbert n = 2…14 with x = ones: forward error vs κε. Least-squares polynomial fits of degree 5–30 to 200 points of e^x sin(5x) on [−1,1], monomial vs Chebyshev basis: coefficient-space conditioning and
fit error. Resistor chains mixing 1 mΩ and R_big up to 10¹² Ω: κ of G and relative error of node voltages vs extended-precision reference.""",
)


def run(p):
    eps = np.finfo(float).eps
    rows = []
    for n in range(2, 15):
        H = sla.hilbert(n); x = np.ones(n); b = H @ x
        xh = np.linalg.solve(H, b)
        rows.append((n, np.linalg.cond(H), np.max(np.abs(xh - x))))
    r = np.array(rows)
    ok = r[:, 1] < 1 / eps
    p.compare("Hilbert systems: forward error ≤ κ·ε (fraction of sizes obeying the bound ×10)", 1.0, np.mean(r[ok, 2] <= 10 * r[ok, 1] * eps), "", kind="abs")
    p.compare("Hilbert n = 12: log₁₀ error ≈ log₁₀(κ·ε) (difference in decades)", 0, np.log10(r[10, 2]) - np.log10(r[10, 1] * eps), "decades", kind="abs", tol=2)
    p.compare("κ(Hilbert) growth rate: log κ per unit n (≈ 3.5)", 3.5, np.polyfit(r[:, 0], np.log(r[:, 1]), 1)[0], "", kind="abs", tol=0.3)
    xs = np.linspace(-1, 1, 200); f = np.exp(xs) * np.sin(5 * xs)
    fits = []
    for deg in (5, 10, 15, 20, 25, 30):
        V = np.vander(xs, deg + 1, increasing=True); T = np.polynomial.chebyshev.chebvander(xs, deg)
        cm, cc = np.linalg.cond(V), np.linalg.cond(T)
        em = np.max(np.abs(V @ np.linalg.lstsq(V, f, rcond=None)[0] - f)); ec = np.max(np.abs(T @ np.linalg.lstsq(T, f, rcond=None)[0] - f))
        fits.append((deg, cm, cc, em, ec))
    fits = np.array(fits)
    p.compare("Chebyshev basis stays well conditioned at degree 30 (κ < 10)", 1, int(fits[-1, 2] < 10), "", kind="abs")
    p.metric("Monomial basis κ at degree 30", fits[-1, 1], "")
    p.metric("Max fit error at degree 30: monomial / Chebyshev", f"{fits[-1, 3]:.1e} / {fits[-1, 4]:.1e}")
    V = np.vander(xs, 31, increasing=True); T = np.polynomial.chebyshev.chebvander(xs, 30)
    dy = 1e-10 * np.random.default_rng(1).normal(size=len(xs))
    cm0 = np.linalg.lstsq(V, f, rcond=None)[0]; cm1 = np.linalg.lstsq(V, f + dy, rcond=None)[0]
    cc0 = np.linalg.lstsq(T, f, rcond=None)[0]; cc1 = np.linalg.lstsq(T, f + dy, rcond=None)[0]
    ratio = (np.linalg.norm(cm1 - cm0) / np.linalg.norm(cm0)) / (np.linalg.norm(cc1 - cc0) / np.linalg.norm(cc0))
    p.compare("Degree 30: coefficient sensitivity to a 1e-10 data perturbation, monomial ÷ Chebyshev (log₁₀; κ ratio predicts ≈ 10)", np.log10(fits[-1, 1] / fits[-1, 2]), np.log10(ratio), "decades", kind="abs", tol=2)
    circ = []
    for Rb in (1e2, 1e4, 1e6, 1e8, 1e10, 1e12):
        n = 6; G = np.zeros((n, n))
        Rs = [1e-3, Rb, 1e-3, Rb, 1e-3, Rb]
        for k in range(n):
            g = 1 / Rs[k]
            G[k, k] += g
            if k + 1 < n:
                G[k, k] += 0; G[k + 1, k + 1] += g; G[k, k + 1] -= g; G[k + 1, k] -= g
        G[-1, -1] += 1.0
        bvec = np.zeros(n); bvec[0] = 1.0
        x = np.linalg.solve(G, bvec)
        from fractions import Fraction
        Gf = [[Fraction(v) for v in row] for row in G]; bf = [Fraction(v) for v in bvec]
        m = len(Gf)
        for i in range(m):
            piv = Gf[i][i]
            for j in range(i + 1, m):
                fac = Gf[j][i] / piv
                if fac:
                    Gf[j] = [a - fac * c for a, c in zip(Gf[j], Gf[i])]; bf[j] -= fac * bf[i]
        xf = [Fraction(0)] * m
        for i in range(m - 1, -1, -1):
            xf[i] = (bf[i] - sum(Gf[i][j] * xf[j] for j in range(i + 1, m))) / Gf[i][i]
        xe = np.array([float(v) for v in xf])
        circ.append((Rb, np.linalg.cond(G), np.max(np.abs(x - xe) / np.abs(xe))))
    cc_ = np.array(circ)
    p.compare("Resistor chain: error grows with κ (log-log slope of error vs κ, error ∝ κ·ε → ≈ 1)", 1.0, np.polyfit(np.log10(cc_[2:, 1]), np.log10(np.maximum(cc_[2:, 2], 1e-17)), 1)[0], "", kind="abs", tol=0.6)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    ax[0].semilogy(r[:, 0], r[:, 2], "o-", color=C_MEAS, label="measured error"); ax[0].semilogy(r[:, 0], r[:, 1] * eps, "--", color=C_PRED, label="κ·ε")
    style_axes(ax[0], "n", "forward error", "Hilbert systems")
    ax[1].semilogy(fits[:, 0], fits[:, 1], "o-", color=COLORS[1], label="κ monomial"); ax[1].semilogy(fits[:, 0], fits[:, 2], "s-", color=C_MEAS, label="κ Chebyshev")
    style_axes(ax[1], "polynomial degree", "condition number", "Basis choice matters")
    ax[2].loglog(cc_[:, 1], np.maximum(cc_[:, 2], 1e-17), "o-", color=C_MEAS, label="measured"); ax[2].loglog(cc_[:, 1], cc_[:, 1] * eps, "--", color=C_PRED, label="κ·ε")
    style_axes(ax[2], "κ(G)", "relative error of node voltages", "mΩ and GΩ in one circuit")
    p.save(fig, "conditioning", "Forward error vs κ·ε for Hilbert systems, conditioning of polynomial bases, and a badly scaled resistor network.")
    p.discuss("""Across all three families the rule of thumb holds: the digits you lose are log₁₀ κ. A 12×12 Hilbert system has κ ≈ 10¹⁶ and its 'solution' has no correct
digits, even though the solver is backward stable. Polynomial fitting shows a subtler point: in the monomial basis (κ ≈ 10¹¹ at degree 30) the *fitted curve* is still accurate, because
SVD-based least squares is backward stable for the residual — it is the *coefficients* that are meaningless: a 10⁻¹⁰ wiggle in the data moves
them by orders of magnitude more than the same wiggle moves Chebyshev coefficients. Use the monomial coefficients for anything (derivatives,
extrapolation, a lookup in firmware) and the ill-conditioning bites; the Chebyshev basis (κ < 10) avoids the issue entirely. In circuits, mixing
milliohm and gigaohm elements drives κ(G) toward 1/ε and node voltages lose accuracy in proportion; SPICE's GMIN and scaling heuristics exist
precisely to keep this in check. Always estimate κ before trusting digits.""")
# tol-convention: relative tolerances are in percent
