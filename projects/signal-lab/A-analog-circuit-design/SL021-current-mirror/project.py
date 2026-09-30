from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-021", title="BJT current mirrors (basic vs Wilson)", level="M",
    tools="eelab mini-SPICE DC sweeps (Ebers-Moll with Early effect)",
    summary="Measure the copying accuracy and output impedance of a two-transistor mirror and a "
            "Wilson mirror against β- and Early-effect predictions.",
    problem="A current mirror should copy a reference current regardless of the output voltage. "
            "How accurate is the copy, and how constant is it?",
    theory=r"""Basic mirror: base currents steal from the reference, $I_{out}=I_{ref}/(1+2/\beta)$, and the Early
effect gives $r_o = (V_A+V_{CE})/I_{out}$, i.e. $\Delta I/\Delta V = 1/r_o$.
Wilson mirror: β error $\approx 2/\beta^2$, but Q₁ sits at $V_{CE}=2V_{BE}$ while Q₂ sits at $V_{BE}$, an Early mismatch of
$\approx V_{BE}/V_A$ (1.4 % here) that the textbook formula omits, output resistance $\approx \beta r_o/2$ (feedback through the
third transistor).""",
    method="""β = 100, V_A = 50 V, I_ref set to 1 mA by a resistor from 10 V. Output voltage swept 1–10 V;
current ratio at V_out = V_BE and output resistance from the slope.""",
)


def build(kind, vout):
    ck = Circuit(kind)
    ck.V("cc", "vcc", "0", dc=10)
    ck.V("o", "vo", "0", dc=vout)
    Q = dict(Is=1e-15, BF=100, VAF=50)
    if kind == "basic":
        ck.R("ref", "vcc", "c1", 9.3e3)
        ck.Q("1", "c1", "c1", "0", **Q); ck.Q("2", "vo", "c1", "0", **Q)
    else:
        ck.R("ref", "vcc", "c1", 8.6e3)
        ck.Q("1", "c1", "b12", "0", **Q)       # reference side
        ck.Q("2", "b12", "b12", "0", **Q)      # diode-connected
        ck.Q("3", "vo", "c1", "b12", **Q)      # output device
    return ck


def run(p):
    beta, VA = 100, 50
    vs = np.linspace(1, 10, 37)
    fig, ax = p.fig()
    for i, kind in enumerate(("basic", "wilson")):
        Iout, Iref = [], []
        for v in vs:
            ck = build(kind, v)
            o = ck.op()
            Iout.append(-o["I(o)"])
            Iref.append((10 - o["c1"]) / (9.3e3 if kind == "basic" else 8.6e3))
        Iout, Iref = np.array(Iout), np.array(Iref)
        k = np.argmin(abs(vs - 1.4))
        ratio = Iout[k] / Iref[k]
        slope = np.polyfit(vs[vs > 2], Iout[vs > 2], 1)[0]
        if kind == "basic":
            vbe = 0.025852 * np.log(Iref[k] / 1e-15)
            p.compare("Basic: I_out/I_ref (β error, at V_CE = V_BE)", 1 / (1 + 2 / beta) * (1 + (1.4 - vbe) / VA), ratio, "", tol=1)
            p.compare("Basic: output resistance", (VA + 5) / Iout[k], 1 / slope, "Ω", tol=10)
        else:
            p.compare("Wilson: I_out/I_ref (β² error × Early mismatch)", (1 - 2 / (beta**2 + 2 * beta + 2)) * (1 + 0.7 / VA) / (1 + 1.4 / VA), ratio, "", tol=1)
            p.compare("Wilson: output resistance", beta * (VA + 5) / Iout[k] / 2, 1 / slope, "Ω", tol=35)
        ax.plot(vs, Iout * 1e3, "o-", ms=3, color=COLORS[i], label=f"{kind} mirror")
        p.write(f"simulation/{kind}_mirror.cir", build(kind, 5).to_spice(), f"SPICE netlist ({kind})")
        p.csv(f"{kind}_sweep", vout_v=vs, iout_a=Iout, iref_a=Iref)
    style_axes(ax, "V_out (V)", "I_out (mA)", "Output current vs output voltage")
    p.save(fig, "iout_vs_vout", "The Wilson mirror's output is nearly flat; the basic mirror slopes by 1/r_o.")
    p.discuss("""The basic mirror's copy error is the 2/β base-current loss plus the Early-effect mismatch between the
diode-connected transistor (V_CE = V_BE) and the output transistor (V_CE = V_out). Its output
resistance equals r_o within a few percent. The Wilson mirror's negative feedback both cancels the
base-current error to second order and multiplies the output resistance by ~β/2; the measured
value is somewhat below βr_o/2 because the formula assumes r_o ≫ everything else in the loop.""")
