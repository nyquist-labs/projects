from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-010", title="Three-op-amp instrumentation amplifier", level="M",
    tools="eelab mini-SPICE, Monte Carlo resistor tolerance",
    summary="Amplify a 1 mV bridge-sensor signal sitting on 2.5 V plus 1 V of 60 Hz common-mode "
            "hum; predict gain and CMRR from resistor tolerance and measure both.",
    problem="A strain-gauge bridge gives millivolts riding on volts of common-mode voltage and mains "
            "pickup. How well does a 3-op-amp in-amp separate them, and what sets the limit?",
    theory=r"""Gain $G=\left(1+\frac{2R}{R_G}\right)\frac{R_3}{R_2}$; with R = 25 kΩ, R_G = 1 kΩ, R₂ = R₃ = 10 kΩ,
G = 51. The input stage passes common-mode at unity gain, so all rejection comes from the difference
amplifier: with resistor tolerance t the worst-case difference-amp CMRR is
$\mathrm{CMRR_{DA}}\approx\frac{1+R_3/R_2}{4t}$, and the whole amp improves this by the first-stage gain:
$\mathrm{CMRR}\approx G_1\cdot\frac{1+R_3/R_2}{4t}$ (G₁ = 51). For t = 0.1 %: ≈ 94 dB worst case.""",
    method="""Ideal-ish op-amps (A₀ = 2×10⁵). AC analysis gives differential gain and common-mode gain; 300
Monte Carlo builds with uniform ±0.1 % and ±1 % resistors give the CMRR distribution. A transient
with 1 mV·sin(2π·5 Hz) differential + 2.5 V + 1 V·sin(2π·60 Hz) common mode shows the separation.""",
)


def build(e=None, vd_wave=None, vc_wave=None):
    e = np.ones(7) if e is None else e
    ck = Circuit("in-amp")
    ck.V("cm", "cm", "0", ac=0, wave=vc_wave)
    ck.E("dp", "inp", "cm", "d", "0", 0.5); ck.E("dn", "inn", "cm", "d", "0", -0.5)
    ck.V("d", "d", "0", ac=1, wave=vd_wave)
    ck.OPAMP("A1", "inp", "n1", "o1"); ck.OPAMP("A2", "inn", "n2", "o2")
    ck.R("f1", "o1", "n1", 25e3 * e[0]); ck.R("f2", "o2", "n2", 25e3 * e[1]); ck.R("g", "n1", "n2", 1e3 * e[2])
    ck.R("2a", "o2", "m", 10e3 * e[3]); ck.R("3a", "m", "out", 10e3 * e[4])
    ck.R("2b", "o1", "pp", 10e3 * e[5]); ck.R("3b", "pp", "0", 10e3 * e[6])
    ck.OPAMP("A3", "pp", "m", "out")
    return ck


def cmrr(e):
    f = np.array([60.0])
    ckd = build(e)
    Ad = abs(ckd.ac(f).v("out")[0])
    ckc = build(e)
    # switch AC excitation to common mode
    ckc.elems = [(x[0], x[1], x[2], x[3], x[4], (1 if x[1] == "cm" else 0), x[6], x[7]) if x[0] == "V" else x for x in ckc.elems]
    Ac = abs(ckc.ac(f).v("out")[0])
    return Ad, Ac


def run(p):
    G_pred = (1 + 2 * 25e3 / 1e3) * 1.0
    Ad, Ac = cmrr(None)
    p.compare("Differential gain", G_pred, Ad, "", tol=0.5)
    p.metric("CMRR with perfect resistors", db(Ad / Ac), "dB", "limited by op-amp finite gain")
    res = {}
    for t in (0.001, 0.01):
        vals = []
        for _ in range(300):
            a, c = cmrr(1 + p.rng.uniform(-t, t, 7))
            vals.append(db(a / c))
        res[t] = np.array(vals)
        worst = 51 * 2 / (4 * t)
        p.compare(f"Worst-case CMRR, ±{t*100:g} % resistors", db(worst), res[t].min(), "dB", kind="abs",
                  note="Monte Carlo minimum of 300 builds")
        p.metric(f"Median CMRR, ±{t*100:g} %", np.median(res[t]), "dB")
    e = 1 + p.rng.uniform(-0.001, 0.001, 7)
    ck = build(e, vd_wave=lambda t: 1e-3 * np.sin(2 * pi * 5 * t),
               vc_wave=lambda t: 2.5 + 1.0 * np.sin(2 * pi * 60 * t))
    tr = ck.tran(0.4, 1e-4)
    out = tr.v("out"); t = tr.t
    fig, ax = p.fig(2, 1, h=5.8, sharex=True)
    ax[0].plot(t, tr.v("inp"), color=COLORS[1], lw=1, label="input + (2.5 V + 60 Hz hum + 0.5 mV signal)")
    style_axes(ax[0], None, "V", "In-amp: input is 99.9 % common-mode")
    ax[1].plot(t, out * 1e3, color=C_MEAS, label="output (simulated)")
    ax[1].plot(t, G_pred * 1e3 * 1e-3 * np.sin(2 * pi * 5 * t), "--", color=C_PRED, label="G · v_d (ideal)")
    style_axes(ax[1], "time (s)", "mV", None)
    p.save(fig, "time_domain", "The 1 mV differential signal emerges ×51 while 1 V of hum is rejected.")
    resid = out - G_pred * 1e-3 * np.sin(2 * pi * 5 * t)
    p.metric("Residual 60 Hz at output (RMS)", np.std(resid[len(t)//4:]) * 1e3, "mV")
    fig, ax = p.fig()
    ax.hist(res[0.001], 30, color=COLORS[0], alpha=.85, label="±0.1 % resistors", rwidth=.9)
    ax.hist(res[0.01], 30, color=COLORS[1], alpha=.75, label="±1 % resistors", rwidth=.9)
    style_axes(ax, "CMRR at 60 Hz (dB)", "builds", "CMRR is set by resistor matching")
    p.save(fig, "cmrr_hist", "Ten times better matching buys 20 dB of CMRR.")
    p.csv("cmrr_montecarlo", tol_0p1pct_db=res[0.001], tol_1pct_db=res[0.01])
    p.discuss("""The gain matches 1 + 2R/R_G to better than 0.1 %. The Monte Carlo minima land just above the
worst-case formula (the formula assumes every resistor at its tolerance edge in the worst direction,
which 300 random builds rarely hit) and the medians are ~10 dB better. Each 10× improvement in
resistor matching buys 20 dB of CMRR — the reason monolithic in-amps use laser-trimmed thin-film
resistors instead of discrete parts.""")
