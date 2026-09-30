from eelab import *
from eelab.nec import solve, far_field, directivity

META = dict(
    id="SL-099", title="Wire-antenna simulator by the method of moments", level="H",
    tools="Own thin-wire method-of-moments solver (piecewise-sinusoidal Galerkin, closed-form near fields)",
    summary="Solve for the current on a dipole numerically, then compute input impedance vs length, resonance, "
            "directivity and pattern, and compare with the classical induced-EMF and sinusoidal-current results.",
    problem="An antenna's pattern and impedance come from the current flowing on it, which nobody knows in advance. "
            "Find it numerically and check it against the few cases with textbook answers.",
    theory=r"""Galerkin MoM: expand the current in piecewise-sinusoidal 'V' functions, enforce the boundary condition in a weighted
sense, solve $\mathbf Z\mathbf I=\mathbf V$ with a delta-gap source. Induced-EMF theory (infinitely thin wire, assumed sinusoidal
current) gives $Z_{in}=73.1+j42.5\,\Omega$ at L = λ/2; finite radius a raises R and X and moves resonance to ≈ 0.47–0.48 λ.
The far-field pattern is ≈ $\cos(\frac\pi2\cos\theta)/\sin\theta$ with directivity 2.15 dBi and 78° beamwidth.""",
    method="""40 segments per wire; radius λ/1000 (and λ/10⁵ for the thin-wire limit); length sweep 0.40–0.55 λ; directivity by
integrating |E|² over the sphere.""",
)


def run(p):
    Ls = np.linspace(0.40, 0.55, 16)
    Z = np.array([solve([(0.0, L, True)], 1.0, 40)[1] for L in Ls])
    c, Zh = solve([(0.0, 0.5, True)], 1.0, 40)
    _, Zthin = solve([(0.0, 0.5, True)], 1.0, 40, radius=1e-5)
    p.compare("λ/2 input resistance (a = λ/1000) vs induced-EMF 73.1 Ω", 73.1, Zh.real, "Ω")
    p.compare("λ/2 input resistance, thin-wire limit (a = λ/10⁵)", 73.1, Zthin.real, "Ω")
    p.compare("λ/2 input reactance (a = λ/1000)", 42.5, Zh.imag, "Ω", kind="abs")
    Lres = float(np.interp(0, Z.imag, Ls))
    p.compare("Resonant length (X = 0)", 0.475, Lres, "λ", tol=3)
    p.metric("Resistance at resonance", float(np.interp(Lres, Ls, Z.real)), "Ω")
    D, P, th, ph = directivity(c, 1.0, 121)
    p.compare("λ/2 dipole directivity", 2.15, 10 * np.log10(D), "dBi", kind="abs")
    E = far_field(c, 1.0, th); g = 20 * np.log10(E / E.max())
    bw = 2 * (90 - np.degrees(th[np.argmax(g > -3.0103)]))
    p.compare("E-plane half-power beamwidth", 78, bw, "°", tol=3)
    fig, ax = p.fig(1, 2)
    ax[0].plot(Ls, Z.real, color=C_MEAS, label="R_in (MoM)"); ax[0].plot(Ls, Z.imag, color=COLORS[1], label="X_in (MoM)")
    ax[0].plot([0.5], [73.1], "o", color=C_PRED, label="73.1 Ω (induced EMF)"); ax[0].plot([0.5], [42.5], "s", color=C_PRED, label="42.5 Ω")
    ax[0].axhline(0, color="gray", lw=.6)
    style_axes(ax[0], "dipole length (λ)", "Ω", "Input impedance vs length")
    ax[1].plot(np.degrees(th), g, color=C_MEAS, label="MoM far field")
    ax[1].plot(np.degrees(th), 20 * np.log10(np.abs(np.cos(pi / 2 * np.cos(th)) / np.sin(th)) + 1e-12), "--", color=C_PRED, label="cos(π/2·cosθ)/sinθ")
    ax[1].set_ylim(-30, 1)
    style_axes(ax[1], "θ (°)", "relative power (dB)", "E-plane pattern")
    p.save(fig, "dipole", "The numerical dipole reproduces the classical resonance, pattern and directivity.")
    x, zn, In = c[0]
    fig, ax = p.fig()
    ax.plot(zn, np.abs(In) / np.abs(In).max(), "o-", color=C_MEAS, ms=3, label="|I(z)| MoM")
    ax.plot(zn, np.sin(2 * pi * (0.25 - np.abs(zn))) / np.sin(2 * pi * 0.25), "--", color=C_PRED, label="sin k(h−|z|) assumption")
    style_axes(ax, "z (λ)", "normalised current", "Current distribution on the λ/2 dipole")
    p.save(fig, "current", "The solved current is nearly — but not exactly — the assumed sinusoid.")
    p.csv("impedance_sweep", length_lambda=Ls, R_ohm=Z.real, X_ohm=Z.imag)
    p.discuss(f"""Pattern, beamwidth and 2.15 dBi directivity match the sinusoidal-current theory closely, and resonance falls at ≈ 0.475 λ
as expected for a finite-radius wire. The input impedance at exactly λ/2 is higher than the famous 73 + j42.5 Ω:
{Zh.real:.0f} + j{Zh.imag:.0f} Ω for a = λ/1000 and {Zthin.real:.0f} + j{Zthin.imag:.0f} Ω for a = λ/10⁵. The textbook number comes from
the induced-EMF method, which *assumes* a sinusoidal current on an infinitely thin wire; the MoM solves for the actual
current (the second figure shows it deviating from the sinusoid near the feed) and the delta-gap feed adds a
thickness-dependent correction. The trend toward 73 Ω as the wire thins is the check that the two agree in their
common limit. The same solver runs the Yagi in SL-100.""")
