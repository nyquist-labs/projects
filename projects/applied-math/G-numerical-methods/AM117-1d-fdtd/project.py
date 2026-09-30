from eelab import *

META = dict(
    id="AM-117", title="1-D FDTD: Maxwell's equations on a Yee grid", level="M",
    tools="Yee staggered E/H grid, leapfrog time stepping, dielectric slab, simple Mur absorbing boundaries, reflection/transmission measurement, animation",
    summary="Discretise Maxwell's curl equations in one dimension, launch a Gaussian pulse at a dielectric slab, and measure the wave speed and the "
            "reflection and transmission coefficients against the Fresnel formulas.",
    problem="How do electromagnetic simulators actually turn Maxwell's equations into numbers?",
    theory=r"""$∂E_z/∂t = \frac1ε∂H_y/∂x$, $∂H_y/∂t = \frac1μ∂E_z/∂x$; Yee staggers E and H by half a cell in space and time, giving second-order accuracy and stability for Courant number S = cΔt/Δx ≤ 1 (exact at S = 1 in vacuum).
At a vacuum/dielectric interface with n = √ε_r: Γ = (1 − n)/(1 + n), T = 2/(1 + n); inside the slab the pulse travels at c/n. For ε_r = 4: Γ = −1/3, T = 2/3.""",
    method="""2000 cells, Δx = 1 mm, S = 0.5; Gaussian pulse (soft source); half-space of ε_r = 4 starting at cell 1200 (for Γ, T) and a slab for multiple reflections; probes before and after the interface.""",
)


def run_fdtd(eps_r_region, n=2000, S=0.5, steps=5000, src=300, probes=(600, 1500)):
    eps = np.ones(n); eps[eps_r_region] = 4.0
    E = np.zeros(n); H = np.zeros(n - 1)
    rec = {k: [] for k in probes}; frames = []
    cE = S / eps; cH = S
    e_left_old = e_right_old = 0.0
    for t in range(steps):
        H += cH * (E[1:] - E[:-1])
        e1_old, en_old = E[1], E[-2]
        E[1:-1] += cE[1:-1] * (H[1:] - H[:-1])
        E[src] += np.exp(-((t - 150) / 50.0) ** 2)
        E[0] = e1_old + (S - 1) / (S + 1) * (E[1] - E[0])
        E[-1] = en_old + (S / 2 - 1) / (S / 2 + 1) * (E[-2] - E[-1])
        for k in probes:
            rec[k].append(E[k])
        if t % 50 == 0:
            frames.append(E.copy())
    return {k: np.array(v) for k, v in rec.items()}, frames


def run(p):
    n = 2000
    rec, frames = run_fdtd(slice(1200, n))
    e1, e2 = rec[600], rec[1500]
    t = np.arange(len(e1))
    inc = e1[: 1500].max()
    win = slice(2400, 4200)                                   # reflection returns after (900 + 600) cells at S = 0.5 → step ≈ 3060
    refl = e1[win][np.argmax(np.abs(e1[win]))]
    trans = e2.max()
    p.compare("Reflection coefficient vacuum → ε_r = 4: (1 − n)/(1 + n)", -1 / 3, refl / inc, "", tol=1)
    p.compare("Transmission coefficient 2/(1 + n)", 2 / 3, trans / inc, "", tol=1)
    rec2, _ = run_fdtd(slice(n, n), probes=(600, 1000))
    dt_cells = (np.argmax(rec2[1000]) - np.argmax(rec2[600])) * 0.5
    p.compare("Vacuum propagation: cells travelled per step = Courant number (speed = c)", 400, dt_cells, "cells", tol=0.5)
    k1 = np.argmax(e2); rec3, _ = run_fdtd(slice(1200, n), probes=(1300, 1700))
    speed = 400 / ((np.argmax(rec3[1700]) - np.argmax(rec3[1300])) * 0.5)
    p.compare("Speed in the dielectric = c/n", 0.5, speed, "c", tol=1)
    fig, ax = p.fig(1, 2, w=11)
    x = np.arange(n)
    for k, fr in enumerate(frames[8::14][:6]):
        ax[0].plot(x, fr + 1.2 * k, color=COLORS[k % 8], lw=.8)
    ax[0].axvspan(1200, n, color=COLORS[7], alpha=.2)
    style_axes(ax[0], "cell", "E_z (offset per snapshot)", "Pulse hits an ε_r = 4 half-space", legend=False)
    ax[1].plot(t, e1, color=C_MEAS, label="probe before interface"); ax[1].plot(t, e2, color=C_PRED, label="probe inside dielectric")
    style_axes(ax[1], "time step", "E_z", "Incident, reflected (−⅓) and transmitted (⅔)")
    p.save(fig, "fdtd1d", "Snapshots of the pulse at a dielectric interface and the probe signals.")
    from matplotlib import animation
    import matplotlib.pyplot as plt
    fa, aa = plt.subplots(figsize=(6, 2.6)); ln, = aa.plot(x, frames[0], color=C_MEAS); aa.axvspan(1200, n, color=COLORS[7], alpha=.2); aa.set_ylim(-0.8, 1.1)
    anim = animation.FuncAnimation(fa, lambda k: ln.set_ydata(frames[k]) or (ln,), frames=len(frames))
    anim.save(p.dir / "figures" / "fdtd1d.gif", writer=animation.PillowWriter(fps=15), dpi=60); plt.close(fa)
    p.files.append(("figures/fdtd1d.gif", "animation of the 1-D FDTD run"))
    p.discuss("""Twenty lines of leapfrog updates reproduce the Fresnel coefficients: a pulse hitting a medium with ε_r = 4 is reflected with −1/3 (inverted,
because the medium is denser) and transmitted with +2/3, and it travels at exactly half the vacuum speed inside. In vacuum the pulse advances one
Courant number of cells per step — the numerical speed of light equals c to within 0.5 % here — while in the dielectric the effective Courant number
halves and slight numerical dispersion appears. The simple first-order Mur boundaries absorb the outgoing pulses in 1-D; in two dimensions
they reflect at oblique incidence, which AM-118 addresses.""")
# tol-convention: relative tolerances are in percent
