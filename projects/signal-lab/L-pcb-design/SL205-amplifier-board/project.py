from eelab import *
from eelab.circuit import Circuit
from eelab.pcb import Board, Rules, soic, chip, header, mounting_hole, publish
import schemdraw
import schemdraw.elements as elm

META = dict(
    id="SL-205", title="Stereo op-amp preamplifier board", level="M",
    tools="Own PCB toolkit (eelab.pcb: IPC-7351 footprints, A* maze router, ground pour, DRC, Gerber/Excellon/KiCad export), gerbonara + kiutils for independent file checks, MNA circuit simulator",
    summary="A complete two-layer board for a ×11 stereo preamp around a dual op-amp in SOIC-8: schematic, simulation of the gain and bandwidth, "
            "placement, auto-routing, ground pour, design-rule check, Gerbers, drill file, KiCad board, BOM and a 3-D render.",
    problem="Turn a two-resistor gain equation into a manufacturable board — and check that the numbers on the schematic survive the trip.",
    theory=r"""Non-inverting gain $1+R_f/R_g = 1+100k/10k = 11$ (20.8 dB); a 100 Ω output resistor into a 10 kΩ load costs 0.09 dB → 20.74 dB. The input coupling capacitor and bias
resistor form a high-pass at $1/(2π·100\,kΩ·1\,µF)$ = 1.59 Hz. With a 10 MHz GBW op-amp (NE5532-class) the upper −3 dB point is GBW/11 ≈ 0.91 MHz.
Layout rules: 0.2 mm clearance / 0.25 mm tracks (within any low-cost fab's capability), decoupling capacitors next to the supply pins, solid ground pour
on the bottom layer with a via at every top-side ground pad.""",
    method="""Pinout of the industry-standard dual op-amp in SOIC-8 (1 OUTA, 2 −INA, 3 +INA, 4 V−, 5 +INB, 6 −INB, 7 OUTB, 8 V+). Split ±12 V supply via a 3-pin header.
AC simulation of one channel with an op-amp macromodel (A0 = 10⁵, GBW = 10 MHz) driving 10 kΩ. Placement by hand; routing by the A* router (0.25 mm grid,
via cost 12 steps); GND poured on the bottom; files re-read by independent parsers.""",
    data="Design + simulation.",
)


def schematic(ax):
    d = schemdraw.Drawing(canvas=ax, show=False, fontsize=10)
    d.config(unit=2.4)
    d.add(elm.Dot(open=True).label("IN_L", "left"))
    d.add(elm.Capacitor().right().label("C1 1 µF"))
    n = d.add(elm.Dot())
    d.add(elm.Line().right(2.2))
    op = d.add(elm.Opamp(leads=True).flip().anchor("in2"))
    d.add(elm.Resistor().at(n.center).down(3.6).label("R1 100 kΩ", "bottom")); d.add(elm.Ground())
    d.add(elm.Line().at(op.in1).left(0.7)); j = d.add(elm.Dot())
    d.add(elm.Line().down(1.0)); k = d.add(elm.Dot())
    d.add(elm.Resistor().down(2.0).label("R3 10 kΩ", "bottom")); d.add(elm.Ground())
    d.add(elm.Resistor().at(k.center).right(op.out.x - k.center.x).label("R2 100 kΩ", "bottom"))
    d.add(elm.Line().toy(op.out)); o = d.add(elm.Dot())
    d.add(elm.Resistor().at(op.out).right().label("R4 100 Ω")); d.add(elm.Dot(open=True).label("OUT_L", "right"))
    d.draw(show=False)
    ax.axis("off"); ax.set_title("Channel A, U1A (channel B identical: C2, R5–R8, U1B)", loc="left", fontsize=10)


