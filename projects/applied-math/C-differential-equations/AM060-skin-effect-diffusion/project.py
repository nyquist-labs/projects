from eelab import *
from scipy.special import jv

META = dict(
    id="AM-060", title="Skin effect as a diffusion problem", level="H",
    tools="Complex finite-difference solution of the magnetic diffusion (Helmholtz-type) equation in a slab and in a round wire (cylindrical Laplacian), Bessel-function analytic solution, AC-resistance ratio",
    summary="Solve d²J/dx² = jωμσJ numerically for current crowding in a conductor, compare the current distribution with e^{−(1+j)x/δ} and the "
            "Bessel-function solution for a round wire, and compute the AC/DC resistance ratio versus frequency.",
    problem="Why does a copper wire's resistance rise with frequency — and can we predict by exactly how much?",
    theory=r"""In a good conductor the current density obeys the diffusion equation; for time-harmonic fields $∇^2J = jωμσJ = \frac{2j}{δ^2}J$ with skin depth $δ=\sqrt{2/(ωμσ)}$ (66 µm in copper at 1 MHz). Half-space:
$J=J_0e^{-(1+j)x/δ}$. Round wire of radius a: $J(r)\propto J_0\!\big(\sqrt{-j}\,\sqrt2\,r/δ\big)$, and $R_{ac}/R_{dc}$ follows from the ratio of the Bessel functions; for a ≫ δ it tends to a/(2δ) + ¼.""",
    method="""Copper σ = 5.8×10⁷ S/m. Slab: 1 mm thick, surface current imposed, 2000 nodes, compare |J| and phase with the exponential. Wire: radius 0.5 mm, cylindrical FD (r J″ + J′ − jωμσ r J = 0) with
J(a) = 1, regular at r = 0; R_ac/R_dc = (total current)⁻¹-weighted power ratio; frequencies 1 kHz–100 MHz; Bessel reference.""",
)

MU0 = 4e-7 * pi; SIG = 5.8e7


def slab(f, thick=1e-3, n=2001):
    x = np.linspace(0, thick, n); h = x[1]; k2 = 1j * 2 * pi * f * MU0 * SIG
    A = np.zeros((n, n), complex); b = np.zeros(n, complex)
    A[0, 0] = 1; b[0] = 1
    for i in range(1, n - 1):
        A[i, i - 1] = A[i, i + 1] = 1 / h ** 2; A[i, i] = -2 / h ** 2 - k2
    A[-1, -1] = 1; A[-1, -2] = -1                   # zero-flux (symmetry) at the far side
    return x, np.linalg.solve(A, b)


def wire(f, a=0.5e-3, n=800):
    r = np.linspace(0, a, n); h = r[1]; k2 = 1j * 2 * pi * f * MU0 * SIG
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
    A = lil_matrix((n, n), dtype=complex); b = np.zeros(n, complex)
    A[0, 0] = -4 / h ** 2 - k2; A[0, 1] = 4 / h ** 2       # regularity at r = 0: ∇²J ≈ 4(J1 − J0)/h²
    for i in range(1, n - 1):
        A[i, i - 1] = 1 / h ** 2 - 1 / (2 * h * r[i]); A[i, i + 1] = 1 / h ** 2 + 1 / (2 * h * r[i]); A[i, i] = -2 / h ** 2 - k2
    A[-1, -1] = 1; b[-1] = 1
    J = spsolve(A.tocsr(), b)
    I = np.trapezoid(J * 2 * pi * r, r)
    P = np.trapezoid(np.abs(J) ** 2 * 2 * pi * r, r) / SIG
    Rac = P / abs(I) ** 2; Rdc = 1 / (SIG * pi * a * a)
    return r, J, Rac / Rdc


def bessel_ratio(f, a=0.5e-3):
    k = np.sqrt(-1j * 2 * pi * f * MU0 * SIG)
    x = np.linspace(0, a, 20000); J = jv(0, k * x) / jv(0, k * a)
    I = np.trapezoid(J * 2 * pi * x, x); P = np.trapezoid(np.abs(J) ** 2 * 2 * pi * x, x) / SIG
    return (P / abs(I) ** 2) * SIG * pi * a * a


def run(p):
    f = 1e6
    d = np.sqrt(2 / (2 * pi * f * MU0 * SIG))
    p.compare("Skin depth of copper at 1 MHz", 66e-6, d, "m", tol=2)
    x, J = slab(f)
    ana = np.exp(-(1 + 1j) * x / d)
    near = x < 5 * d
    p.compare("Slab: |J(x)| vs e^(−x/δ) within 5δ (max abs error)", 0, np.max(np.abs(np.abs(J[near]) - np.abs(ana[near]))), "", kind="abs", tol=1e-3)
    ph = np.unwrap(np.angle(J[near]))
    p.compare("Slab: phase lags by 1 rad per skin depth (slope × δ)", -1.0, np.polyfit(x[near] / d, ph, 1)[0], "rad/δ", tol=1)
    fs = np.logspace(3, 8, 11)
    rows = [(fq, wire(fq)[2], bessel_ratio(fq)) for fq in fs]
    worst = max(abs(a / b - 1) for _, a, b in rows)
    p.compare("Round wire R_ac/R_dc: finite differences vs Bessel solution (worst over 1 kHz–100 MHz)", 0, worst, "", kind="abs", tol=0.02)
    a = 0.5e-3; d100 = np.sqrt(2 / (2 * pi * 1e8 * MU0 * SIG))
    p.compare("100 MHz: R_ac/R_dc ≈ a/(2δ) + ¼ (thick-wire limit)", a / (2 * d100) + 0.25, rows[-1][1], "", tol=2)
    fig, ax = p.fig(1, 2, w=11)
    r, J, _ = wire(1e6)
    ax[0].plot(r * 1e3, np.abs(J), color=C_MEAS, label="|J| at 1 MHz (FD)")
    kk = np.sqrt(-1j * 2 * pi * 1e6 * MU0 * SIG); ax[0].plot(r * 1e3, np.abs(jv(0, kk * r) / jv(0, kk * a)), "--", color=C_PRED, label="Bessel J₀")
    style_axes(ax[0], "radius (mm)", "|J| / |J(a)|", "Current crowds to the surface")
    ax[1].loglog([r_[0] for r_ in rows], [r_[1] for r_ in rows], "o", color=C_MEAS, label="finite differences")
    ax[1].loglog([r_[0] for r_ in rows], [r_[2] for r_ in rows], "--", color=C_PRED, label="Bessel")
    style_axes(ax[1], "frequency (Hz)", "R_ac / R_dc", "0.5 mm copper wire")
    p.save(fig, "skin", "Current density across a copper wire at 1 MHz and the AC resistance ratio vs frequency.")
    p.discuss("""The diffusion equation reproduces the skin effect quantitatively: in a slab the current falls as e^{−x/δ} while its phase lags one radian per skin
depth (66 µm in copper at 1 MHz), and in a round wire the finite-difference profile coincides with the Bessel-function solution. The AC resistance
of a 1 mm copper wire is flat up to ~20 kHz, then rises as √f, approaching a/(2δ) + ¼ — about 19× its DC value at 100 MHz. This is why RF inductors
use silver plating or Litz wire and why PCB trace loss at GHz depends on surface roughness: only the outer few micrometres carry current.""")
# tol-convention: relative tolerances are in percent
