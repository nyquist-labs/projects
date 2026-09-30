from eelab import *
from scipy.interpolate import CubicSpline

META = dict(
    id="AM-123", title="Lookup tables: linear vs spline interpolation", level="M",
    tools="Table-based evaluation of an NTC thermistor's temperature (β model) and of a sine, linear/cubic-spline/Chebyshev interpolation, error vs table size (O(h²) vs O(h⁴)), memory–accuracy trade-off for firmware",
    summary="Replace an expensive function with a small table plus interpolation, predict the error scaling for linear and cubic-spline interpolation, "
            "and determine the smallest table that meets a 0.01 °C (thermistor) or 16-bit (sine) accuracy target.",
    problem="A microcontroller converts thermistor resistance to temperature. How big must the lookup table be?",
    theory=r"""Linear interpolation error ≤ h²/8·max|f''|; natural/not-a-knot cubic spline error = O(h⁴)·max|f⁗|. So each halving of the table spacing gains ×4 accuracy with linear and ×16 with splines. For T(R) of an NTC (β = 3950, 10 kΩ at 25 °C),
using ln R as the table variable makes the function nearly linear (T⁻¹ is linear in ln R for the β model), which shrinks the table dramatically.""",
    method="""Thermistor over −20…100 °C; tables uniform in R and uniform in ln R; sizes 8–256 entries; max error over 10⁵ test points. Sine over a quarter wave with 16–512 entries; 16-bit target (≤ 1.5e-5). Error slopes fitted.""",
)


def T_of_R(R, beta=3950.0, R0=1e4, T0=298.15):
    return 1 / (1 / T0 + np.log(R / R0) / beta) - 273.15


def run(p):
    Rmin, Rmax = 1e4 * np.exp(3950 * (1 / 373.15 - 1 / 298.15)), 1e4 * np.exp(3950 * (1 / 253.15 - 1 / 298.15))
    test = np.exp(np.linspace(np.log(Rmin), np.log(Rmax), 100000))
    rows = []
    for n in (8, 16, 32, 64, 128, 256):
        for space in ("R", "lnR"):
            xs = np.linspace(Rmin, Rmax, n) if space == "R" else np.exp(np.linspace(np.log(Rmin), np.log(Rmax), n))
            u, ut = (xs, test) if space == "R" else (np.log(xs), np.log(test))
            lin = np.max(np.abs(np.interp(ut, u, T_of_R(xs)) - T_of_R(test)))
            spl = np.max(np.abs(CubicSpline(u, T_of_R(xs))(ut) - T_of_R(test)))
            rows.append((n, space, lin, spl))
    def slope(space, k):
        d = [(r_[0], r_[k]) for r_ in rows if r_[1] == space and r_[0] >= 32]
        return np.polyfit(np.log([a for a, _ in d]), np.log([b for _, b in d]), 1)[0]
    p.compare("ln R table, linear interpolation: error ∝ n^slope (−2)", -2.0, slope("lnR", 2), "", kind="abs", tol=0.15)
    p.compare("ln R table, cubic spline: error ∝ n^slope (−4)", -4.0, slope("lnR", 3), "", kind="abs", tol=0.3)
    need = lambda space, k: next((r_[0] for r_ in rows if r_[1] == space and r_[k] < 0.01), None)
    p.metric("Entries for 0.01 °C: linear in R / linear in ln R / spline in R / spline in ln R",
             f"{need('R', 2)} / {need('lnR', 2)} / {need('R', 3)} / {need('lnR', 3)}", "", "None = not reached with ≤ 256")
    xs_ = np.linspace(0, pi / 2, 1 << 18)
    srows = []
    for n in (16, 32, 64, 128, 256, 512):
        x = np.linspace(0, pi / 2, n)
        srows.append((n, np.max(np.abs(np.interp(xs_, x, np.sin(x)) - np.sin(xs_))), np.max(np.abs(CubicSpline(x, np.sin(x), bc_type=((1, 1.0), (1, 0.0)))(xs_) - np.sin(xs_)))))
    sr = np.array(srows)
    h = (pi / 2) / (sr[:, 0] - 1)
    p.compare("Sine table, linear interpolation: max error = h²/8 (worst ratio)", 1.0, np.max(sr[:, 1] / (h ** 2 / 8)), "", tol=2)
    p.metric("Quarter-wave sine entries for 16-bit accuracy (1.5e-5): linear / clamped spline",
             f"{int(next(n for n, e, _ in srows if e < 1.5e-5))} / {int(next(n for n, _, e in srows if e < 1.5e-5))}")
    fig, ax = p.fig(1, 2, w=11)
    for space, c in (("R", COLORS[1]), ("lnR", C_MEAS)):
        d = [r_ for r_ in rows if r_[1] == space]
        ax[0].loglog([r_[0] for r_ in d], [r_[2] for r_ in d], "o-", color=c, label=f"linear, table in {space}")
        ax[0].loglog([r_[0] for r_ in d], [r_[3] for r_ in d], "s--", color=c, label=f"spline, table in {space}")
    ax[0].axhline(0.01, color="gray", ls=":")
    style_axes(ax[0], "table entries", "max error (°C)", "Thermistor T(R), −20…100 °C")
    ax[1].loglog(sr[:, 0], sr[:, 1], "o-", color=C_MEAS, label="linear"); ax[1].loglog(sr[:, 0], sr[:, 2], "s-", color=C_PRED, label="clamped cubic spline"); ax[1].axhline(1.5e-5, color="gray", ls=":", label="16-bit")
    style_axes(ax[1], "table entries (quarter wave)", "max error", "Sine table")
    p.save(fig, "lookup", "Table-size vs accuracy for a thermistor linearisation and a sine table.")
    p.discuss("""The error scalings are textbook-exact: linear interpolation improves 4× per doubling of the table (error = h²/8·|f''| for the sine, matched to 2 %),
cubic splines 16×. The bigger lever, though, is choosing the table's *independent variable*: indexing the thermistor table by ln R instead of R makes
T nearly linear in the index (the β model is exactly linear in 1/T vs ln R), so a linear-interpolated table of a few dozen entries reaches 0.01 °C,
whereas a table uniform in R needs far more because the curve is steep at low temperature. In firmware the choice is then memory (entries) vs
cycles (spline evaluation) — and the transformation of variables is free.""")
# tol-convention: relative tolerances are in percent
