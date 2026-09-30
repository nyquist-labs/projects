from eelab import *
from eelab.laplace import solve, energy

META = dict(
    id="SL-127", title="Parallel-plate capacitor: fringing fields by finite differences", level="M",
    tools="2-D finite-difference Laplace solver (eelab.laplace), energy method, Palmer's fringing formula",
    summary="Compute the capacitance of finite parallel plates numerically, show how the fringing field makes it exceed "
            "εA/d, and compare the excess with Palmer's analytic fringing correction.",
    problem="εA/d is the first capacitance formula everyone learns. When is it wrong, and by how much?",
    theory=r"""Ideal: $C'=\varepsilon w/d$ (per unit depth). Fringing adds capacitance at the edges; Palmer (1927) for 2-D plates of width w, gap d:
$C'\approx\frac{\varepsilon w}{d}\left[1+\frac{d}{\pi w}+\frac{d}{\pi w}\ln\frac{2\pi w}{d}\right]$. For w/d = 10 the correction is ≈ 16 %; it vanishes as w/d → ∞.""",
    method="""Plates ±0.5 V, thickness one cell, in a 12w × 12w grounded box, Δ = d/20. w/d = 1, 2, 5, 10, 20. C′ from field energy.""",
)


def run(p):
    rows = []
    for ratio in (1, 2, 5, 10, 20):
        d = 1.0; w = ratio * d; h = d / 20
        L = max(12 * w, 40 * d)
        n = int(L / h) | 1; ny = n; nx = n
        if nx * ny > 900000:
            h = L / 941; nx = ny = 941
        yc, xc = ny // 2, nx // 2
        fixed = np.zeros((ny, nx), bool); V0 = np.zeros((ny, nx))
        fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
        hw = int(round(w / 2 / h)); hd = int(round(d / 2 / h))
        fixed[yc - hd, xc - hw: xc + hw + 1] = True; V0[yc - hd, xc - hw: xc + hw + 1] = 0.5
        fixed[yc + hd, xc - hw: xc + hw + 1] = True; V0[yc + hd, xc - hw: xc + hw + 1] = -0.5
        V = solve(fixed, V0)
        C = 2 * energy(V, np.ones_like(V), h) / 1.0 / 8.854e-12
        ideal = w / d
        palmer = ideal * (1 + d / (pi * w) + d / (pi * w) * np.log(2 * pi * w / d))
        rows.append((ratio, C, ideal, palmer))
        p.compare(f"w/d = {ratio}: C′/ε₀ vs Palmer fringing formula", palmer, C, "", tol=8)
        if ratio == 2:
            Vs = V; box = (yc, xc, hw, hd)
    r_, C_, I_, P_ = map(np.array, zip(*rows))
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(r_, C_ / I_, "o", ms=8, color=C_MEAS, label="finite-difference solver")
    ax[0].plot(r_, P_ / I_, "--", color=C_PRED, label="Palmer")
    ax[0].axhline(1, color="gray", ls=":", label="εA/d")
    ax[0].set_xscale("log")
    style_axes(ax[0], "w/d", "C / (εw/d)", "Fringing excess vs aspect ratio")
    yc, xc, hw, hd = box
    ax[1].contour(Vs[yc - 6 * hd: yc + 6 * hd, xc - 2 * hw: xc + 2 * hw], 21, cmap="RdBu", linewidths=.8)
    ax[1].set_aspect("equal"); ax[1].axis("off"); ax[1].set_title("equipotentials, w/d = 2", loc="left", fontsize=10)
    p.save(fig, "fringing", "Narrow plates store much of their energy outside the gap.")
    p.csv("capacitance", w_over_d=r_, C_fd=C_, C_ideal=I_, C_palmer=P_)
    p.discuss("""For wide plates the solver converges to εA/d, but at w/d = 1 the true capacitance is roughly double the textbook value
because the fringing field outside the gap stores as much energy as the field between the plates. Palmer's closed-form
correction tracks the numerical result closely down to w/d ≈ 2 and degrades for nearly square cross-sections, where its
conformal-mapping approximations break down. The one-cell-thick plates in the model add a little extra edge capacitance.""")
