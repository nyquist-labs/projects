from eelab import *

META = dict(
    id="AM-193", title="How Maxwell's equations make a wave: a 2-D Yee simulation", level="H",
    tools="Own 2-D FDTD (TM_z: E_z, H_x, H_y on a Yee grid, PEC walls), discrete divergence of B monitored during the run, wavefront timing along the axis and the diagonal, Yee numerical-dispersion relation solved for the predicted anisotropy, 1/√r cylindrical spreading, discrete energy bookkeeping",
    summary="Start from nothing but the two curl equations on a staggered grid, launch a pulse, and check that what emerges is an electromagnetic wave "
            "obeying the other two Maxwell equations and the physics derived from them: ∇·B stays zero, the wave travels at c (with the grid's predictable anisotropy), amplitude falls as 1/√r, and energy is conserved.",
    problem="The four Maxwell equations are usually quoted, not watched. What does it take to see them produce light — and how do we know the simulation respects all four?",
    theory=r"""Faraday and Ampère–Maxwell (source-free): $\partial_t B=-\nabla\times E$, $\partial_t D=\nabla\times H$. Taking the divergence gives $\partial_t(\nabla\cdot B)=0$: if B starts divergence-free it stays so. Yee's staggered grid reproduces this identity exactly in
discrete form. Eliminating H gives the wave equation with speed $c=1/\sqrt{μ_0ε_0}$. In 2-D a line source radiates a cylindrical wave whose amplitude falls as $1/\sqrt r$. On the grid the phase velocity depends on direction:
$\left[\tfrac{1}{cΔt}\sin\tfrac{ωΔt}{2}\right]^2=\left[\tfrac1Δ\sin\tfrac{k_xΔ}{2}\right]^2+\left[\tfrac1Δ\sin\tfrac{k_yΔ}{2}\right]^2$ — waves along the axes are slower than along the diagonal.""",
    method="""400 × 400 cells, Δ = 1 mm, Courant number 0.5, PEC walls. Source: soft E_z Gaussian-modulated sinusoid at 30 GHz (10 cells per wavelength) at the centre. Arrival times of the envelope peak at 60 and 150 cells along x and along the diagonal. Discrete
div B = ∂ₓHₓ + ∂ᵧHᵧ on cell centres after every 20 steps. Energy after the source has switched off, in Yee's conserved form ½ε₀ΣEⁿ² + ½μ₀ΣHⁿ⁻½·Hⁿ⁺½.""",
)

C0 = 299792458.0; MU0 = 4e-7 * pi; EPS0 = 1 / (MU0 * C0 ** 2)


def signal_env(x):
    from scipy.signal import hilbert
    return np.abs(hilbert(x))


def k_of(omega, theta, d, dt):
    from scipy.optimize import brentq
    lhs = (np.sin(omega * dt / 2) / (C0 * dt)) ** 2; k0 = omega / C0
    return brentq(lambda q: (np.sin(q * np.cos(theta) * d / 2) / d) ** 2 + (np.sin(q * np.sin(theta) * d / 2) / d) ** 2 - lhs, 0.5 * k0, 1.5 * k0)


