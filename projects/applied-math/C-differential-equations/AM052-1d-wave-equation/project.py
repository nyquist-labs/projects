from eelab import *

META = dict(
    id="AM-052", title="1-D wave equation: reflecting and absorbing boundaries", level="M",
    tools="Second-order leapfrog finite differences, Dirichlet/Neumann boundaries, first-order Mur absorbing boundary, CFL stability, numerical dispersion",
    summary="Solve u_tt = c²u_xx for a pulse hitting fixed, free and absorbing ends; measure reflection coefficients, show that the scheme is "
            "exact at Courant number 1 and dispersive below it, and find the CFL stability limit.",
    problem="Every wave simulation needs edges. How do you make a boundary that does not reflect?",
    theory=r"""Fixed end (u = 0): reflection −1; free end (u_x = 0): +1. Mur's first-order absorbing condition $u_t + c u_x = 0$ is exact for normally incident waves in 1-D, so reflection → O(discretisation)
— and exactly zero at Courant number S = cΔt/Δx = 1. The leapfrog scheme is stable iff S ≤ 1 and has no dispersion at S = 1 (the 'magic time step'); below 1 short wavelengths lag.""",
    method="""Domain 0–1, c = 1, 1000 cells. Gaussian pulse travelling right; reflected amplitude measured at x = 0.5 after interaction with the right boundary. S = 1.0, 0.5 for the boundaries;
S = 1.001 for the stability test; pulse shape after travelling 5 units for dispersion.""",
)


def simulate(bc, S=0.5, n=1000, T=1.6, width=0.02):
    dx = 1.0 / n; dt = S * dx; x = np.arange(n + 1) * dx
    u0 = np.exp(-((x - 0.3) / width) ** 2)
    u_prev = np.exp(-((x - 0.3 + dt) / width) ** 2)          # right-moving pulse
    u = u0.copy(); probe = []; steps = int(T / dt)
    for _ in range(steps):
        un = np.empty_like(u)
        un[1:-1] = 2 * u[1:-1] - u_prev[1:-1] + S * S * (u[2:] - 2 * u[1:-1] + u[:-2])
        un[0] = 0
        if bc == "fixed":
            un[-1] = 0
        elif bc == "free":
            un[-1] = 2 * u[-1] - u_prev[-1] + S * S * 2 * (u[-2] - u[-1])
        else:  # Mur
            un[-1] = u[-2] + (S - 1) / (S + 1) * (un[-2] - u[-1])
        u_prev, u = u, un
        probe.append(u[n // 2])
        if not np.isfinite(u).all() or np.abs(u).max() > 1e6:
            return np.array(probe), u, False
    return np.array(probe), u, True


def run(p):
    rows = {}
    for bc, pred in (("fixed", -1.0), ("free", 1.0), ("absorbing", 0.0)):
        for S in (1.0, 0.5):
            pr, _, _ = simulate(bc, S)
            dt = S / 1000; t = np.arange(1, len(pr) + 1) * dt
            inc = pr[t < 0.5].max(); ref = pr[(t > 0.8) & (t < 1.4)]
            val = ref[np.argmax(np.abs(ref))]
            rows[(bc, S)] = val / inc
    for (bc, S), r in rows.items():
        pred = {"fixed": -1, "free": 1, "absorbing": 0}[bc]
        p.compare(f"{bc} end, Courant {S}: reflection coefficient", pred, r, "", kind="abs", tol=0.02 if bc != "absorbing" else 0.01)
    _, _, ok = simulate("fixed", 1.001, T=3.0)
    p.compare("Stability: S = 1.001 blows up (CFL violated; 1 = yes)", 1, int(not ok), "", kind="abs")
    def travelled(S):
        n = 1000; dx = 1 / n; dt = S * dx; x = np.arange(n + 1) * dx
        u_prev = np.exp(-((x - 0.2 + dt) / 0.01) ** 2); u = np.exp(-((x - 0.2) / 0.01) ** 2)
        for _ in range(int(0.6 / dt)):
            un = np.zeros_like(u); un[1:-1] = 2 * u[1:-1] - u_prev[1:-1] + S * S * (u[2:] - 2 * u[1:-1] + u[:-2]); u_prev, u = u, un
        exact = np.exp(-((x - 0.8) / 0.01) ** 2)
        return np.max(np.abs(u - exact)), x, u, exact
    e1, x, u1, ex = travelled(1.0); e5, _, u5, _ = travelled(0.5)
    p.compare("Courant 1 ('magic time step'): pulse shape after 0.6 units, max error", 0, e1, "", kind="abs", tol=1e-9)
    p.metric("Courant 0.5: max shape error from numerical dispersion", e5, "")
    fig, ax = p.fig(1, 2, w=11)
    for (bc, S), c in zip([("fixed", 0.5), ("free", 0.5), ("absorbing", 0.5)], COLORS):
        pr, _, _ = simulate(bc, S)
        ax[0].plot(np.arange(1, len(pr) + 1) * S / 1000, pr, color=c, label=f"{bc} end")
    style_axes(ax[0], "t", "u at x = 0.5", "Incident pulse and reflection")
    ax[1].plot(x, ex, color="black", lw=3, alpha=.3, label="exact"); ax[1].plot(x, u1, "--", color=C_MEAS, label="S = 1"); ax[1].plot(x, u5, color=C_PRED, lw=1, label="S = 0.5 (dispersive tail)")
    ax[1].set_xlim(0.7, 0.9)
    style_axes(ax[1], "x", "u", "Numerical dispersion")
    p.save(fig, "wave1d", "Reflections from fixed, free and absorbing ends, and numerical dispersion vs Courant number.")
    p.discuss(f"""The fixed and free ends reflect with −1 and +1, and Mur's absorbing boundary reflects essentially nothing — exactly zero at Courant number 1,
where the discrete scheme propagates waves one cell per step with no error at all (the pulse arrives with {e1:.0e} shape error). At S = 0.5 the
scheme stays stable but becomes dispersive: short wavelengths travel slower than c, leaving an oscillating tail behind the pulse, and Mur's
condition then reflects a few tenths of a percent. S = 1.001 violates the CFL condition and explodes within a few hundred steps. In 2-D and 3-D
no single time step is dispersion-free and first-order Mur leaks at oblique incidence, which is why FDTD codes use PML absorbers (AM-118).""")
# tol-convention: relative tolerances are in percent
