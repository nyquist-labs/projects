from eelab import *
from eelab.nec import solve as nec_solve

META = dict(
    id="AM-120", title="Method of moments: charge on a conductor and current on a dipole", level="H",
    tools="Own electrostatic MoM with pulse basis and point matching (sphere and square plate capacitance), convergence study; thin-wire antenna MoM (Galerkin, repository solver) for input impedance vs length",
    summary="Turn an integral equation into a matrix: compute the capacitance of an isolated sphere (known exactly) and of a square plate (a classic "
            "benchmark) from surface-charge patches, then use a wire-antenna MoM to find a dipole's input impedance and current distribution.",
    problem="Field solvers that only discretise the conductors, not the space around them — how do they work and how accurate are they?",
    theory=r"""The potential of surface charge σ satisfies $V(r)=\int\frac{σ(r')}{4πε|r-r'|}dS'$. With N patches of constant charge and V = 1 enforced at patch centres, Zq = v with $Z_{ij}=\frac{A_j}{4πε|r_i-r_j|}$ (self term by integrating 1/r over the patch).
C = Σq. Sphere: C = 4πεa exactly (111.3 pF for a = 1 m). Unit square plate: C ≈ 40.8 pF (≈ 0.3607·4πε·... benchmark 40.8 pF per metre side). Half-wave dipole (thin): Z_in ≈ 73 + j42 Ω; resonance slightly shorter.""",
    method="""Sphere a = 1 m: patches from a latitude–longitude grid with near-equal areas, N = 50 … 1600. Plate 1 m × 1 m: N×N square patches, N = 10…40, self term analytic for a square. Wire: repository PWS-Galerkin solver, L = 0.40…0.55 λ, radius 10⁻⁵ λ (and 10⁻³ λ for comparison).""",
)

EPS0 = 8.8541878128e-12


def sphere_patches(n):
    pts, areas = [], []
    nl = int(np.sqrt(n / 2))
    edges = np.arccos(np.linspace(1, -1, nl + 1))
    for i in range(nl):
        t0, t1 = edges[i], edges[i + 1]; band = 2 * pi * (np.cos(t0) - np.cos(t1))
        m = max(3, int(round(2 * nl * np.sin((t0 + t1) / 2))))
        tc = (t0 + t1) / 2
        for j in range(m):
            ph = 2 * pi * (j + 0.5) / m
            pts.append((np.sin(tc) * np.cos(ph), np.sin(tc) * np.sin(ph), np.cos(tc))); areas.append(band / m)
    return np.array(pts), np.array(areas)


