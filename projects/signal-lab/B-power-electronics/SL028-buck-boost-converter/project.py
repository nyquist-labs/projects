from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-028", title="Inverting buck-boost converter", level="M",
    tools="eelab mini-SPICE switch-level transient",
    summary="One switch, one inductor, one diode — and a negative output that can be larger or smaller "
            "than the input. Verify −D/(1−D) and compare stresses with buck and boost.",
    problem="How does the buck-boost produce both step-down and step-up with inverted polarity, and "
            "what does that flexibility cost in component stress?",
    theory=r"""The inductor is charged from $V_{in}$ during $DT$ and dumps into the output during $(1-D)T$:
$$\frac{V_{out}}{V_{in}}=-\frac{D}{1-D}$$
The switch sees $V_{in}+|V_{out}|$ and the inductor carries $I_L = I_{out}/(1-D)$ — higher stress than
either buck ($I_L=I_{out}$) or boost ($V_{sw}=V_{out}$).""",
    method="""V_in = 12 V, L = 47 µH, C = 100 µF, R_L = 10 Ω, f_sw = 100 kHz, D ∈ {0.33, 0.5, 0.67}. Switch in series with
V_in to the inductor top; the inductor goes to ground; the diode points from output to the inductor
node (so the output goes negative).""",
)


def run(p):
    Vin, L, C, RL, fsw = 12.0, 47e-6, 100e-6, 10.0, 100e3
    rows = []
    for Dc in (0.33, 0.5, 0.67):
        ck = Circuit("buck-boost")
        ck.V("in", "vin", "0", dc=Vin)
        ck.SW("q", "vin", "x", lambda t, Dc=Dc: (t * fsw) % 1 < Dc, ron=0.05, roff=1e6)
        ck.L("b", "x", "0", L)
        ck.D("d", "out", "x", Is=1e-5, N=1.05)
        ck.C("o", "out", "0", C); ck.R("L", "out", "0", RL)
        if Dc == 0.5:
            p.write("simulation/buck_boost.cir", ck.to_spice(), "SPICE netlist")
        M = Dc / (1 - Dc)
        v0 = M * Vin * 0.96
        tr = ck.tran(3e-3, 25e-9, method="be", ic={"out": -v0, "I(b)": v0 / RL / (1 - Dc)})
        m = tr.t >= tr.t[-1] - 40e-6
        vo = tr.v("out")[m].mean()
        il = tr.i("b")[m]
        p.compare(f"D = {Dc}: V_out", -M * Vin, vo, "V", tol=6)
        p.compare(f"D = {Dc}: mean inductor current", abs(vo) / RL / (1 - Dc), abs(il.mean()), "A", tol=5)
        vsw = Vin + abs(vo)
        p.metric(f"D = {Dc}: switch off-state voltage", vsw, "V", "V_in + |V_out|")
        rows.append((Dc, vo, -M * Vin))
    D_, vo_, vp_ = map(np.array, zip(*rows))
    Dd = np.linspace(0.2, 0.75, 100)
    fig, ax = p.fig()
    ax.plot(Dd, -Dd / (1 - Dd) * Vin, "--", color=C_PRED, label="−D/(1−D)·V_in")
    ax.plot(D_, vo_, "o", color=C_MEAS, ms=8, label="simulated")
    ax.axhline(-Vin, color="gray", lw=.8, ls=":")
    style_axes(ax, "duty cycle D", "V_out (V)", "Buck-boost: |V_out| < V_in for D < ½, > V_in for D > ½")
    p.save(fig, "transfer", "Inverting output crossing −V_in at D = 0.5.")
    p.csv("duty_sweep", duty=D_, vout_v=vo_, vout_pred_v=vp_)
    p.discuss("""Measured magnitudes are slightly lower than D/(1−D)·V_in because of the diode drop and switch/
inductor resistance; the error grows at high D because the inductor current (I_out/(1−D)) — and
hence every resistive loss — grows. The stress numbers show the price of flexibility: at D = 0.67 the
switch blocks ~36 V for a 12 V input.""")
