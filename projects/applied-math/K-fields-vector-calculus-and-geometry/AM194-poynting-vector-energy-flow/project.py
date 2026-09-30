from eelab import *
from eelab.poisson import solve, EPS0

C0 = 299792458.0; MU0 = 4e-7 * pi; ETA0 = MU0 * C0

META = dict(
    id="AM-194", title="Where the power flows: the Poynting vector in a transmission line", level="H",
    tools="Own 2-D Laplace solution of a square coaxial line, TEM fields (E from the potential, H = ẑ×E/η), current from Ampère's circulation, cross-section integral of E×H, capacitance from field energy, analytic circular coax, surface-impedance loss flux into the conductors",
    summary="Show that the power carried by a cable travels in the space between the conductors, not in the copper: integrate the Poynting vector over the "
            "cross-section of a numerically solved line and recover V·I exactly, map how the power is distributed, and derive conductor loss as the small inward component of S at the metal surfaces.",
    problem="Power 'flows through the wires' — or does it? Where exactly is the energy of a signal on a cable while it travels?",
    theory=r"""For a TEM line with voltage V and current I, the fields satisfy $H=\hat z\times E/η$ in a homogeneous dielectric and $\int_{cross\ section}(E\times H)\cdot\hat z\,dA=VI$: all the power is in the dielectric. $Z_0=V/I=\frac{1}{v\,C'}$. Circular coax: $E=\frac{V}{r\ln(b/a)}$,
$H=\frac{I}{2πr}$, so the power inside radius r is $VI\frac{\ln(r/a)}{\ln(b/a)}$ — concentrated near the inner conductor. With finite conductivity each conductor surface absorbs $S_n=\tfrac12R_s|H_t|^2$ per area, $R_s=\sqrt{πfμ_0/σ}$; integrating gives the conductor loss
$P'=\tfrac12|I|^2R'$ with $R'=\frac{R_s}{2π}(\frac1a+\frac1b)$ and attenuation α = R'/(2Z₀).""",
    method="""Square coax: inner 4 × 4 mm, outer 12 × 12 mm, air, 0.05 mm grid, V = 1 V. H from ẑ×E/η₀; I from ∮H·dl on a square contour; power by summing S_z over all cells. Circular coax: RG-58-like a = 0.45 mm, b = 1.47 mm, polyethylene ε_r = 2.3, copper, 100 MHz,
power distribution and conductor loss by numerical integration of the analytic fields.""",
)


