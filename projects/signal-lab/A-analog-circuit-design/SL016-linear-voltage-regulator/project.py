from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-016", title="LM317-style linear regulator", level="M",
    tools="eelab mini-SPICE (error amplifier + pass transistor + 1.25 V reference)",
    summary="Model an adjustable regulator from an error amp, a 1.25 V reference and an NPN pass "
            "device; predict V_out and measure line and load regulation.",
    problem="How does an LM317 turn a 1.25 V reference and two resistors into any output voltage, and "
            "how well does it hold that voltage as input and load change?",
    theory=r"""The regulator forces $V_{OUT}-V_{ADJ}=V_{REF}=1.25$ V, so a current $V_{REF}/R_1$ flows in R₁ and on through
R₂ together with the adjust-pin current:
$$V_{out}=1.25\left(1+\frac{R_2}{R_1}\right)+I_{ADJ}R_2$$
R₁ = 240 Ω, R₂ = 720 Ω, I_ADJ = 50 µA → 5.036 V. With loop gain T, output resistance is the pass
device's $1/g_m$ divided by (1+T) → load regulation of order mV per amp.""",
    method="""Pass transistor NPN (β = 100, Is = 1e-13) in a darlington-free follower, error amplifier op-amp
macromodel (A₀ = 10⁴ to mimic a simple on-chip amp), 50 µA adjust current source. DC sweeps: V_in
7–25 V at 100 mA; load 1 mA–1.5 A at V_in = 12 V.""",
)


def build(vin=12.0, iload=0.1):
    ck = Circuit("LM317 model")
    ck.V("in", "vin", "0", dc=vin)
    ck.Q("pass", "vin", "base", "out", Is=1e-13, BF=100, VAF=200)
    ck.V("ref", "refp", "adj", dc=1.25)
    ck.OPAMP("EA", "refp", "out", "ea", A0=1e4, GBW=1e6, VSAT=30)
    ck.R("b", "ea", "base", 100)
    ck.I("adj", "refp", "adj", dc=0)            # reference draws nothing extra
    ck.I("iadj", "0", "adj", dc=50e-6)          # 50 µA leaves the ADJ pin into R2
    ck.R("1", "out", "adj", 240); ck.R("2", "adj", "0", 720)
    ck.I("load", "out", "0", dc=iload)
    return ck


def run(p):
    Vpred = 1.25 * (1 + 720 / 240) + 50e-6 * 720
    o = build().op()
    p.write("simulation/lm317_model.cir", build().to_spice(), "SPICE netlist")
    p.compare("Output voltage (12 V in, 100 mA)", Vpred, o["out"], "V", tol=1)
    vins = np.linspace(7, 25, 37)
    vl = np.array([build(v, 0.1).op()["out"] for v in vins])
    line = (vl[-1] - vl[4]) / (vins[-1] - vins[4]) / Vpred * 100
    ils = np.logspace(-3, np.log10(1.5), 30)
    vo = np.array([build(12, i).op()["out"] for i in ils])
    load = (vo[0] - vo[-1]) / vo[0] * 100
    ro = -(vo[-1] - vo[-8]) / (ils[-1] - ils[-8])
    p.metric("Line regulation (9 → 25 V)", line, "%/V", "LM317 datasheet typ. 0.01 %/V")
    p.metric("Load regulation (1 mA → 1.5 A)", load, "%", "LM317 datasheet typ. 0.1 %")
    re_pass = 0.025852 / 1.0
    p.compare("Output resistance at ~1 A", (re_pass + 100 / 101) / (1 + 1e4 * 240 / 960), ro, "Ω", kind="abs",
              note="(r_e + R_b/β)/(1 + A₀β_fb)")
    dropout = vins[np.argmax(vl > 0.99 * vl[-1])]
    p.metric("Dropout (V_in where V_out reaches 99 %)", dropout - vl[-1], "V", "headroom above V_out")
    fig, ax = p.fig(1, 2)
    ax[0].plot(vins, vl, color=C_MEAS, label="simulated")
    ax[0].axhline(Vpred, ls="--", color=C_PRED, label="1.25(1+R₂/R₁)+I_adj·R₂")
    style_axes(ax[0], "V_in (V)", "V_out (V)", "Line regulation")
    ax[1].semilogx(ils, (vo - Vpred) * 1e3, color=C_MEAS, label="simulated")
    style_axes(ax[1], "I_load (A)", "V_out − V_pred (mV)", "Load regulation")
    p.save(fig, "regulation", "Output holds within millivolts across input and load.")
    p.csv("line", vin_v=vins, vout_v=vl); p.csv("load", iload_a=ils, vout_v=vo)
    p.discuss("""V_out matches the formula to within the error amplifier's finite-gain error (≈ V_out/A₀β). The
dropout region at low V_in is set by the base drive: the op-amp can't pull the base above V_in, so the
pass transistor needs V_BE + a little headroom — our single NPN drops out much lower than a real LM317
(≈ 2 V), which uses a darlington pass device and has internal current sources that need headroom. Load
regulation is dominated by the pass device's r_e = V_T/I_C divided by the loop gain.""")
