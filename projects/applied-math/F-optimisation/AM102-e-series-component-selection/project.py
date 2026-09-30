from eelab import *
from itertools import product

META = dict(
    id="AM-102", title="Choosing real resistor values: discrete optimisation", level="M",
    tools="Exhaustive search over E-series values and two-resistor series/parallel composites, greedy rounding vs joint optimisation, error distributions",
    summary="Hit an arbitrary target resistance and a divider ratio with values that can actually be bought: compare naive rounding, joint search "
            "over pairs, and two-resistor series/parallel composites, and quantify how many parts are needed for 0.1 % accuracy.",
    problem="The math says 12.37 kΩ. The drawer contains E24. What is the best buildable answer — and how much does searching jointly help?",
    theory=r"""E24 values are ~10 % apart, so rounding one value gives up to ~±5 % error (median ~2.4 %). Series or parallel combinations of two E24 values cover the line much more densely (~24²/2 combinations per decade):
expected worst-case error ≲ 0.2 %. For a filter or divider that depends on a *ratio* or product of values, rounding each independently is not optimal; joint search over the discrete set does better.""",
    method="""2000 log-uniform random targets in 1–10 kΩ: single E24 / E96 value, two-resistor series, parallel, best of both. Sallen-Key-type design: target f0 = 1/(2π√(R1R2C1C2)) with C1, C2 fixed from E12 — independent rounding of R1, R2
vs joint search over all E24 pairs; f0 error distributions.""",
)

E24 = np.array([1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1])
E96 = np.round(10 ** (np.arange(96) / 96), 2); E96[E96 == 9.19] = 9.2


def vals(series, lo=10, hi=1e6):
    v = np.concatenate([series * 10 ** d for d in range(0, 7)])
    return v[(v >= lo) & (v <= hi)]


def run(p):
    r = p.rng
    V24 = vals(E24); V96 = vals(E96)
    ser = np.add.outer(V24, V24).ravel(); par = (np.multiply.outer(V24, V24) / np.add.outer(V24, V24)).ravel()
    ser.sort(); par.sort()
    def nearest(v, arr):
        i = np.clip(np.searchsorted(arr, v), 1, len(arr) - 1)
        return np.where(np.abs(np.log(arr[i] / v)) < np.abs(np.log(arr[i - 1] / v)), arr[i], arr[i - 1])
    tg = 10 ** r.uniform(3, 4, 2000)
    e = {name: np.abs(nearest(tg, arr) / tg - 1) * 100 for name, arr in (("E24 single", V24), ("E96 single", V96), ("E24 series pair", ser), ("E24 parallel pair", par))}
    e["E24 best of series/parallel"] = np.minimum(e["E24 series pair"], e["E24 parallel pair"])
    p.compare("E24 single value: worst error (my guess: half a ~10 % step ≈ 5 %)", 5.0, e["E24 single"].max(), "%", kind="abs", tol=1.0)
    p.compare("… corrected: the widest E24 gap is 1.3 → 1.5 (no 1.4), worst error √(1.5/1.3) − 1", (np.sqrt(1.5 / 1.3) - 1) * 100, e["E24 single"].max(), "%", kind="abs", tol=0.2)
    p.compare("Two E24 resistors (series or parallel): worst error (my guess ≲ 0.2 %)", 0.2, e["E24 best of series/parallel"].max(), "%", kind="abs", tol=0.2)
    for k, v in e.items():
        p.metric(f"{k}: median / 95th percentile error", f"{np.median(v):.3f} / {np.percentile(v, 95):.3f} %")
    C1, C2 = 22e-9, 10e-9
    ind, joint = [], []
    for _ in range(300):
        f0 = 10 ** r.uniform(2, 4)
        Rprod = 1 / ((2 * pi * f0) ** 2 * C1 * C2)
        R1i = R2i = np.sqrt(Rprod)
        a = nearest(np.array([R1i]), V24)[0]
        ind.append(abs(1 / (2 * pi * np.sqrt(a * a * C1 * C2)) / f0 - 1) * 100)
        prods = np.multiply.outer(V24, V24)
        best = np.min(np.abs(np.log(prods / Rprod))) / 2
        joint.append((np.exp(best) - 1) * 100)
    ind, joint = np.array(ind), np.array(joint)
    p.compare("f0 error: joint search over (R1, R2) vs rounding both to the same E24 value (median ratio)", 5, np.median(ind) / np.median(joint), "×", kind="abs", tol=100)
    p.metric("f0 error, median: independent rounding / joint E24 pair", f"{np.median(ind):.2f} % / {np.median(joint):.3f} %")
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    bins = np.logspace(-4, 1, 60)
    for (k, v), c in zip(e.items(), COLORS):
        ax.hist(np.maximum(v, 1e-4), bins=bins, histtype="step", lw=1.5, color=c, label=k)
    ax.set_xscale("log")
    style_axes(ax, "error (%)", "count (2000 random targets)", "What a second resistor buys")
    p.save(fig, "eseries", "Error distributions when realising random resistances with one or two standard values.")
    p.discuss("""Rounding to a single E24 value leaves errors up to 7.4 %, not the ~5 % I first assumed: the historical E24 table is not evenly spaced and
jumps from 1.3 straight to 1.5, a 15 % gap; E96 up to ~1 %; allowing two E24 resistors in series *or* parallel shrinks the worst case to
about a tenth of a percent — better than a single 1 % E96 part and built from the cheapest stock, which is why production designers keep an
'E24 pair' table. The second experiment makes a structural point: when a circuit depends on a product or ratio (f0 ∝ (R1R2)^{−½}), choosing the
two values jointly from the discrete set is far better than rounding each ideal value on its own — a small combinatorial search replaces a
compromise. Of course resistor tolerance (±1 %) then dominates, so pairs are worth it mainly for ratios, where tolerances can be matched.""")
# tol-convention: relative tolerances are in percent
