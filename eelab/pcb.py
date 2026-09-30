"""A small, dependency-light PCB toolkit: footprints (incl. IPC-7351 land-pattern maths), a
2-layer grid maze router (A*), copper pours, design-rule checks, and exporters for Gerber
RS-274X, Excellon drill, KiCad .kicad_pcb, BOM and pick-and-place files, plus plots.

Coordinates are millimetres with y pointing up (Gerber convention); the KiCad exporter flips y.
Component rotation is restricted to multiples of 90 degrees.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

# ------------------------------------------------------------------ footprints


@dataclass
class Pad:
    num: str
    x: float
    y: float
    w: float
    h: float
    shape: str = "rect"          # rect | circle | oval | roundrect
    drill: float | None = None   # None = SMD
    plated: bool = True

    def geom(self, cx=0.0, cy=0.0, rot=0, grow=0.0):
        x, y, w, h = _rot_pad(self.x, self.y, self.w, self.h, rot)
        x += cx; y += cy
        w += 2 * grow; h += 2 * grow
        if self.shape == "circle":
            return Point(x, y).buffer(w / 2, quad_segs=12)
        if self.shape == "oval":
            r = min(w, h) / 2
            if w >= h:
                return LineString([(x - w / 2 + r, y), (x + w / 2 - r, y)]).buffer(r, quad_segs=12)
            return LineString([(x, y - h / 2 + r), (x, y + h / 2 - r)]).buffer(r, quad_segs=12)
        if self.shape == "roundrect":
            r = 0.25 * min(w, h)
            return box(x - w / 2 + r, y - h / 2 + r, x + w / 2 - r, y + h / 2 - r).buffer(r, quad_segs=6)
        return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _rot_pad(x, y, w, h, rot):
    rot %= 360
    if rot == 0:
        return x, y, w, h
    if rot == 90:
        return -y, x, h, w
    if rot == 180:
        return -x, -y, w, h
    return y, -x, h, w


@dataclass
class Footprint:
    name: str
    pads: list
    body: tuple = (1.0, 1.0)       # body size (x, y) for silk/courtyard/3-D
    height: float = 1.0
    courtyard: float = 0.25
    thru: bool = False
    edge_ok: bool = False          # edge-launch connectors may reach the board edge

    def bbox(self):
        g = unary_union([p.geom() for p in self.pads] + [box(-self.body[0] / 2, -self.body[1] / 2, self.body[0] / 2, self.body[1] / 2)])
        return g.bounds


def ipc_chip(L, W, T, Jt=0.35, Jh=0.0, Js=0.0, F=0.05, P=0.025):
    """IPC-7351-style land pattern for a two-terminal chip. L, W, T are (min, max) body length,
    body width and terminal length. Returns (pad length, pad width, centre-to-centre pitch)."""
    Lmin, Lmax = L; Wmin, Wmax = W; Tmin, Tmax = T
    CL, CW, CT = Lmax - Lmin, Wmax - Wmin, Tmax - Tmin
    Smin, Smax = Lmin - 2 * Tmax, Lmax - 2 * Tmin
    CS = math.sqrt(CL ** 2 + 2 * CT ** 2)          # IPC-7351: the gap tolerance is the RMS of its parts, centred on the nominal gap
    Smax = Smax - ((Smax - Smin) - CS) / 2
    Z = Lmin + 2 * Jt + math.sqrt(CL ** 2 + F ** 2 + P ** 2)
    G = Smax - 2 * Jh - math.sqrt(CS ** 2 + F ** 2 + P ** 2)
    X = Wmin + 2 * Js + math.sqrt(CW ** 2 + F ** 2 + P ** 2)
    rnd = lambda v: round(v * 20) / 20       # round to 0.05 mm
    Z, G, X = rnd(Z), rnd(G), rnd(X)
    return (Z - G) / 2, X, (Z + G) / 2


def ipc_gullwing(E, Lead, b, Jt=0.35, Jh=0.35, Js=0.03, F=0.05, P=0.025):
    """Gull-wing leads (SOIC/SOT): E = overall lead span, Lead = foot length, b = lead width (min, max)."""
    Emin, Emax = E; Lmin, Lmax = Lead; bmin, bmax = b
    CL, CW, CLead = Emax - Emin, bmax - bmin, Lmax - Lmin
    Smin, Smax = Emin - 2 * Lmax, Emax - 2 * Lmin
    CS = math.sqrt(CL ** 2 + 2 * CLead ** 2)       # RMS tolerance for the inner gap, centred on the nominal (IPC-7351)
    Smax = Smax - ((Smax - Smin) - CS) / 2
    Z = Emin + 2 * Jt + math.sqrt(CL ** 2 + F ** 2 + P ** 2)
    G = Smax - 2 * Jh - math.sqrt(CS ** 2 + F ** 2 + P ** 2)
    X = bmin + 2 * Js + math.sqrt(CW ** 2 + F ** 2 + P ** 2)
    rnd = lambda v: round(v * 20) / 20
    Z, G, X = rnd(Z), rnd(G), rnd(X)
    return (Z - G) / 2, X, (Z + G) / 2


# typical body dimensions (min, max) in mm — resistor/capacitor chip packages per common manufacturer datasheets (approximate)
CHIP_DIMS = {
    "0402": ((0.90, 1.10), (0.40, 0.60), (0.10, 0.40)),
    "0603": ((1.45, 1.75), (0.65, 0.95), (0.15, 0.50)),
    "0805": ((1.80, 2.20), (1.05, 1.45), (0.20, 0.60)),
    "1206": ((3.00, 3.40), (1.40, 1.80), (0.25, 0.75)),
}


def chip(code="0805", height=0.5):
    L, W, T = CHIP_DIMS[code]
    pl, pw, c = ipc_chip(L, W, T)
    pads = [Pad("1", -c / 2, 0, pl, pw, "roundrect"), Pad("2", c / 2, 0, pl, pw, "roundrect")]
    return Footprint(f"C_{code}", pads, (L[1], W[1]), height)


def soic(n=8, pitch=1.27):
    pl, pw, c = ipc_gullwing((5.80, 6.20), (0.40, 1.27), (0.31, 0.51))
    half = n // 2
    pads = []
    for i in range(half):
        y = (half - 1) / 2 * pitch - i * pitch
        pads.append(Pad(str(i + 1), -c / 2, y, pl, pw, "roundrect"))
    for i in range(half):
        y = -(half - 1) / 2 * pitch + i * pitch
        pads.append(Pad(str(half + i + 1), c / 2, y, pl, pw, "roundrect"))
    return Footprint(f"SOIC-{n}", pads, (3.9, (half - 1) * pitch + 1.2), 1.5)


def sot23(n=3):
    pl, pw, c = ipc_gullwing((2.10, 2.64), (0.30, 0.60), (0.30, 0.50))
    if n == 3:
        pads = [Pad("1", -c / 2, 0.95, pl, pw, "roundrect"), Pad("2", -c / 2, -0.95, pl, pw, "roundrect"), Pad("3", c / 2, 0, pl, pw, "roundrect")]
    else:  # SOT-23-5
        pads = [Pad("1", -c / 2, 0.95, pl, pw, "roundrect"), Pad("2", -c / 2, 0, pl, pw, "roundrect"), Pad("3", -c / 2, -0.95, pl, pw, "roundrect"),
                Pad("4", c / 2, -0.95, pl, pw, "roundrect"), Pad("5", c / 2, 0.95, pl, pw, "roundrect")]
    return Footprint(f"SOT-23-{n}", pads, (1.6, 2.9), 1.1)


def dip(n=8, pitch=2.54, row=7.62):
    half = n // 2
    pads = []
    for i in range(half):
        pads.append(Pad(str(i + 1), -row / 2, (half - 1) / 2 * pitch - i * pitch, 1.6, 1.6, "rect" if i == 0 else "oval", 0.8))
    for i in range(half):
        pads.append(Pad(str(half + i + 1), row / 2, -(half - 1) / 2 * pitch + i * pitch, 1.6, 1.6, "oval", 0.8))
    return Footprint(f"DIP-{n}", pads, (6.4, half * pitch), 3.5, thru=True)


def header(n, rows=1, pitch=2.54):
    pads = []
    k = 1
    for i in range(n):
        for r in range(rows):
            pads.append(Pad(str(k), i * pitch - (n - 1) * pitch / 2, -r * pitch + (rows - 1) * pitch / 2, 1.7, 1.7, "rect" if k == 1 else "circle", 1.0))
            k += 1
    return Footprint(f"PinHeader_{rows}x{n:02d}_P{pitch}mm", pads, (n * pitch, rows * pitch), 8.5, thru=True)


def to220():
    pads = [Pad(str(i + 1), (i - 1) * 2.54, 0, 1.8, 2.4, "rect" if i == 0 else "oval", 1.1) for i in range(3)]
    return Footprint("TO-220-3_Vertical", pads, (10.0, 4.5), 15.0, thru=True)


def radial_cap(pitch=2.5, dia=6.3):
    pads = [Pad("1", -pitch / 2, 0, 1.6, 1.6, "rect", 0.8), Pad("2", pitch / 2, 0, 1.6, 1.6, "circle", 0.8)]
    return Footprint(f"CP_Radial_D{dia}mm_P{pitch}mm", pads, (dia, dia), 11.0, thru=True)


def terminal(n=2, pitch=5.08):
    pads = [Pad(str(i + 1), (i - (n - 1) / 2) * pitch, 0, 2.6, 2.6, "rect" if i == 0 else "circle", 1.3) for i in range(n)]
    return Footprint(f"TerminalBlock_1x{n:02d}_P{pitch}mm", pads, (n * pitch, 7.6), 10.0, thru=True)


def sma_edge():
    pads = [Pad("1", 0, 0, 1.5, 4.0, "rect"), Pad("2", -2.825, 0, 1.35, 4.0, "rect"), Pad("3", 2.825, 0, 1.35, 4.0, "rect")]
    return Footprint("SMA_EdgeMount", pads, (6.35, 4.0), 6.35, edge_ok=True)


def mounting_hole(d=3.2):
    return Footprint(f"MountingHole_{d}mm", [Pad("", 0, 0, d, d, "circle", d, plated=False)], (d, d), 0.0, thru=True)


def testpoint():
    return Footprint("TestPoint_Pad_D1.5mm", [Pad("1", 0, 0, 1.5, 1.5, "circle")], (1.5, 1.5), 0.05)


# ------------------------------------------------------------------ board model


@dataclass
class Component:
    ref: str
    fp: Footprint
    x: float
    y: float
    rot: int = 0
    value: str = ""
    mpn: str = ""
    side: str = "F"

    def pad(self, num):
        return next(p for p in self.fp.pads if p.num == str(num))

    def pad_xy(self, num):
        p = self.pad(num)
        x, y, _, _ = _rot_pad(p.x, p.y, p.w, p.h, self.rot)
        return self.x + x, self.y + y

    def pad_layers(self, p):
        return ("F", "B") if p.drill else (self.side,)


@dataclass
class Rules:
    clearance: float = 0.2
    track: float = 0.25
    via_drill: float = 0.3
    via_dia: float = 0.6
    min_drill: float = 0.3
    min_annular: float = 0.13
    edge_clearance: float = 0.3
    min_track: float = 0.15


@dataclass
class Track:
    layer: str
    x1: float
    y1: float
    x2: float
    y2: float
    w: float
    net: str

    def geom(self):
        return LineString([(self.x1, self.y1), (self.x2, self.y2)]).buffer(self.w / 2, quad_segs=8) if (self.x1, self.y1) != (self.x2, self.y2) \
            else Point(self.x1, self.y1).buffer(self.w / 2, quad_segs=8)


@dataclass
class Via:
    x: float
    y: float
    net: str
    dia: float = 0.6
    drill: float = 0.3

    def geom(self):
        return Point(self.x, self.y).buffer(self.dia / 2, quad_segs=12)


@dataclass
class Board:
    name: str
    w: float
    h: float
    rules: Rules = field(default_factory=Rules)
    thickness: float = 1.6
    comps: list = field(default_factory=list)
    nets: dict = field(default_factory=dict)          # net -> list of (ref, pad)
    tracks: list = field(default_factory=list)
    vias: list = field(default_factory=list)
    zones: list = field(default_factory=list)         # (layer, net, polygon geometry)
    zone_requests: list = field(default_factory=list)  # (layer, net)
    net_widths: dict = field(default_factory=dict)
    pin_widths: dict = field(default_factory=dict)      # (ref, pin) -> track width for that pin's connection (e.g. a sense/feedback tap)
    corner_r: float = 1.0
    layers: tuple = ("F", "B")
    shape: object = None            # optional custom outline polygon (overrides the rounded rectangle)

    # -------------------------------------------------------------- building
    def add(self, ref, fp, x, y, rot=0, value="", mpn="", side="F"):
        c = Component(ref, fp, x, y, rot, value, mpn, side)
        self.comps.append(c)
        return c

    def comp(self, ref):
        return next(c for c in self.comps if c.ref == ref)

    def connect(self, net, *pins):
        """pins: 'R1.1' strings"""
        lst = self.nets.setdefault(net, [])
        for s in pins:
            ref, num = s.split(".")
            lst.append((ref, num))

    def outline(self):
        if self.shape is not None:
            return self.shape
        r = self.corner_r
        return box(r, r, self.w - r, self.h - r).buffer(r, quad_segs=8) if r > 0 else box(0, 0, self.w, self.h)

    def pad_net(self, ref, num):
        for n, pins in self.nets.items():
            if (ref, str(num)) in pins:
                return n
        return None

    # -------------------------------------------------------------- copper queries
    def pad_geoms(self, grow=0.0):
        """list of (layer, net, geometry, comp, pad)"""
        out = []
        for c in self.comps:
            for p in c.fp.pads:
                g = p.geom(c.x, c.y, c.rot, grow)
                net = self.pad_net(c.ref, p.num)
                if p.drill and not p.plated:
                    continue
                for L in c.pad_layers(p):
                    out.append((L, net, g, c, p))
        return out

    def copper(self, layer, include_zones=True):
        """list of (net, geometry) on a copper layer"""
        items = [(n, g) for L, n, g, _, _ in self.pad_geoms() if L == layer]
        items += [(t.net, t.geom()) for t in self.tracks if t.layer == layer]
        items += [(v.net, v.geom()) for v in self.vias]
        if include_zones:
            items += [(n, g) for L, n, g in self.zones if L == layer]
        return items

    def holes(self):
        out = []
        for c in self.comps:
            for p in c.fp.pads:
                if p.drill:
                    x, y = c.pad_xy(p.num) if p.num else (c.x, c.y)
                    out.append((x, y, p.drill, p.plated, self.pad_net(c.ref, p.num) if p.num else None))
        for v in self.vias:
            out.append((v.x, v.y, v.drill, True, v.net))
        return out

    # -------------------------------------------------------------- routing
    def route(self, order=None, grid=0.25, via_cost=12, layers=None, max_expand=400000, skip=()):
        """Route all nets (except `skip`, e.g. nets that will be poured) with an A* maze router.
        Returns dict net -> list of failed connections."""
        layers = layers or list(self.layers)
        nx, ny = int(self.w / grid) + 1, int(self.h / grid) + 1
        xs, ys = np.arange(nx) * grid, np.arange(ny) * grid
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        outline_in = self.outline().buffer(-self.rules.edge_clearance)
        failures = {}
        nets = [n for n in (order or sorted(self.nets, key=lambda n: self._net_span(n))) if n not in skip and len(self.nets[n]) > 1]
        for net in nets:
            w_net = self.net_widths.get(net, self.rules.track)
            cache = {}

            def maps(w):
                if w in cache:
                    return cache[w]
                inside = shapely.contains_xy(outline_in.buffer(-w / 2), X, Y)
                free, via_ok = {}, None
                for L in layers:
                    other = [g for n, g in self.copper(L) if n != net]
                    blk = unary_union(other).buffer(self.rules.clearance + w / 2) if other else Polygon()
                    free[L] = inside & ~shapely.contains_xy(blk, X, Y)
                    vb = unary_union(other).buffer(self.rules.clearance + self.rules.via_dia / 2) if other else Polygon()
                    vok = shapely.contains_xy(outline_in.buffer(-self.rules.via_dia / 2), X, Y) & ~shapely.contains_xy(vb, X, Y)
                    via_ok = vok if via_ok is None else via_ok & vok
                cache[w] = (free, via_ok)
                return cache[w]
            pins = self.nets[net]
            pads = []
            for ref, num in pins:
                c = self.comp(ref); p = c.pad(num)
                pads.append((c, p, p.geom(c.x, c.y, c.rot), c.pad_layers(p)))
            done = [0]
            todo = list(range(1, len(pads)))
            while todo:
                ctr = lambda k: np.array(pads[k][2].centroid.coords[0])
                j = min(todo, key=lambda k: min(np.linalg.norm(ctr(k) - ctr(d)) for d in done))
                todo.remove(j)
                w = self.pin_widths.get((pads[j][0].ref, pads[j][1].num), w_net)
                free, via_ok = maps(w)
                # track ends may only sit where the whole track width is legal: clear of other nets, or deep inside own copper
                goal, src = {}, {}
                for L in layers:
                    tree = [pads[d][2] for d in done if L in pads[d][3]]
                    tree += [t.geom() for t in self.tracks if t.net == net and t.layer == L]
                    tree += [v.geom() for v in self.vias if v.net == net]
                    if tree:
                        tu = unary_union(tree)
                        goal[L] = shapely.contains_xy(tu, X, Y) & (free[L] | shapely.contains_xy(tu.buffer(-w / 2 + 1e-3), X, Y))
                    else:
                        goal[L] = np.zeros_like(X, bool)
                    if L in pads[j][3]:
                        pg = pads[j][2]
                        src[L] = shapely.contains_xy(pg, X, Y) & (free[L] | shapely.contains_xy(pg.buffer(-w / 2 + 1e-3), X, Y))
                        if not src[L].any():                     # tiny pad: start from the cell nearest its centre
                            cx, cy = pg.centroid.coords[0]
                            k = (int(round(cx / grid)), int(round(cy / grid)))
                            src[L] = np.zeros_like(X, bool); src[L][k] = True
                    else:
                        src[L] = np.zeros_like(X, bool)
                path = _astar(src, goal, free, via_ok, layers, via_cost, max_expand)
                if path is None:
                    failures.setdefault(net, []).append(f"{pads[j][0].ref}.{pads[j][1].num}")
                else:
                    self._commit(path, xs, ys, net, w)
                    cache.clear()                                # own copper changed; other nets' maps unaffected but keep it simple
                done.append(j)
        return failures

    def _net_span(self, net):
        pts = np.array([self.comp(r).pad_xy(n) for r, n in self.nets[net]])
        return np.ptp(pts[:, 0]) + np.ptp(pts[:, 1]) if len(pts) > 1 else 0

    def _commit(self, path, xs, ys, net, w):
        # path: list of (layer, i, j); merge collinear steps into segments, add vias at layer changes
        seg_start = path[0]
        prev = path[0]
        prev_dir = None
        for cur in path[1:] + [None]:
            if cur is not None and cur[0] != prev[0]:
                if (seg_start[1], seg_start[2]) != (prev[1], prev[2]):
                    self.tracks.append(Track(prev[0], xs[seg_start[1]], ys[seg_start[2]], xs[prev[1]], ys[prev[2]], w, net))
                self.vias.append(Via(xs[prev[1]], ys[prev[2]], net, self.rules.via_dia, self.rules.via_drill))
                seg_start, prev, prev_dir = cur, cur, None
                continue
            d = None if cur is None else (cur[1] - prev[1], cur[2] - prev[2])
            if cur is None or (prev_dir is not None and d != prev_dir):
                if (seg_start[1], seg_start[2]) != (prev[1], prev[2]):
                    self.tracks.append(Track(prev[0], xs[seg_start[1]], ys[seg_start[2]], xs[prev[1]], ys[prev[2]], w, net))
                seg_start = prev
            prev_dir = d
            if cur is not None:
                prev = cur

    # -------------------------------------------------------------- pours
    def pour(self, layer, net, clearance=None):
        """Fill the board on `layer` with `net`, keeping only islands that touch that net's copper."""
        cl = clearance or self.rules.clearance
        area = self.outline().buffer(-self.rules.edge_clearance - 0.01)
        other = [g for n, g in self.copper(layer, include_zones=False) if n != net]
        # plated holes of other nets need clearance on every layer
        other += [Point(x, y).buffer(d / 2 + 0.1) for x, y, d, pl, n in self.holes() if n != net]
        fill = area.difference(unary_union(other).buffer(cl + 0.01)) if other else area   # 10 µm margin for polygonised arcs
        mine = unary_union([g for n, g in self.copper(layer, include_zones=False) if n == net] or [Polygon()])
        polys = [g for g in getattr(fill, "geoms", [fill]) if not g.is_empty and g.intersects(mine)]
        polys = [p.buffer(-0.1).buffer(0.1) for p in polys]          # remove slivers narrower than 0.2 mm
        polys = [q for p in polys for q in getattr(p, "geoms", [p]) if q.area > 0.5 and q.intersects(mine)]
        self.zones = [z for z in self.zones if not (z[0] == layer and z[1] == net)]
        for p in polys:
            self.zones.append((layer, net, p))
        self.zone_requests.append((layer, net))
        return polys

    def stitch_pad_vias(self, net, zone_layer="B", offset=1.0):
        """Drop a via next to every SMD pad of `net` on the other layer so it reaches the pour (adds a short stub)."""
        added = 0
        for ref, num in self.nets[net]:
            c = self.comp(ref); p = c.pad(num)
            if p.drill or c.side == zone_layer:
                continue
            px, py = c.pad_xy(num)
            g = p.geom(c.x, c.y, c.rot)
            best = None
            for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                for r in (offset, offset + 0.5, offset + 1.0, offset + 1.6):
                    vx, vy = px + r * np.cos(ang), py + r * np.sin(ang)
                    vg = Point(vx, vy).buffer(self.rules.via_dia / 2)
                    stub = Track(c.side, px, py, vx, vy, self.rules.track, net)
                    ok = self.outline().buffer(-self.rules.edge_clearance - self.rules.via_dia / 2).contains(Point(vx, vy))
                    for L in ("F", "B"):
                        for n, og in self.copper(L, include_zones=False):
                            if n != net and (vg.distance(og) < self.rules.clearance or (L == c.side and stub.geom().distance(og) < self.rules.clearance)):
                                ok = False
                                break
                        if not ok:
                            break
                    if ok:
                        best = (vx, vy, stub)
                        break
                if best:
                    break
            if best:
                self.tracks.append(best[2]); self.vias.append(Via(best[0], best[1], net, self.rules.via_dia, self.rules.via_drill)); added += 1
        return added

    # -------------------------------------------------------------- checks
    def drc(self):
        """Returns list of violation dicts: {rule, detail, x, y}."""
        R = self.rules
        v = []
        edge = self.outline()
        exempt = unary_union([p.geom(c.x, c.y, c.rot, 0.5) for c in self.comps if c.fp.edge_ok for p in c.fp.pads] or [Polygon()])
        for L in self.layers:
            items = self.copper(L)
            geoms = [g for _, g in items]
            tree = shapely.STRtree(geoms)
            for i, (n1, g1) in enumerate(items):
                for j in tree.query(g1.buffer(R.clearance)):
                    if j <= i:
                        continue
                    n2, g2 = items[j]
                    if n1 == n2 and n1 is not None:
                        continue
                    if n1 is None and n2 is None and g1.equals(g2):
                        continue
                    d = g1.distance(g2)
                    if d < R.clearance - 1e-3:
                        p = shapely.ops.nearest_points(g1, g2)[0]
                        v.append(dict(rule="clearance", layer=L, detail=f"{n1} ↔ {n2}: {d:.3f} mm < {R.clearance}", x=p.x, y=p.y))
                if (edge.exterior.distance(g1) < R.edge_clearance - 1e-3 or not edge.contains(g1)) and not (g1.intersects(exempt) and g1.area < exempt.area * 4):
                    c = g1.centroid
                    v.append(dict(rule="edge clearance", layer=L, detail=f"{n1}: {edge.exterior.distance(g1):.3f} mm", x=c.x, y=c.y))
        for t in self.tracks:
            if t.w < R.min_track - 1e-9:
                v.append(dict(rule="track width", layer=t.layer, detail=f"{t.net}: {t.w} mm < {R.min_track}", x=(t.x1 + t.x2) / 2, y=(t.y1 + t.y2) / 2))
        for vi in self.vias:
            if (vi.dia - vi.drill) / 2 < R.min_annular - 1e-9:
                v.append(dict(rule="annular ring", layer="F/B", detail=f"via {vi.net}: {(vi.dia - vi.drill) / 2:.3f} mm", x=vi.x, y=vi.y))
        hl = self.holes()
        for i, (x, y, d, pl, n) in enumerate(hl):
            if d < R.min_drill - 1e-9:
                v.append(dict(rule="min drill", layer="drill", detail=f"{d} mm", x=x, y=y))
            for x2, y2, d2, _, n2 in hl[i + 1:]:
                gap = math.hypot(x - x2, y - y2) - (d + d2) / 2
                if gap < 0.25 and not (x == x2 and y == y2 and n == n2):
                    v.append(dict(rule="hole-to-hole", layer="drill", detail=f"{gap:.3f} mm", x=x, y=y))
        # courtyard overlaps (same side)
        cy = [(c, box(*_rot_bounds(c))) for c in self.comps]
        for i, (c1, b1) in enumerate(cy):
            for c2, b2 in cy[i + 1:]:
                if c1.side == c2.side and b1.intersection(b2).area > 1e-6:
                    v.append(dict(rule="courtyard overlap", layer=c1.side, detail=f"{c1.ref} ↔ {c2.ref}", x=b1.centroid.x, y=b1.centroid.y))
        for n, miss in self.unconnected().items():
            for m in miss:
                v.append(dict(rule="unconnected", layer="-", detail=f"{n}: {m}", x=self.comp(m.split('.')[0]).x, y=self.comp(m.split('.')[0]).y))
        return v

    def unconnected(self):
        """Per net, pins not galvanically connected to the net's first pin (tracks, vias, zones, THT pads bridge layers)."""
        out = {}
        for net, pins in self.nets.items():
            if len(pins) < 2:
                continue
            nodes = []   # (layer, geometry)
            for L in self.layers:
                for n, g in self.copper(L):
                    if n == net:
                        nodes.append((L, g))
            # union-find over geometric contact on the same layer; vias and THT pads appear on both layers
            parent = list(range(len(nodes)))

            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a
            geoms = [g for _, g in nodes]
            tree = shapely.STRtree(geoms)
            for i, (L, g) in enumerate(nodes):
                for j in tree.query(g):
                    if j != i and (nodes[j][0] == L or geoms[j].equals(g)) and g.intersects(geoms[j]):
                        parent[find(i)] = find(j)
            pin_nodes = []
            for ref, num in pins:
                c = self.comp(ref); p = c.pad(num); g = p.geom(c.x, c.y, c.rot)
                idx = [k for k, (L, gg) in enumerate(nodes) if L in c.pad_layers(p) and gg.equals(g)]
                pin_nodes.append((f"{ref}.{num}", find(idx[0]) if idx else -1))
            root = pin_nodes[0][1]
            miss = [s for s, r in pin_nodes[1:] if r != root]
            if miss:
                out[net] = miss
        return out

    # -------------------------------------------------------------- metrics
    def track_length(self, net=None):
        return sum(math.hypot(t.x2 - t.x1, t.y2 - t.y1) for t in self.tracks if net is None or t.net == net)

    def stats(self):
        return dict(components=len(self.comps), pads=sum(len(c.fp.pads) for c in self.comps), nets=len(self.nets),
                    tracks=len(self.tracks), vias=len(self.vias), track_length_mm=self.track_length(),
                    holes=len(self.holes()), area_mm2=self.outline().area)


