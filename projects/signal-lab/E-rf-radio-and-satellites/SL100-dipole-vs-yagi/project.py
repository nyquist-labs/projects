from eelab import *
from eelab.nec import solve, far_field, directivity

META = dict(
    id="SL-100", title="Dipole vs 3-element Yagi: gain, beamwidth and front-to-back", level="M",
    tools="Method-of-moments solver from SL-099 (parasitic elements via mutual coupling)",
    summary="Add a reflector and a director to a dipole and quantify what they buy: directivity, beamwidth, "
            "front-to-back ratio and the drop in feed-point impedance, compared with published Yagi figures.",
    problem="Two passive rods can turn an omnidirectional dipole into a beam antenna. By how much, and at what cost?",
    theory=r"""Parasitic elements are driven by mutual coupling; a longer element (reflector, inductive) re-radiates with a phase that
reinforces the forward direction, a shorter one (director, capacitive) pulls the beam forward. A well-tuned 3-element
Yagi with ~0.4 λ boom reaches ≈ 7–8 dBi (≈ 5–6 dBd), front-to-back 15–25 dB, and its feed impedance drops to ~20–35 Ω
because of the strong coupling.""",
    method="""Driven element 0.47 λ; reflector 0.50 λ at −0.20 λ; director 0.44 λ at +0.20 λ; radius λ/1000; 30 segments per element. H-plane
(azimuth, θ = 90°) and E-plane patterns; directivity by sphere integration; F/B = forward/backward power at θ = 90°.""",
)


def run(p):
    dip, Zd = solve([(0.0, 0.47, True)], 1.0, 30)
    yagi, Zy = solve([(0.0, 0.47, True), (-0.20, 0.50, False), (0.20, 0.44, False)], 1.0, 30)
    Dd, *_ = directivity(dip, 1.0, 91)
    Dy, P, th, ph = directivity(yagi, 1.0, 181)
    p.compare("Dipole directivity", 2.15, 10 * np.log10(Dd), "dBi", kind="abs")
    p.compare("3-element Yagi directivity (published ≈ 7.5 dBi)", 7.5, 10 * np.log10(Dy), "dBi", kind="abs")
    phis = np.radians(np.linspace(0, 360, 721))
    Hy = np.array([far_field(yagi, 1.0, pi / 2, f) for f in phis]); Hy = 20 * np.log10(Hy / Hy.max())
    fb = Hy[0] - Hy[360]
    p.compare("Front-to-back ratio (published 15–25 dB)", 20, fb, "dB", kind="abs")
    k0 = 0
    bw = 2 * np.degrees(phis[np.argmax(Hy[:360] < -3.0103)])
    p.metric("H-plane half-power beamwidth, Yagi", bw, "°", "dipole: 360° (omnidirectional)")
    p.compare("Feed impedance, Yagi (published 20–35 Ω)", 27, Zy.real, "Ω", kind="abs")
    p.metric("Feed impedance, dipole", f"{Zd.real:.1f} {Zd.imag:+.1f}j Ω")
    fig = __import__("matplotlib.pyplot", fromlist=["x"]).figure(figsize=(8, 4))
    a1 = fig.add_subplot(121, projection="polar"); a2 = fig.add_subplot(122, projection="polar")
    Hd = np.array([far_field(dip, 1.0, pi / 2, f) for f in phis]); Hd = 20 * np.log10(Hd / Hy.max() * 0 + Hd / Hd.max())
    a1.plot(phis, np.maximum(Hy, -40), color=C_MEAS, label="Yagi"); a1.plot(phis, np.maximum(Hd - (10 * np.log10(Dy) - 10 * np.log10(Dd)), -40), color=COLORS[1], label="dipole (same scale)")
    a1.set_rmin(-40); a1.set_title("H-plane (azimuth), dB", fontsize=10); a1.legend(fontsize=7, loc="lower left")
    thf = np.radians(np.linspace(0.5, 359.5, 719))
    Ey = np.array([far_field(yagi, 1.0, t % pi if t < pi else 2 * pi - t, 0 if t < pi else pi) for t in thf]); Ey = 20 * np.log10(Ey / Ey.max())
    a2.plot(thf, np.maximum(Ey, -40), color=C_MEAS); a2.set_rmin(-40); a2.set_theta_zero_location("N"); a2.set_title("E-plane, dB", fontsize=10)
    p.save(fig, "patterns", "The Yagi's beam points toward the director; the dipole is omnidirectional in azimuth.")
    p.csv("h_plane", phi_deg=np.degrees(phis), yagi_db=Hy)
    p.discuss("""Two parasitic rods add roughly 5 dB of directivity and a front-to-back ratio in the published range, at the cost of a
narrow bandwidth and a low feed resistance (~20–30 Ω) that needs a matching section (gamma match or folded dipole)
to meet 50 Ω — see the L-network in SL-103. Exact numbers depend strongly on the element lengths and spacings; these
are an untuned textbook design, and optimising them is a classic application of the genetic algorithm in AM-105.""")
