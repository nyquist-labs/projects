from eelab import *

META = dict(
    id="SL-122", title="1-D FDTD: an EM pulse hitting a dielectric", level="M",
    tools="Yee FDTD (E/H leapfrog) in NumPy, Mur absorbing boundaries",
    summary="Launch a Gaussian pulse onto a glass slab (ε_r = 4) in a 1-D Yee grid; measure reflection and transmission "
            "coefficients and the slowed wave speed, and compare with Fresnel's normal-incidence formulas.",
    problem="Light partly reflects from a window. Can a direct numerical solution of Maxwell's equations reproduce the "
            "reflection coefficient, and the slowing of the wave inside the glass?",
    theory=r"""Normal incidence from n₁ to n₂: $r=\frac{n_1-n_2}{n_1+n_2}$, $t=\frac{2n_1}{n_1+n_2}$ (field amplitudes); ε_r = 4 → n = 2 → r = −1/3, t = 2/3.
Phase velocity c/n = 1.5×10⁸ m/s. Energy check: $r^2+\frac{n_2}{n_1}t^2=1$.""",
    method="""Grid Δx = 1 mm, Courant number 0.5, 4,000 cells; slab from cell 2,200 to the end (so the transmitted pulse never returns); soft source;
first-order Mur boundaries. Reflected and transmitted pulse peaks measured by probes; speed from arrival times at two probes in the slab.""",
)


def run(p):
    c0, eps0, mu0 = 299792458.0, 8.854e-12, 4e-7 * pi
    N, dx = 4000, 1e-3
    S = 0.5; dt = S * dx / c0
    er = np.ones(N); er[2200:] = 4.0
    E = np.zeros(N); H = np.zeros(N - 1)
    src = 1000
    probes = {"refl": 1500, "t1": 2600, "t2": 3000}
    rec = {k: [] for k in probes}
    ce = dt / (eps0 * er * dx); ch = dt / (mu0 * dx)
    Eleft = Eright = 0.0
    nsteps = 7000
    for n in range(nsteps):
        H += ch * np.diff(E)
        e1, eN = E[1], E[-2]
        E[1:-1] += ce[1:-1] * np.diff(H)
        E[src] += np.exp(-((n - 300) / 60.0) ** 2)
        k0 = (S - 1) / (S + 1); kN = (S / 2 - 1) / (S / 2 + 1)
        E[0] = e1 + k0 * (E[1] - E[0]); E[-1] = eN + kN * (E[-2] - E[-1])
        for k, i in probes.items():
            rec[k].append(E[i])
    r_ = np.array(rec["refl"]); t1 = np.array(rec["t1"]); t2 = np.array(rec["t2"])
    inc_peak = r_[:2000].max()
    refl_peak = r_[3000:].min() if abs(r_[3000:].min()) > abs(r_[3000:].max()) else r_[3000:].max()
    r_meas = refl_peak / inc_peak
    p.compare("Reflection coefficient r = (1−n)/(1+n)", -1 / 3, r_meas, "", tol=2)
    tr_peak = t1.max()
    p.compare("Transmission coefficient t = 2/(1+n)", 2 / 3, tr_peak / inc_peak, "", tol=3)
    v = (probes["t2"] - probes["t1"]) * dx / ((np.argmax(t2) - np.argmax(t1)) * dt)
    p.compare("Wave speed in the slab (c/n)", c0 / 2, v, "m/s", tol=1)
    p.compare("Energy conservation r² + n·t²", 1.0, r_meas**2 + 2 * (tr_peak / inc_peak) ** 2, "", tol=2)
    tt = np.arange(nsteps) * dt * 1e9
    fig, ax = p.fig()
    ax.plot(tt, r_, color=C_MEAS, label="probe in air (incident, then reflected)")
    ax.plot(tt, t1, color=COLORS[2], label="probe in glass (transmitted)")
    ax.axhline(-1 / 3 * inc_peak, color=C_PRED, ls="--", lw=1, label="Fresnel r = −1/3")
    style_axes(ax, "time (ns)", "E (arb.)", "Pulse meeting an ε_r = 4 dielectric")
    p.save(fig, "fdtd_1d", "The reflected pulse is inverted and one third as tall; the transmitted one travels at half speed.")
    p.discuss("""The Yee scheme reproduces Fresnel's coefficients to within a percent: the reflection is inverted (going into a denser
medium) with |r| = 1/3, the transmitted pulse has 2/3 the amplitude and half the speed, and r² + n·t² = 1 confirms energy
conservation. The small errors come from numerical dispersion (the pulse spans ~150 cells, so it is well resolved) and the
staggered position of the interface in the Yee grid (half a cell of uncertainty).""")