def _rot_bounds(c):
    x0, y0, x1, y1 = c.fp.bbox()
    m = c.fp.courtyard
    pts = [(x0 - m, y0 - m), (x1 + m, y1 + m)]
    rp = [(_rot_pad(x, y, 0, 0, c.rot)[0] + c.x, _rot_pad(x, y, 0, 0, c.rot)[1] + c.y) for x, y in pts]
    return min(p[0] for p in rp), min(p[1] for p in rp), max(p[0] for p in rp), max(p[1] for p in rp)


def _astar(src, goal, free, via_ok, layers, via_cost, max_expand):
    L0 = layers
    nx, ny = next(iter(free.values())).shape
    # the source pad and goal copper are always enterable for this net
    ok = {L: free[L] | src[L] | goal[L] for L in L0}
    goals = {L: np.argwhere(goal[L]) for L in L0}
    gpts = np.vstack([g for g in goals.values() if len(g)]) if any(len(g) for g in goals.values()) else None
    if gpts is None:
        return None
    gset = {(L, int(i), int(j)) for L in L0 for i, j in goals[L]}

    def h(i, j):
        d = np.abs(gpts - (i, j))
        dd = np.min(np.max(d, 1) + (math.sqrt(2) - 1) * np.min(d, 1))
        return dd

    # heuristic via a coarse distance transform would be faster; bounded cache keeps it cheap
    hcache = {}

    def H(i, j):
        k = (i, j)
        if k not in hcache:
            hcache[k] = h(i, j)
        return hcache[k]
    openq, g, came = [], {}, {}
    for L in L0:
        for i, j in np.argwhere(src[L]):
            s = (L, int(i), int(j))
            g[s] = 0.0
            heapq.heappush(openq, (H(s[1], s[2]), 0.0, s))
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]
    n = 0
    while openq:
        f, gc, s = heapq.heappop(openq)
        if gc > g.get(s, 1e18):
            continue
        if s in gset and not src[s[0]][s[1], s[2]]:
            path = [s]
            while s in came:
                s = came[s]; path.append(s)
            return path[::-1]
        n += 1
        if n > max_expand:
            return None
        L, i, j = s
        for di, dj, c in moves:
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and ok[L][a, b]:
                if di and dj and not (ok[L][a, j] and ok[L][i, b]):
                    continue           # no corner cutting
                t = (L, a, b)
                ng = gc + c
                if ng < g.get(t, 1e18):
                    g[t] = ng; came[t] = s
                    heapq.heappush(openq, (ng + H(a, b), ng, t))
        if via_ok[i, j]:
            for L2 in L0:
                if L2 != L and ok[L2][i, j]:
                    t = (L2, i, j)
                    ng = gc + via_cost
                    if ng < g.get(t, 1e18):
                        g[t] = ng; came[t] = s
                        heapq.heappush(openq, (ng + H(i, j), ng, t))
    return None


