"""Project harness: every project records predicted-vs-measured rows, figures, data
files and discussion, and this module turns them into a README + results.json."""
from __future__ import annotations

import json
import math
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
C_MEAS_, C_PRED_ = "#2a78d6", "#eb6834"

# Units that take SI prefixes when formatting (k, M, µ, n ...)
_SI_UNITS = {"Hz", "V", "A", "W", "Ω", "F", "H", "s", "m", "J", "C", "S", "bit/s", "b/s",
             "Vpp", "V/s", "A/s", "Wb", "T", "Hz/s", "sps", "ohm", "VA", "var", "Ω/m", "F/m", "H/m"}
_PREFIX = [(1e12, "T"), (1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"),
           (1e-6, "µ"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")]

DISCLOSURE = (
    "**Tooling & honesty.** This project was generated with Claude Code (Anthropic's AI coding "
    "assistant): the code, derivations, simulations and this write-up were AI-produced. "
    "*Measured* means computed by an independent model, simulator or public dataset — "
    "not a physical lab bench. Every number in the tables is reproduced by running the code."
)


def rng(seed_text: str):
    return np.random.default_rng(zlib.crc32(seed_text.encode()))


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-300))


def undb(x):
    return 10 ** (np.asarray(x) / 20)


def pct_err(pred, meas):
    return (meas - pred) / abs(pred) * 100 if pred != 0 else float("nan")


def find_crossing(x, y, level, logx=True, falling=None):
    """First x where y crosses `level` (linear interpolation, optionally in log-x)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    s = y - level
    idx = np.where(np.sign(s[:-1]) != np.sign(s[1:]))[0]
    if falling is not None:
        idx = [i for i in idx if (s[i] > s[i + 1]) == falling]
    if len(idx) == 0:
        return float("nan")
    i = idx[0]
    xa, xb = (np.log10(x[i]), np.log10(x[i + 1])) if logx else (x[i], x[i + 1])
    xc = xa + (xb - xa) * (level - y[i]) / (y[i + 1] - y[i])
    return float(10 ** xc if logx else xc)


def fmt(v, unit=""):
    """Human formatting with SI prefixes and 4 significant figures."""
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(v):
        return "n/a"
    if math.isinf(v):
        return "∞"
    if unit in _SI_UNITS and v != 0:
        for f, p in _PREFIX:
            if abs(v) >= f * 0.9995:
                return f"{v / f:.4g} {p}{unit}"
        return f"{v:.4g} {unit}"
    if v != 0 and (abs(v) >= 1e6 or abs(v) < 1e-3):
        s = f"{v:.4e}"
    else:
        s = f"{v:.4g}"
    return f"{s} {unit}".strip()


class Project:
    def __init__(self, folder: Path, meta: dict):
        self.dir = Path(folder)
        self.meta = dict(meta)
        self.rows, self.metrics, self.figs, self.csvs, self.files = [], [], [], [], []
        self.sections: dict[str, str] = {}
        self.discussion: list[str] = []
        self.rng = rng(meta["id"])
        (self.dir / "figures").mkdir(exist_ok=True)
        (self.dir / "data").mkdir(exist_ok=True)

    # ---------------------------------------------------------------- results
    def compare(self, quantity, predicted, measured, unit="", tol=None, kind="rel", note=""):
        """Predicted-vs-measured row. kind='rel' -> % error, 'abs' -> absolute difference."""
        predicted = float(np.real(predicted))
        measured = float(np.real(measured))
        if kind == "rel" and predicted != 0:
            err = pct_err(predicted, measured)
            err_s = f"{err:+.2f} %"
            ok = None if tol is None else abs(err) <= tol
        else:
            err = measured - predicted
            err_s = (("+" if err >= 0 else "") + fmt(err, unit)) if unit not in ("%",) else f"{err:+.3g} pp"
            if kind == "rel" and predicted == 0:
                err_s = f"{err:+.3g} {unit}".strip()
            ok = None if tol is None else abs(err) <= tol
        self.rows.append(dict(quantity=quantity, predicted=predicted, measured=measured, unit=unit,
                              error=err, error_str=err_s, kind=kind, ok=ok, note=note))
        return err

    def metric(self, quantity, value, unit="", note=""):
        if not isinstance(value, str):
            value = float(np.real(value))
        self.metrics.append(dict(quantity=quantity, value=value, unit=unit, note=note))

    # ---------------------------------------------------------------- figures
    def fig(self, nrows=1, ncols=1, w=None, h=None, **kw):
        import matplotlib.pyplot as plt
        w = w or (7.6 if ncols == 1 else 4.2 * ncols)
        h = h or (4.0 if nrows == 1 else 3.2 * nrows)
        fig, ax = plt.subplots(nrows, ncols, figsize=(w, h), **kw)
        return fig, ax

    def save(self, fig, name, caption=""):
        import matplotlib.pyplot as plt
        fig.tight_layout()
        path = self.dir / "figures" / f"{name}.png"
        fig.savefig(path)
        plt.close(fig)
        self.figs.append((f"figures/{name}.png", caption))

    def plot_compare(self, x, pred, meas, name, xlabel="", ylabel="", title="", caption="",
                     logx=False, logy=False, pred_label="predicted (theory)",
                     meas_label="measured (simulation)", marker=None):
        """One-call predicted-vs-measured overlay plot."""
        fig, ax = self.fig()
        if pred is not None:
            ax.plot(x, pred, "--", color=C_PRED_, label=pred_label, zorder=3)
        ax.plot(x, meas, color=C_MEAS_, label=meas_label, marker=marker, ms=4, zorder=2)
        if logx:
            ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title, loc="left")
        ax.legend()
        self.save(fig, name, caption)

    # ---------------------------------------------------------------- data
    def csv(self, name, max_rows=4000, **cols):
        import pandas as pd
        df = pd.DataFrame({k: np.asarray(v).ravel() if np.ndim(v) else [v] for k, v in cols.items()})
        return self.csv_df(name, df, max_rows)

    def csv_df(self, name, df, max_rows=4000):
        if len(df) > max_rows:
            step = int(math.ceil(len(df) / max_rows))
            df = df.iloc[::step]
        path = self.dir / "data" / f"{name}.csv"
        df.to_csv(path, index=False, float_format="%.6g")
        self.csvs.append(f"data/{name}.csv")
        return path

    def write(self, relpath, text, describe=""):
        path = self.dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.files.append((relpath, describe))
        return path

    def section(self, title, md):
        self.sections[title] = md.strip()

    def discuss(self, md):
        self.discussion.append(md.strip())

    # ---------------------------------------------------------------- output
    def _table(self):
        if not self.rows:
            return ""
        has_tol = any(r["ok"] is not None for r in self.rows)
        head = "| Quantity | Predicted | Measured | Error |" + (" Within tolerance |" if has_tol else "")
        sep = "|---|---|---|---|" + ("---|" if has_tol else "")
        lines = [head, sep]
        for r in self.rows:
            ok = "" if r["ok"] is None else ("yes" if r["ok"] else "**no**")
            line = (f"| {r['quantity']} | {fmt(r['predicted'], r['unit'])} | "
                    f"{fmt(r['measured'], r['unit'])} | {r['error_str']} |")
            lines.append(line + (f" {ok} |" if has_tol else ""))
        return "\n".join(lines)

    def _metrics(self):
        if not self.metrics:
            return ""
        lines = ["| Quantity | Value | Note |", "|---|---|---|"]
        for m in self.metrics:
            lines.append(f"| {m['quantity']} | {fmt(m['value'], m['unit'])} | {m['note']} |")
        return "\n".join(lines)

    def finish(self, runtime_s=None):
        m = self.meta
        out = [f"# {m['id']} · {m['title']}", "", f"> {m['summary']}", ""]
        if self.figs:
            out += [f"![{m['title']}]({self.figs[0][0]})", ""]
            if self.figs[0][1]:
                out += [f"*{self.figs[0][1]}*", ""]
        out += [f"**Track:** {m['track']} · **Category:** {m['category']} · **Level:** "
                f"{ {'E': 'Easy', 'M': 'Moderate', 'H': 'Hard'}[m['level']] } · "
                f"**Tools:** {m['tools']}", "",
                f"**Data:** {m.get('data', 'Simulated (numerical model in this repo).')}", ""]
        out += ["## Problem", "", m["problem"].strip(), ""]
        out += ["## Prediction", "", m["theory"].strip(), ""]
        out += ["## Method", "", m["method"].strip(), ""]
        out += ["## Measured results", "", "*Predicted vs measured vs error. \"Measured\" = computed by an independent simulation, HDL simulator or public dataset.*", ""]
        if self.rows:
            out += [self._table(), ""]
        if self.metrics:
            out += ["**Additional measurements**", "", self._metrics(), ""]
        for path, cap in self.figs[1:]:
            out += [f"![{cap or path}]({path})", ""] + ([f"*{cap}*", ""] if cap else [])
        for title, md in self.sections.items():
            out += [f"## {title}", "", md, ""]
        if self.discussion:
            out += ["## Error analysis", "",
                    "\n\n".join(self.discussion), ""]
        folder = self.dir.relative_to(ROOT).as_posix()
        out += ["## Reproduce", "", "```bash", "pip install -r requirements.txt",
                f"python run_all.py --only {m['id']}", "```", "",
                f"The script [`project.py`](project.py) regenerates every figure and number above."]
        files = [f"- [`{p}`]({p}) — {d}" if d else f"- [`{p}`]({p})" for p, d in self.files]
        files += [f"- [`{c}`]({c})" for c in self.csvs]
        if files:
            out += ["", "**Files produced**", ""] + files
        out += ["", "## License", "", "Code and text: MIT (see the repository [LICENSE](../../../../LICENSE)). Datasets remain under their own licences (see the repository README).",
                "", "---", "", DISCLOSURE, ""]
        (self.dir / "README.md").write_text("\n".join(out))
        res = dict(meta=m, rows=self.rows, metrics=self.metrics,
                   figures=[f for f, _ in self.figs], runtime_s=runtime_s, folder=folder)
        (self.dir / "results.json").write_text(json.dumps(res, indent=1, default=float))
        return res
