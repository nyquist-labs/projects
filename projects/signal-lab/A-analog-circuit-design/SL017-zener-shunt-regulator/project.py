from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-017", title="Zener shunt regulator", level="E",
    tools="eelab mini-SPICE (diode with reverse breakdown)",
    summary="A 5.1 V zener and 220 Ω series resistor from 12 V: predict the maximum load current, "
            "zener dissipation and line regulation, then sweep load and input.",
    problem="A zener regulator is the simplest voltage reference. How much load can it hold before "
            "regulation fails, and where does the power go?",
    theory=r"""Series current $I_S=(V_{in}-V_Z)/R_S$ splits between zener and load. Regulation holds while
$I_Z>0$, so $I_{L,max} \approx (12-5.1)/220 = 31.4$ mA. At no load the zener dissipates
$P_Z=V_Z I_S=0.16$ W. Line regulation is set by the zener's dynamic resistance:
$\Delta V_{out}/\Delta V_{in} = r_z/(R_S+r_z)$.""",
    method="""Zener modelled as a diode with BV = 5.1 V, 5 mA at BV, exponential breakdown (ideality 1). DC sweeps of load
current 0–45 mA and of input 8–16 V.""",
)


def build(vin=12.0, il=0.0):
    ck = Circuit("zener")
    ck.V("in", "in", "0", dc=vin)
    ck.R("s", "in", "out", 220)
    ck.D("z", "0", "out", Is=1e-14, N=1.0, BV=5.1, IBV=5e-3)
    ck.I("L", "out", "0", dc=il)
    return ck


def run(p):
    ils = np.linspace(0, 45e-3, 91)
    vo = np.array([build(12, i).op()["out"] for i in ils])
    Vz = vo[0]
    lim = ils[np.argmax(vo < 0.98 * Vz)]
    p.compare("Output voltage at no load", 5.1, Vz, "V", tol=3)
    p.compare("Max load for regulation (−2 % point)", (12 - Vz) / 220, lim, "A", tol=15)
    p.compare("Zener dissipation at no load", 5.1 * (12 - 5.1) / 220, Vz * (12 - Vz) / 220, "W", tol=5)
    vins = np.linspace(8, 16, 33)
    vl = np.array([build(v, 10e-3).op()["out"] for v in vins])
    slope = np.polyfit(vins, vl, 1)[0]
    Iz = (12 - Vz) / 220 - 10e-3
    rz = 1.0 * 0.025852 / Iz
    p.compare("Line regulation ΔV_out/ΔV_in", rz / (220 + rz), slope, "", kind="abs")
    p.write("simulation/zener.cir", build().to_spice(), "SPICE netlist")
    fig, ax = p.fig(1, 2)
    ax[0].plot(ils * 1e3, vo, color=C_MEAS, label="simulated")
    ax[0].axvline((12 - 5.1) / 220 * 1e3, ls="--", color=C_PRED, label="predicted I_L,max")
    ax[0].plot(ils * 1e3, 12 * 1 / (1 + 220 * ils / 12), ":", color="gray")
    style_axes(ax[0], "I_load (mA)", "V_out (V)", "Load regulation")
    ax[1].plot(vins, vl, color=C_MEAS, label="simulated")
    style_axes(ax[1], "V_in (V)", "V_out (V)", "Line regulation (10 mA load)")
    p.save(fig, "regulation", "Output collapses once the load steals all the zener current.")
    Pz = vo * ((12 - vo) / 220 - ils)
    p.metric("Efficiency at 25 mA load", vo[50] * ils[50] / (12 * (12 - vo[50]) / 220) * 100, "%")
    p.csv("load_sweep", iload_a=ils, vout_v=vo, pzener_w=Pz)
    p.discuss("""Regulation fails slightly *before* the simple limit because the zener's knee is soft: as its
current approaches zero its voltage falls, so the output already sags 2 % while a little current still
flows. Line regulation follows r_z/(R_S + r_z) with r_z = N·V_T/I_Z, and the efficiency figure shows the
shunt regulator's real weakness: it burns the full series current at all times, whatever the load.""")