# ------------------------------------------------------------------ exporters

def _fmt(v):
    return str(int(round(v * 1e6)))


class _Gerber:
    def __init__(self, func, polarity="Positive"):
        self.lines = ["G04 Nyquist Labs eelab.pcb*", f"%TF.FileFunction,{func}*%", f"%TF.FilePolarity,{polarity}*%",
                      "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%"]
        self.aps = {}
        self.body = []

    def ap(self, kind, *dims):
        key = (kind,) + tuple(round(d, 4) for d in dims)
        if key not in self.aps:
            code = 10 + len(self.aps)
            self.aps[key] = code
            self.lines.append(f"%ADD{code}{kind},{'X'.join(f'{d:.4f}' for d in dims)}*%")
        return self.aps[key]

    def flash(self, code, x, y):
        self.body += [f"D{code}*", f"X{_fmt(x)}Y{_fmt(y)}D03*"]

    def line(self, code, x1, y1, x2, y2):
        self.body += [f"D{code}*", f"X{_fmt(x1)}Y{_fmt(y1)}D02*", f"X{_fmt(x2)}Y{_fmt(y2)}D01*"]

    def region(self, coords, dark=True):
        self.body.append("%LPD*%" if dark else "%LPC*%")
        self.body += ["G36*", f"X{_fmt(coords[0][0])}Y{_fmt(coords[0][1])}D02*"]
        self.body += [f"X{_fmt(x)}Y{_fmt(y)}D01*" for x, y in coords[1:]]
        self.body += ["G37*", "%LPD*%"]

    def polygon(self, poly):
        for p in getattr(poly, "geoms", [poly]):
            self.region(list(p.exterior.coords), True)
            for hole in p.interiors:
                self.region(list(hole.coords), False)

    def text(self):
        return "\n".join(self.lines + ["G01*"] + self.body + ["M02*"]) + "\n"


