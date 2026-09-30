from eelab import *
from eelab.fields2d import Section, extrapolate, hammerstad, wheeler_width, gcpw, C0
from eelab.pcb import Board, Rules, Via, Track, sma_edge, publish
from scipy.optimize import brentq

META = dict(
    id="SL-209", title="Controlled-impedance RF board: 50 Ω microstrip vs grounded CPW", level="H",
    tools="Closed-form synthesis (Wheeler/Hammerstad, conformal-mapping GCPW), own 2-D finite-difference field solver with Richardson extrapolation, eelab.pcb for the via-fenced SMA-to-SMA board",
    summary="Design a 50 Ω through-line between two edge-mount SMA connectors on standard 1.6 mm FR-4. The closed-form widths for microstrip and "
            "grounded coplanar waveguide are checked with a 2-D field solver, and the board is built with a stitched via fence and poured grounds.",
    problem="On a 1.6 mm board a 50 Ω microstrip is 3 mm wide — wider than an SMA centre pin. How do RF boards get narrow 50 Ω lines, and how accurate are the formulas?",
    theory=r"""Microstrip Z0 depends on w/h: on h = 1.6 mm, ε_r = 4.4 the Wheeler synthesis gives w ≈ 3.06 mm for 50 Ω. Bringing ground up beside the trace (grounded CPW,
gap s) adds capacitance, so the same 50 Ω is reached with a much narrower trace: conformal mapping gives s for w = 1.0 mm. Both closed forms claim ≈ 1 %
accuracy (zero-thickness strips). The via fence ties the top grounds to the bottom plane; spacing ≤ λ_g/10 at the highest frequency keeps the fence
from resonating.""",
    method="""Field solver: 5-point finite differences on a grounded box 30h × 15h, zero-thickness conductors, capacitance from field energy with and without the
dielectric (Z0 = 1/(c√(C·C_air))); three grids (0.2/0.1/0.05 mm) and Richardson extrapolation with the observed convergence order. Board: 50 × 20 mm, SMA
edge launches, GCPW trace, top ground pour with clearance s, bottom ground plane, vias every 2.5 mm on both sides.""",
    data="Simulation.",
)

H, ER = 1.6e-3, 4.4


def ms_section(w):
    def f(dx):
        s = Section(30 * H, 15 * H, dx); s.dielectric(0, H, ER); s.conductor((-w / 2, w / 2, H, H)); return s
    return f


def cpw_section(w, gap):
    def f(dx):
        s = Section(30 * H, 15 * H, dx); s.dielectric(0, H, ER); s.conductor((-w / 2, w / 2, H, H))
        s.ground((-15 * H, -w / 2 - gap, H, H), (w / 2 + gap, 15 * H, H, H)); return s
    return f


