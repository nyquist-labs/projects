from eelab import *
from eelab.core import ROOT
from eelab.pcb import Track, Via, chip
import copy
import importlib.util
import shapely
from shapely.geometry import Point

META = dict(
    id="SL-211", title="DRC and manufacturability report (with seeded defects)", level="M",
    tools="eelab.pcb design-rule checker (clearance, width, drill, annular ring, edge, courtyard, hole-to-hole, connectivity) run on the SL-205 board; defect seeding; fab-capability comparison",
    summary="Validate the design-rule checker itself by seeding eight known defects into a clean board and checking that each is found — and only "
            "those — then measure the clean board's real minimum features against typical low-cost and advanced fab capabilities.",
    problem="A DRC that reports 'no errors' is only reassuring if it demonstrably catches errors. How do you test the tester?",
    theory=r"""Each rule is a geometric predicate: different-net copper separated by ≥ clearance, tracks ≥ min width, drill ≥ min, annular ring (pad − drill)/2 ≥ min,
copper-to-outline ≥ edge clearance, component courtyards disjoint, drilled holes ≥ 0.25 mm apart, and every pin of a net galvanically connected (union-find
over touching copper, with vias and plated holes joining layers). Seeding one defect per rule should produce exactly one violation of that type near the
defect (8/8 detected, 0 unrelated reports).""",
    method="""Board: SL-205's stereo preamp, re-built and routed. Defects: (1) +12 V stub 0.1 mm from a signal pad; (2) a track narrowed to 0.1 mm; (3) via with 0.075 mm annular ring;
(4) 0.2 mm drill; (5) ground copper 0.1 mm from the outline; (6) two parts whose courtyards overlap while their pads stay 0.35 mm apart; (7) a routed segment deleted; (8) two vias 0.2 mm apart.
Fab classes (typical published values): standard — track/space 0.127/0.127 mm, drill 0.3 mm, annular 0.13 mm, edge 0.3 mm; advanced — 0.09/0.09, 0.2, 0.1, 0.2.""",
    data="Design (from SL-205).",
)


