from eelab import *
from scipy.special import erfc

META = dict(
    id="AM-051", title="Heat equation: temperature rise of a component", level="M",
    tools="Explicit (FTCS) and implicit (Crank–Nicolson) finite differences for the 1-D heat equation, stability limit r = αΔt/Δx² ≤ ½, analytic semi-infinite solution, lumped thermal RC",
    summary="Solve the heat equation for a heat pulse entering a thick copper bar and for a power resistor on a finite heat-sink bar, compare "
            "with the erfc solution and the lumped thermal-RC model, and measure the stability limit of the explicit scheme.",
    problem="A component switches on: how fast does its temperature rise, and when is a single 'thermal time constant' good enough?",
    theory=r"""$∂T/∂t=α∂^2T/∂x^2$. Constant surface flux q into a semi-infinite solid: $ΔT_s(t)=\frac{2q}{k}\sqrt{\frac{αt}{π}}$ (√t rise, no time constant). A finite bar cooled at its far end tends to
$ΔT=qL/k$ with a slowest time constant $τ_1=4L^2/(π^2α)$ — the lumped RC model captures only this first mode. FTCS is stable iff r = αΔt/Δx² ≤ ½; Crank–Nicolson is unconditionally stable.""",
    method="""Copper: k = 400 W/mK, α = 1.17×10⁻⁴ m²/s. Case 1: q = 10⁶ W/m² into a 0.2 m bar for 1 s (effectively semi-infinite). Case 2: 5 cm bar with the far end held at ambient, same flux, 60 s.
FTCS run at r = 0.49 and 0.51; Crank–Nicolson at r = 10.""",
)


def solve(Lbar, q, T, dx, r, k=400.0, alpha=1.17e-4, method="ftcs", far="fixed"):
    n = int(Lbar / dx) + 1; dt = r * dx * dx / alpha; steps = int(T / dt)
    u = np.zeros(n); hist = []
    if method == "cn":
        from scipy.sparse import diags
        from scipy.sparse.linalg import splu
        main = np.full(n, 1 + r); off = np.full(n - 1, -r / 2)
        A = diags([off, main, off], [-1, 0, 1]).tolil()
        A[0, 1] = -r                                   # flux (Neumann) boundary with ghost node
        if far == "fixed":
            A[-1, :] = 0; A[-1, -1] = 1
        lu = splu(A.tocsc())
    for s in range(steps):
        if method == "ftcs":
            un = u.copy()
            un[1:-1] = u[1:-1] + r * (u[2:] - 2 * u[1:-1] + u[:-2])
            un[0] = u[0] + r * (2 * u[1] - 2 * u[0]) + 2 * r * dx * q / k
            un[-1] = 0 if far == "fixed" else u[-1]
            u = un
        else:
            rhs = u.copy()
            rhs[1:-1] = u[1:-1] + r / 2 * (u[2:] - 2 * u[1:-1] + u[:-2])
            rhs[0] = u[0] + r * (u[1] - u[0]) + 2 * r * dx * q / k
            rhs[-1] = 0
            u = lu.solve(rhs)
        hist.append(u[0])
        if not np.isfinite(u[0]) or abs(u[0]) > 1e9:
            break
    return np.arange(1, len(hist) + 1) * dt, np.array(hist)


def run(p):
    k, al, q = 400.0, 1.17e-4, 1e6
    t, Ts = solve(0.2, q, 1.0, 1e-3, 0.4)
    ana = 2 * q / k * np.sqrt(al * t / pi)
    p.compare("Semi-infinite bar: surface temperature rise at 1 s, FTCS vs 2q/k·√(αt/π)", ana[-1], Ts[-1], "K", tol=1)
    p.compare("Rise ∝ √t (log-log slope)", 0.5, np.polyfit(np.log(t[len(t) // 10:]), np.log(Ts[len(t) // 10:]), 1)[0], "", kind="abs", tol=0.02)
    Lb = 0.05
    t2, T2 = solve(Lb, q, 60.0, 0.5e-3, 0.4)
    p.compare("Finite bar (far end at ambient): steady rise qL/k", q * Lb / k, T2[-1], "K", tol=1)
    tau1 = 4 * Lb * Lb / (pi * pi * al)
    tail = t2 > 2 * tau1
    rate = np.polyfit(t2[tail], np.log(q * Lb / k - T2[tail]), 1)[0]
    p.compare("Slowest thermal time constant τ1 = 4L²/(π²α)", tau1, -1 / rate, "s", tol=2)
    _, a = solve(Lb, q, 2.0, 0.5e-3, 0.49); _, b = solve(Lb, q, 2.0, 0.5e-3, 0.51)
    p.compare("FTCS at r = 0.49 stays bounded; at r = 0.51 it blows up (1 = as predicted)", 1, int(np.isfinite(a).all() and abs(a[-1]) < 1e4 and (not np.isfinite(b[-1]) or abs(b).max() > 1e4)), "", kind="abs")
    t3, T3 = solve(Lb, q, 60.0, 0.5e-3, 10.0, method="cn")
    p.compare("Crank–Nicolson at r = 10 (20× the FTCS limit): final value", q * Lb / k, T3[-1], "K", tol=1)
    lump = q * Lb / k * (1 - np.exp(-t2 / tau1))
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, Ts, color=C_MEAS, lw=3, alpha=.5, label="FTCS"); ax[0].plot(t, ana, "--", color=C_PRED, label="2q/k·√(αt/π)")
    style_axes(ax[0], "t (s)", "surface ΔT (K)", "Semi-infinite: √t, no time constant")
    ax[1].plot(t2, T2, color=C_MEAS, label="PDE (FTCS)"); ax[1].plot(t3, T3, ":", color=COLORS[2], label="Crank–Nicolson r = 10"); ax[1].plot(t2, lump, "--", color=C_PRED, label="lumped RC (first mode)")
    style_axes(ax[1], "t (s)", "surface ΔT (K)", "Finite bar: lumped model misses the early √t rise")
    p.save(fig, "heat", "Surface temperature rise for a semi-infinite and a finite copper bar, with analytic and lumped models.")
    p.discuss(f"""The finite-difference solution reproduces the semi-infinite erfc result (a √t rise with no characteristic time) to under 1 %, and on the finite
bar it settles at qL/k with the slowest mode's time constant τ1 = 4L²/(π²α) = {tau1:.1f} s. The single-RC 'thermal time constant' model gets the
end point and the late approach right but badly underestimates the early rise, where the heat has not yet felt the far boundary — exactly the
regime of short power pulses, where datasheets give a transient thermal impedance curve instead of one R and C. The explicit scheme's r ≤ ½ limit
is sharp (bounded at 0.49, exploding at 0.51); Crank–Nicolson runs happily at r = 10.""")
# tol-convention: relative tolerances are in percent
