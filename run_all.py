#!/usr/bin/env python3
"""Run every project (or a subset), regenerate READMEs, the project index and the site.

    python run_all.py                    # everything, in parallel
    python run_all.py --only SL-001 AM-062
    python run_all.py --track applied-math --category D
    python run_all.py --index-only       # just rebuild README index + docs/ from results.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
# Projects run in parallel worker processes; letting each one also spawn a full set of BLAS threads oversubscribes the CPU
# (a 10 s project was seen taking 15 min next to two others). Two threads per worker is a good compromise.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

TRACKS = {
    "signal-lab": "Signal Lab — 214 electrical-engineering projects",
    "applied-math": "Applied Mathematics — 218 projects in electrical engineering",
}


CATEGORIES = {
    "signal-lab": {
        "A": "A. Analog circuit design & simulation", "B": "B. Power electronics",
        "C": "C. Digital logic & HDL", "D": "D. Digital signal processing",
        "E": "E. RF, radio & satellites (real signals)", "F": "F. Communication systems",
        "G": "G. Electromagnetics & device physics", "H": "H. Embedded systems (simulated)",
        "I": "I. Control systems", "J": "J. Biosignals & HCI (real patient data)",
        "K": "K. Interactive tools & web apps", "L": "L. PCB design"},
    "applied-math": {
        "A": "A. Complex analysis & phasors", "B": "B. Fourier analysis & transforms",
        "C": "C. Differential equations", "D": "D. Linear algebra",
        "E": "E. Probability & stochastic processes", "F": "F. Optimisation",
        "G": "G. Numerical methods", "H": "H. Discrete math, finite fields & coding",
        "I": "I. Control theory", "J": "J. Statistics & learning on real signals",
        "K": "K. Fields, vector calculus & geometry", "L": "L. Information theory"},
}


def category_name(track: str, folder: str) -> str:
    return CATEGORIES[track][folder.split("-")[0]]


def discover():
    out = []
    for p in sorted(ROOT.glob("projects/*/*/*/project.py")):
        out.append(p)
    return out


def load_meta(path: Path):
    spec = importlib.util.spec_from_file_location(f"proj_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_one(path_str: str):
    import matplotlib
    matplotlib.use("Agg")
    from eelab.core import Project
    path = Path(path_str)
    t0 = time.time()
    try:
        mod = load_meta(path)
        meta = dict(mod.META)
        meta.setdefault("track", TRACKS[path.parts[-4]])
        meta.setdefault("category", category_name(path.parts[-4], path.parts[-3]))
        meta.setdefault("data", "Simulated (numerical model in this repo).")
        # clean previous outputs so stale figures never survive
        for sub in ("figures", "data"):
            shutil.rmtree(path.parent / sub, ignore_errors=True)
        p = Project(path.parent, meta)
        mod.run(p)
        res = p.finish(runtime_s=round(time.time() - t0, 2))
        return dict(ok=True, id=meta["id"], runtime=res["runtime_s"], path=path_str)
    except Exception:
        return dict(ok=False, id=path.parent.name, error=traceback.format_exc(), path=path_str,
                    runtime=round(time.time() - t0, 2))


def build_index():
    rows = []
    for rj in sorted(ROOT.glob("projects/*/*/*/results.json")):
        r = json.loads(rj.read_text())
        rows.append(r)
    key = lambda r: (r["folder"].split("/")[1], r["meta"]["id"])
    rows.sort(key=key)
    from eelab.core import fmt

    def headline(r):
        if r["rows"]:
            x = r["rows"][0]
            return (f"{x['quantity']}: {fmt(x['predicted'], x['unit'])} → "
                    f"{fmt(x['measured'], x['unit'])} ({x['error_str']})")
        if r["metrics"]:
            m = r["metrics"][0]
            return f"{m['quantity']}: {fmt(m['value'], m['unit'])}"
        return ""

    # ---------------- PROJECTS.md (full index) + CSV
    lines = ["# Project index", "",
             f"{len(rows)} projects. Each row links to a folder with `project.py`, a README "
             "(problem → prediction → method → predicted-vs-measured table → discussion), "
             "figures and data.", ""]
    import csv
    with open(ROOT / "PROJECTS.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "title", "track", "category", "level", "tools", "data", "headline", "folder"])
        cur_track = cur_cat = None
        for r in rows:
            m = r["meta"]
            if m["track"] != cur_track:
                cur_track = m["track"]
                lines += ["", f"## {cur_track}", ""]
                cur_cat = None
            if m["category"] != cur_cat:
                cur_cat = m["category"]
                lines += ["", f"### {cur_cat}", "", "| # | Project | Lvl | Headline result |",
                          "|---|---|---|---|"]
            hl = headline(r).replace("|", "\\|")
            lines.append(f"| {m['id']} | [{m['title']}]({r['folder']}) | {m['level']} | {hl} |")
            w.writerow([m["id"], m["title"], m["track"], m["category"], m["level"], m["tools"],
                        m["data"], headline(r), r["folder"]])
    (ROOT / "PROJECTS.md").write_text("\n".join(lines) + "\n")

    # ---------------- docs/ (GitHub Pages site)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    tools_dir = docs / "tools"
    shutil.rmtree(tools_dir, ignore_errors=True)
    tools = []
    for r in rows:
        web = ROOT / r["folder"] / "web"
        if (web / "index.html").exists():
            dest = tools_dir / r["meta"]["id"]
            shutil.copytree(web, dest)
            tools.append((r["meta"]["id"], r["meta"]["title"], f"tools/{r['meta']['id']}/index.html"))
    data = [dict(id=r["meta"]["id"], title=r["meta"]["title"], cat=r["meta"]["category"],
                 track=r["meta"]["track"], lvl=r["meta"]["level"], sum=r["meta"]["summary"],
                 hl=headline(r), real=not r["meta"]["data"].startswith(("Simulated", "Synthetic", "Simulation")),
                 folder=r["folder"]) for r in rows]
    tpl = (ROOT / "site" / "template.html").read_text()
    html = (tpl.replace("/*DATA*/", json.dumps(data))
               .replace("/*TOOLS*/", json.dumps([dict(id=a, title=b, href=c) for a, b, c in tools])))
    (docs / "index.html").write_text(html)
    (docs / "projects.json").write_text(json.dumps([dict(id=d["id"], title=d["title"], track=d["track"], cat=d["cat"], lvl=d["lvl"], real=d["real"]) for d in data]))
    (docs / ".nojekyll").write_text("")
    sys.path.insert(0, str(ROOT / "tools"))
    import readme
    readme.write(ROOT, rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--track")
    ap.add_argument("--category")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--index-only", action="store_true")
    a = ap.parse_args()
    if not a.index_only:
        paths = discover()
        if a.only:
            want = {w.upper().replace("-", "") for w in a.only}
            paths = [p for p in paths if p.parent.name.split("-")[0].upper() in want]
        if a.track:
            paths = [p for p in paths if p.parts[-4] == a.track]
        if a.category:
            paths = [p for p in paths if p.parts[-3].startswith(a.category + "-")]
        print(f"running {len(paths)} project(s) with {a.jobs} worker(s)")
        t0 = time.time()
        with Pool(a.jobs) as pool:
            results = []
            for r in pool.imap_unordered(run_one, [str(p) for p in paths]):
                results.append(r)
                flag = "ok " if r["ok"] else "ERR"
                print(f"  [{flag}] {r['id']:<8} {r['runtime']:6.1f}s", flush=True)
                if not r["ok"]:
                    print("      " + r["error"].strip().splitlines()[-1][:200])
        bad = [r for r in results if not r["ok"]]
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs" / "last_run.json").write_text(json.dumps(results, indent=1))
        print(f"done in {time.time() - t0:.0f}s — {len(results) - len(bad)} ok, {len(bad)} failed")
    rows = build_index()
    print(f"index rebuilt: {len(rows)} projects")


if __name__ == "__main__":
    main()