def _pad_flash(gb, pad, c, grow=0.0):
    x, y, w, h = _rot_pad(pad.x, pad.y, pad.w, pad.h, c.rot)
    x += c.x; y += c.y; w += 2 * grow; h += 2 * grow
    if pad.shape == "circle":
        gb.flash(gb.ap("C", w), x, y)
    elif pad.shape == "oval":
        gb.flash(gb.ap("O", w, h), x, y)
    elif pad.shape == "roundrect":
        gb.polygon(pad.geom(c.x, c.y, c.rot, grow))       # exact outline as a region
    else:
        gb.flash(gb.ap("R", w, h), x, y)


def export_gerbers(b: Board, outdir, silk_text=True):
    """Write Gerber X2-ish RS-274X layers + Excellon drill. Returns dict name -> path."""
    from pathlib import Path
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    files = {}
    for L, side in (("F", "Top"), ("B", "Bot")):
        cu = _Gerber(f"Copper,L{1 if L == 'F' else 2},{side}")
        for layer, net, poly in sorted([z for z in b.zones if z[0] == L], key=lambda z: -z[2].area):
            cu.polygon(poly)
        for t in b.tracks:
            if t.layer == L:
                cu.line(cu.ap("C", t.w), t.x1, t.y1, t.x2, t.y2)
        for v in b.vias:
            cu.flash(cu.ap("C", v.dia), v.x, v.y)
        for c in b.comps:
            for p in c.fp.pads:
                if L in c.pad_layers(p) and not (p.drill and not p.plated):
                    _pad_flash(cu, p, c)
        files[f"{L}_Cu"] = cu
        mk = _Gerber(f"Soldermask,{side}", "Negative")
        for c in b.comps:
            for p in c.fp.pads:
                if L in c.pad_layers(p):
                    _pad_flash(mk, p, c, grow=0.05)
        files[f"{L}_Mask"] = mk
        pa = _Gerber(f"Paste,{side}")
        for c in b.comps:
            for p in c.fp.pads:
                if not p.drill and c.side == L:
                    _pad_flash(pa, p, c)
        files[f"{L}_Paste"] = pa
        sk = _Gerber(f"Legend,{side}")
        ap = sk.ap("C", 0.15)
        for c in b.comps:
            if c.side != L or c.fp.height == 0:
                continue
            x0, y0, x1, y1 = _rot_bounds(c)
            m = c.fp.courtyard
            x0 += m; y0 += m; x1 -= m; y1 -= m
            pads_u = unary_union([p.geom(c.x, c.y, c.rot, 0.2) for p in c.fp.pads])
            outline = LineString([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]).difference(pads_u)
            for seg in getattr(outline, "geoms", [outline]):
                pts = list(seg.coords)
                for (a1, b1), (a2, b2) in zip(pts, pts[1:]):
                    sk.line(ap, a1, b1, a2, b2)
            if silk_text:
                for poly in _text_polys(c.ref, x0, y1 + 0.3, 0.9):
                    for (a1, b1), (a2, b2) in zip(poly, poly[1:]):
                        sk.line(ap, a1, b1, a2, b2)
        files[f"{L}_Silk"] = sk
    ed = _Gerber("Profile,NP")
    ap = ed.ap("C", 0.1)
    pts = list(b.outline().exterior.coords)
    for (a1, b1), (a2, b2) in zip(pts, pts[1:]):
        ed.line(ap, a1, b1, a2, b2)
    files["Edge_Cuts"] = ed
    paths = {}
    for k, gb in files.items():
        p = out / f"{b.name}-{k}.gbr"
        p.write_text(gb.text())
        paths[k] = p
    # Excellon
    tools = {}
    for x, y, d, pl, n in b.holes():
        tools.setdefault((round(d, 3), pl), []).append((x, y))
    lines = ["M48", "; Nyquist Labs eelab.pcb", "FMAT,2", "METRIC,TZ"]
    for k, (d, pl) in enumerate(sorted(tools), 1):
        lines.append(f"; {'PTH' if pl else 'NPTH'}")
        lines.append(f"T{k}C{d:.3f}")
    lines.append("%")
    for k, key in enumerate(sorted(tools), 1):
        lines.append(f"T{k}")
        lines += [f"X{x:.3f}Y{y:.3f}" for x, y in tools[key]]
    lines.append("M30")
    p = out / f"{b.name}.drl"
    p.write_text("\n".join(lines) + "\n")
    paths["drill"] = p
    return paths


