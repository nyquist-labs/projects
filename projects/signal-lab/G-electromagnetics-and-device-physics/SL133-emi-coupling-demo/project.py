from eelab import *
from eelab.circuit import Circuit
from eelab.laplace import solve, energy

META = dict(
    id="SL-133", title="PCB crosstalk vs trace spacing", level="M",
    tools="2-D Laplace solver for coupled microstrip capacitances + eelab mini-SPICE coupled-line ladder (transient)",
    summary="Extract mutual capacitance and inductance of two parallel microstrips for several spacings, predict near-end "
            "crosstalk K_NE = ¼(C_m/C + L_m/L), and verify with a transient simulation of a 1 ns edge on a 20 cm pair.",
    problem="Two neighbouring traces talk to each other. How much, and how much does spacing them out help?",
    theory=r"""For weakly coupled lines the backward (near-end) crosstalk saturates at $K_{NE}=\frac14\left(\frac{C_m}{C}+\frac{L_m}{L}\right)$ once the line delay exceeds
half the rise time. Mutual terms fall roughly as $1/(1+(s/h)^2)$, so doubling the spacing cuts crosstalk ~4× (the '3W rule').""",
    method="""Two 0.3 mm traces, h = 0.2 mm, ε_r = 4.4, spacings 0.15–1.2 mm. Capacitance matrix from two Laplace solves; inductance from the air-filled
capacitance matrix (L = μ₀ε₀ C₀⁻¹). Transient: 40-section LC ladder with coupling capacitors and K-coupled inductors, 50 Ω terminations,
1 V / 1 ns ramp on the aggressor.""",
)


def cap_matrix(s, w=0.3e-3, h=0.2e-3, er=4.4, dx=0.02e-3):
    W, H = 6e-3, 3e-3
    nx, ny = int(W / dx), int(H / dx)
    js = int(round(h / dx))
    xc = nx // 2
    hw = int(round(w / 2 / dx)); hs = int(round(s / 2 / dx))
    l1 = (xc - hs - 2 * hw, xc - hs); l2 = (xc + hs, xc + hs + 2 * hw)
    C = np.zeros((2, 2))
    for epsr in (er, 1.0):
        eps = np.ones((ny, nx)); eps[:js, :] = epsr
        M = np.zeros((2, 2))
        for k, (a, b) in enumerate((l1, l2)):
            fixed = np.zeros((ny, nx), bool); V0 = np.zeros((ny, nx))
            fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
            for (c0, c1) in (l1, l2):
                fixed[js, c0:c1 + 1] = True
            V0[js, a:b + 1] = 1.0
            V = solve(fixed, V0, eps)
            # charge on each trace from Gauss contours
            for m, (c0, c1) in enumerate((l1, l2)):
                j0, j1, i0, i1 = js - 2, js + 2, c0 - 2, c1 + 2
                Q = 0.0
                Q += np.sum(eps[j0, i0:i1 + 1] * (V[j0 + 1, i0:i1 + 1] - V[j0, i0:i1 + 1]))
                Q += np.sum(1.0 * (V[j1 - 1, i0:i1 + 1] - V[j1, i0:i1 + 1]))
                for j in range(j0, j1):
                    e = eps[j, i0]
                    Q += e * (V[j, i0 + 1] - V[j, i0]) + e * (V[j, i1 - 1] - V[j, i1])
                M[m, k] = 8.854e-12 * Q
        if epsr == er:
            C = M.copy()
        else:
            C0 = M.copy()
    Lm = 4e-7 * pi * 8.854e-12 * np.linalg.inv(C0)
    return C, Lm


def xtalk_sim(C, L, length=0.2, nsec=40, tr=1e-9):
    ck = Circuit("coupled")
    ck.V("s", "src", "0", wave=lambda t: min(max(t / tr, 0), 1.0))
    ck.R("s", "src", "a0", 50); ck.R("vn", "v0", "0", 50)
    dz = length / nsec
    c11, cm = C[0, 0] + C[0, 1], -C[0, 1]
    for k in range(nsec):
        ck.L(f"a{k}", f"a{k}", f"a{k+1}", L[0, 0] * dz); ck.L(f"v{k}", f"v{k}", f"v{k+1}", L[1, 1] * dz)
        ck.K(f"a{k}", f"v{k}", L[0, 1] / np.sqrt(L[0, 0] * L[1, 1]))
        ck.C(f"a{k}", f"a{k+1}", "0", c11 * dz); ck.C(f"v{k}", f"v{k+1}", "0", c11 * dz); ck.C(f"m{k}", f"a{k+1}", f"v{k+1}", cm * dz)
    ck.R("la", f"a{nsec}", "0", 50); ck.R("lv", f"v{nsec}", "0", 50)
    tr_ = ck.tran(6e-9, 5e-12, method="trap", uic=True)
    return tr_.t, tr_.v("a0"), tr_.v("v0")


def run(p):
    spacings = [0.15e-3, 0.3e-3, 0.6e-3, 1.2e-3]
    rows = []
    for s in spacings:
        C, L = cap_matrix(s)
        Cself = C[0, 0]; Cm = -C[0, 1]
        K = 0.25 * (Cm / Cself + L[0, 1] / L[0, 0])
        t, va, vn = xtalk_sim(C, L)
        vin = va.max()
        next_ = np.max(np.abs(vn)) / vin
        rows.append((s, K, next_, Cm / Cself, L[0, 1] / L[0, 0]))
        p.compare(f"s = {s*1e3:.2f} mm: near-end crosstalk (¼(Cm/C + Lm/L))", K, next_, "", tol=15)
        if s == 0.3e-3:
            wave = (t, va, vn)
    s_, K_, N_, cc, ll = map(np.array, zip(*rows))
    p.metric("Crosstalk reduction from 0.3 → 0.6 mm spacing", N_[1] / N_[2], "×")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(s_ * 1e3, K_ * 100, "--", color=C_PRED, label="¼(Cm/C + Lm/L)")
    ax[0].semilogy(s_ * 1e3, N_ * 100, "o", color=C_MEAS, ms=7, label="transient simulation")
    style_axes(ax[0], "edge-to-edge spacing (mm)", "near-end crosstalk (%)", "Crosstalk vs spacing (h = 0.2 mm)")
    t, va, vn = wave
    ax[1].plot(t * 1e9, va, color=COLORS[1], label="aggressor near end")
    ax[1].plot(t * 1e9, vn * 10, color=C_MEAS, label="victim near end × 10")
    style_axes(ax[1], "time (ns)", "V", "Near-end crosstalk plateau (s = 0.3 mm)")
    p.save(fig, "crosstalk", "The victim's near end sees a plateau lasting the round-trip delay; its height falls quickly with spacing.")
    import pandas as pd
    p.csv_df("crosstalk", pd.DataFrame(rows, columns=["spacing_m", "K_pred", "NEXT_sim", "Cm_over_C", "Lm_over_L"]))
    p.discuss("""The field-solver coupling coefficients predict the simulated near-end crosstalk plateau within the ladder model's
discretisation error, and both fall quickly with spacing: going from one trace width to two widths apart cuts crosstalk
by several times — the origin of the '3W' layout rule. Moving the traces closer to the ground plane (smaller h) has the
same effect, because the field then terminates on the plane instead of the neighbour.""")
