from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-024", title="Logarithmic and anti-log amplifiers", level="H",
    tools="eelab mini-SPICE DC sweeps over 6 decades",
    summary="Exploit the diode law to build an amplifier whose output is the logarithm of its input: "
            "verify 59.5 mV per decade over six decades and invert it with an anti-log stage.",
    problem="The diode's exponential I–V curve is usually a nuisance. Can it be turned into an exact "
            "logarithm function, and over how many decades does it hold?",
    theory=r"""With the diode in the feedback of an inverting op-amp, the input current $I=V_{in}/R$ flows through it:
$$V_{out}=-nV_T\ln\frac{V_{in}}{RI_s}\quad\Rightarrow\quad \frac{dV_{out}}{d\log_{10}V_{in}}=-2.303\,nV_T=-59.5\text{ mV/decade}\ (n=1)$$
Anti-log (diode at the input): $V_{out}=-RI_s e^{-V_{in}/nV_T}$. Cascading the two should return the input.
Limits: at low currents the op-amp offset and leakage dominate; at high currents the diode's series
resistance adds a linear term.""",
    method="""Transistor-quality diode (Is = 10 fA, n = 1, Rs = 1 Ω), R = 10 kΩ, op-amp with 50 µV input offset. Input
100 µV–10 V (6 decades). Slope measured by linear regression in the log domain over the middle
4 decades; conformance error = deviation from the fitted line.""",
)


def run(p):
    VT = 0.025852
    Is, R = 10e-15, 10e3
    vin = np.logspace(-4, 1, 51)
    vo = []
    xprev = None
    for v in vin[::-1]:
        ck = Circuit("log amp")
        ck.V("in", "in", "0", dc=v); ck.R("in", "in", "n", R)
        ck.OPAMP("U1", "0", "n", "out", VOS=50e-6, VSAT=13)
        ck.D("1", "n", "out", Is=Is, N=1.0, Rs=1.0)
        o = ck.op(x0=xprev, guess=None if xprev is not None else {"out": -0.8, "n": 0.0})
        xprev = ck.x0
        vo.append(o["out"])
    vo = np.array(vo[::-1])
    p.write("simulation/log_amp.cir", ck.to_spice(), "SPICE netlist")
    mid = (vin > 1e-3) & (vin < 1)
    slope, icpt = np.polyfit(np.log10(vin[mid]), vo[mid], 1)
    p.compare("Log slope", -2.303 * VT, slope, "V/dec", tol=2)
    pred = -VT * np.log(vin / (R * Is))
    p.compare("V_out at V_in = 10 mV", float(np.interp(-2, np.log10(vin), pred)), float(np.interp(-2, np.log10(vin), vo)), "V", tol=2)
    conf = vo - (slope * np.log10(vin) + icpt)
    p.metric("Conformance error at 100 µV (offset-limited)", conf[0] * 1e3, "mV")
    p.metric("Conformance error at 10 V (R_s-limited)", conf[-1] * 1e3, "mV")
    # anti-log: diode at input, resistor feedback
    x = np.linspace(-0.62, -0.36, 27)
    ya = []
    xprev = None
    for v in x:
        ck = Circuit("antilog")
        ck.V("in", "in", "0", dc=-v)
        ck.D("1", "in", "n", Is=Is, N=1.0)
        ck.R("f", "n", "out", R)
        ck.OPAMP("U1", "0", "n", "out", VSAT=13)
        ya.append(-ck.op(x0=xprev)["out"])
        xprev = ck.x0
    ya = np.array(ya)
    ya_pred = R * Is * np.exp(-x / VT)
    p.compare("Anti-log output at input −0.55 V", float(np.interp(-0.55, x, ya_pred)), float(np.interp(-0.55, x, ya)), "V", tol=2)
    recovered = np.interp(-vo[mid], x[::-1] * -1, ya[::-1]) if False else R * Is * np.exp(-(vo[mid]) / VT)
    fig, ax = p.fig(1, 2)
    ax[0].semilogx(vin, pred, "--", color=C_PRED, label="−V_T·ln(V_in/RI_s)")
    ax[0].semilogx(vin, vo, "o", ms=3, color=C_MEAS, label="simulated")
    style_axes(ax[0], "V_in (V)", "V_out (V)", "Log amplifier over 5 decades")
    ax[1].semilogx(vin, conf * 1e3, color=C_MEAS, label="deviation from straight line")
    style_axes(ax[1], "V_in (V)", "conformance error (mV)", "Where the log law breaks")
    p.save(fig, "log_amp", "Straight line in log-x across the middle decades; offset and R_s bend both ends.")
    fig, ax = p.fig()
    ax.semilogy(x, ya_pred, "--", color=C_PRED, label="R·I_s·e^(−v/V_T)")
    ax.semilogy(x, ya, "o", color=C_MEAS, label="simulated anti-log")
    style_axes(ax, "V_in (V)", "|V_out| (V)", "Anti-log amplifier")
    p.save(fig, "antilog", "The anti-log stage is an exponential amplifier.")
    p.csv("log_sweep", vin_v=vin, vout_v=vo, predicted_v=pred)
    p.discuss("""Across the middle four decades the slope is within a fraction of a percent of 2.303·V_T. At the
bottom the 50 µV op-amp offset is half of the 100 µV input and the curve flattens; at the top the
1 Ω series resistance adds I·R_s (1 mA → 1 mV and growing). Real log amps use a matched transistor pair
to cancel I_s and its strong temperature dependence, and a temperature-compensating resistor for V_T.""")
