from eelab import *

META = dict(
    id="SL-132", title="Antenna near field vs far field (Hertzian dipole)", level="H",
    tools="Exact closed-form fields of an oscillating dipole (NumPy), wave-impedance and energy analysis",
    summary="Plot the exact E and H fields of a small dipole from 0.01λ to 10λ, locate where the 1/r³, 1/r² and 1/r terms "
            "cross over (r = λ/2π), and watch the wave impedance approach 377 Ω.",
    problem="Close to an antenna the fields behave like a capacitor; far away they form a radiating wave. Where is the "
            "boundary, and what changes there?",
    theory=r"""Hertzian dipole (Idl): $E_\theta\propto\left[\frac{1}{r}+\frac{1}{jkr^2}-\frac{1}{k^2r^3}\right]$, $H_\phi\propto\left[\frac1r+\frac{1}{jkr^2}\right]$. All three terms are equal in
magnitude at kr = 1, i.e. r = λ/2π ≈ 0.16λ. Wave impedance |E_θ/H_φ| → η₀ = 376.7 Ω for kr ≫ 1 and ≈ η₀/(kr) (high, 'electric') for kr ≪ 1.
Reactive (stored) energy dominates for kr < 1; the power flow's real part is independent of r.""",
    method="""Broadside (θ = 90°) fields for kr from 0.03 to 60; crossover of the |1/r| and |1/r³| terms; |Z_w| vs r; ratio of reactive to real Poynting
flux integrated over a sphere.""",
)


def run(p):
    eta = 376.73
    kr = np.logspace(-1.5, 1.8, 400)
    E = eta * (1 / kr + 1 / (1j * kr**2) - 1 / kr**3) * 1j        # common factor dropped
    H = (1 / kr + 1 / (1j * kr**2)) * 1j
    Zw = np.abs(E / H)
    p.compare("Wave impedance at kr = 60 (far field)", eta, Zw[-1], "Ω", tol=0.1)
    p.compare("Wave impedance at kr = 0.1 ≈ η₀/(kr)", eta / 0.1, float(np.interp(0.1, kr, Zw)), "Ω", tol=2)
    t1, t3 = 1 / kr, 1 / kr**3
    cross = kr[np.argmin(np.abs(t1 - t3))]
    p.compare("Near/far crossover (|1/r| = |1/r³| term)", 1.0, cross, "kr", tol=2)
    S = 0.5 * E * np.conj(H)
    p.metric("Reactive / real power ratio at kr = 0.2", float(np.interp(0.2, kr, np.abs(S.imag) / S.real)))
    p.metric("Reactive / real power ratio at kr = 5", float(np.interp(5, kr, np.abs(S.imag) / S.real)))
    flux = S.real * kr**2
    p.compare("Real power through a sphere (∝ Re S·r²) at kr = 60 vs kr = 0.03", 1.0, float(flux[-1] / flux[0]), "", tol=0.1)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(kr, 1 / kr, color=COLORS[0], label="radiation 1/r"); ax[0].loglog(kr, 1 / kr**2, color=COLORS[1], label="induction 1/r²")
    ax[0].loglog(kr, 1 / kr**3, color=COLORS[2], label="quasi-static 1/r³"); ax[0].loglog(kr, np.abs(E) / eta, "--", color="black", lw=1, label="|E_θ| total")
    ax[0].axvline(1, color="gray", ls=":")
    style_axes(ax[0], "kr = 2πr/λ", "relative magnitude", "Field terms of a Hertzian dipole")
    ax[1].loglog(kr, Zw, color=C_MEAS, label="|E_θ / H_φ|")
    ax[1].axhline(eta, color=C_PRED, ls="--", label="η₀ = 377 Ω")
    style_axes(ax[1], "kr", "wave impedance (Ω)", "Near field is high-impedance (electric)")
    p.save(fig, "near_far", "All terms cross at kr = 1; beyond a few λ only the 1/r radiation field remains.")
    p.discuss("""The exact fields show three regimes meeting at r = λ/2π: inside it the 1/r³ quasi-static term dominates, the wave impedance
is far above 377 Ω (a small electric dipole's near field is mostly E) and most of the Poynting flux is reactive — energy
sloshing in and out each cycle. Outside it the 1/r radiation term wins and E/H → 377 Ω. The real part of the power flow is
the same at every radius (energy conservation), a useful check on the algebra. This is why near-field EMC probes and
far-field antenna measurements need different set-ups.""")
