# Nyquist Labs

**Created and maintained by Anna Lin.** Nyquist Labs is Anna Lin's independent project; it is not affiliated with any company or organisation of a similar name.

**432 electrical-engineering projects, each one a prediction checked against a measurement.** Two tracks: a hands-on *signal lab* (circuits, power electronics, digital logic and HDL, DSP, communications, RF, control, embedded systems, biosignals, PCB design, browser tools) and an *applied-mathematics* track (complex analysis to information theory), built from two public project lists.

Every project writes down the expected answer from theory **before** measuring it with an independent simulation, an HDL simulator or a real public dataset, then tabulates prediction vs measurement and explains any disagreement — including the predictions that were wrong. See [METHODOLOGY.md](METHODOLOGY.md).

> **How this was made — please read.** The code, derivations, simulations and write-ups in this repository were produced with an AI coding assistant (Claude Code). "Measured" means computed by an independent model, simulator or public dataset, not a physical lab bench. If you use this work for coursework, applications or a portfolio, say so and describe your own contribution truthfully; presenting it as solely your own work would be academically dishonest.

## At a glance

| | |
|---|---|
| Projects | 432 (index: [PROJECTS.md](PROJECTS.md), [PROJECTS.csv](PROJECTS.csv)) |
| Predicted-vs-measured comparisons | 2257 |
| Comparisons with an explicit tolerance | 1426, of which 1357 within tolerance and 69 outside it (flagged **no** in the project table — wrong first guesses, rules of thumb that do not hold, or tolerances set tighter than the numerics) |
| Projects using real or recorded data | 90 |
| Website | `docs/` (enable GitHub Pages on the `docs` folder) — searchable index and the interactive tools |

## Tracks and categories

| Track | Category | Projects | Comparisons | Within tolerance | Real data |
|---|---|---|---|---|---|
| Applied Mathematics — 218 projects in electrical engineering | A. Complex analysis & phasors | 18 | 96 | 88/92 | 1 |
| Applied Mathematics — 218 projects in electrical engineering | B. Fourier analysis & transforms | 25 | 132 | 124/129 | 4 |
| Applied Mathematics — 218 projects in electrical engineering | C. Differential equations | 18 | 101 | 88/91 | 0 |
| Applied Mathematics — 218 projects in electrical engineering | D. Linear algebra | 18 | 91 | 76/80 | 1 |
| Applied Mathematics — 218 projects in electrical engineering | E. Probability & stochastic processes | 20 | 105 | 96/102 | 0 |
| Applied Mathematics — 218 projects in electrical engineering | F. Optimisation | 15 | 51 | 41/43 | 1 |
| Applied Mathematics — 218 projects in electrical engineering | G. Numerical methods | 18 | 79 | 70/70 | 0 |
| Applied Mathematics — 218 projects in electrical engineering | H. Discrete math, finite fields & coding | 20 | 167 | 19/19 | 1 |
| Applied Mathematics — 218 projects in electrical engineering | I. Control theory | 16 | 136 | 103/104 | 0 |
| Applied Mathematics — 218 projects in electrical engineering | J. Statistics & learning on real signals | 20 | 150 | 87/97 | 20 |
| Applied Mathematics — 218 projects in electrical engineering | K. Fields, vector calculus & geometry | 15 | 111 | 106/107 | 0 |
| Applied Mathematics — 218 projects in electrical engineering | L. Information theory | 15 | 91 | 62/63 | 8 |
| Signal Lab — 214 electrical-engineering projects | A. Analog circuit design & simulation | 25 | 120 | 68/76 | 0 |
| Signal Lab — 214 electrical-engineering projects | B. Power electronics | 12 | 73 | 54/56 | 1 |
| Signal Lab — 214 electrical-engineering projects | C. Digital logic & HDL | 22 | 120 | 16/17 | 0 |
| Signal Lab — 214 electrical-engineering projects | D. Digital signal processing | 25 | 116 | 25/27 | 4 |
| Signal Lab — 214 electrical-engineering projects | E. RF, radio & satellites (real signals) | 22 | 80 | 21/21 | 12 |
| Signal Lab — 214 electrical-engineering projects | F. Communication systems | 15 | 65 | 32/35 | 0 |
| Signal Lab — 214 electrical-engineering projects | G. Electromagnetics & device physics | 15 | 63 | 55/57 | 0 |
| Signal Lab — 214 electrical-engineering projects | H. Embedded systems (simulated) | 20 | 72 | 20/21 | 0 |
| Signal Lab — 214 electrical-engineering projects | I. Control systems | 15 | 52 | 21/28 | 0 |
| Signal Lab — 214 electrical-engineering projects | J. Biosignals & HCI (real patient data) | 21 | 53 | 7/9 | 19 |
| Signal Lab — 214 electrical-engineering projects | K. Interactive tools & web apps | 12 | 62 | 38/40 | 10 |
| Signal Lab — 214 electrical-engineering projects | L. PCB design | 10 | 71 | 40/42 | 8 |