def run(p):
    h = 0.05e-3; L = 12e-3; n = int(round(L / h)) + 1; x = np.linspace(-L / 2, L / 2, n); X, Y = np.meshgrid(x, x)
    inner = (np.abs(X) <= 2e-3 + 1e-9) & (np.abs(Y) <= 2e-3 + 1e-9); outer = (np.abs(X) >= L / 2 - 1e-9) | (np.abs(Y) >= L / 2 - 1e-9)
    fixed = inner | outer; V0 = np.where(inner, 1.0, 0.0)
    V = solve(fixed, V0, np.zeros((n, n)), h)
    Ey, Ex = np.gradient(-V, h)
    Hx, Hy = -Ey / ETA0, Ex / ETA0                                 # H = ẑ × E / η
    Sz = Ex * Hy - Ey * Hx
    P = np.sum(Sz[~fixed]) * h * h
    lo, hi = int(round((L / 2 - 3.5e-3) / h)), int(round((L / 2 + 3.5e-3) / h))      # square contour at ±3.5 mm, counter-clockwise
    I = abs((np.sum(Hx[lo, lo:hi]) + np.sum(Hy[lo:hi, hi]) - np.sum(Hx[hi, lo:hi]) - np.sum(Hy[lo:hi, lo])) * h)
    p.compare("∫(E×H)·ẑ dA over the cross-section = V·I (power is carried by the fields between the conductors)", 1.0 * I, P, "W", tol=2)
    W = 0.5 * EPS0 * np.sum((Ex ** 2 + Ey ** 2)[~fixed]) * h * h; Cp = 2 * W / 1.0 ** 2
    p.compare("Z₀ = V/I from Ampère's law vs 1/(c·C′) from the stored energy", 1 / (C0 * Cp), 1.0 / I, "Ω", tol=2)
    p.metric("Square coax (4 mm inner, 12 mm outer, air): Z₀", 1 / (C0 * Cp), "Ω")
    core = (np.abs(X) <= 2e-3 - 2 * h) & (np.abs(Y) <= 2e-3 - 2 * h); inside_metal = np.sum(Sz[core]) * h * h
    p.compare("Power flowing inside the inner conductor (ideal conductor: E = 0 there)", 0.0, inside_metal / P, "", kind="abs", tol=1e-9)
    a, b, er = 0.45e-3, 1.47e-3, 2.3; eta = ETA0 / np.sqrt(er); Z0 = eta / (2 * pi) * np.log(b / a)
    r = np.linspace(a, b, 20001); Vc, Ic = 1.0, 1.0 / Z0
    S = Vc / (r * np.log(b / a)) * Ic / (2 * pi * r); cum = np.concatenate([[0], np.cumsum(0.5 * (S[1:] * r[1:] + S[:-1] * r[:-1]) * np.diff(r))]) * 2 * pi
    p.compare("Circular coax: total ∫S dA = V²/Z₀", Vc * Ic, cum[-1], "W", tol=0.01)
    rh = np.exp(0.5 * (np.log(a) + np.log(b)))
    p.compare("Half of the power flows inside r = √(ab) (from ln(r/a)/ln(b/a))", 0.5, float(np.interp(rh, r, cum) / cum[-1]), "", tol=0.1)
    f = 100e6; sig = 5.8e7; Rs = np.sqrt(pi * f * MU0 / sig)
    Ha, Hb = Ic / (2 * pi * a), Ic / (2 * pi * b)
    loss = 0.5 * Rs * Ha ** 2 * 2 * pi * a + 0.5 * Rs * Hb ** 2 * 2 * pi * b
    Rp = Rs / (2 * pi) * (1 / a + 1 / b)
    p.compare("Inward Poynting flux at the metal surfaces (per metre) = ½|I|²R′", 0.5 * Ic ** 2 * Rp, loss, "W/m", tol=1e-6)
    alpha = Rp / (2 * Z0); dB100 = 8.686 * alpha * 100
    p.compare("Resulting conductor attenuation at 100 MHz (RG-58 datasheets list ≈ 15 dB/100 m including dielectric loss)", 12.0, dB100, "dB/100 m", kind="abs", tol=4)
    p.metric("Circular coax: Z₀ / R′ / conductor attenuation at 100 MHz", f"{Z0:.1f} Ω / {Rp:.3f} Ω/m / {dB100:.1f} dB per 100 m")
    fig, ax = p.fig(1, 2, w=11, h=4.8)
    im = ax[0].imshow(np.where(fixed, np.nan, Sz), extent=[-6, 6, -6, 6], origin="lower", cmap="magma"); fig.colorbar(im, ax=ax[0], label="S_z (W/m² for 1 V)")
    sk = 12; ax[0].quiver(X[::sk, ::sk] * 1e3, Y[::sk, ::sk] * 1e3, Ex[::sk, ::sk], Ey[::sk, ::sk], color="w", scale=8e3, width=0.003)
    ax[0].grid(False); ax[0].set_title("Square coax: power density (colour) and E (arrows)", loc="left", fontsize=10)
    ax[1].plot(r * 1e3, cum / cum[-1] * 100, color=C_MEAS, label="numerical integral"); ax[1].plot(r * 1e3, np.log(r / a) / np.log(b / a) * 100, "--", color=C_PRED, label="ln(r/a)/ln(b/a)")
    ax[1].axvline(rh * 1e3, color="gray", ls=":", label="√(ab)")
    style_axes(ax[1], "radius (mm)", "power inside radius r (%)", "RG-58-like coax: power hugs the inner conductor")
    p.save(fig, "poynting", "Poynting-vector map of a square coaxial line and the cumulative power distribution in a circular coax.")
    p.discuss(f"""Integrating E × H over the cross-section of the numerically solved line gives exactly V·I (to {abs(P / I - 1) * 100:.2f} %), and nothing flows inside the ideal
conductors: the energy of the signal travels in the dielectric, guided by the metal. The map shows where — the power density peaks at the corners
of the inner conductor, where the field crowds. In a round coax half of the power passes within √(ab) of the axis. Two ways of computing Z₀ — Ampère's
law for the current and the stored electric energy for the capacitance — agree, as they must for a TEM line. The wires do have a job in the energy
budget: with finite conductivity the Poynting vector acquires a small inward component at their surfaces, and integrating it gives the familiar
conductor loss ½I²R′, {dB100:.0f} dB per 100 m at 100 MHz for an RG-58-like cable, below the datasheet figure because dielectric loss is not included.""")
# tol-convention: relative tolerances are in percent
