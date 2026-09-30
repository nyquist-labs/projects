"""Build and run firmware logic on the host against eelab/fw/hal_sim.h, and decode its logs."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np

HAL = Path(__file__).parent / "fw" / "hal_sim.h"


def run(p, sources: dict[str, str], args=(), timeout=300, cflags=("-O2", "-std=c11", "-Wall")):
    fw = p.dir / "firmware"
    fw.mkdir(exist_ok=True)
    shutil.copy(HAL, fw / "hal_sim.h")
    for name, text in sources.items():
        kind = "Wokwi/Arduino sketch" if name.endswith(".ino") else ("Wokwi diagram" if name.endswith(".json") else "firmware source")
        p.write(f"firmware/{name}", text.strip() + "\n", kind)
    cfiles = [n for n in sources if n.endswith(".c")]
    build = fw / "build"
    build.mkdir(exist_ok=True)
    exe = build / "fw_sim"
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    r = subprocess.run([cc, *cflags, "-o", str(exe), *cfiles, "-lm"], cwd=fw, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("compile failed:\n" + r.stderr)
    r = subprocess.run([str(exe), *map(str, args)], cwd=fw, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("firmware sim failed:\n" + r.stderr[-2000:] + r.stdout[-2000:])
    return r.stdout


def results(log):
    out = {}
    for line in log.splitlines():
        if line.startswith("RES "):
            _, k, v = line.split(None, 2)
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v.strip()
    return out


def gpio(log):
    """-> {pin: (times_us ndarray, levels ndarray)} from 'G t pin v' lines."""
    d = {}
    for line in log.splitlines():
        if line.startswith("G "):
            _, t, pin, v = line.split()
            d.setdefault(int(pin), ([], []))
            d[int(pin)][0].append(int(t)); d[int(pin)][1].append(int(v))
    return {k: (np.array(a), np.array(b)) for k, (a, b) in d.items()}


def rows(log, tag):
    return np.array([[float(x) for x in l.split()[1:]] for l in log.splitlines() if l.startswith(tag + " ")])