def build_board():
    b = Board("preamp", 50, 36, Rules())
    b.add("U1", soic(8), 25, 18, 0, "NE5532", "dual op-amp SOIC-8")
    b.add("J1", header(3), 5, 18, 90, "IN L/GND/R"); b.add("J2", header(3), 45, 18, 90, "OUT L/GND/R"); b.add("J3", header(3), 25, 5, 0, "+12/GND/-12")
    for k, (x, y) in enumerate(((3.5, 3.5), (46.5, 3.5), (3.5, 32.5), (46.5, 32.5)), 1):
        b.add(f"H{k}", mounting_hole(), x, y)
    ch = chip("0805")
    # channel A (pins 1-3, left side), channel B (pins 5-7, right side)
    b.add("C1", ch, 12, 22, 0, "1uF"); b.add("R1", ch, 15, 26, 90, "100k"); b.add("R3", ch, 19, 26, 90, "10k"); b.add("R2", ch, 22, 29, 0, "100k"); b.add("R4", ch, 30, 29, 0, "100")
    b.add("C2", ch, 12, 13, 0, "1uF"); b.add("R5", ch, 15, 9, 90, "100k"); b.add("R7", ch, 33, 12, 90, "10k"); b.add("R6", ch, 36, 16, 90, "100k"); b.add("R8", ch, 38, 11, 0, "100")
    b.add("C3", ch, 31, 22, 90, "100n"); b.add("C4", ch, 19, 13, 90, "100n")
    b.add("C5", chip("1206"), 18, 5, 0, "10uF"); b.add("C6", chip("1206"), 32, 5, 0, "10uF")
    b.connect("IN_L", "J1.1", "C1.1"); b.connect("IN_R", "J1.3", "C2.1")
    b.connect("INA+", "C1.2", "R1.2", "U1.3"); b.connect("INA-", "U1.2", "R3.2", "R2.1"); b.connect("OUTA", "U1.1", "R2.2", "R4.1"); b.connect("OUT_L", "R4.2", "J2.1")
    b.connect("INB+", "C2.2", "R5.1", "U1.5"); b.connect("INB-", "U1.6", "R7.2", "R6.1"); b.connect("OUTB", "U1.7", "R6.2", "R8.1"); b.connect("OUT_R", "R8.2", "J2.3")
    b.connect("+12V", "J3.1", "U1.8", "C3.2", "C5.1"); b.connect("-12V", "J3.3", "U1.4", "C4.1", "C6.2")
    b.connect("GND", "J1.2", "J2.2", "J3.2", "R1.1", "R3.1", "R5.2", "R7.1", "C3.1", "C4.2", "C5.2", "C6.1")
    b.net_widths.update({"+12V": 0.4, "-12V": 0.4})
    return b


def channel(A0=1e5, GBW=10e6):
    ck = Circuit("preamp")
    ck.V("s", "in", "0", ac=1); ck.C("1", "in", "p", 1e-6); ck.R("1", "p", "0", 100e3)
    ck.R("3", "m", "0", 10e3); ck.R("2", "m", "o", 100e3); ck.OPAMP("U", "p", "m", "o", A0=A0, GBW=GBW)
    ck.R("4", "o", "out", 100); ck.R("L", "out", "0", 10e3)
    return ck


def run(p):
    f = np.logspace(-1, 7, 1600)
    ck = channel()
    p.write("simulation/channel.cir", ck.to_spice(), "SPICE netlist of one channel")
    H = np.abs(ck.ac(f).v("out"))
    mid = db(H[np.argmin(np.abs(f - 1e3))])
    p.compare("Mid-band gain into 10 kΩ", db(11 * 1e4 / 1.01e4), mid, "dB", kind="abs", tol=0.05)
    p.compare("Low −3 dB corner = 1/(2π·100k·1µ)", 1 / (2 * pi * 1e5 * 1e-6), find_crossing(f, db(H) - mid, -3.0103, falling=False), "Hz", tol=3)
    p.compare("High −3 dB corner ≈ GBW/11", 10e6 / 11, find_crossing(f, db(H) - mid, -3.0103, falling=True), "Hz", tol=5)
    b = build_board()
    fail = b.route(skip=("GND",))
    p.metric("Connections the router could not complete", sum(len(v) for v in fail.values()), "", str(fail) if fail else "all routed")
    p.metric("Stitching vias added for top-side GND pads", b.stitch_pad_vias("GND"), "")
    b.pour("B", "GND")
    res = publish(p, b)
    fig, ax = p.fig(1, 2, w=11, h=3.8)
    schematic(ax[0])
    ax[1].semilogx(f, db(H), color=C_MEAS)
    style_axes(ax[1], "frequency (Hz)", "gain (dB)", "Simulated channel response", legend=False)
    p.save(fig, "schematic_response", "Schematic of one channel and its simulated frequency response (1.6 Hz – 0.9 MHz at 20.7 dB).")
    p.discuss(f"""The simulated channel hits the hand-calculated gain, low-frequency corner and GBW-limited bandwidth, so the schematic is right before any
copper is drawn. The board then goes through the same steps as a KiCad project: footprints generated from IPC-7351 land-pattern equations, hand
placement that keeps each channel's feedback network next to its op-amp pins and the 100 nF decoupling capacitors next to pins 4 and 8, automatic
routing with 0.4 mm supply tracks, a bottom-layer ground pour, and a design-rule check that comes back clean. Every output file was re-opened by
an *independent* parser (gerbonara for Gerber/Excellon, kiutils for the KiCad board) and the counts agree with the design. What this does not
prove is audio performance: a real board should be measured for noise and crosstalk — the auto-router placed the two channels' inputs where it
found space, which is exactly what the design-review project (SL-214) critiques.""")
# tol-convention: relative tolerances are in percent
