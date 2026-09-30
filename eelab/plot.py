"""Consistent, colour-blind-safe figure style (validated categorical order)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
C_MEAS = COLORS[0]   # measured / simulated  -> blue, solid
C_PRED = COLORS[1]   # predicted / theory     -> orange, dashed
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 110, "figure.facecolor": "#fcfcfb",
    "axes.facecolor": "#fcfcfb", "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 9.5,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.prop_cycle": matplotlib.cycler(color=COLORS),
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "lines.linewidth": 1.8, "lines.markersize": 5, "legend.fontsize": 8.5,
    "legend.frameon": False, "font.family": "DejaVu Sans", "figure.titlesize": 12,
    "figure.titleweight": "bold", "image.cmap": "viridis",
})

def style_axes(ax, xlabel=None, ylabel=None, title=None, legend=True):
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)
    if title: ax.set_title(title, loc="left")
    if legend and ax.get_legend_handles_labels()[0]:
        ax.legend()
    return ax
