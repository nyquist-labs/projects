from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-015", title="Rectifier and reservoir-capacitor ripple study", level="E",
    tools="eelab mini-SPICE transient (1N4001-class diode model)",
    summary="Half-wave vs full-wave bridge rectifiers feeding a 100 Ω load: predict ripple from "
            "V_p/(f·R·C) and measure it for three capacitor sizes.",
    problem="How big must the reservoir capacitor be, and why does a full-wave bridge halve the "
            "ripple for the same capacitor?",
    theory=r"""Between recharges the capacitor supplies the load almost linearly, so
$$V_{r,pp}\approx\frac{V_{p}}{f_r R C},\qquad f_r = f \text{ (half-wave)},\ 2f\text{ (full-wave)}$$
with $V_p$ the peak after diode drops ($V_p = 12\sqrt2 - V_D$ half-wave, $-2V_D$ bridge). 60 Hz, 12 V RMS,
R = 100 Ω, C ∈ {470, 1000, 2200} µF.""",
    method="""1N4001-like diode (Is = 14 nA, N = 1.98, Rs = 34 mΩ), 0.5 Ω transformer winding resistance. 250 ms
transient (backward Euler, 20 µs step); ripple = max − min of the output over the last 50 ms.""",
)

D = dict(Is=14.1e-9, N=1.984, Rs=0.034)


def run(p):
    Vp_src = 12 * np.sqrt(2)
    res = []
    for kind in ("half", "full"):
        for C in (470e-6, 1000e-6, 2200e-6):
            ck = Circuit(f"{kind} {C}")
            ck.V("ac", "a", "b", wave=lambda t: Vp_src * np.sin(2 * pi * 60 * t))
            ck.R("w", "b", "bb", 0.5)
            if kind == "half":
                ck.R("gnd", "bb", "0", 1e-3)
                ck.D("1", "a", "out", **D)
                nd = 1
            else:
                ck.D("1", "a", "out", **D); ck.D("2", "bb", "out", **D)
                ck.D("3", "0", "a", **D); ck.D("4", "0", "bb", **D)
                nd = 2
            ck.C("res", "out", "0", C); ck.R("L", "out", "0", 100)
            if kind == "full" and C == 1000e-6:
                p.write("simulation/bridge_1000uF.cir", ck.to_spice(), "SPICE netlist (bridge, 1000 µF)")
            tr = ck.tran(0.25, 20e-6, method="be", uic=True)
            v = tr.v("out"); t = tr.t
            m = t > 0.2
            rip = v[m].max() - v[m].min()
            Vp = v[m].max()
            fr = 60 * (1 if kind == "half" else 2)
            pred = Vp / (fr * 100 * C)
            p.compare(f"{kind}-wave, C = {C*1e6:g} µF: ripple (pk-pk)", pred, rip, "V", tol=15)
            refined = Vp * (1 - np.exp(-1 / (fr * 100 * C)))
            p.metric(f"{kind}-wave, {C*1e6:g} µF: exponential-decay estimate", refined, "V", "V_p(1−e^(−T/RC))")
            res.append((kind, C, pred, rip, Vp, t, v))
    p.metric("Peak output, half-wave (1000 µF)", res[1][4], "V", f"diode drop ≈ {Vp_src - res[1][4]:.2f} V")
    p.metric("Peak output, bridge (1000 µF)", res[4][4], "V", f"two diode drops ≈ {Vp_src - res[4][4]:.2f} V")
    fig, ax = p.fig()
    for i, (kind, C, pred, rip, Vp, t, v) in enumerate([res[1], res[4]]):
        m = t > 0.17
        ax.plot((t[m] - 0.17) * 1e3, v[m], color=COLORS[i], label=f"{kind}-wave, 1000 µF")
    style_axes(ax, "time (ms)", "V_out (V)", "Output ripple: the bridge recharges twice per cycle")
    p.save(fig, "ripple_waveforms", "Same capacitor, same load: full-wave ripple is about half.")
    fig, ax = p.fig()
    for i, kind in enumerate(("half", "full")):
        rr = [r for r in res if r[0] == kind]
        Cs = np.array([r[1] for r in rr]) * 1e6
        ax.loglog(Cs, [r[2] for r in rr], "--", color=COLORS[i], label=f"{kind}-wave predicted")
        ax.loglog(Cs, [r[3] for r in rr], "o-", color=COLORS[i], label=f"{kind}-wave simulated")
    style_axes(ax, "C (µF)", "ripple pk-pk (V)", "Ripple ∝ 1/C")
    p.save(fig, "ripple_vs_c", "Predicted and simulated ripple versus reservoir capacitance.")
    p.csv("ripple", kind=[r[0] for r in res], C_uF=[r[1] * 1e6 for r in res], predicted_v=[r[2] for r in res], measured_v=[r[3] for r in res])
    p.discuss("""The simple formula slightly *overestimates* ripple because it assumes the capacitor discharges
for the full period, whereas the diodes actually recharge it during the last part of each cycle, and
because the load current falls as the voltage sags. The error is largest for the smallest capacitor,
where the voltage droops most. The peak is also lower than 12√2 by one diode drop (half-wave) or two
(bridge) plus the winding-resistance drop during the large charging-current pulses.""")
