"""Generate the top-level README.md from the projects' results.json files (called by run_all.build_index)."""
import json
from collections import OrderedDict

DATASETS = [
    ("MIT-BIH Arrhythmia Database", "PhysioNet (Moody & Mark 2001)", "ODC Attribution License", "https://physionet.org/content/mitdb/"),
    ("MIT-BIH Noise Stress Test Database", "PhysioNet (Moody et al. 1984)", "ODC Attribution License", "https://physionet.org/content/nstdb/"),
    ("EEG Motor Movement/Imagery Dataset", "PhysioNet (Schalk et al. 2004)", "ODC Attribution License", "https://physionet.org/content/eegmmidb/"),
    ("Sleep-EDF Expanded", "PhysioNet (Kemp et al. 2000)", "ODC Attribution License", "https://physionet.org/content/sleep-edfx/"),
    ("CHB-MIT Scalp EEG Database", "PhysioNet (Shoeb 2009)", "ODC Attribution License", "https://physionet.org/content/chbmit/"),
    ("BIDMC PPG and Respiration Dataset", "PhysioNet (Pimentel et al. 2016)", "ODC Attribution License", "https://physionet.org/content/bidmc/"),
    ("Examples of Electromyograms", "PhysioNet", "ODC Attribution License", "https://physionet.org/content/emgdb/"),
    ("Human Activity Recognition Using Smartphones", "UCI ML Repository (Anguita et al. 2013)", "CC BY 4.0", "https://archive.ics.uci.edu/dataset/240"),
    ("EMG data for gestures", "UCI ML Repository (Lobov et al. 2018)", "CC BY 4.0", "https://archive.ics.uci.edu/dataset/481"),
    ("Free Spoken Digit Dataset", "Jakobovski et al.", "CC BY-SA 4.0", "https://github.com/Jakobovski/free-spoken-digit-dataset"),
    ("Li-ion Battery Aging Datasets", "NASA Ames Prognostics Center of Excellence (Saha & Goebel 2007)", "NASA open data", "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/"),
    ("Satellite observation recordings (NOAA APT)", "SatNOGS Network", "CC BY-SA 4.0", "https://network.satnogs.org/"),
    ("Orbital elements (TLE)", "CelesTrak", "public", "https://celestrak.org/"),
    ("WSPR propagation spots", "WSPRnet via wspr.live", "see provider terms", "https://wspr.live/"),
    ("Mode S / ADS-B test capture", "dump1090 test files (antirez)", "BSD-3-Clause", "https://github.com/antirez/dump1090"),
    ("'Hello' pronunciation audio", "Wikimedia Commons", "CC BY-SA", "https://commons.wikimedia.org/wiki/File:En-us-hello.ogg"),
    ("KiCad footprint library (reference footprints)", "KiCad project", "CC BY-SA 4.0 with exception", "https://gitlab.com/kicad/libraries/kicad-footprints"),
    ("Alice's Adventures in Wonderland", "Project Gutenberg eBook #11", "public domain", "https://www.gutenberg.org/ebooks/11"),
]


