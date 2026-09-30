# Contributing to Nyquist Labs

Thank you for helping. Issues and pull requests are welcome in every repository — especially reports of a prediction that
is wrong, an error analysis that claims more than the numbers show, a broken link, or a project that no longer runs.

## The documentation standard

Every project has **one folder** and **one README** with these sections, in this order:

| Section | What it must contain |
|---|---|
| **Problem** | The engineering question in one or two sentences. |
| **Prediction** | The expected result from theory, written *before* measuring: formulas, assumptions, published values. A guess is allowed if it is labelled "my guess". |
| **Method** | How the result is measured: model, simulator, dataset (with source), parameters, sample sizes. Enough detail to redo it. |
| **Measured results** | A table: *Quantity · Predicted · Measured · Error · Within tolerance*. Tolerances are set in advance; relative tolerances in percent. |
| **Error analysis** | Why predicted and measured differ — model limits, finite samples, numerical error, bugs found. Keep wrong predictions in the table and explain them; never tune a prediction after seeing the measurement. |
| **Reproduce** | The exact command that regenerates every number and figure. |
| **License** | MIT for code and text; datasets under their own licences, credited. |

Plus a one-line summary, the main figure, the data source, and the disclosure of how the work was produced.

## Rules for results

- **No hand-typed numbers.** Every value in a results table is computed by the project's code.
- **"Measured" means independently obtained**: a separate numerical model, an HDL simulation, a public dataset — or a real
  bench measurement, which must be labelled as such.
- **Reproducible**: seeded random numbers; downloaded data fetched by code from a stable URL and cached, not committed.
- **Honest attribution**: say when code or text was produced with AI assistance, and credit datasets and prior work.

## Project layout (in the `projects` repository)

```
projects/<track>/<category>/<ID>-<short-slug>/
    project.py      META (problem, prediction, method) + run(p): predict → measure → compare → explain
    README.md       generated from project.py — do not edit by hand
    figures/  data/  results.json
```

Start from this organisation's `project-template` repository, run
`python run_all.py --only <ID>`, check the generated README, and open a pull request.

## Conduct

Be kind and specific. Critique results, not people.
