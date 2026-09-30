from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-074", title="Chaining filter stages with ABCD matrices", level="M",
    tools="ABCD (transmission) matrices for series/shunt elements and transmission-line sections, cascade by matrix multiplication, comparison with full-circuit AC simulation",
    summary="Model a multi-section LC filter and a transmission-line matching section as products of 2×2 ABCD matrices, compute their insertion "
            "loss by one matrix product per frequency, and verify against simulating the whole circuit.",
    problem="Cascaded two-ports are easy to analyse if each is a matrix. Why does multiplication work, and how accurate is it?",
    theory=r"""$\begin{bmatrix}V_1\\I_1\end{bmatrix}=\begin{bmatrix}A&B\\C&D\end{bmatrix}\begin{bmatrix}V_2\\I_2\end{bmatrix}$ with output current leaving port 2, so cascades multiply. Series Z: [[1, Z],[0, 1]]; shunt Y: [[1, 0],[Y, 1]]; line of length ℓ:
[[cos βℓ, jZ0 sin βℓ], [j sin βℓ / Z0, cos βℓ]]. With source and load R0: $S_{21}=\frac{2}{A+B/R_0+CR_0+D}$. Reciprocity ⇔ AD − BC = 1. A quarter-wave line transforms R_L into Z0²/R_L.""",
    method="""5th-order Chebyshev 0.5 dB low-pass (50 Ω, 100 MHz) as 5 ABCD factors; same circuit in the MNA simulator with 50 Ω source/load; quarter-wave 70.7 Ω line matching 100 Ω to 50 Ω (as an LC-ladder line
approximation in the simulator with 50 sections).""",
)

G_CHEB = [1.7058, 1.2296, 2.5408, 1.2296, 1.7058]      # 0.5 dB ripple, n = 5 prototype values


def ser(Z):
    return np.array([[1, Z], [0, 1]], complex)


def sh(Y):
    return np.array([[1, 0], [Y, 1]], complex)


def s21(M, R0=50.0):
    A, B, C, D = M.ravel()
    return 2 / (A + B / R0 + C * R0 + D)


def run(p):
    R0, fc = 50.0, 100e6; wc = 2 * pi * fc
    L = [g * R0 / wc for g in G_CHEB[1::2]]; C = [g / (R0 * wc) for g in G_CHEB[0::2]]
    f = np.linspace(1e6, 250e6, 600); w = 2 * pi * f
    H = []
    for wk in w:
        M = sh(1j * wk * C[0]) @ ser(1j * wk * L[0]) @ sh(1j * wk * C[1]) @ ser(1j * wk * L[1]) @ sh(1j * wk * C[2])
        H.append((s21(M), np.linalg.det(M)))
    S21 = np.array([h[0] for h in H]); dets = np.array([h[1] for h in H])
    ck = Circuit("cheb"); ck.V("s", "src", "0", ac=2.0); ck.R("s", "src", "n1", R0)
    ck.C("1", "n1", "0", C[0]); ck.L("1", "n1", "n2", L[0]); ck.C("2", "n2", "0", C[1]); ck.L("2", "n2", "n3", L[1]); ck.C("3", "n3", "0", C[2]); ck.R("l", "n3", "0", R0)
    Vo = ck.ac(f).v("n3")
    p.compare("Cascade of ABCD matrices vs full-circuit simulation, max |ΔS21|", 0, np.max(np.abs(S21 - Vo)), "", kind="abs", tol=1e-9)
    p.compare("Reciprocity: det(ABCD) = AD − BC = 1 (worst)", 0, np.max(np.abs(dets - 1)), "", kind="abs", tol=1e-9)
    pb = f <= fc
    p.compare("Passband ripple of the 0.5 dB Chebyshev", 0.5, db(np.abs(S21[pb])).max() - db(np.abs(S21[pb])).min(), "dB", kind="abs", tol=0.02)
    RL, Z0 = 100.0, np.sqrt(50.0 * 100.0); f0 = 1e9
    fl = np.linspace(0.3e9, 1.7e9, 400)
    gam = []
    for fk in fl:
        bl = pi / 2 * fk / f0
        M = np.array([[np.cos(bl), 1j * Z0 * np.sin(bl)], [1j * np.sin(bl) / Z0, np.cos(bl)]])
        Zin = (M[0, 0] * RL + M[0, 1]) / (M[1, 0] * RL + M[1, 1])
        gam.append((Zin - 50) / (Zin + 50))
    gam = np.array(gam)
    p.compare("Quarter-wave transformer (70.7 Ω line): |Γ| at 1 GHz", 0, abs(gam[np.argmin(abs(fl - f0))]), "", kind="abs", tol=1e-3)
    bw = fl[np.abs(gam) < 0.1]
    p.metric("Quarter-wave match: bandwidth for |Γ| < 0.1", (bw.max() - bw.min()) / f0 * 100, "% of f0")
    Nsec = 50; Lsec = Z0 * (1 / (4 * f0)) / Nsec; Csec = (1 / (4 * f0)) / (Z0 * Nsec)
    ck = Circuit("qw"); ck.V("s", "src", "0", ac=2.0); ck.R("s", "src", "m0", 50.0)
    for k in range(Nsec):
        ck.L(f"{k}", f"m{k}", f"m{k + 1}", Lsec); ck.C(f"{k}", f"m{k + 1}", "0", Csec)
    ck.R("l", f"m{Nsec}", "0", RL)
    ac = ck.ac(fl)
    Zin_sim = ac.v("m0") / ((ac.v("src") - ac.v("m0")) / 50.0)
    gs = (Zin_sim - 50) / (Zin_sim + 50)
    p.compare("Line built from 50 LC sections: |Γ| vs ideal line (worst over 0.3–1.7 GHz)", 0, np.max(np.abs(np.abs(gs) - np.abs(gam))), "", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(f / 1e6, db(np.abs(S21)), color=C_MEAS, lw=3, alpha=.5, label="ABCD cascade"); ax[0].plot(f / 1e6, db(np.abs(Vo)), "--", color=C_PRED, label="circuit simulation")
    ax[0].set_ylim(-60, 2)
    style_axes(ax[0], "frequency (MHz)", "|S21| (dB)", "5th-order 0.5 dB Chebyshev")
    ax[1].plot(fl / 1e9, np.abs(gam), color=C_MEAS, label="ideal line (ABCD)"); ax[1].plot(fl / 1e9, np.abs(gs), "--", color=C_PRED, label="50 LC sections (sim)")
    style_axes(ax[1], "frequency (GHz)", "|Γ_in|", "Quarter-wave transformer 100 Ω → 50 Ω")
    p.save(fig, "abcd", "ABCD cascade vs full simulation for a Chebyshev filter, and a quarter-wave matching section.")
    p.discuss("""Multiplying five 2×2 matrices per frequency reproduces the full nodal simulation of the Chebyshev filter to machine precision, with the designed
0.5 dB ripple, and every product has determinant 1 — the algebraic signature of reciprocity. The same formalism handles distributed elements: a
quarter-wave 70.7 Ω line matches 100 Ω to 50 Ω perfectly at 1 GHz with the characteristic narrow bandwidth (Γ < 0.1 over roughly ±20 %), and a
line approximated by 50 LC sections agrees with the ideal line until the sections become electrically long. ABCD matrices are why RF CAD
can optimise ladders and line cascades so quickly: each evaluation is a handful of 2×2 multiplications.""")
# tol-convention: relative tolerances are in percent
