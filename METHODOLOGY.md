# Methodology

Every project in this repository follows the same four steps, and every README is generated from the same template.

## 1. Predict
Before anything is simulated, the expected result is written down from theory: a closed-form formula, a textbook
rule of thumb, a published value, or — where no formula exists — an explicit guess labelled as such ("my guess",
"my expectation"). Predictions are made *before* the measurement code is run and are not tuned afterwards to match.
Where a first prediction was wrong, it is kept in the table and the discussion explains why.

## 2. Measure
"Measured" never means a physical lab bench. It means one of:

* **an independent numerical model** — a circuit simulator (the repository's own modified-nodal-analysis engine),
  a field solver, a Monte-Carlo simulation, an optimiser — implemented separately from the formula being tested;
* **a hardware-description-language flow** — Verilog simulated in Icarus Verilog and synthesised with Yosys;
* **a real, public dataset** — ECG, EEG, EMG, smartphone IMU, spoken digits, battery ageing, satellite recordings
  and others (see README for sources and licences);
* **an independent library** used as a referee — SciPy, networkx, gerbonara, kiutils — where the project implements
  an algorithm from scratch.

No number in a results table is typed in by hand; every one is computed when `project.py` runs.

## 3. Compare
Each comparison records the predicted value, the measured value, the error (relative in percent, or absolute), and
optionally a tolerance. A row outside its tolerance is shown as **no** in the README's "within tolerance" column. Those
rows are not failures of the software; they are the interesting cases, and each is discussed. Relative tolerances are
given in percent throughout.

## 4. Explain
The discussion states what agreed, what did not, and why — including bugs found along the way, wrong first
predictions, finite-sample effects, and the assumptions under which a result holds.

## Reproducibility
* `python run_all.py` rebuilds every project; `--only AM-150`, `--track applied-math --category H` select subsets.
* Random numbers come from a generator seeded by the project id, so reruns give identical numbers.
* Downloaded datasets are cached in `data_cache/` (not committed); the first run needs internet access.
* `python run_all.py --index-only` regenerates `PROJECTS.md`, `PROJECTS.csv` and the website in `docs/`.

## What this repository is not
It is not a substitute for building and measuring hardware. Simulations share the idealisations of their models,
and real datasets were recorded by others under their own conditions. The projects are best read as worked,
checkable examples of the mathematics — and as starting points for experiments on real benches.
