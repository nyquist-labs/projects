from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-001", title="RC low-pass filter", level="E",
    tools="eelab mini-SPICE (AC + transient), NumPy",
    summary="First-order RC low-pass: predict the −3 dB cutoff with 1/(2πRC), then sweep it "
            "in simulation with a realistic 50 Ω source and 10 MΩ probe load.",
    problem="Where exactly does a 1.6 kΩ / 100 nF RC network stop passing signals, and how much "
            "do the source and the measuring instrument shift that point?",
    theory=r"""Voltage divider with $Z_C = 1/(j\omega C)$:

$$H(j\omega)=\frac{1}{1+j\omega RC},\qquad f_c=\frac{1}{2\pi RC}=\frac{1}{2\pi(1600)(100\,\text{nF})}\approx 994.7\ \text{Hz}$$

At $f_c$: $|H| = 1/\sqrt2$ (−3.01 dB) and phase −45°. Above $f_c$ the slope is −20 dB/decade.
Step response: $v(t)=1-e^{-t/\tau}$ with $\tau = RC = 160\ \mu s$, 10–90 % rise time $2.2\tau$.""",
    method="""Netlist: 50 Ω generator → R = 1.6 kΩ → node `out` → C = 100 nF to ground, with a 10 MΩ
‖ 12 pF oscilloscope-probe load on `out`. AC analysis over 10 Hz–100 kHz (400 log points),
the −3 dB point found by interpolation. A transient step (trapezoidal, 1 µs step) gives τ and rise time.""",
)


def run(p):
    R, C = 1600.0, 100e-9
    fc_pred = 1 / (2 * pi * R * C)
    ck = Circuit("RC low-pass")
    ck.V("in", "src", "0", dc=0, ac=1, wave=lambda t: 1.0 if t > 1e-4 else 0.0)
    ck.R("s", "src", "a", 50)
    ck.R("1", "a", "out", R)
    ck.C("1", "out", "0", C)
    ck.R("probe", "out", "0", 10e6)
    ck.C("probe", "out", "0", 12e-12)
    p.write("simulation/rc_lowpass.cir", ck.to_spice() , "SPICE netlist (LTspice/ngspice)")

    f = np.logspace(1, 5, 400)
    H = ck.ac(f).v("out")
    g = db(H)
    fc_meas = find_crossing(f, g, g[0] - 3.0103)
    ph_at_fc = np.degrees(np.angle(np.interp(fc_meas, f, H.real) + 1j * np.interp(fc_meas, f, H.imag)))
    slope = (np.interp(1e5, f, g) - np.interp(1e4, f, g))
    Hth = 1 / (1 + 1j * 2 * pi * f * R * C)

    tr = ck.tran(2e-3, 1e-6, uic=True)
    t, v = tr.t - 1e-4, tr.v("out")
    vf = v[-1]
    t10 = find_crossing(t, v, 0.1 * vf, logx=False)
    t90 = find_crossing(t, v, 0.9 * vf, logx=False)
    tau_meas = find_crossing(t, v, (1 - np.exp(-1)) * vf, logx=False)

    p.compare("−3 dB cutoff frequency", fc_pred, fc_meas, "Hz", tol=5)
    p.compare("Phase at cutoff", -45, ph_at_fc, "°", kind="abs")
    p.compare("High-frequency slope (10k→100k)", -20, slope, "dB/dec", kind="abs")
    p.compare("Time constant τ", R * C, tau_meas, "s", tol=5)
    p.compare("10–90 % rise time", 2.197 * R * C, t90 - t10, "s", tol=5)
    p.metric("DC gain (probe loading)", db(H[0]), "dB", "10 MΩ probe vs 1.65 kΩ source path")

    fig, ax = p.fig(2, 1, w=7.6, h=6.2, sharex=True)
    ax[0].semilogx(f, db(Hth), "--", color=C_PRED, label="theory 1/(1+jωRC)")
    ax[0].semilogx(f, g, color=C_MEAS, label="simulated (source + probe)")
    ax[0].axhline(-3.01, color="gray", lw=0.8); ax[0].axvline(fc_meas, color="gray", lw=0.8)
    ax[0].annotate(f"f_c = {fc_meas:.0f} Hz", (fc_meas, -3), (fc_meas * 1.5, 1),
                   fontsize=9)
    style_axes(ax[0], None, "gain (dB)", "RC low-pass — Bode plot")
    ax[1].semilogx(f, np.degrees(np.angle(Hth)), "--", color=C_PRED, label="theory")
    ax[1].semilogx(f, np.degrees(np.angle(H)), color=C_MEAS, label="simulated")
    style_axes(ax[1], "frequency (Hz)", "phase (°)")
    p.save(fig, "bode", "Simulated Bode response against the first-order prediction.")

    fig, ax = p.fig()
    ax.plot(t * 1e3, 1 - np.exp(-np.clip(t, 0, None) / (R * C)), "--", color=C_PRED, label="theory")
    ax.plot(t * 1e3, v, color=C_MEAS, label="simulated")
    style_axes(ax, "time (ms)", "v_out (V)", "Step response")
    p.save(fig, "step", "1 V step response; τ read at 63.2 %.")
    p.csv("bode_sweep", freq_hz=f, gain_db=g, phase_deg=np.degrees(np.angle(H)), theory_db=db(Hth))

    err = pct_err(fc_pred, fc_meas)
    p.discuss(f"""The measured cutoff sits {err:+.2f} % from the ideal formula. Two real-world
elements not in 1/(2πRC) cause it: the 50 Ω generator adds to R (R_eff = 1650 Ω → predicts
{1/(2*pi*1650*C):.1f} Hz, i.e. −3 %), and the probe's 12 pF adds to C (+0.012 %). The 10 MΩ probe
resistance slightly lowers the DC gain ({db(H[0]):.4f} dB), which I measure the −3 dB point
relative to. Lesson: include the source impedance in the prediction when R is only ~30× larger.""")