def _text_polys(s, x, y, size):
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), s, size=size, prop=FontProperties(family="DejaVu Sans"))
    return [[(x + px, y + py) for px, py in poly] for poly in tp.to_polygons()]


def export_kicad(b: Board, path):
    """Minimal KiCad 7 (.kicad_pcb, version 20221018) board file with footprints, pads, tracks, vias, zones and outline."""
    nets = ["", *sorted(b.nets)]
    nid = {n: i for i, n in enumerate(nets)}
    q = lambda s: '"' + str(s).replace('"', "'") + '"'
    Y = lambda y: -y   # KiCad's y axis points down
    L = {"F": "F.Cu", "B": "B.Cu"}
    o = [f"(kicad_pcb (version 20221018) (generator eelab)", f"  (general (thickness {b.thickness}))", '  (paper "A4")',
         '  (layers (0 "F.Cu" signal) (31 "B.Cu" signal) (32 "B.Adhes" user) (33 "F.Adhes" user) (34 "B.Paste" user) (35 "F.Paste" user)'
         ' (36 "B.SilkS" user) (37 "F.SilkS" user) (38 "B.Mask" user) (39 "F.Mask" user) (44 "Edge.Cuts" user) (46 "B.CrtYd" user) (47 "F.CrtYd" user)'
         ' (48 "B.Fab" user) (49 "F.Fab" user))',
         "  (setup (pad_to_mask_clearance 0.05))"]
    o += [f"  (net {i} {q(n)})" for i, n in enumerate(nets)]
    for c in b.comps:
        side = "F.Cu" if c.side == "F" else "B.Cu"
        o.append(f"  (footprint {q('eelab:' + c.fp.name)} (layer {q(side)}) (at {c.x:.4f} {Y(c.y):.4f} {c.rot})")
        o.append(f"    (fp_text reference {q(c.ref)} (at 0 {-(c.fp.body[1] / 2 + 1):.3f} {c.rot}) (layer \"F.SilkS\") (effects (font (size 1 1) (thickness 0.15))))")
        o.append(f"    (fp_text value {q(c.value or c.fp.name)} (at 0 {c.fp.body[1] / 2 + 1:.3f} {c.rot}) (layer \"F.Fab\") (effects (font (size 1 1) (thickness 0.15))))")
        bw, bh = c.fp.body
        o.append(f"    (fp_rect (start {-bw / 2:.3f} {-bh / 2:.3f}) (end {bw / 2:.3f} {bh / 2:.3f}) (stroke (width 0.1) (type solid)) (fill none) (layer \"F.Fab\"))")
        for p in c.fp.pads:
            net = b.pad_net(c.ref, p.num) if p.num else None
            shape = {"rect": "rect", "circle": "circle", "oval": "oval", "roundrect": "roundrect"}[p.shape]
            if p.drill:
                kind = "thru_hole" if p.plated else "np_thru_hole"
                layers = '"*.Cu" "*.Mask"'
                drill = f" (drill {p.drill})"
            else:
                kind = "smd"; layers = '"F.Cu" "F.Paste" "F.Mask"' if c.side == "F" else '"B.Cu" "B.Paste" "B.Mask"'; drill = ""
            rr = " (roundrect_rratio 0.25)" if shape == "roundrect" else ""
            nets_s = f" (net {nid[net]} {q(net)})" if net else ""
            o.append(f"    (pad {q(p.num)} {kind} {shape} (at {p.x:.4f} {Y(p.y):.4f} {c.rot}) (size {p.w:.4f} {p.h:.4f}){drill} (layers {layers}){rr}{nets_s})")
        o.append("  )")
    pts = list(b.outline().exterior.coords)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        o.append(f"  (gr_line (start {x1:.4f} {Y(y1):.4f}) (end {x2:.4f} {Y(y2):.4f}) (stroke (width 0.1) (type solid)) (layer \"Edge.Cuts\"))")
    for t in b.tracks:
        o.append(f"  (segment (start {t.x1:.4f} {Y(t.y1):.4f}) (end {t.x2:.4f} {Y(t.y2):.4f}) (width {t.w}) (layer {q(L[t.layer])}) (net {nid[t.net]}))")
    for v in b.vias:
        o.append(f"  (via (at {v.x:.4f} {Y(v.y):.4f}) (size {v.dia}) (drill {v.drill}) (layers \"F.Cu\" \"B.Cu\") (net {nid[v.net]}))")
    for layer, net in b.zone_requests:
        ow = list(b.outline().buffer(-b.rules.edge_clearance).exterior.coords)[:-1]
        o.append(f"  (zone (net {nid[net]}) (net_name {q(net)}) (layer {q(L[layer])}) (hatch edge 0.5) (connect_pads yes (clearance {b.rules.clearance}))"
                 f" (min_thickness 0.2) (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5))")
        o.append("    (polygon (pts " + " ".join(f"(xy {x:.4f} {Y(y):.4f})" for x, y in ow) + "))")
        for lz, nz, poly in b.zones:
            if lz == layer and nz == net:
                o.append("    (filled_polygon (layer " + q(L[layer]) + ") (pts " + " ".join(f"(xy {x:.4f} {Y(y):.4f})" for x, y in list(poly.exterior.coords)[:-1]) + "))")
        o.append("  )")
    o.append(")")
    from pathlib import Path
    Path(path).write_text("\n".join(o) + "\n")
    return path