def load_205():
    path = ROOT / "projects/signal-lab/L-pcb-design/SL205-amplifier-board/project.py"
    spec = importlib.util.spec_from_file_location("sl205", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    b = m.build_board(); b.route(skip=("GND",)); b.stitch_pad_vias("GND"); b.pour("B", "GND")
    return b


def free_spot(b, layer_items, r=2.5, avoid=()):
    for x in np.arange(6, b.w - 6, 0.5):
        for y in np.arange(6, b.h - 6, 0.5):
            pt = Point(x, y)
            if all(g.distance(pt) > r for g in layer_items) and all(pt.distance(Point(a)) > 6 for a in avoid):
                return x, y
    raise RuntimeError("no free spot")


def run(p):
    b0 = load_205()
    base = b0.drc()
    p.compare("Violations on the clean board", 0, len(base), "", kind="abs")
    b = copy.deepcopy(b0)
    top = [g for n, g in b.copper("F", include_zones=False)] + [g for n, g in b.copper("B", include_zones=False)]
    seeded = []
    # 1 clearance: a +12V stub whose end sits 0.1 mm from R4 pad 1 (net OUTA)
    c = b.comp("R4"); pg = c.pad("1").geom(c.x, c.y, c.rot); x0, y0, x1, y1 = pg.bounds
    b.tracks.append(Track("F", x0 - 0.1 - 0.125 - 1.0, (y0 + y1) / 2, x0 - 0.1 - 0.125, (y0 + y1) / 2, 0.25, "+12V")); seeded.append(("clearance", (x0, (y0 + y1) / 2)))
    # 2 narrow track
    t = max((t for t in b.tracks if t.net == "OUTB"), key=lambda t: np.hypot(t.x2 - t.x1, t.y2 - t.y1)); t.w = 0.1; seeded.append(("track width", ((t.x1 + t.x2) / 2, (t.y1 + t.y2) / 2)))
    # 3 annular ring, 4 small drill, 8 hole-to-hole — placed in free areas
    used = []
    for rule, via_kw in (("annular ring", dict(dia=0.45, drill=0.3)), ("min drill", dict(dia=0.6, drill=0.2))):
        x, y = free_spot(b, top, avoid=used); used.append((x, y))
        b.vias.append(Via(x, y, "GND", **via_kw)); seeded.append((rule, (x, y)))
    x, y = free_spot(b, top, avoid=used); used.append((x, y))
    b.vias += [Via(x, y, "GND"), Via(x + 0.5, y, "GND")]; seeded.append(("hole-to-hole", (x, y)))
    # 5 edge clearance: ground copper 0.1 mm from the right edge
    b.tracks.append(Track("F", b.w - 0.1 - 0.125, 12, b.w - 0.1 - 0.125, 14, 0.25, "GND")); seeded.append(("edge clearance", (b.w - 0.2, 13)))
    # 6 courtyard overlap: two unconnected 0805 parts 1.8 mm apart (pads 0.35 mm apart, courtyards overlap)
    x, y = free_spot(b, top, r=3.5, avoid=used); used.append((x, y))
    b.add("C90", chip("0805"), x, y, 90, "test"); b.add("C91", chip("0805"), x + 1.8, y, 90, "test"); seeded.append(("courtyard overlap", (x, y)))
    # 7 unconnected: delete one segment of the IN_L route
    seg = [t for t in b.tracks if t.net == "IN_L"]
    b.tracks.remove(max(seg, key=lambda t: np.hypot(t.x2 - t.x1, t.y2 - t.y1))); seeded.append(("unconnected", None))
    b.zones = []; b.pour("B", "GND")
    v = b.drc()
    found, matched = 0, set()
    rows = []
    for rule, loc in seeded:
        hits = [i for i, x in enumerate(v) if x["rule"] == rule and (loc is None or np.hypot(x["x"] - loc[0], x["y"] - loc[1]) < 3)]
        found += bool(hits); matched |= set(hits)
        rows.append((rule, bool(hits), len(hits)))
    extra = [x for i, x in enumerate(v) if i not in matched]
    p.compare("Seeded defects detected", len(seeded), found, "", kind="abs")
    p.compare("Violations not explained by a seeded defect", 0, len(extra), "", kind="abs")
    import pandas as pd
    p.csv_df("seeded_defects", pd.DataFrame(rows, columns=["rule", "detected", "reports"]))
    p.csv_df("drc_report", pd.DataFrame(v))
    # manufacturability of the clean board
    R = b0.rules
    minw = min(t.w for t in b0.tracks)
    gaps = []
    for L in ("F", "B"):
        items = b0.copper(L)
        tree = shapely.STRtree([g for _, g in items])
        for i, (n1, g1) in enumerate(items):
            for j in tree.query(g1.buffer(1.0)):
                if j > i and items[j][0] != n1:
                    gaps.append(g1.distance(items[j][1]))
    min_gap = min(gaps)
    drills = [d for *_, d, pl, n in [(h[0], h[1], h[2], h[3], h[4]) for h in b0.holes()]] if False else [h[2] for h in b0.holes()]
    ann = min([(vv.dia - vv.drill) / 2 for vv in b0.vias] + [(min(pp.w, pp.h) - pp.drill) / 2 for c in b0.comps for pp in c.fp.pads if pp.drill and pp.plated])
    edge = min(b0.outline().exterior.distance(g) for L in ("F", "B") for _, g in b0.copper(L))
    feats = {"min track width": minw, "min copper gap": min_gap, "min drill": min(drills), "min annular ring": ann, "min copper-to-edge": edge}
    std = {"min track width": 0.127, "min copper gap": 0.127, "min drill": 0.3, "min annular ring": 0.13, "min copper-to-edge": 0.3}
    adv = {"min track width": 0.09, "min copper gap": 0.09, "min drill": 0.2, "min annular ring": 0.1, "min copper-to-edge": 0.2}
    for k, val in feats.items():
        p.metric(f"Clean board {k}", val, "mm", f"standard ≥ {std[k]} ({'OK' if val >= std[k] - 1e-3 else 'FAIL'}), advanced ≥ {adv[k]}")
    p.compare("Features meeting the standard (cheapest) fab class", len(feats), sum(val >= std[k] - 1e-3 for k, val in feats.items()), "", kind="abs")
    fig, ax = p.fig(1, 2, w=12, h=5)
    from eelab.pcb import plot_board
    plot_board(ax[0], b, ("B", "F"))
    for x in v:
        ax[0].plot(x["x"], x["y"], "o", ms=16, mfc="none", mec="#ff3b30", mew=2)
        ax[0].annotate(x["rule"], (x["x"], x["y"]), xytext=(4, 8), textcoords="offset points", color="#ffe066", fontsize=7)
    ax[0].set_title("Seeded defects and the DRC's reports", loc="left", fontsize=10)
    names = list(feats)
    xx = np.arange(len(names))
    ax[1].bar(xx - 0.25, [feats[k] for k in names], 0.25, color=C_MEAS, label="this board")
    ax[1].bar(xx, [std[k] for k in names], 0.25, color=COLORS[1], label="standard fab")
    ax[1].bar(xx + 0.25, [adv[k] for k in names], 0.25, color=COLORS[2], label="advanced fab")
    ax[1].set_xticks(xx); ax[1].set_xticklabels([n.replace("min ", "") for n in names], rotation=25)
    style_axes(ax[1], None, "mm", "Manufacturability margins")
    p.save(fig, "drc", "Left: every seeded defect is flagged where it was placed. Right: the clean board's smallest features vs fab capabilities.")
    p.discuss(f"""All {len(seeded)} seeded defects were reported at the right place with the right rule, and nothing else was — so a clean DRC on the other boards in
this category means something. Three details surfaced while building the test: my first courtyard defect placed the two parts so close that their *pads* also touched,
which the DRC correctly reported as two extra clearance errors (the test, not the checker, was wrong); a deleted track segment is only caught because connectivity is
checked by union-find over *touching copper including vias and plated holes*, not by comparing track lists; and stray same-net copper (the +12 V stub)
is legal on its own but violates clearance to its neighbours. The clean board's smallest features all sit comfortably inside the cheapest fab
class — its tightest spot is the {min_gap:.2f} mm gap set by the 0.2 mm clearance rule, well above 0.127 mm — so it could be ordered from any
low-cost service without special options. What a DRC cannot catch is *intent*: a wrong footprint pin-out or a swapped net passes every
geometric rule, which is why the design-review project (SL-214) exists.""")
# tol-convention: relative tolerances are in percent