def run(p):
    w_ms = wheeler_width(50, H, ER)
    z_hj, ee_hj = hammerstad(w_ms, H, ER)
    w_grid = round(w_ms / 0.4e-3) * 0.4e-3          # strip edges must sit on nodes of all three grids (0.2/0.1/0.05 mm)
    z_fd, raw, order = extrapolate(ms_section(w_grid))
    p.metric("Wheeler synthesis: microstrip width for 50 Ω", w_ms * 1e3, "mm", f"field-solved at the grid-aligned width {w_grid * 1e3:.1f} mm")
    p.compare(f"Microstrip w = {w_grid * 1e3:.1f} mm: Hammerstad–Jensen vs field solver", hammerstad(w_grid, H, ER)[0], z_fd, "Ω", tol=2)
    p.metric("Field solver: raw values on 0.2/0.1/0.05 mm grids and observed order", f"{raw[0]:.2f} / {raw[1]:.2f} / {raw[2]:.2f} Ω, p = {order:.2f}")
    gap_g = 0.2e-3                                    # a comfortable gap for any low-cost fab (≥ 0.15 mm)
    w = brentq(lambda x: gcpw(x, gap_g, H, ER)[0] - 50, 0.2e-3, 5e-3)
    z_c, ee_c = gcpw(w, gap_g, H, ER)
    p.metric("Conformal mapping: GCPW width for 50 Ω with 0.20 mm gaps", w * 1e3, "mm")
    wc_grid = 1.2e-3                                  # nearest geometry whose edges sit on the 0.1/0.05/0.025 mm grids
    zc_fd, rawc, oc = extrapolate(cpw_section(wc_grid, gap_g), dxs=(0.1e-3, 0.05e-3, 0.025e-3))
    p.compare("GCPW w = 1.2 mm, s = 0.20 mm: conformal mapping vs field solver", gcpw(wc_grid, gap_g, H, ER)[0], zc_fd, "Ω", tol=3)
    p.metric("GCPW field solver: raw values and observed order", f"{rawc[0]:.2f} / {rawc[1]:.2f} / {rawc[2]:.2f} Ω, p = {oc:.2f}")
    lam_g = C0 / 6e9 / np.sqrt(ee_c)
    p.metric("λ_g/10 at 6 GHz (via-fence pitch 2.5 mm is below it)", lam_g / 10 * 1e3, "mm")
    # --- board
    b = Board("rf_thru_50ohm", 50, 20, Rules(clearance=0.2, edge_clearance=0.3))
    b.add("J1", sma_edge(), 2.0, 10, 90, "SMA edge"); b.add("J2", sma_edge(), 48.0, 10, 270, "SMA edge")
    b.connect("RF", "J1.1", "J2.1"); b.connect("GND", "J1.2", "J1.3", "J2.2", "J2.3")
    b.tracks.append(Track("F", 2.0, 10, 48.0, 10, w * 1e3, "RF"))
    yoff = w * 1e3 / 2 + gap_g * 1e3 + 0.6
    for x in np.arange(6.0, 44.1, 2.5):
        for y in (10 - yoff, 10 + yoff):
            b.vias.append(Via(float(x), float(y), "GND", 0.6, 0.3))
    b.pour("F", "GND", clearance=gap_g * 1e3); b.pour("B", "GND")
    res = publish(p, b)
    # actual gap in the poured copper next to the line
    from shapely.geometry import LineString
    f_gnd = [z[2] for z in b.zones if z[0] == "F"]
    tr = LineString([(10, 10), (40, 10)]).buffer(w * 1e3 / 2, cap_style=2)
    gmin = min(g.distance(tr) for g in f_gnd)
    p.compare("Gap between trace and top ground pour in the exported copper", gap_g * 1e3, gmin, "mm", tol=3)
    fig, ax = p.fig(1, 2, w=11)
    ws = np.linspace(0.5e-3, 4e-3, 30)
    ax[0].plot(ws * 1e3, [hammerstad(x, H, ER)[0] for x in ws], color=C_PRED, ls="--", label="microstrip (Hammerstad–Jensen)")
    ax[0].plot(ws * 1e3, [gcpw(x, gap_g, H, ER)[0] for x in ws], color=COLORS[2], ls="--", label=f"GCPW, s = {gap_g * 1e3:.2f} mm (conformal)")
    ax[0].plot([w_grid * 1e3], [z_fd], "o", color=C_MEAS, label="field solver"); ax[0].plot([wc_grid * 1e3], [zc_fd], "s", color=C_MEAS)
    ax[0].axhline(50, color="gray", lw=.8)
    style_axes(ax[0], "trace width (mm)", "Z0 (Ω)", "Coplanar ground makes 50 Ω narrow")
    s = cpw_section(wc_grid, gap_g)(0.05e-3)
    from eelab.laplace import solve as lsolve
    m = s._mask(s.conductors[0]); gnd = np.zeros_like(m); gnd[0, :] = gnd[-1, :] = gnd[:, 0] = gnd[:, -1] = True; gnd |= s._mask(s.grounds)
    V0 = np.zeros_like(m, float); V0[m] = 1
    V = lsolve(gnd | m, V0, s.eps())
    X, Y = np.meshgrid(s.x * 1e3, s.y * 1e3)
    ax[1].contourf(X, Y, V, levels=20, cmap="viridis"); ax[1].axhline(H * 1e3, color="w", lw=.6)
    ax[1].set_xlim(-4, 4); ax[1].set_ylim(0, 4); ax[1].set_aspect("equal")
    ax[1].set_xlabel("x (mm)"); ax[1].set_ylabel("y (mm)"); ax[1].set_title("GCPW potential: field shared by gaps and plane", loc="left", fontsize=10); ax[1].grid(False)
    p.save(fig, "impedance", "Z0 vs width for microstrip and GCPW (formulas dashed, field solver markers) and the GCPW potential map.")
    p.discuss(f"""The field solver agrees with both closed forms to within about 1–2 % once its grid error is extrapolated away (raw results on the finest grid still differ
by up to ~1 Ω, because the charge singularity at a zero-thickness strip edge converges slowly). A first run gave an absurd convergence order
because the strip edges did not sit on the coarse grid's nodes, so each grid effectively solved a different width — edges must be grid-aligned. The design point of the project is the comparison:
a 1.6 mm board needs a {w_ms * 1e3:.2f} mm microstrip for 50 Ω, twice the width of an SMA pad, whereas grounded CPW gets 50 Ω with a {w * 1e3:.2f} mm trace
and {gap_g * 1e3:.2f} mm gaps — and keeps the fields tightly confined, reducing radiation and crosstalk. The exported copper has exactly the designed gap,
and the 2.5 mm via fence is below λ_g/10 up to 6 GHz. What this cannot show: FR-4's ε_r varies with frequency and between suppliers (±10 %), which moves
Z0 by a few ohms — for real RF work, ask the fab for its stack-up and impedance-controlled process, and measure with a TDR or VNA.""")
# tol-convention: relative tolerances are in percent
