from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-002", title="RC high-pass filter", level="E",
    tools="eelab mini-SPICE (AC + transient)",
    summary="Swap R and C of the low-pass: predict the cutoff and the +45° phase lead, then "
            "measure both, plus the edge-differentiating step response.",
    problem="A CR network blocks DC and passes high frequencies. Where is its corner, and why "
            "does the output *lead* the input by 45° there?",
    theory=r"""$$H(j\omega)=\frac{j\omega RC}{1+j\omega RC},\qquad f_c=\frac1{2\pi RC}$$
With R = 1.6 kΩ, C = 100 nF: $f_c$ = 994.7 Hz. Phase $=90^\circ-\arctan(\omega RC)$, i.e. +90° at DC falling to
+45° at $f_c$ and 0° at high frequency: the capacitor current (and so the voltage across R) leads the
voltage. Step response: $v_{out}=e^{-t/RC}$ — the circuit passes the edge and forgets the level.""",
    method="""50 Ω generator → C = 100 nF → node `out` → R = 1.6 kΩ to ground, 10 MΩ ‖ 12 pF probe.
AC sweep 10 Hz – 100 kHz, then a 1 V step transient to measure the decay constant.""",
)


def run(p):
    R, C = 1600.0, 100e-9
    fc = 1 / (2 * pi * R * C)
    ck = Circuit("RC high-pass")
    ck.V("in", "src", "0", ac=1, wave=lambda t: 1.0 if t > 1e-4 else 0.0)
    ck.R("s", "src", "a", 50); ck.C("1", "a", "out", C); ck.R("1", "out", "0", R)
    ck.R("probe", "out", "0", 10e6); ck.C("probe", "out", "0", 12e-12)
    p.write("simulation/rc_highpass.cir", ck.to_spice(), "SPICE netlist")
    f = np.logspace(1, 5, 400)
    H = ck.ac(f).v("out")
    g = db(H)
    fc_m = find_crossing(f, g, g[-1] - 3.0103)
    ph = np.degrees(np.angle(H))
    ph_fc = np.interp(np.log10(fc_m), np.log10(f), ph)
    slope = np.interp(100, f, g) - np.interp(10, f, g)
    Hth = 1j * 2 * pi * f * R * C / (1 + 1j * 2 * pi * f * R * C)
    tr = ck.tran(1.5e-3, 1e-6, uic=True)
    t = tr.t - 1e-4; v = tr.v("out")
    pk = v.max()
    tau = find_crossing(t[np.argmax(v):], v[np.argmax(v):], pk * np.exp(-1), logx=False) - t[np.argmax(v)]
    p.compare("−3 dB cutoff frequency", fc, fc_m, "Hz", tol=5)
    p.compare("Phase at cutoff", 45, ph_fc, "°", kind="abs")
    p.compare("Low-frequency slope (10→100 Hz)", 20, slope, "dB/dec", kind="abs")
    p.compare("Decay time constant", R * C, tau, "s", tol=5)
    p.compare("Step peak (divider R/(R+Rs))", R / (R + 50), pk, "V", tol=2)
    fig, ax = p.fig(2, 1, h=6.2, sharex=True)
    ax[0].semilogx(f, db(Hth), "--", color=C_PRED, label="theory")
    ax[0].semilogx(f, g, color=C_MEAS, label="simulated")
    ax[0].axvline(fc_m, color="gray", lw=.8); ax[0].axhline(-3.01, color="gray", lw=.8)
    style_axes(ax[0], None, "gain (dB)", "RC high-pass — Bode plot")
    ax[1].semilogx(f, np.degrees(np.angle(Hth)), "--", color=C_PRED, label="theory")
    ax[1].semilogx(f, ph, color=C_MEAS, label="simulated")
    style_axes(ax[1], "frequency (Hz)", "phase (°)")
    p.save(fig, "bode", "High-pass Bode response; the phase lead passes through +45° at the corner.")
    p.plot_compare(t * 1e3, np.where(t > 0, np.exp(-np.clip(t, 0, None) / (R * C)), 0), v, "step",
                   "time (ms)", "v_out (V)", "Step response: the edge passes, the level decays",
                   "Output decays with τ = RC after the input step.")
    p.csv("bode_sweep", freq_hz=f, gain_db=g, phase_deg=ph)
    p.discuss(f"""The cutoff error ({pct_err(fc, fc_m):+.2f} %) again comes from the 50 Ω source adding to the
series path, and the step peak is {pk:.4f} V instead of 1 V because Rs and R form a divider at the
instant of the edge (C is a short). The phase measurement shows why this is called a *lead*
network: the output crosses +45° at the corner, which is exactly what makes RC high-pass sections
useful for phase compensation.""")
