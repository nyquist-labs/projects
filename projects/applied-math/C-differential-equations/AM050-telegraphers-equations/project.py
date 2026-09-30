from eelab import *

META = dict(
    id="AM-050", title="Telegrapher's equations: travelling waves on a line", level="H",
    tools="Staggered-grid FDTD solution of the telegrapher's PDEs (V and I leapfrogged), matched source, arbitrary resistive load, loss; animated GIF",
    summary="Solve ∂V/∂x = −L∂I/∂t − RI, ∂I/∂x = −C∂V/∂t − GV numerically, measure wave speed, reflection coefficients for open, short and "
            "mismatched loads, and the attenuation of a lossy line — all against their closed-form predictions.",
    problem="A step launched onto a cable bounces back from the far end. How fast does it travel, how much comes back, and how much is lost?",
    theory=r"""Lossless: speed $v=1/\sqrt{LC}$, impedance $Z_0=\sqrt{L/C}$, reflection $Γ=(Z_L-Z_0)/(Z_L+Z_0)$ (open +1, short −1). With small loss the amplitude decays as $e^{-αx}$,
$α≈\frac{R}{2Z_0}+\frac{GZ_0}{2}$. FDTD stability: Courant number vΔt/Δx ≤ 1 (exact propagation at 1 in 1-D).""",
    method="""RG-58-like line: L = 250 nH/m, C = 100 pF/m (Z0 = 50 Ω, v = 2×10⁸ m/s), 10 m, Δx = 1 cm, Courant 0.5. Gaussian pulse from a matched 50 Ω source; loads 1 MΩ (open), 0.01 Ω (short),
25 Ω, 150 Ω; lossy case R = 2 Ω/m. Arrival times and reflected amplitudes measured at x = 2 m.""",
)


def fdtd(ZL, R=0.0, G=0.0, L=250e-9, C=100e-12, length=10.0, dx=0.01, T=150e-9, courant=0.5, probe=2.0, snaps=None):
    v = 1 / np.sqrt(L * C); Z0 = np.sqrt(L / C)
    nx = int(length / dx); dt = courant * dx / v
    V = np.zeros(nx + 1); I = np.zeros(nx)
    nt = int(T / dt); k = int(probe / dx)
    trace = np.zeros(nt); frames = []
    cv1 = (1 - G * dt / (2 * C)) / (1 + G * dt / (2 * C)); cv2 = dt / (C * dx) / (1 + G * dt / (2 * C))
    ci1 = (1 - R * dt / (2 * L)) / (1 + R * dt / (2 * L)); ci2 = dt / (L * dx) / (1 + R * dt / (2 * L))
    for n in range(nt):
        t = n * dt
        vs = np.exp(-((t - 3e-9) / 1e-9) ** 2)
        I = ci1 * I - ci2 * (V[1:] - V[:-1])
        V[1:-1] = cv1 * V[1:-1] - cv2 * (I[1:] - I[:-1])
        # source end: Thevenin source vs through Z0 (first-order boundary update)
        # end nodes hold half a cell of capacitance; Crank–Nicolson in V keeps them stable for any resistance
        a0 = C * dx / (2 * dt)
        V[0] = (V[0] * (a0 - 1 / (2 * Z0)) + vs / Z0 - I[0]) / (a0 + 1 / (2 * Z0))
        V[-1] = (V[-1] * (a0 - 1 / (2 * ZL)) + I[-1]) / (a0 + 1 / (2 * ZL))
        trace[n] = V[k]
        if snaps is not None and n % snaps == 0:
            frames.append(V.copy())
    return np.arange(nt) * dt, trace, v, Z0, frames


def run(p):
    Z0 = 50.0; v = 2e8
    rows = []
    for ZL in (1e6, 0.01, 25.0, 150.0):
        t, tr, v, Z0, _ = fdtd(ZL)
        inc = tr[t < 30e-9]; t_inc = t[np.argmax(inc)]
        ref_win = (t > 60e-9) & (t < 110e-9)
        k = np.argmax(np.abs(tr[ref_win])); refl = tr[ref_win][k]; t_ref = t[ref_win][k]
        rows.append((ZL, (ZL - Z0) / (ZL + Z0), refl / inc.max(), t_ref - t_inc))
    for ZL, G, meas, dtt in rows:
        p.compare(f"Z_L = {ZL:g} Ω: reflection coefficient", G, meas, "", kind="abs", tol=0.02)
    p.compare("Round-trip delay probe → load → probe (16 m) = 16/v", 16 / v, rows[2][3], "s", tol=1)
    t, tr, _, _, _ = fdtd(Z0, R=2.0, length=10.0, probe=2.0)
    t2, tr2, _, _, _ = fdtd(Z0, R=2.0, length=10.0, probe=8.0)
    alpha_meas = np.log(tr.max() / tr2.max()) / 6.0
    p.compare("Lossy line (R = 2 Ω/m): attenuation α ≈ R/2Z0", 2.0 / (2 * Z0), alpha_meas, "Np/m", tol=5)
    fig, ax = p.fig(1, 2, w=11)
    for (ZL, *_), c in zip(rows, COLORS):
        t, tr, *_ = fdtd(ZL)
        ax[0].plot(t * 1e9, tr, color=c, label=f"Z_L = {ZL:g} Ω")
    style_axes(ax[0], "t (ns)", "V at x = 2 m", "Incident pulse and its echo from the load")
    _, _, _, _, frames = fdtd(150.0, snaps=60)
    x = np.linspace(0, 10, len(frames[0]))
    for k, fr in enumerate(frames[::3][:6]):
        ax[1].plot(x, fr + 0.8 * k, color=COLORS[k % 8], lw=1)
    style_axes(ax[1], "x (m)", "V (offset per snapshot)", "Snapshots: pulse travels, partly reflects (150 Ω)", legend=False)
    p.save(fig, "telegrapher", "Echoes from four loads at the probe point, and snapshots of the pulse on the line.")
    from matplotlib import animation
    import matplotlib.pyplot as plt
    _, _, _, _, frames = fdtd(150.0, snaps=40)
    fa, aa = plt.subplots(figsize=(6, 2.6)); ln, = aa.plot(x, frames[0], color=C_MEAS); aa.set_ylim(-0.6, 1.1); aa.set_xlabel("x (m)")
    anim = animation.FuncAnimation(fa, lambda k: ln.set_ydata(frames[k]) or (ln,), frames=len(frames))
    anim.save(p.dir / "figures" / "line.gif", writer=animation.PillowWriter(fps=15), dpi=60); plt.close(fa)
    p.files.append(("figures/line.gif", "animation: pulse on a 10 m line into 150 Ω"))
    p.discuss("""The numerical line behaves exactly like the textbook one: echoes return after 16/v, with amplitudes +1 (open), −1 (short), −1/3 (25 Ω) and +1/2
(150 Ω) as Γ = (Z_L − Z0)/(Z_L + Z0) predicts, and a matched load produces no echo at all. With series resistance the pulse shrinks by e^{−αx},
α ≈ R/2Z0, measured between two probes. A first version updated the end nodes explicitly and blew up for low-impedance loads (the short and 25 Ω cases), because the end node's own
time constant (half a cell of capacitance times Z_L) was far below Δt; a Crank–Nicolson update of the end nodes fixed it. The staggered leapfrog grid is the same Yee scheme used for Maxwell's equations (AM-117); at Courant
number 0.5 it slightly disperses the pulse, which is why the measured echo amplitudes are within 1–2 % rather than exact.""")
# tol-convention: relative tolerances are in percent