## Repository layout

```
eelab/            shared engine: Project/README generator, circuit simulator (MNA), HDL flow (Icarus + Yosys),
                  PCB toolkit (footprints, router, DRC, Gerber/KiCad export), field solvers, coding & comms,
                  from-scratch ML (eelab.ml), dataset fetchers with caching
projects/<track>/<category>/<ID>-<slug>/
    project.py    META (problem, theory, method) + run(p): predict → measure → compare → discuss
    README.md     generated: prediction-vs-measurement table, figures, discussion
    figures/ data/ results.json   (hdl/, web/, fab/, kicad/ where relevant)
run_all.py        runs projects in parallel and rebuilds PROJECTS.md/.csv and docs/
site/template.html  website template; docs/ is the generated site
tools/show.py     print a project's results table in the terminal
```

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_all.py                     # everything (first run downloads datasets into data_cache/)
python run_all.py --only AM-150 SL-205
python run_all.py --track applied-math --category H
python run_all.py --index-only        # rebuild the index and website from existing results
python tools/show.py AM150            # results table in the terminal
```

Requirements: Python 3.11+; [Icarus Verilog](https://steveicarus.github.io/iverilog/) (`brew install icarus-verilog` / `apt install iverilog`) for the HDL projects; [Node.js](https://nodejs.org/) to verify the JavaScript of the browser tools. A full run takes roughly half an hour on a laptop with 8 cores; a handful of projects (genetic-algorithm antenna design, the NumPy CNN, spherical-harmonic expansions) take several minutes each.

## Datasets and licences

Datasets are downloaded at run time and cached locally; they are **not** redistributed in this repository and remain under their own licences. Please cite the original sources.

| Dataset | Source | Licence | Link |
|---|---|---|---|
| MIT-BIH Arrhythmia Database | PhysioNet (Moody & Mark 2001) | ODC Attribution License | <https://physionet.org/content/mitdb/> |
| MIT-BIH Noise Stress Test Database | PhysioNet (Moody et al. 1984) | ODC Attribution License | <https://physionet.org/content/nstdb/> |
| EEG Motor Movement/Imagery Dataset | PhysioNet (Schalk et al. 2004) | ODC Attribution License | <https://physionet.org/content/eegmmidb/> |
| Sleep-EDF Expanded | PhysioNet (Kemp et al. 2000) | ODC Attribution License | <https://physionet.org/content/sleep-edfx/> |
| CHB-MIT Scalp EEG Database | PhysioNet (Shoeb 2009) | ODC Attribution License | <https://physionet.org/content/chbmit/> |
| BIDMC PPG and Respiration Dataset | PhysioNet (Pimentel et al. 2016) | ODC Attribution License | <https://physionet.org/content/bidmc/> |
| Examples of Electromyograms | PhysioNet | ODC Attribution License | <https://physionet.org/content/emgdb/> |
| Human Activity Recognition Using Smartphones | UCI ML Repository (Anguita et al. 2013) | CC BY 4.0 | <https://archive.ics.uci.edu/dataset/240> |
| EMG data for gestures | UCI ML Repository (Lobov et al. 2018) | CC BY 4.0 | <https://archive.ics.uci.edu/dataset/481> |
| Free Spoken Digit Dataset | Jakobovski et al. | CC BY-SA 4.0 | <https://github.com/Jakobovski/free-spoken-digit-dataset> |
| Li-ion Battery Aging Datasets | NASA Ames Prognostics Center of Excellence (Saha & Goebel 2007) | NASA open data | <https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/> |
| Satellite observation recordings (NOAA APT) | SatNOGS Network | CC BY-SA 4.0 | <https://network.satnogs.org/> |
| Orbital elements (TLE) | CelesTrak | public | <https://celestrak.org/> |
| WSPR propagation spots | WSPRnet via wspr.live | see provider terms | <https://wspr.live/> |
| Mode S / ADS-B test capture | dump1090 test files (antirez) | BSD-3-Clause | <https://github.com/antirez/dump1090> |
| 'Hello' pronunciation audio | Wikimedia Commons | CC BY-SA | <https://commons.wikimedia.org/wiki/File:En-us-hello.ogg> |
| KiCad footprint library (reference footprints) | KiCad project | CC BY-SA 4.0 with exception | <https://gitlab.com/kicad/libraries/kicad-footprints> |
| Alice's Adventures in Wonderland | Project Gutenberg eBook #11 | public domain | <https://www.gutenberg.org/ebooks/11> |

## Licence

Code and generated documents: MIT (see [LICENSE](LICENSE)). Third-party data: see above.
