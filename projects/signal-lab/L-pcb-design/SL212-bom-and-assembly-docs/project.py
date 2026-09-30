from eelab import *
from eelab.core import ROOT
from eelab.pcb import bom, pick_and_place, export_gerbers, plot_board, _rot_bounds
import importlib.util
import warnings

META = dict(
    id="SL-212", title="BOM, pick-and-place and assembly documentation package", level="M",
    tools="eelab.pcb exporters (grouped BOM, centroid/CPL file, Gerber paste layer), gerbonara to re-read the paste layer, matplotlib assembly drawings",
    summary="Produce the documents an assembly house needs for the SL-205 preamp — grouped BOM, pick-and-place file, assembly drawing with pin-1 "
            "marks, fabrication notes — and verify them against each other: every placement's centroid is checked against the solder-paste openings in the Gerber.",
    problem="Assembly errors come from documents that disagree with each other (a rotated centroid, a BOM line that doesn't match the board). Can the package check itself?",
    theory=r"""For a symmetric footprint the placement centroid must coincide with the centroid of its paste openings; for a rotation error of θ the pads of a two-terminal part would
be displaced by half the pad pitch. BOM quantities must sum to the number of placed parts; the paste layer must contain exactly the SMD pads (THT pads get no
paste); every THT part must be listed for hand/wave soldering. I expect all cross-checks to agree exactly (0 mm deviation, 0 missing lines).""",
    method="""Board rebuilt from SL-205's design. Paste Gerber re-read with gerbonara; openings grouped by nearest SMD placement; centroid of each group vs CPL (x, y); rotation checked by comparing the
opening layout with the footprint rotated by the CPL angle.""",
    data="Design (from SL-205).",
)


def load_205():
    path = ROOT / "projects/signal-lab/L-pcb-design/SL205-amplifier-board/project.py"
    spec = importlib.util.spec_from_file_location("sl205", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    b = m.build_board(); b.route(skip=("GND",)); b.stitch_pad_vias("GND"); b.pour("B", "GND")
    return b


def run(p):
    import gerbonara
    import pandas as pd
    b = load_205()
    B = bom(b); cpl = pick_and_place(b)
    p.csv_df("bom", pd.DataFrame(B)); p.csv_df("pick_and_place", pd.DataFrame(cpl))
    paths = export_gerbers(b, p.dir / "fab")
    for k, path in paths.items():
        p.files.append((f"fab/{path.name}", "Gerber/drill (same board as SL-205)"))
    placed = [c for c in b.comps if c.fp.pads and c.fp.pads[0].num != ""]
    p.compare("BOM quantities sum to the number of placed parts", len(placed), sum(r["qty"] for r in B), "", kind="abs")
    p.compare("Pick-and-place rows = placed parts", len(placed), len(cpl), "", kind="abs")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = gerbonara.GerberFile.open(paths["F_Paste"])
    boxes = [o.bounding_box(gerbonara.utils.MM) for o in g.objects]
    ctr = np.array([((a[0] + c[0]) / 2, (a[1] + c[1]) / 2) for a, c in boxes])
    smd = [c for c in placed if not any(pp.drill for pp in c.fp.pads)]
    n_smd_pads = sum(len(c.fp.pads) for c in smd)
    p.compare("Paste openings in the Gerber = SMD pads (THT pads get none)", n_smd_pads, len(ctr), "", kind="abs")
    dev, rot_ok = [], 0
    for c in smd:
        x0, y0, x1, y1 = _rot_bounds(c)
        sel = ctr[(ctr[:, 0] > x0) & (ctr[:, 0] < x1) & (ctr[:, 1] > y0) & (ctr[:, 1] < y1)]
        row = next(r for r in cpl if r["ref"] == c.ref)
        dev.append(np.hypot(sel[:, 0].mean() - row["x_mm"], sel[:, 1].mean() - row["y_mm"]))
        exp = np.array([c.pad_xy(pp.num) for pp in c.fp.pads])
        rot_ok += all(np.min(np.hypot(*(sel - e).T)) < 1e-3 for e in exp)
    p.compare("Max |CPL centroid − paste-opening centroid| over SMD parts", 0, max(dev), "mm", kind="abs", tol=1e-3)
    p.compare("SMD parts whose paste openings match the CPL rotation", len(smd), rot_ok, "", kind="abs")
    tht = [c.ref for c in placed if any(pp.drill for pp in c.fp.pads)]
    p.metric("THT parts for hand/selective soldering", ", ".join(tht), "")
    p.metric("BOM lines / unique values", f"{len(B)} / {len(set(r['value'] for r in B))}")
    notes = f"""# Fabrication and assembly notes — {b.name}

| Item | Specification |
|---|---|
| Layers | 2 (F.Cu, B.Cu) |
| Board size | {b.w} × {b.h} mm, 1 mm corner radius |
| Material / thickness | FR-4, {b.thickness} mm, 1 oz copper both sides |
| Min track / space | {b.rules.min_track} mm / {b.rules.clearance} mm (design uses ≥ {b.rules.track} mm tracks) |
| Min drill / via | {b.rules.via_drill} mm drill, {b.rules.via_dia} mm pad (vias tented) |
| Finish / mask / legend | HASL lead-free or ENIG; green mask; white legend |
| Impedance control | not required |

**Files:** `fab/*.gbr` (RS-274X copper, mask, paste, legend, outline), `fab/*.drl` (Excellon, plated), `data/bom.csv`, `data/pick_and_place.csv`
(top side, mm, rotation counter-clockwise, origin at the lower-left board corner).

**Assembly:** SMD parts on top only; THT parts ({', '.join(tht)}) hand-soldered after reflow. U1 pin 1 is marked on the assembly drawing.
Polarised parts: none among the SMD parts (ceramic capacitors).
"""
    p.write("docs/FAB_NOTES.md", notes, "fabrication & assembly notes")
    fig, ax = p.fig(1, 1, w=9, h=6.8)
    plot_board(ax, b, ("F",), labels=True, show_zones=False)
    for c in placed:
        if c.fp.name.startswith(("SOIC", "PinHeader")):
            x, y = c.pad_xy("1")
            ax.plot(x, y, "o", ms=9, mfc="none", mec="#ffd166", mew=1.5)
        ax.text(c.x, c.y, c.value, color="#9ad1ff", fontsize=5.5, ha="center", va="center", zorder=9)
    ax.set_title("Assembly drawing, top (values in blue, pin 1 circled)", loc="left", fontsize=10)
    p.save(fig, "assembly_top", "Assembly drawing generated from the same data as the BOM and CPL files.")
    p.discuss(f"""Because the BOM, the pick-and-place file, the Gerbers and the drawing are all generated from one board model, they agree — and the checks prove it
rather than assume it: quantities add up, every SMD part's centroid sits exactly on the centre of its own paste openings, and the openings match
the stated rotation. The paste layer correctly omits the {len(tht)} through-hole parts. Two things a real assembly house would still ask for that
this package cannot supply honestly: manufacturer part numbers with stock/lifecycle status (this BOM gives values and footprints only; no
prices are invented), and a confirmation of each part's rotation convention against their machine library — the zero-rotation orientation
of a footprint is a convention that differs between CAD tools, which is the most common real-world pick-and-place error.""")
# tol-convention: relative tolerances are in percent
