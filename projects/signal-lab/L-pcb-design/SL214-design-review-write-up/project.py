from eelab import *
from eelab.core import ROOT
from eelab.pcb import Board, Rules, soic, chip, header, mounting_hole, publish, plot_board
import importlib.util
from shapely.ops import unary_union
from shapely.geometry import Point

META = dict(
    id="SL-214", title="Design review: critiquing and re-laying-out the preamp board", level="M",
    tools="Geometric review metrics computed from the routed boards (decoupling-loop length, feedback-node length, channel separation, input/output spacing), eelab.pcb re-layout, DRC/exports",
    summary="Review the SL-205 stereo preamp layout the way a senior engineer would, turn each criticism into a number measured on the routed "
            "copper, then re-place the board (v2) and measure whether the fixes actually worked.",
    problem="'Put decoupling caps close to the pins' and 'keep channels apart' are easy advice. How much did the first layout violate them, and did the revision fix it?",
    theory=r"""Review criteria and why they matter: (1) decoupling loop — cap → supply pin → ground via; its inductance (~0.8 nH/mm for a 0.25 mm trace 1.6 mm above the plane, see
SL-210) limits how well the cap supplies fast current; (2) the inverting-input node is high-impedance: its copper length adds capacitance and picks up noise;
(3) crosstalk between channels falls roughly as 1/(1+(D/h)²) with separation D; (4) a channel's input copper near its own output copper creates a feedback path.
Prediction for v2 (per-channel connectors, each channel kept on its own side of the dual op-amp, parts hugging their pins): decoupling loops ≥ 2× shorter,
channel separation ≥ 3× larger, shorter feedback nodes.""",
    method="""v1 = SL-205 exactly as routed. v2 = same schematic, but split connectors (IN/OUT per channel on each side), R_f/R_g placed at pins 1–2 / 6–7, 100 nF caps within ~2.5 mm of
pins 4 and 8. Metrics measured on routed copper (tracks + pads, excluding the ground pour).""",
    data="Design (SL-205 v1 and this project's v2).",
)

CH_A = ("IN_L", "INA+", "INA-", "OUTA", "OUT_L"); CH_B = ("IN_R", "INB+", "INB-", "OUTB", "OUT_R")


