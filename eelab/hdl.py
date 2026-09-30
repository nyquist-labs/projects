"""eelab.hdl — run Verilog through Icarus Verilog (simulation) and Yosys (synthesis).

Icarus Verilog is looked up in ./.tools/bin first, then on PATH (install it with your package manager:
`brew install icarus-verilog`, `apt install iverilog`). Yosys comes from the `yowasp-yosys` pip package.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .core import ROOT

TOOLS = ROOT / ".tools" / "bin"


def _which(name):
    p = TOOLS / name
    if p.exists():
        return str(p)
    w = shutil.which(name)
    if not w:
        raise RuntimeError(f"{name} not found — install Icarus Verilog (see README, 'Requirements')")
    return w


def simulate(p, sources: dict[str, str], tb_top: str, timeout=120):
    """Write sources into <project>/hdl/, compile with iverilog -g2012, run vvp.
    Returns (stdout, vcd_dict or None)."""
    hdl = p.dir / "hdl"
    hdl.mkdir(exist_ok=True)
    files = []
    for name, text in sources.items():
        p.write(f"hdl/{name}", text.strip() + "\n", "Verilog source" if "tb" not in name else "testbench")
        files.append(name)
    build = hdl / "build"
    build.mkdir(exist_ok=True)
    out = build / "sim.vvp"
    r = subprocess.run([_which("iverilog"), "-g2012", "-s", tb_top, "-o", str(out)] + files,
                       cwd=hdl, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + r.stderr)
    r = subprocess.run([_which("vvp"), "-n", str(out)], cwd=hdl, capture_output=True, text=True,
                       timeout=timeout)
    log = r.stdout + r.stderr
    vcds = list(hdl.glob("*.vcd"))
    vcd = parse_vcd(vcds[0]) if vcds else None
    for v in vcds:              # keep repo small: waveforms are re-generated on demand
        v.rename(build / v.name)
    return log, vcd


def synth(p, sources: dict[str, str], top: str, gates="AND,NAND,OR,NOR,XOR,XNOR,MUX", preserve=False):
    """Synthesize and return dict(cells, depth, breakdown, ffs, stat).

    preserve=False: full `synth` + ABC re-optimisation (best area/depth ABC can find — ABC is free to
    restructure the logic, so this measures the *function*, not the hand-built architecture).
    preserve=True: only technology-map the written structure into 2-input gates (no ABC), so the
    cell count and depth reflect the architecture as designed (used for adder comparisons)."""
    work = p.dir / "hdl" / "build" / f"synth_{top}"
    work.mkdir(parents=True, exist_ok=True)
    for name, text in sources.items():
        (work / name).write_text(text.strip() + "\n")
    reads = " ".join(f"read_verilog -sv {n};" for n in sources)
    if preserve:
        flow = (f"hierarchy -top {top}; proc; flatten; opt_clean; techmap; opt_clean; "
                f"tee -o stat.txt stat; tee -o ltp.txt ltp -noff")
    else:
        flow = (f"synth -flatten -top {top}; abc -g {gates}; opt_clean; "
                f"tee -o stat.txt stat; tee -o ltp.txt ltp -noff")
    yosys = shutil.which("yowasp-yosys") or str(Path(sys.executable).parent / "yowasp-yosys")
    r = subprocess.run([yosys, "-q", "-p", reads + " " + flow], cwd=work, capture_output=True,
                       text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError("yosys failed:\n" + r.stderr[-3000:] + r.stdout[-3000:])
    stat = (work / "stat.txt").read_text()
    ltp = (work / "ltp.txt").read_text()
    cells = 0
    m = re.search(r"(\d+)\s+cells", stat) or re.search(r"Number of cells:\s+(\d+)", stat)
    if m:
        cells = int(m.group(1))
    breakdown = {k: int(v) for v, k in re.findall(r"^\s+(\d+)\s+.*?\$_(\w+?)_?\s*$", stat, re.M)}
    if not breakdown:
        breakdown = {k: int(v) for k, v in re.findall(r"\$_(\w+?)_\s+(\d+)", stat)}
    sm = re.search(r"^\s+(\d+)\s+\$scopeinfo", stat, re.M)      # Yosys bookkeeping cells left by `flatten`, not logic
    if sm:
        cells -= int(sm.group(1)); breakdown.pop("scopeinfo", None)
    dm = re.search(r"Longest topological path.*?\(length=(\d+)\)", ltp)
    depth = int(dm.group(1)) if dm else None
    ffs = sum(v for k, v in breakdown.items() if "DFF" in k or "DLATCH" in k)
    return dict(cells=cells, depth=depth, breakdown=breakdown, ffs=ffs, stat=stat)


def parse_vcd(path):
    """Minimal VCD parser -> {signal_name: (times[list], values[list of int or None])}."""
    ids, sigs, scope = {}, {}, []
    t = 0
    with open(path) as f:
        header = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            if header:
                if line.startswith("$scope"):
                    scope.append(line.split()[2])
                elif line.startswith("$upscope"):
                    scope.pop()
                elif line.startswith("$var"):
                    parts = line.split()
                    code, name = parts[3], parts[4]
                    full = ".".join(scope + [name])
                    ids.setdefault(code, []).append(full)
                    sigs[full] = ([], [])
                elif line.startswith("$enddefinitions"):
                    header = False
                continue
            c = line[0]
            if c == "#":
                t = int(line[1:])
            elif c in "01xzXZ" and len(line) > 1 and not line.startswith("$"):
                val = None if c in "xzXZ" else int(c)
                for nm in ids.get(line[1:], []):
                    sigs[nm][0].append(t); sigs[nm][1].append(val)
            elif c in "bB":
                bits, code = line[1:].split()
                val = None if any(ch in "xzXZ" for ch in bits) else int(bits, 2)
                for nm in ids.get(code, []):
                    sigs[nm][0].append(t); sigs[nm][1].append(val)
            elif c in "rR":
                v, code = line[1:].split()
                for nm in ids.get(code, []):
                    sigs[nm][0].append(t); sigs[nm][1].append(float(v))
    return sigs


def sample(sig, times):
    """Sample a VCD signal (times, values) at the given times (zero-order hold)."""
    import numpy as np
    ts, vs = sig
    idx = np.searchsorted(ts, times, side="right") - 1
    return [vs[i] if i >= 0 else None for i in idx]


def results(log):
    """Parse testbench lines of the form 'RES <name> <value>' into a dict of floats/strings."""
    out = {}
    for line in log.splitlines():
        if line.startswith("RES "):
            parts = line.split(None, 2)
            if len(parts) == 3:
                try:
                    out[parts[1]] = float(parts[2])
                except ValueError:
                    out[parts[1]] = parts[2].strip()
    return out


def waveform_plot(ax, vcd, signals, t0=0, t1=None, scale=1.0, unit="ns"):
    """Draw a digital timing diagram for the given (name, label) signals on ax."""
    import numpy as np
    y = 0
    ticks, labels = [], []
    for name, label in signals[::-1]:
        ts, vs = vcd[name]
        ts = np.array(ts, float) * scale
        vs = np.array([np.nan if v is None else v for v in vs], float)
        end = t1 if t1 is not None else ts[-1]
        tt = np.append(ts, end)
        vv = np.append(vs, vs[-1])
        mx = np.nanmax(vv) if np.nanmax(vv) > 0 else 1
        if mx <= 1:
            ax.step(tt, y + 0.8 * vv, where="post", lw=1.4)
        else:
            ax.step(tt, y + 0.8 * vv / mx, where="post", lw=1.2)
            for a, b, v in zip(tt[:-1], tt[1:], vv[:-1]):
                if b - a > (end - t0) / 40 and t0 <= a <= end:
                    ax.text((a + min(b, end)) / 2, y + 0.9, f"{int(v)}", ha="center", fontsize=7)
        ticks.append(y + 0.4); labels.append(label)
        y += 1.3
    ax.set_yticks(ticks); ax.set_yticklabels(labels)
    ax.set_xlim(t0, t1 if t1 is not None else None)
    ax.set_xlabel(f"time ({unit})")
    ax.grid(axis="y", visible=False)