def write(root, rows):
    tracks = OrderedDict()
    for r in rows:
        m = r["meta"]; t = tracks.setdefault(m["track"], OrderedDict()); c = t.setdefault(m["category"], dict(n=0, cmp=0, tol=0, ok=0, real=0))
        c["n"] += 1; c["real"] += not m["data"].startswith(("Simulated", "Synthetic", "Simulation"))
        for x in r["rows"]:
            c["cmp"] += 1
            if x.get("ok") is not None:
                c["tol"] += 1; c["ok"] += bool(x["ok"])
    tot = dict(n=0, cmp=0, tol=0, ok=0, real=0)
    for t in tracks.values():
        for c in t.values():
            for k in tot:
                tot[k] += c[k]
    L = ["# Nyquist Labs", "", "**Created and maintained by Anna Lin.** Nyquist Labs is Anna Lin's independent project; it is not affiliated with any company or organisation of a similar name.", "",
         f"**{tot['n']} electrical-engineering projects, each one a prediction checked against a measurement.** Two tracks: a hands-on "
         "*signal lab* (circuits, power electronics, digital logic and HDL, DSP, communications, RF, control, embedded systems, biosignals, "
         "PCB design, browser tools) and an *applied-mathematics* track (complex analysis to information theory), built from two public project lists.", "",
         "Every project writes down the expected answer from theory **before** measuring it with an independent simulation, an HDL "
         "simulator or a real public dataset, then tabulates prediction vs measurement and explains any disagreement — including the "
         "predictions that were wrong. See [METHODOLOGY.md](METHODOLOGY.md).", "",
         "> **How this was made — please read.** The code, derivations, simulations and write-ups in this repository were produced with an "
         "AI coding assistant (Claude Code). \"Measured\" means computed by an independent model, simulator or public dataset, not a "
         "physical lab bench. If you use this work for coursework, applications or a portfolio, say so and describe your own contribution "
         "truthfully; presenting it as solely your own work would be academically dishonest.", "",
         "## At a glance", "",
         f"| | |", "|---|---|",
         f"| Projects | {tot['n']} (index: [PROJECTS.md](PROJECTS.md), [PROJECTS.csv](PROJECTS.csv)) |",
         f"| Predicted-vs-measured comparisons | {tot['cmp']} |",
         f"| Comparisons with an explicit tolerance | {tot['tol']}, of which {tot["ok"]} within tolerance and {tot["tol"] - tot["ok"]} outside it (flagged **no** in the project table — wrong first guesses, rules of thumb that do not hold, or tolerances set tighter than the numerics) |",
         f"| Projects using real or recorded data | {tot['real']} |",
         "| Website | `docs/` (enable GitHub Pages on the `docs` folder) — searchable index and the interactive tools |", "",
         "## Tracks and categories", "", "| Track | Category | Projects | Comparisons | Within tolerance | Real data |", "|---|---|---|---|---|---|"]
    for tn, t in tracks.items():
        for cn, c in t.items():
            L.append(f"| {tn} | {cn} | {c['n']} | {c['cmp']} | {c['ok']}/{c['tol']} | {c['real']} |")
    L += ["", "## Repository layout", "", "```",
          "eelab/            shared engine: Project/README generator, circuit simulator (MNA), HDL flow (Icarus + Yosys),",
          "                  PCB toolkit (footprints, router, DRC, Gerber/KiCad export), field solvers, coding & comms,",
          "                  from-scratch ML (eelab.ml), dataset fetchers with caching",
          "projects/<track>/<category>/<ID>-<slug>/",
          "    project.py    META (problem, theory, method) + run(p): predict → measure → compare → discuss",
          "    README.md     generated: prediction-vs-measurement table, figures, discussion",
          "    figures/ data/ results.json   (hdl/, web/, fab/, kicad/ where relevant)",
          "run_all.py        runs projects in parallel and rebuilds PROJECTS.md/.csv and docs/",
          "site/template.html  website template; docs/ is the generated site",
          "tools/show.py     print a project's results table in the terminal", "```", "",
          "## Running it", "", "```bash",
          "python3 -m venv .venv && source .venv/bin/activate",
          "pip install -r requirements.txt",
          "python run_all.py                     # everything (first run downloads datasets into data_cache/)",
          "python run_all.py --only AM-150 SL-205",
          "python run_all.py --track applied-math --category H",
          "python run_all.py --index-only        # rebuild the index and website from existing results",
          "python tools/show.py AM150            # results table in the terminal", "```", "",
          "Requirements: Python 3.11+; [Icarus Verilog](https://steveicarus.github.io/iverilog/) (`brew install icarus-verilog` / "
          "`apt install iverilog`) for the HDL projects; [Node.js](https://nodejs.org/) to verify the JavaScript of the browser tools. "
          "A full run takes roughly half an hour on a laptop with 8 cores; a handful of projects (genetic-algorithm antenna design, "
          "the NumPy CNN, spherical-harmonic expansions) take several minutes each.", "",
          "## Datasets and licences", "",
          "Datasets are downloaded at run time and cached locally; they are **not** redistributed in this repository and remain under "
          "their own licences. Please cite the original sources.", "", "| Dataset | Source | Licence | Link |", "|---|---|---|---|"]
    for d in DATASETS:
        L.append(f"| {d[0]} | {d[1]} | {d[2]} | <{d[3]}> |")
    L += ["", "## Licence", "", "Code and generated documents: MIT (see [LICENSE](LICENSE)). Third-party data: see above.", ""]
    (root / "README.md").write_text("\n".join(L))