def load_v1():
    path = ROOT / "projects/signal-lab/L-pcb-design/SL205-amplifier-board/project.py"
    spec = importlib.util.spec_from_file_location("sl205", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    b = m.build_board(); b.route(skip=("GND",)); b.stitch_pad_vias("GND"); b.pour("B", "GND")
    return b


def build_v2():
    b = Board("preamp_v2", 50, 36, Rules())
    b.add("U1", soic(8), 25, 18, 0, "NE5532", "dual op-amp SOIC-8")
    ch = chip("0805")
    # channel A on the left (pins 1-4), channel B on the right (pins 5-8)
    b.add("R2", ch, 19.2, 19.3, 90, "100k"); b.add("R3", ch, 16.2, 18.4, 0, "10k"); b.add("R1", ch, 18.5, 16.2, 0, "100k")
    b.add("C1", ch, 13.5, 16.2, 0, "1uF"); b.add("R4", ch, 15.5, 22.5, 0, "100"); b.add("C4", ch, 21.5, 13.6, 0, "100n")
    b.add("R6", ch, 30.8, 18.0, 90, "100k"); b.add("R7", ch, 33.8, 17.1, 0, "10k"); b.add("R5", ch, 31.5, 14.9, 0, "100k")
    b.add("C2", ch, 36.5, 14.9, 0, "1uF"); b.add("R8", ch, 34.5, 21.2, 0, "100"); b.add("C3", ch, 28.5, 22.4, 0, "100n")
    b.add("J1", header(2), 5, 16, 90, "IN L/GND"); b.add("J2", header(2), 5, 24, 90, "OUT L/GND")
    b.add("J3", header(2), 45, 15, 90, "IN R/GND"); b.add("J4", header(2), 45, 23, 90, "OUT R/GND")
    b.add("J5", header(3), 25, 5, 0, "+12/GND/-12"); b.add("C5", chip("1206"), 18, 5, 0, "10uF"); b.add("C6", chip("1206"), 32, 5, 0, "10uF")
    for k, (x, y) in enumerate(((3.5, 3.5), (46.5, 3.5), (3.5, 32.5), (46.5, 32.5)), 1):
        b.add(f"H{k}", mounting_hole(), x, y)
    b.connect("IN_L", "J1.1", "C1.1"); b.connect("INA+", "C1.2", "R1.2", "U1.3"); b.connect("INA-", "U1.2", "R3.2", "R2.1")
    b.connect("OUTA", "U1.1", "R2.2", "R4.2"); b.connect("OUT_L", "R4.1", "J2.1")
    b.connect("IN_R", "J3.1", "C2.2"); b.connect("INB+", "C2.1", "R5.2", "U1.5"); b.connect("INB-", "U1.6", "R7.1", "R6.1")
    b.connect("OUTB", "U1.7", "R6.2", "R8.1"); b.connect("OUT_R", "R8.2", "J4.1")
    b.connect("+12V", "J5.1", "U1.8", "C3.1", "C6.1"); b.connect("-12V", "J5.3", "U1.4", "C4.2", "C5.1")
    b.connect("GND", "J1.2", "J2.2", "J3.2", "J4.2", "J5.2", "R1.1", "R3.1", "R5.1", "R7.2", "C3.2", "C4.1", "C5.2", "C6.2")
    b.net_widths.update({"+12V": 0.4, "-12V": 0.4})
    return b


def copper_of(b, nets, layer):
    from shapely.geometry import Polygon
    return unary_union([gg for n, gg in b.copper(layer, include_zones=False) if n in nets] or [Polygon()])


def spacing(b, a, c):
    """Smallest same-layer distance between two groups of nets (copper on different layers does not couple directly)."""
    d = []
    for L in ("F", "B"):
        ga, gc = copper_of(b, a, L), copper_of(b, c, L)
        if not ga.is_empty and not gc.is_empty:
            d.append(ga.distance(gc))
    return min(d)


def decap_loop(b, cap, pin):
    """Length of cap→IC-pin supply path (straight-line proxy along routed copper) + cap GND pad → nearest GND via/THT pad."""
    c = b.comp(cap); u = b.comp("U1")
    supply_pad = next(pp.num for pp in c.fp.pads if b.pad_net(cap, pp.num) != "GND")
    gnd_pad = next(pp.num for pp in c.fp.pads if b.pad_net(cap, pp.num) == "GND")
    net = b.pad_net(cap, supply_pad)
    # routed length between the cap pad and the IC pin: shortest path through this net's track graph
    import networkx as nx
    G = nx.Graph()
    key = lambda x, y: (round(x, 3), round(y, 3))
    for t in b.tracks:
        if t.net == net:
            G.add_edge(key(t.x1, t.y1), key(t.x2, t.y2), weight=np.hypot(t.x2 - t.x1, t.y2 - t.y1))
    for v in b.vias:
        if v.net == net:
            G.add_node(key(v.x, v.y))
    def attach(ref, num, tag):
        cc = b.comp(ref); pg = cc.pad(num).geom(cc.x, cc.y, cc.rot); px, py = cc.pad_xy(num)
        G.add_node(tag)
        for n in list(G.nodes):
            if isinstance(n, tuple) and pg.buffer(0.01).contains(Point(n)):
                G.add_edge(tag, n, weight=np.hypot(n[0] - px, n[1] - py))
    attach(cap, supply_pad, "cap"); attach("U1", pin, "pin")
    try:
        L_supply = nx.shortest_path_length(G, "cap", "pin", weight="weight")
    except Exception:
        L_supply = np.nan
    gx, gy = c.pad_xy(gnd_pad)
    L_gnd = min(np.hypot(v.x - gx, v.y - gy) for v in b.vias if v.net == "GND")
    return L_supply, L_gnd


def metrics(b):
    m = {}
    for cap, pin, name in (("C3", "8", "+12V"), ("C4", "4", "-12V")):
        ls, lg = decap_loop(b, cap, pin)
        m[f"decoupling loop {name} (mm)"] = ls + lg
    m["inverting-node copper, INA−+INB− (mm)"] = b.track_length("INA-") + b.track_length("INB-")
    m["channel A ↔ B separation (mm)"] = spacing(b, CH_A, CH_B)
    m["input ↔ output spacing, worst channel (mm)"] = min(spacing(b, ("IN_L", "INA+"), ("OUTA", "OUT_L")), spacing(b, ("IN_R", "INB+"), ("OUTB", "OUT_R")))
    m["total track length (mm)"] = b.track_length()
    m["vias"] = len(b.vias)
    return m


def run(p):
    v1 = load_v1()
    v2 = build_v2()
    fail = v2.route(skip=("GND",))
    p.metric("v2 unrouted connections", sum(len(v) for v in fail.values()), "")
    v2.stitch_pad_vias("GND"); v2.pour("B", "GND")
    publish(p, v2, title="Revised layout (v2): each channel on its own side, parts at their pins.")
    m1, m2 = metrics(v1), metrics(v2)
    for k in m1:
        p.metric(f"{k}: v1 → v2", f"{m1[k]:.1f} → {m2[k]:.1f}")
    for rail in ("+12V", "-12V"):
        k = f"decoupling loop {rail} (mm)"
        p.compare(f"Decoupling loop {rail}: v1/v2 length ratio (≥ 2 predicted)", 2, m1[k] / m2[k], "×", kind="abs", tol=10)
    k = "channel A ↔ B separation (mm)"
    p.compare("Channel separation v2/v1 (≥ 3 predicted)", 3, m2[k] / m1[k], "×", kind="abs", tol=100)
    p.metric("v1 also has channel A and B tracks crossing on opposite layers (broadside coupling through 1.6 mm FR-4)",
             int(any(copper_of(v1, CH_A, "F").intersects(copper_of(v1, CH_B, "B")) or copper_of(v1, CH_A, "B").intersects(copper_of(v1, CH_B, "F")) for _ in [0])), "")
    h = 1.6
    D1, D2 = m1[k] + 0.25, m2[k] + 0.25
    p.metric("Estimated worst-case inter-channel coupling reduction, (1+(D2/h)²)/(1+(D1/h)²)", (1 + (D2 / h) ** 2) / (1 + (D1 / h) ** 2), "×")
    Lper = 0.8
    p.metric("Decoupling-loop inductance estimate v1 → v2 (+12 V rail, 0.8 nH/mm)", f"{m1['decoupling loop +12V (mm)'] * Lper:.0f} → {m2['decoupling loop +12V (mm)'] * Lper:.0f} nH")
    import pandas as pd
    p.csv_df("review_metrics", pd.DataFrame({"metric": list(m1), "v1": list(m1.values()), "v2": list(m2.values())}))
    fig, ax = p.fig(1, 2, w=12, h=5)
    for a, b, t in ((ax[0], v1, "v1 (SL-205)"), (ax[1], v2, "v2 (this review)")):
        plot_board(a, b, ("B", "F"))
        for nets, col in ((CH_A, "#ffd166"), (CH_B, "#9ad1ff")):
            for tr in b.tracks:
                if tr.net in nets:
                    a.plot([tr.x1, tr.x2], [tr.y1, tr.y2], color=col, lw=2.2, zorder=8)
        a.set_title(f"{t}: channel A yellow, channel B blue", loc="left", fontsize=10)
    p.save(fig, "review", "Before and after: v1 interleaves the two channels across the board; v2 keeps each channel on its side of the op-amp.")
    p.discuss(f"""Written as a review, the v1 critique is: (1) the 100 nF caps are placed 'near' the op-amp but their routed supply paths are long
({m1['decoupling loop +12V (mm)']:.0f} mm and {m1['decoupling loop -12V (mm)']:.0f} mm loops); (2) channel A's output must cross the chip to reach the shared output connector, so
the two channels' signal copper comes within {m1['channel A ↔ B separation (mm)']:.2f} mm of each other; (3) the single 3-pin input connector forces channel B's input to travel
across channel A's territory. The v2 layout answers each point with placement, not with rules: per-channel connectors on each side, R_f/R_g
straddling pins 1–2 and 6–7, and each decoupling cap within a few millimetres of its pin. The measured outcome: decoupling loops shrink to
{m2['decoupling loop +12V (mm)']:.0f} and {m2['decoupling loop -12V (mm)']:.0f} mm, channel separation grows to {m2['channel A ↔ B separation (mm)']:.1f} mm, and total copper drops from {m1['total track length (mm)']:.0f} to
{m2['total track length (mm)']:.0f} mm. Not every prediction held: I expected the decoupling loops to shrink ≥ 2×, but they shrank only
{m1['decoupling loop +12V (mm)'] / m2['decoupling loop +12V (mm)']:.1f}× and {m1['decoupling loop -12V (mm)'] / m2['decoupling loop -12V (mm)']:.1f}× — v1's caps were not far away to begin with, and in v2 the stub from each cap's ground pad to its
stitching via is now the larger part of the loop; via-in-pad or a top-side ground pour is the next step. The review also found that v1 routes
channel A and channel B tracks across each other on opposite layers, which couples them broadside through the 1.6 mm board — invisible to a
same-layer clearance check. These are geometric proxies: the crosstalk and inductance numbers are estimates from SL-210's per-length results, not
measurements, and the change of connector pin-out is a real interface change that a review must flag to whoever wires the board.""")
# tol-convention: relative tolerances are in percent
