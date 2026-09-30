from eelab import *
from eelab.control import step_info

META = dict(
    id="SL-171", title="Integrator windup and anti-windup strategies", level="M",
    tools="PI loop with actuator saturation on a first-order plant; clamping and back-calculation anti-windup",
    summary="Show how a saturated actuator lets a PI integrator 'wind up' and cause large overshoot, predict the extra overshoot from "
            "the integrated error during saturation, and compare conditional integration and back-calculation fixes.",
    problem="When the actuator hits its limit the controller keeps integrating an error it can't act on. How bad is it, and "
            "which fix works best?",
    theory=r"""Plant G = 1/(s + 1) (τ = 1 s, gain 1), PI K_p = 5, K_i = 5, actuator limited to ±1.2 (just above the 1.0 needed at steady state). During saturation the
integrator accumulates ∫e dt; after leaving saturation it must be 'unwound' by an equal area of negative error, so overshoot area ≈ excess
integral. Back-calculation feeds (u_sat − u) back into the integrator with gain 1/T_t, T_t ≈ √(T_i·T_d) or ≈ T_i.""",
    method="""Unit step at t = 0, 10 ms steps. Variants: no anti-windup, conditional integration (freeze when saturated and error drives further), back-calculation
(T_t = 0.2 s). Measured overshoot, settling, and the negative-error area after saturation vs the integral accumulated during it.""",
)


def run(p):
    dt = 1e-3; T = 12; umax = 1.2
    res = {}
    for mode in ("none", "clamp", "backcalc"):
        y = I = 0.0; out = []; sat_area = 0.0; sat_time = 0.0
        for n in range(int(T / dt)):
            e = 1.0 - y
            u = 5 * e + 5 * I
            us = np.clip(u, -umax, umax)
            if mode == "none":
                I += e * dt
            elif mode == "clamp":
                if us == u or np.sign(e) != np.sign(u): I += e * dt
            else:
                I += (e + (us - u) / 5 / 0.2) * dt
            if us != u:
                sat_area += e * dt; sat_time += dt
            y += (-y + us) * dt
            out.append(y)
        t = np.arange(1, len(out) + 1) * dt; yv = np.array(out)
        res[mode] = (t, yv, sat_area, sat_time, step_info(t, yv, 1.0))
    t, y, sa, st, inf = res["none"]
    neg = -np.sum(np.minimum(1 - y, 0)) * dt
    p.compare("No anti-windup: overshoot area ≈ error integrated beyond the linear integrator state", sa - 0.0, neg, "s", tol=30,
              note="integral of (1 − y) accumulated while saturated")
    p.metric("No anti-windup: overshoot / settling", f"{inf['overshoot']:.1f} % / {inf['settle']:.2f} s")
    for mode in ("clamp", "backcalc"):
        i = res[mode][4]
        p.compare(f"{mode}: overshoot (should be ≪ windup case)", 0, i["overshoot"], "%", kind="abs")
        p.metric(f"{mode}: settling time", i["settle"], "s")
    fig, ax = p.fig()
    for i, (mode, lab) in enumerate((("none", "no anti-windup"), ("clamp", "conditional integration"), ("backcalc", "back-calculation"))):
        ax.plot(res[mode][0], res[mode][1], color=COLORS[i], label=lab)
    ax.axhline(1, color="gray", ls=":")
    style_axes(ax, "time (s)", "output", "Step with actuator limited to 1.2")
    p.save(fig, "windup", "Windup produces a large, slow overshoot; both anti-windup schemes remove it.")
    p.discuss("""While the actuator is pinned at its limit, the plain PI keeps integrating a large error; afterwards the output must overshoot until an equal area
of negative error unwinds the integrator — the measured overshoot area is of the same size as the error integrated during saturation. Both
anti-windup schemes stop that accumulation. Conditional integration is simplest; back-calculation also bleeds the integrator smoothly
toward a consistent value and is standard in industrial PID blocks.""")
