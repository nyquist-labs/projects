from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-008", title="BJT differential pair", level="M",
    tools="eelab mini-SPICE (DC sweep + AC), Monte Carlo mismatch",
    summary="Measure the tanh transfer curve, differential gain and common-mode rejection of the "
            "long-tailed pair — the input stage of every op-amp.",
    problem="Why does a differential pair amplify the difference between its inputs but ignore what "
            "they have in common, and what limits that rejection?",
    theory=r"""With tail current $I_{EE}$: $\Delta I_C = I_{EE}\tanh\!\left(\frac{v_d}{2V_T}\right)$ (linear only for
$|v_d| \ll 2V_T$). Single-ended differential gain $A_d = g_mR_C/2$ with $g_m = I_{EE}/(2V_T)$.
Common-mode gain (tail resistance $R_{EE}$): $A_{cm}\approx -R_C/(2R_{EE})$, so
$\mathrm{CMRR}\approx g_mR_{EE}$. With perfectly matched halves the *differential output* has
CMRR → ∞; a load mismatch δ gives $A_{cm,diff}\approx \delta R_C/(2R_{EE})$.""",
    method="""±12 V supplies, R_C = 5 kΩ, tail resistor R_EE = 10 kΩ to −12 V. DC sweep of v_d (−150…150 mV),
AC small-signal gains, and 300 Monte Carlo builds with ±1 % R_C mismatch for differential-output CMRR.""",
)


def build(vd=0.0, vcm=0.0, rc1=5e3, rc2=5e3, ac_mode="diff"):
    ck = Circuit("diff pair")
    ck.V("p", "vp", "0", dc=12); ck.V("n", "vn", "0", dc=-12)
    a1, a2 = (0.5, -0.5) if ac_mode == "diff" else (1, 1)
    ck.V("i1", "b1", "0", dc=vcm + vd / 2, ac=a1); ck.V("i2", "b2", "0", dc=vcm - vd / 2, ac=a2)
    ck.R("c1", "vp", "c1", rc1); ck.R("c2", "vp", "c2", rc2)
    ck.Q("1", "c1", "b1", "e", Is=1e-15, BF=200, VAF=100)
    ck.Q("2", "c2", "b2", "e", Is=1e-15, BF=200, VAF=100)
    ck.R("ee", "e", "vn", 10e3)
    return ck


def run(p):
    VT = 0.025852
    vds = np.linspace(-0.15, 0.15, 61)
    dI = []
    for vd in vds:
        o = build(vd).op()
        dI.append(((12 - o["c1"]) / 5e3 - (12 - o["c2"]) / 5e3))
    dI = np.array(dI)
    o = build().op()
    IEE = 2 * (12 - o["c1"]) / 5e3
    IEE_pred = (12 - 0.65) / 10e3
    p.write("simulation/diff_pair.cir", build().to_spice(), "SPICE netlist")
    p.compare("Tail current I_EE", IEE_pred, IEE / (200 / 201), "A", tol=5)
    th = IEE * np.tanh(vds / (2 * VT))
    p.compare("ΔI_C at v_d = 50 mV (tanh law)", IEE * np.tanh(0.05 / (2 * VT)), np.interp(0.05, vds, dI), "A", tol=3)
    gm = IEE / (2 * VT)
    f = np.array([1e3])
    Ad = abs(build(ac_mode="diff").ac(f).v("c1")[0])
    Acm = abs(build(ac_mode="cm").ac(f).v("c1")[0])
    p.compare("Differential gain (single-ended)", gm * 5e3 / 2, Ad, "", tol=5)
    p.compare("Common-mode gain (single-ended)", 5e3 / (2 * 10e3), Acm, "", tol=10)
    p.compare("CMRR single-ended", db(gm * 10e3), db(Ad / Acm), "dB", kind="abs")
    cm = []
    for _ in range(300):
        e = 1 + p.rng.uniform(-0.01, 0.01, 2)
        ck_d = build(rc1=5e3 * e[0], rc2=5e3 * e[1], ac_mode="diff")
        ck_c = build(rc1=5e3 * e[0], rc2=5e3 * e[1], ac_mode="cm")
        rd = ck_d.ac(f); rc = ck_c.ac(f)
        Addf = abs(rd.v("c1")[0] - rd.v("c2")[0]); Acdf = abs(rc.v("c1")[0] - rc.v("c2")[0])
        cm.append(db(Addf / Acdf))
    cm = np.array(cm)
    p.metric("Differential-output CMRR, ±1 % R_C (median)", np.median(cm), "dB",
             f"5th percentile {np.percentile(cm, 5):.1f} dB")
    p.compare("Diff-output CMRR at δ = 1 % (analytic)", db(gm * 5e3 / (0.01 * 5e3 / (2 * 10e3))),
              np.percentile(cm, 1), "dB", kind="abs", note="worst builds approach δ = 2 %")
    fig, ax = p.fig()
    ax.plot(vds * 1e3, th * 1e3, "--", color=C_PRED, label="I_EE·tanh(v_d / 2V_T)")
    ax.plot(vds * 1e3, dI * 1e3, color=C_MEAS, label="simulated")
    ax.plot(vds * 1e3, gm * vds * 1e3, ":", color=COLORS[2], label="small-signal line g_m·v_d")
    ax.set_ylim(-1.5, 1.5)
    style_axes(ax, "v_d (mV)", "ΔI_C (mA)", "Differential pair transfer curve")
    p.save(fig, "transfer", "The pair is linear only within about ±V_T of balance, then steers all the tail current.")
    fig, ax = p.fig()
    ax.hist(cm, 30, color=C_MEAS, rwidth=.9)
    style_axes(ax, "CMRR (dB)", "builds", "Differential-output CMRR with ±1 % collector resistors", legend=False)
    p.save(fig, "cmrr_hist", "Monte Carlo: mismatch, not the tail resistor, limits differential CMRR.")
    p.csv("transfer", vd_v=vds, delta_ic_a=dI, tanh_a=th)
    p.discuss("""The large-signal curve lies on the tanh law; the small differences come from base current
(α = β/(β+1)) and the Early effect. Single-ended CMRR is limited by the 10 kΩ tail resistor as
predicted; in a real op-amp the tail is a current source with MΩ output impedance precisely to push
this up. Taking the output differentially removes the common-mode term entirely *if* the halves match,
so the Monte Carlo shows the true limit is component mismatch: 1 % resistors give CMRR in the
70–90 dB range rather than infinity.""")