def run(p):
    rows = []
    for n in (50, 200, 800, 1600):
        pts, A = sphere_patches(n)
        s = np.sqrt(A)
        d = np.linalg.norm(pts[:, None] - pts[None], axis=-1); np.fill_diagonal(d, 1.0)
        Z = A[None, :] / (4 * pi * EPS0 * d)
        np.fill_diagonal(Z, 4 * s * np.log(1 + np.sqrt(2)) / (4 * pi * EPS0))   # ∫ over a square of side s of 1/r seen from its centre = 4s·ln(1+√2)
        q = np.linalg.solve(Z, np.ones(len(pts)))
        rows.append((len(pts), float(np.sum(q * A))))          # q is the charge density on each patch
    rr = np.array(rows)
    p.compare("Sphere a = 1 m: MoM capacitance (finest) vs 4πε₀a", 4 * pi * EPS0, rr[-1, 1], "F", tol=1)
    p.metric("Sphere capacitance vs patches", ", ".join(f"N = {int(n)}: {c * 1e12:.2f} pF" for n, c in rr))
    prow = []
    for N in (10, 20, 30, 40):
        h = 1.0 / N; c = (np.arange(N) + 0.5) * h
        X, Y = np.meshgrid(c, c); pts = np.c_[X.ravel(), Y.ravel(), np.zeros(N * N)]
        d = np.linalg.norm(pts[:, None] - pts[None], axis=-1); np.fill_diagonal(d, 1.0)
        Z = h * h / (4 * pi * EPS0 * d); np.fill_diagonal(Z, 4 * h * np.log(1 + np.sqrt(2)) / (4 * pi * EPS0))
        q = np.linalg.solve(Z, np.ones(N * N)); prow.append((N, q.sum() * h * h, q.reshape(N, N)))
    Ns = np.array([r_[0] for r_ in prow], float); Cs = np.array([r_[1] for r_ in prow])
    Cext = Cs[-1] + (Cs[-1] - Cs[-2]) * (Ns[-2] / (Ns[-1] - Ns[-2])) * 1.0
    p.compare("Unit square plate: capacitance extrapolated in 1/N (benchmark ≈ 40.8 pF)", 40.8e-12, Cext, "F", tol=1)
    Ls = np.linspace(0.40, 0.55, 16); Zs = []
    for L in Ls:
        _, Z = nec_solve([(0.0, L, True)], lam=1.0, nseg=41, radius=1e-5); Zs.append(Z)
    Zs = np.array(Zs)
    Zhalf = Zs[np.argmin(abs(Ls - 0.5))]
    p.compare("Half-wave dipole input resistance, radius 10⁻⁵ λ (sinusoidal-current theory: 73.1 Ω)", 73.1, Zhalf.real, "Ω", tol=8)
    thick = nec_solve([(0.0, 0.5, True)], lam=1.0, nseg=41, radius=1e-3)[1]
    p.metric("Same dipole with radius 10⁻³ λ", f"{thick.real:.1f} + j{thick.imag:.1f} Ω", "", "the 73 Ω figure is the thin-wire limit; R at exactly λ/2 rises with wire thickness")
    p.compare("Half-wave dipole input reactance (≈ +42.5 Ω)", 42.5, Zhalf.imag, "Ω", kind="abs", tol=8)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    ax[0].semilogx(rr[:, 0], rr[:, 1] * 1e12, "o-", color=C_MEAS, label="MoM"); ax[0].axhline(4 * pi * EPS0 * 1e12, color=C_PRED, ls="--", label="4πε₀a")
    style_axes(ax[0], "patches N", "C (pF)", "Sphere, a = 1 m")
    im = ax[1].imshow(prow[-1][2] / prow[-1][2].mean(), cmap="magma"); fig.colorbar(im, ax=ax[1]); ax[1].set_title("Plate charge density (edges crowd)", loc="left", fontsize=10); ax[1].grid(False)
    ax[2].plot(Ls, Zs.real, "o-", color=C_MEAS, label="R_in"); ax[2].plot(Ls, Zs.imag, "s-", color=C_PRED, label="X_in"); ax[2].axhline(0, color="gray", lw=.6)
    style_axes(ax[2], "dipole length (λ)", "Ω", "Thin-wire dipole impedance")
    p.save(fig, "mom", "Sphere capacitance convergence, charge density on a square plate, and dipole input impedance vs length.")
    p.discuss(f"""With only the conductor surfaces discretised, the moment method gets the sphere's capacitance to within 1 % and converges toward 4πε₀a as patches
are refined; the square plate lands on the classic ≈ 40.8 pF benchmark after extrapolating the patch size to zero, and its charge density shows the
expected crowding toward edges and corners (the singularity that makes MoM convergence slow near edges). The same idea for wires — current instead
of charge as the unknown — gives {Zhalf.real:.0f} + j{Zhalf.imag:.0f} Ω for a very thin half-wave dipole — about 7 % above the 73 + j42.5 Ω of the assumed-sinusoidal-current theory, and rising to {thick.real:.0f} Ω for a λ/1000-radius wire, because the true current is not exactly sinusoidal — with resonance a few percent short of λ/2. (An earlier version of this script summed charge *densities* instead of charges and reported a capacitance that grew with N; C = Σσᵢ·Aᵢ.) The price of MoM is the dense N×N
matrix (every patch talks to every other), which is why large problems use fast multipole or iterative solvers.""")
# tol-convention: relative tolerances are in percent