def run(p):
    n = 400; d = 1e-3; S = 0.5; dt = S * d / C0; f0 = 30e9
    Ez = np.zeros((n, n)); Hx = np.zeros((n - 1, n)); Hy = np.zeros((n, n - 1)); c = n // 2     # arrays indexed [y, x]
    probes = {"x60": (c, c + 60), "x150": (c, c + 150), "d60": (c + 42, c + 42), "d150": (c + 106, c + 106)}
    rec = {k: [] for k in probes}; divB = []; energy = []; steps = 1400
    t0, tw = 240 * dt, 80 * dt
    ch, ce = dt / (MU0 * d), dt / (EPS0 * d)
    for t in range(steps):
        keep = t > 700 and t % 10 == 0
        if keep:
            Hx0, Hy0 = Hx.copy(), Hy.copy()
        Hx -= ch * (Ez[1:, :] - Ez[:-1, :]); Hy += ch * (Ez[:, 1:] - Ez[:, :-1])
        if keep:                                                   # Yee's conserved energy: E at step n, H at n − ½ and n + ½
            energy.append(0.5 * EPS0 * np.sum(Ez ** 2) * d * d + 0.5 * MU0 * (np.sum(Hx0 * Hx) + np.sum(Hy0 * Hy)) * d * d)
        Ez[1:-1, 1:-1] += ce * ((Hy[1:-1, 1:] - Hy[1:-1, :-1]) - (Hx[1:, 1:-1] - Hx[:-1, 1:-1]))
        tt = t * dt; Ez[c, c] += np.exp(-((tt - t0) / tw) ** 2) * np.sin(2 * pi * f0 * tt)
        for k, (i, j) in probes.items():
            rec[k].append(Ez[i, j])
        if t % 20 == 0 and t > 0:
            div = (Hx[:, 1:] - Hx[:, :-1]) + (Hy[1:, :] - Hy[:-1, :])          # d·(∂x Hx + ∂y Hy) on cell centres
            divB.append(np.max(np.abs(div)) / max(np.max(np.abs(Hx)), np.max(np.abs(Hy)), 1e-300))
    p.compare("Gauss's law for magnetism: max |∇·B|·Δ / max |H| over the whole run (zero up to round-off)", 0.0, float(max(divB)), "", kind="abs", tol=1e-12)
    env = {k: signal_env(np.array(v)) for k, v in rec.items()}
    dist = {"x60": 60, "x150": 150, "d60": 42 * np.sqrt(2), "d150": 106 * np.sqrt(2)}
    win = {k: slice(0, int(t0 / dt + dist[k] / S * 1.08 + 3 * tw / dt)) for k in env}          # only the direct pulse, not later wall reflections
    tp = {k: np.argmax(env[k][win[k]]) * dt for k in env}
    v_ax = 90 * d / (tp["x150"] - tp["x60"]); v_dg = (106 - 42) * np.sqrt(2) * d / (tp["d150"] - tp["d60"])
    w0 = 2 * pi * f0; dw = 1e-3 * w0
    vg = {th: 2 * dw / (k_of(w0 + dw, th, d, dt) - k_of(w0 - dw, th, d, dt)) for th in (0.0, pi / 4)}
    vpp = {th: w0 / k_of(w0, th, d, dt) for th in (0.0, pi / 4)}
    p.compare("Pulse (group) speed along the grid axis vs Yee's dispersion relation", vg[0.0], v_ax, "m/s", tol=1)
    p.compare("Pulse speed along the diagonal vs Yee's dispersion relation", vg[pi / 4], v_dg, "m/s", tol=1)
    p.metric("Grid speed errors at 10 cells per wavelength — phase: axis / diagonal; group: axis / diagonal", f"{(vpp[0.0] / C0 - 1) * 100:.2f} % / {(vpp[pi / 4] / C0 - 1) * 100:.2f} %; {(vg[0.0] / C0 - 1) * 100:.2f} % / {(vg[pi / 4] / C0 - 1) * 100:.2f} %", "", "the continuum limit is exactly c in every direction")
    ratio = env["x60"][win["x60"]].max() / env["x150"][win["x150"]].max()
    p.compare("Cylindrical spreading: peak amplitude ratio at 60 and 150 cells = √(150/60)", np.sqrt(150 / 60), ratio, "", tol=3)
    en = np.array(energy)
    p.compare("Energy in the PEC box after the source has switched off: relative variation", 0.0, float((en.max() - en.min()) / en.mean()), "", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 2, w=11, h=4.6)
    m = np.abs(Ez).max() * 0.3; ax[0].imshow(Ez, cmap="RdBu_r", vmin=-m, vmax=m, origin="lower"); ax[0].grid(False)
    ax[0].set_title("E_z at the end: the wave has reflected off the PEC walls", loc="left", fontsize=10)
    tt = np.arange(steps) * dt * 1e9
    for k_, c_, lab in (("x60", C_MEAS, "axis, r = 60 cells"), ("x150", C_PRED, "axis, r = 150 cells"), ("d150", COLORS[2], "diagonal, r = 150 cells")):
        ax[1].plot(tt, env[k_], color=c_, label=lab)
    style_axes(ax[1], "time (ns)", "|E_z| envelope", "Arrival of the pulse")
    p.save(fig, "maxwell2d", "The E_z field at the end of the run and the pulse envelopes seen at three probes.")
    p.discuss(f"""Only the two curl equations are coded, yet the result behaves like light. The divergence of B, never computed during the update, stays at
{max(divB):.0e} of the field scale for the whole run — the staggered Yee grid makes 'div curl = 0' hold exactly, so Gauss's law for magnetism is
inherited rather than imposed. The pulse travels at c to within the grid's own dispersion: along the axis its envelope moves at {v_ax / C0:.4f} c and
along the diagonal at {v_dg / C0:.4f} c, both matching the group velocities predicted by Yee's discrete dispersion relation (at 10 cells per wavelength
the grid is a slightly anisotropic medium). The amplitude falls as 1/√r, the energy signature of a cylindrical wave, and once the source is off
the total field energy in the metal box stays constant to {(en.max() - en.min()) / en.mean() * 100:.2f} % while the wave bounces around. Maxwell's four equations
are in the simulation even though only two were written down.""")
# tol-convention: relative tolerances are in percent