def bom(b: Board):
    """Grouped bill of materials: list of dicts."""
    groups = {}
    for c in b.comps:
        if not c.fp.pads or c.fp.pads[0].num == "":
            continue
        k = (c.value, c.fp.name, c.mpn)
        groups.setdefault(k, []).append(c.ref)
    import re
    key = lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))
    rows = [dict(refs=",".join(sorted(v, key=key)), qty=len(v), value=k[0], footprint=k[1], mpn=k[2]) for k, v in groups.items()]
    return sorted(rows, key=lambda r: key(r["refs"].split(",")[0]))


def pick_and_place(b: Board):
    rows = []
    for c in b.comps:
        if c.fp.pads and c.fp.pads[0].num == "":
            continue
        smd = not any(p.drill for p in c.fp.pads)
        rows.append(dict(ref=c.ref, value=c.value, footprint=c.fp.name, x_mm=round(c.x, 4), y_mm=round(c.y, 4), rot=c.rot, side="top" if c.side == "F" else "bottom",
                         type="SMD" if smd else "THT"))
    return rows


# ------------------------------------------------------------------ plots

LAYER_COL = {"F": "#c8553d", "B": "#2a78d6"}


def plot_board(ax, b: Board, layers=("B", "F"), labels=True, show_zones=True):
    import matplotlib.patches as mp
    from matplotlib.path import Path as MPath
    ax.set_facecolor("#0f3d2e")
    outline = b.outline()
    ax.add_patch(mp.Polygon(list(outline.exterior.coords), fc="#1d6b4a", ec="#e8e8e0", lw=1.2, zorder=0))

    def fill(g, **kw):
        for p in getattr(g, "geoms", [g]):
            if p.is_empty:
                continue
            verts = list(p.exterior.coords); codes = [MPath.MOVETO] + [MPath.LINETO] * (len(verts) - 2) + [MPath.CLOSEPOLY]
            for h in p.interiors:
                hv = list(h.coords); verts += hv; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(hv) - 2) + [MPath.CLOSEPOLY]
            ax.add_patch(mp.PathPatch(MPath(verts, codes), **kw))
    for L in layers:
        a = 0.35 if L == "B" and "F" in layers else 0.9
        if show_zones:
            for lz, n, poly in b.zones:
                if lz == L:
                    fill(poly, fc=LAYER_COL[L], ec="none", alpha=0.45 if L == "B" else 0.55, zorder=1)
        for t in b.tracks:
            if t.layer == L:
                ax.plot([t.x1, t.x2], [t.y1, t.y2], color=LAYER_COL[L], lw=t.w * 72 / 25.4 * _scale(ax, b), solid_capstyle="round", alpha=a, zorder=2)
    for lay, n, g, c, p in b.pad_geoms():
        if lay in layers:
            fill(g, fc="#d9b44a" if p.drill else ("#d9b44a" if lay == "F" else "#7fa7d9"), ec="none", zorder=3)
    for v in b.vias:
        ax.add_patch(mp.Circle((v.x, v.y), v.dia / 2, fc="#d9b44a", zorder=4)); ax.add_patch(mp.Circle((v.x, v.y), v.drill / 2, fc="#0b0b0b", zorder=5))
    for x, y, d, pl, n in b.holes():
        ax.add_patch(mp.Circle((x, y), d / 2, fc="#0b0b0b", zorder=5))
    if labels:
        for c in b.comps:
            if c.fp.height:
                x0, y0, x1, y1 = _rot_bounds(c)
                ax.add_patch(mp.Rectangle((x0 + c.fp.courtyard, y0 + c.fp.courtyard), x1 - x0 - 2 * c.fp.courtyard, y1 - y0 - 2 * c.fp.courtyard,
                                          fill=False, ec="#f2f2f2", lw=0.6, zorder=6))
                ax.text((x0 + x1) / 2, y1 + 0.1, c.ref, color="#f2f2f2", fontsize=6, ha="center", va="bottom", zorder=7)
    ax.set_xlim(-1, b.w + 1); ax.set_ylim(-1, b.h + 1); ax.set_aspect("equal"); ax.grid(False)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")


