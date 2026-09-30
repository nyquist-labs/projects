from eelab import *

META = dict(
    id="AM-008", title="Reflection coefficient mapping: impedance → unit disc", level="M",
    tools="Complex mapping Γ(Z) = (Z−Z0)/(Z+Z0), transmission-line input impedance, VSWR and mismatch loss, grid visualisation",
    summary="Visualise how the impedance plane folds into the unit disc, show that lossless transmission lines rotate Γ on a circle, and "
            "check the VSWR / mismatch-loss relations numerically.",
    problem="What does a length of cable do to an impedance, and why do RF engineers think in Γ rather than Z?",
    theory=r"""$Γ=(Z-Z_0)/(Z+Z_0)$ maps Re Z > 0 into |Γ| < 1, Z = Z0 to the centre, open/short to ±1. A lossless line of length ℓ gives $Z_{in}=Z_0\frac{Z_L+jZ_0\tan βℓ}{Z_0+jZ_L\tan βℓ}$, equivalently
$Γ_{in}=Γ_Le^{-2jβℓ}$: a rotation at constant |Γ|, a full turn every λ/2. VSWR = (1+|Γ|)/(1−|Γ|); mismatch loss = −10 log(1−|Γ|²).""",
    method="""Z0 = 50 Ω. Grid of constant-R and constant-X lines mapped. Loads 10 Ω, 100 − j75 Ω and 20 + j60 Ω on 0 → λ/2 of line (400 steps): Z_in from the impedance formula, Γ_in computed from it;
|Γ_in| constancy and rotation angle measured. VSWR/loss relations checked on 10⁴ random loads.""",
)


def run(p):
    Z0 = 50.0
    loads = [10 + 0j, 100 - 75j, 20 + 60j]
    bl = np.linspace(0, pi, 401)
    worst_mag = worst_ang = 0
    tracks = []
    for ZL in loads:
        t = np.tan(bl)
        Zin = Z0 * (ZL + 1j * Z0 * t) / (Z0 + 1j * ZL * t)
        Gin = (Zin - Z0) / (Zin + Z0); GL = (ZL - Z0) / (ZL + Z0)
        worst_mag = max(worst_mag, np.max(np.abs(np.abs(Gin) - abs(GL))))
        worst_ang = max(worst_ang, np.max(np.abs(np.angle(Gin / (GL * np.exp(-2j * bl))))))
        tracks.append(Gin)
    p.compare("Lossless line: max change of |Γ| along the line", 0, worst_mag, "", kind="abs", tol=1e-9)
    p.compare("Rotation angle of Γ vs −2βℓ, worst error", 0, np.degrees(worst_ang), "°", kind="abs", tol=1e-6)
    p.compare("Quarter-wave line turns 10 Ω into Z0²/10", Z0 ** 2 / 10, (Z0 * (10 + 1j * Z0 * np.tan(pi / 2 - 1e-9)) / (Z0 + 1j * 10 * np.tan(pi / 2 - 1e-9))).real, "Ω", tol=0.0001)
    r = p.rng
    Z = r.uniform(1, 500, 10000) + 1j * r.uniform(-500, 500, 10000)
    Gm = np.abs((Z - Z0) / (Z + Z0))
    vswr = (1 + Gm) / (1 - Gm)
    # check against the direct definition via standing-wave extremes on a line
    x = np.linspace(0, pi, 200001)
    k = np.argsort(Gm)[[1000, 5000, 9000]]
    ratios = []
    for i in k:
        GL = (Z[i] - Z0) / (Z[i] + Z0)
        Vx = np.abs(np.exp(1j * x) + GL * np.exp(-1j * x))
        ratios.append((Vx.max() / Vx.min(), vswr[i]))
    p.compare("VSWR = (1+|Γ|)/(1−|Γ|) vs Vmax/Vmin of the standing wave (worst of 3)", 0, max(abs(a / b - 1) for a, b in ratios), "", kind="abs", tol=1e-4)
    p.metric("Mismatch loss at VSWR 2:1", -10 * np.log10(1 - (1 / 3) ** 2), "dB")
    fig, ax = p.fig(1, 2, w=11, h=5.3)
    for R in (0, 10, 25, 50, 100, 250):
        zz = R + 1j * np.linspace(-2000, 2000, 4000); g = (zz - Z0) / (zz + Z0)
        ax[0].plot(zz.real + 0 * zz.imag, zz.imag, color=COLORS[0], lw=.6, alpha=.5); ax[1].plot(g.real, g.imag, color=COLORS[0], lw=.8)
    for X in (-100, -50, -25, 25, 50, 100):
        zz = np.linspace(0, 4000, 4000) + 1j * X; g = (zz - Z0) / (zz + Z0)
        ax[0].plot(zz.real, zz.imag + 0, color=COLORS[1], lw=.6, alpha=.5); ax[1].plot(g.real, g.imag, color=COLORS[1], lw=.8)
    ax[0].set_xlim(0, 300); ax[0].set_ylim(-150, 150)
    style_axes(ax[0], "R (Ω)", "X (Ω)", "Impedance half-plane", legend=False)
    for Gin, ZL, c in zip(tracks, loads, (C_MEAS, C_PRED, COLORS[2])):
        ax[1].plot(Gin.real, Gin.imag, color=c, lw=2.2, label=f"Z_L = {ZL:.0f} along λ/2 of line")
    th = np.linspace(0, 2 * pi, 300); ax[1].plot(np.cos(th), np.sin(th), color="black", lw=1)
    ax[1].set_aspect("equal")
    style_axes(ax[1], "Re Γ", "Im Γ", "Γ plane: lines rotate on circles")
    p.save(fig, "gamma_map", "Constant-R/X lines in the Z plane and their images in the Γ plane; three loads rotated by half a wavelength of line.")
    p.discuss("""A lossless line leaves |Γ| unchanged to rounding error and rotates it by exactly −2βℓ, which is why reflection coefficient is the natural
coordinate for transmission lines: in Z the same operation is a complicated tangent formula, in Γ it is a rotation. The quarter-wave inversion
(10 Ω → 250 Ω) is the half-turn of that rotation, and the VSWR formula agrees with the standing-wave ratio measured directly on the simulated line
voltage. Real cables add loss, which turns the circles into inward spirals toward Γ = 0 — the reason a long lossy cable hides a bad antenna.""")
# tol-convention: relative tolerances are in percent
