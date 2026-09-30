from eelab import *
from eelab.nec import solve as nec_solve, far_field

ETA0 = 376.730313668

META = dict(
    id="AM-196", title="Antenna far fields by numerical radiation integrals", level="H",
    tools="Radiation integral of a line current evaluated numerically (Gauss–Legendre), total radiated power by integration over the sphere, radiation resistance and directivity, short/half-wave/full-wave dipoles against closed forms, small loop via its equivalent magnetic dipole, comparison with the currents from the repository's MoM solver",
    summary="Compute the far field of any wire current by integrating it, then integrate the far field over a sphere to get radiated power, radiation "
            "resistance and directivity. Check against every classical closed form (73.1 Ω, 1.64, 1.5, 2.41 …) and against a moment-method current that is not assumed sinusoidal.",
    problem="An antenna's pattern and radiation resistance follow from its current. How is that computed for an arbitrary current, and how good is the textbook sinusoidal-current assumption?",
    theory=r"""For a z-directed current I(z): $E_θ=jη\frac{k e^{-jkr}}{4πr}\sinθ\int I(z')e^{jkz'\cosθ}dz'$. Radiated power $P=\frac{1}{2η}\oint|E_θ|^2r^2dΩ$, $R_{rad}=2P/|I_{feed}|^2$, directivity $D=4π|E|^2_{max}r^2/(2ηP)$. Hertzian dipole of length ℓ ≪ λ: $R=80π^2(ℓ/λ)^2$,
D = 1.5. Half-wave with $I=I_0\cos kz$: pattern $\frac{\cos(\frac π2\cosθ)}{\sinθ}$, R = 73.08 Ω, D = 1.641. Full-wave: D = 2.41, R (referred to the current maximum) = 199 Ω. Small loop of area A: $R=320π^4(A/λ^2)^2$ = 31 171 (A/λ²)² Ω.""",
    method="""Gauss–Legendre integration along the wire (64 nodes), θ integration with 2000 nodes. Cases: Hertzian dipole ℓ = 0.01λ (uniform current), λ/2 and λ sinusoidal dipoles, a 1.25λ dipole, small loop (circumference 0.1λ) by direct integration of its ring current.
MoM: thin half-wave dipole (radius 10⁻⁴ λ), its computed current in the same integral.""",
)


def pattern_z(I_of_z, L, theta, lam=1.0, n=64):
    k = 2 * pi / lam; x, w = np.polynomial.legendre.leggauss(n); z = x * L / 2; w = w * L / 2
    F = np.array([np.sum(w * I_of_z(z) * np.exp(1j * k * z * np.cos(t))) for t in theta])
    return ETA0 * k / (4 * pi) * np.sin(theta) * F                   # E_θ · r


def power_z(I_of_z, L, lam=1.0):
    th = np.linspace(1e-6, pi - 1e-6, 2000); E = pattern_z(I_of_z, L, th, lam)
    P = 2 * pi / (2 * ETA0) * np.trapezoid(np.abs(E) ** 2 * np.sin(th), th)
    D = 4 * pi * np.max(np.abs(E)) ** 2 / (2 * ETA0) / P
    return P, D, th, E