def _scale(ax, b):
    fig = ax.figure
    wpx = ax.get_position().width * fig.get_size_inches()[0] * 72
    return wpx / (b.w + 2) / (72 / 25.4)


def plot_3d(ax, b: Board, elev=35, azim=-60):
    """Simple 3-D render: board slab + component bodies as boxes."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    ax.computed_zorder = False          # mplot3d's depth sort puts the big board slab in front of small parts

    def boxf(x0, y0, z0, x1, y1, z1, col, alpha=1.0, z=1):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [[v[i] for i in q] for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
        pc = Poly3DCollection(f, facecolors=col, edgecolors="#00000040", linewidths=0.3, alpha=alpha)
        pc.set_zorder(z)
        ax.add_collection3d(pc)
    boxf(0, 0, -b.thickness, b.w, b.h, 0, "#1d6b4a", z=0)
    for lay, n, g, c, p in b.pad_geoms():
        if lay == "F":
            x0, y0, x1, y1 = g.bounds
            boxf(x0, y0, 0, x1, y1, 0.04, "#d9b44a", z=0.5)
    cols = {"C_": "#c9a66b", "SOIC": "#2b2b2b", "SOT": "#2b2b2b", "DIP": "#2b2b2b", "PinHeader": "#1b1b1b", "TO-220": "#3a3a3a", "CP_": "#2a4d8f",
            "Terminal": "#2f7d4b", "SMA": "#d4af37", "TestPoint": "#d9b44a"}
    for c in b.comps:
        if c.fp.height <= 0:
            continue
        x0, y0, x1, y1 = _rot_bounds(c)
        m = c.fp.courtyard
        col = next((v for k, v in cols.items() if c.fp.name.startswith(k)), "#555")
        boxf(x0 + m, y0 + m, 0, x1 - m, y1 - m, min(c.fp.height, 12), col, z=1 + c.fp.height / 100 + (x0 + y1) / 1e4)
    ax.set_xlim(0, b.w); ax.set_ylim(0, b.h); ax.set_zlim(-2, max(b.w, b.h) * 0.5)
    ax.set_box_aspect((b.w, b.h, max(b.w, b.h) * 0.25))
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off()


# ------------------------------------------------------------------ project helper

def publish(p, b: Board, title=None, schematic=None):
    """Export fab files, KiCad board, BOM/CPL, plots; verify Gerbers with gerbonara and the KiCad file with kiutils.
    Adds metrics/compares to project `p` and returns a dict of verification numbers."""
    import warnings
    import pandas as pd
    import gerbonara
    from kiutils.board import Board as KBoard
    fab = p.dir / "fab"
    paths = export_gerbers(b, fab)
    for k, path in paths.items():
        p.files.append((f"fab/{path.name}", f"{'Excellon drill' if k == 'drill' else 'Gerber ' + k}"))
    kpath = export_kicad(b, p.dir / "kicad" / f"{b.name}.kicad_pcb") if (p.dir / "kicad").mkdir(exist_ok=True) is None else None
    p.files.append((f"kicad/{b.name}.kicad_pcb", "KiCad 7 board (open in KiCad; press B to refill zones)"))
    rows = bom(b)
    p.csv_df("bom", pd.DataFrame(rows))
    p.csv_df("pick_and_place", pd.DataFrame(pick_and_place(b)))
    # independent parse of every Gerber / drill file
    res = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cu_flash = 0
        for k, path in paths.items():
            if k == "drill":
                d = gerbonara.ExcellonFile.open(path)
                res["drill_hits"] = len(d.objects)
            else:
                g = gerbonara.GerberFile.open(path)
                res[f"{k}_objects"] = len(g.objects)
                if k == "Edge_Cuts":
                    (x0, y0), (x1, y1) = g.bounding_box()
                    res["edge_w"], res["edge_h"] = x1 - x0 - 0.1, y1 - y0 - 0.1
    kb = KBoard.from_file(str(kpath))
    res["kicad_footprints"] = len(kb.footprints)
    res["kicad_pads"] = sum(len(f.pads) for f in kb.footprints)
    res["kicad_tracks_vias"] = len(kb.traceItems)
    st = b.stats()
    viol = b.drc()
    p.compare("DRC violations (clearance, widths, drills, annular rings, edge, courtyards, connectivity)", 0, len(viol), "", kind="abs")
    p.compare("Drill hits in the Excellon file (re-read with gerbonara) = holes in the design", st["holes"], res["drill_hits"], "", kind="abs")
    p.compare("Board outline from the Gerber profile (re-read with gerbonara)", b.w, res["edge_w"], "mm", tol=0.01)
    p.compare("Pads in the KiCad file (re-read with kiutils) = pads in the design", st["pads"], res["kicad_pads"], "", kind="abs")
    p.metric("Board", f"{b.w:g} × {b.h:g} mm, {len(b.layers)} layers, {b.thickness} mm")
    p.metric("Components / nets / pads", f"{st['components']} / {st['nets']} / {st['pads']}")
    p.metric("Routed track length", st["track_length_mm"], "mm", f"{st['tracks']} segments, {st['vias']} vias")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(11, 4.6))
    a1 = fig.add_subplot(1, 3, 1); plot_board(a1, b, ("F",)); a1.set_title("Top copper", loc="left", fontsize=10)
    a2 = fig.add_subplot(1, 3, 2); plot_board(a2, b, ("B",), labels=False); a2.set_title("Bottom copper", loc="left", fontsize=10)
    a3 = fig.add_subplot(1, 3, 3, projection="3d"); plot_3d(a3, b); a3.set_title("3-D render", loc="left", fontsize=10)
    fig.tight_layout()
    p.save(fig, "board", title or f"{b.name}: routed layout (top, bottom) and 3-D render. Gerbers, drill, KiCad board, BOM and pick-and-place are in fab/, kicad/ and data/.")
    if viol:
        p.csv_df("drc", pd.DataFrame(viol))
    return dict(res, drc=viol, stats=st)
