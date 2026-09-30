from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-103", title="L-network impedance-matching designer", level="M",
    tools="Analytic L-network solver + verification in the eelab mini-SPICE (AC analysis)",
    summary="Solve the two-element L-network that matches an arbitrary load (e.g. a 25 − j40 Ω antenna) to 50 Ω at "
            "100 MHz, choose L/C values, then verify the match and bandwidth by circuit simulation.",
    problem="A load that isn't 50 Ω reflects power. What two components cancel the mismatch, and how wide is the "
            "resulting match?",
    theory=r"""For R_L < R_S: series element $X_s$ then shunt $B$: $B=\pm\frac{\sqrt{R_L/R_S}\cdots}{}$ — in closed form (Pozar 5.1)
$X=\pm\sqrt{R_L(R_S-R_L)}-X_L$, $B=\pm\frac{\sqrt{(R_S-R_L)/R_L}}{R_S}$. The loaded Q is $Q=\sqrt{R_S/R_L-1}$ and the
fractional bandwidth for a given VSWR scales roughly as $\approx\frac{1}{Q}\cdot\frac{VSWR-1}{\sqrt{VSWR}}$; lower Q → wider match.""",
    method="""Load 25 − j40 Ω at 100 MHz (modelled as 25 Ω + 39.8 pF). Both L-network solutions computed; component values from X and B.
Verification: a 50 Ω source driving the network + load in the mini-SPICE AC sweep 50–150 MHz; Γ at the input from the
simulated input impedance; VSWR ≤ 2 bandwidth measured.""",
)


def run(p):
    f0, R0 = 100e6, 50.0
    w = 2 * pi * f0
    RL, XL = 25.0, -40.0
    CL = -1 / (w * XL)
    sols = []
    for s in (+1, -1):
        X = s * np.sqrt(RL * (R0 - RL)) - XL
        B = s * np.sqrt((R0 - RL) / RL) / R0
        sols.append((X, B))
    fig, ax = p.fig()
    f = np.linspace(50e6, 150e6, 1001)
    for i, (X, B) in enumerate(sols):
        ck = Circuit("L-match")
        ck.V("s", "src", "0", ac=1); ck.R("s", "src", "in", R0)
        if X > 0: ck.L("x", "in", "mid", X / w)
        else: ck.C("x", "in", "mid", -1 / (w * X))
        if B > 0: ck.C("b", "in", "0", B / w)
        else: ck.L("b", "in", "0", -1 / (w * B))
        ck.R("l", "mid", "lc", RL); ck.C("l", "lc", "0", CL)
        res = ck.ac(f)
        vin = res.v("in"); iin = (1 - vin) / R0
        Zin = vin / iin
        G = (Zin - R0) / (Zin + R0)
        g0 = abs(np.interp(f0, f, np.abs(G)))
        vs = (1 + np.abs(G)) / (1 - np.abs(G))
        ok = f[vs <= 2]
        bw = ok.max() - ok.min()
        Q = np.sqrt(R0 / RL - 1)
        p.compare(f"Solution {i+1}: |Γ| at 100 MHz", 0, g0, "", kind="abs")
        p.metric(f"Solution {i+1} components", f"series {'L' if X > 0 else 'C'} = {X/w*1e9 if X > 0 else -1/(w*X)*1e12:.2f} {'nH' if X > 0 else 'pF'}, shunt {'C' if B > 0 else 'L'} = {B/w*1e12 if B > 0 else -1/(w*B)*1e9:.2f} {'pF' if B > 0 else 'nH'}")
        p.compare(f"Solution {i+1}: VSWR ≤ 2 bandwidth (≈ f₀/Q·(VSWR−1)/√VSWR estimate)", f0 / Q * 1 / np.sqrt(2), bw, "Hz", tol=60)
        ax.plot(f / 1e6, db(G), color=COLORS[i], label=f"solution {i+1}")
        if i == 0:
            p.write("simulation/l_match.cir", ck.to_spice(), "SPICE netlist (solution 1)")
    Gun = ((RL + 1j * (w * 0 + XL * 100e6 / f)) - R0) / ((RL + 1j * XL * 100e6 / f) + R0)
    ax.plot(f / 1e6, db(Gun), "--", color="gray", label="unmatched load")
    style_axes(ax, "frequency (MHz)", "return loss |Γ| (dB)", "L-network match of 25 − j40 Ω to 50 Ω")
    p.save(fig, "match", "Both solutions reach a perfect match at 100 MHz; bandwidth is set by the network Q.")
    p.discuss("""Both closed-form L-network solutions produce a reflection coefficient of essentially zero at 100 MHz in the independent
circuit simulation, confirming the algebra (and the component values the web Smith chart in SL-101 would trace). The
bandwidth estimate from the loaded Q is only a rough guide — it ignores that the load's own reactance also varies with
frequency — which is why the two solutions, having the same Q, still have different bandwidths. For wider bandwidth use
two cascaded L-sections through an intermediate impedance (lower Q per section).""")