def run(p):
    k = 2 * pi
    P, D, *_ = power_z(lambda z: np.ones_like(z), 0.01)
    p.compare("Hertzian dipole ℓ = 0.01λ: R_rad = 80π²(ℓ/λ)²", 80 * pi ** 2 * 1e-4, 2 * P, "Ω", tol=0.1)
    p.compare("Hertzian dipole: directivity 1.5", 1.5, D, "", tol=0.1)
    P, D, th, E = power_z(lambda z: np.cos(k * z), 0.5)
    p.compare("Half-wave dipole: R_rad", 73.08, 2 * P, "Ω", tol=0.1)
    p.compare("Half-wave dipole: directivity 1.641 (2.15 dBi)", 1.641, D, "", tol=0.1)
    shape = np.abs(E) / np.abs(E).max(); ex = np.abs(np.cos(pi / 2 * np.cos(th)) / np.sin(th))
    p.compare("Half-wave dipole: pattern vs cos(π/2·cosθ)/sinθ (worst difference, normalised)", 0.0, float(np.max(np.abs(shape - ex / ex.max()))), "", kind="abs", tol=1e-6)
    P, D, *_ = power_z(lambda z: np.sin(k * (0.5 - np.abs(z))), 1.0)
    p.compare("Full-wave dipole: directivity 2.41", 2.41, D, "", tol=0.5)
    p.compare("Full-wave dipole: radiation resistance at the current maximum", 199.1, 2 * P, "Ω", tol=0.5)
    P, D, th15, E15 = power_z(lambda z: np.sin(k * (0.625 - np.abs(z))), 1.25)
    p.metric("1.25λ dipole: directivity", D, "", f"{10 * np.log10(D):.2f} dBi — the longest centre-fed dipole before the main beam splits")
    C = 0.1; a = C / (2 * pi); ph = np.linspace(0, 2 * pi, 400, endpoint=False); th = np.linspace(1e-6, pi - 1e-6, 400); pv = np.linspace(0, 2 * pi, 60, endpoint=False)
    Pt = 0.0; Emax = 0.0
    for phi in pv:
        # E_φ ∝ ∮ I (φ̂ · dl) e^{jk r̂·r'}, ring current of unit amplitude
        rr = np.outer(np.sin(th), np.cos(ph - phi)) * a
        Ephi = ETA0 * k / (4 * pi) * np.sum(np.cos(ph - phi)[None] * a * (2 * pi / len(ph)) * np.exp(1j * k * rr), axis=1)
        Pt += np.trapezoid(np.abs(Ephi) ** 2 * np.sin(th), th) * (2 * pi / len(pv)) / (2 * ETA0); Emax = max(Emax, np.abs(Ephi).max())
    A = pi * a * a
    p.compare("Small loop, circumference 0.1λ: R_rad = 320π⁴(A/λ²)²", 320 * pi ** 4 * A ** 2, 2 * Pt, "Ω", tol=1)
    p.compare("Small loop: directivity 1.5 (same pattern as a short dipole, rotated)", 1.5, 4 * pi * Emax ** 2 / (2 * ETA0) / Pt, "", tol=1)
    cur, Z = nec_solve([(0.0, 0.5, True)], lam=1.0, nseg=81, radius=1e-4)
    _, zn, In = cur[0]; In = In / In[np.argmin(np.abs(zn))]
    Imom = lambda z: np.interp(z, zn, In.real) + 1j * np.interp(z, zn, In.imag)
    Pm, Dm, thm, Em = power_z(Imom, 0.5)
    p.compare("MoM current (radius 10⁻⁴λ) in the same integral: radiation resistance vs the MoM input resistance", Z.real, 2 * Pm, "Ω", tol=3)
    p.metric("MoM half-wave dipole: R from the far field / R_in from the solver / sinusoidal theory", f"{2 * Pm:.1f} / {Z.real:.1f} / 73.1 Ω", "", "the thin-wire current is not exactly sinusoidal")
    p.compare("MoM current: directivity (pattern barely changes)", 1.641, Dm, "", tol=1)
    fig = __import__("matplotlib.pyplot", fromlist=["figure"]).figure(figsize=(11, 4))
    for i, (L_, f_, lab) in enumerate(((0.01, lambda z: np.ones_like(z), "ℓ = 0.01λ"), (0.5, lambda z: np.cos(k * z), "λ/2"), (1.0, lambda z: np.sin(k * (0.5 - np.abs(z))), "λ"), (1.25, lambda z: np.sin(k * (0.625 - np.abs(z))), "1.25λ"))):
        ax = fig.add_subplot(1, 4, i + 1, projection="polar"); tt = np.linspace(0, 2 * pi, 721); E_ = np.abs(pattern_z(f_, L_, tt)); ax.plot(tt, E_ / E_.max(), color=COLORS[i])
        ax.set_theta_zero_location("N"); ax.set_theta_direction(-1); ax.set_yticklabels([]); ax.set_title(lab, fontsize=10)
    p.save(fig, "radiation", "Elevation patterns (|E_θ|, normalised) of four dipole lengths, computed by the radiation integral.")
    p.discuss(f"""One numerical integral along the wire and one over the sphere reproduce the whole table of classical antenna results: 80π²(ℓ/λ)² for a
short dipole, 73.1 Ω and 2.15 dBi for the half-wave dipole with its exact cos(π/2·cosθ)/sinθ pattern, D = 2.41 for the full-wave dipole, and the
small loop's 320π⁴(A/λ²)², computed from its ring current with no dipole approximation. Feeding the same integral with the current found by the
moment method (not assumed sinusoidal) gives a radiation resistance of {2 * Pm:.1f} Ω, agreeing with the MoM solver's own input resistance
({Z.real:.1f} Ω) — two independent routes to the same power — while the directivity hardly moves ({Dm:.3f}). The sinusoidal current is an excellent model
of the *pattern*; the input resistance is more sensitive to the real current distribution near the feed.""")
# tol-convention: relative tolerances are in percent
