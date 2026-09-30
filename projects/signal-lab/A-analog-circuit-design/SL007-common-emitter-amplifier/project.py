from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-007", title="Common-emitter BJT amplifier", level="M",
    tools="eelab mini-SPICE (Ebers-Moll BJT), FFT-based THD",
    summary="Bias a 2N3904-like transistor with a divider, predict Q-point and mid-band gain, then "
            "find the input level where distortion reaches 1 % THD.",
    problem="What gain does a textbook common-emitter stage really give, and at what input "
            "amplitude does the exponential transistor start to distort?",
    theory=r"""Divider bias: $V_B = 12\cdot\frac{10k}{57k}=2.105$ V (ignoring base current), $V_E=V_B-0.65$,
$I_C\approx V_E/R_E \approx 1.45$ mA, $V_C = 12 - I_C R_C$.
Mid-band gain with $R_E$ bypassed: $A_v = -g_m (R_C\parallel R_L)$, $g_m = I_C/V_T$.
Distortion: $i_c \propto e^{v_{be}/V_T}$; for input amplitude $\hat v$ the 2nd-harmonic ratio is
$HD_2 \approx \hat v/(4V_T)$, so 1 % distortion at $\hat v \approx 0.04V_T \approx 1.03$ mV.""",
    method="""Transistor: Is = 6.7 fA, β = 150, VA = 75 V. R1 = 47 k, R2 = 10 k, RC = 4.7 k, RE = 1 k ‖ 100 µF,
10 µF coupling caps, RL = 10 k. Operating point by Newton-Raphson, gain from AC analysis at 1 kHz,
distortion from 5 ms transients at 1 kHz for input amplitudes 0.25–8 mV (THD from an FFT over
whole cycles).""",
)


def thd(x, fs, f0, nh=6):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    fr = np.fft.rfftfreq(len(x), 1 / fs)
    amp = [X[np.argmin(abs(fr - k * f0))] for k in range(1, nh + 1)]
    return np.sqrt(np.sum(np.square(amp[1:]))) / amp[0] * 100


def build(vin_amp=0.0):
    ck = Circuit("CE amp")
    ck.V("cc", "vcc", "0", dc=12)
    ck.V("in", "sig", "0", ac=1, wave=lambda t: vin_amp * np.sin(2 * pi * 1000 * t))
    ck.C("in", "sig", "b", 10e-6)
    ck.R("1", "vcc", "b", 47e3); ck.R("2", "b", "0", 10e3)
    ck.R("c", "vcc", "c", 4.7e3); ck.R("e", "e", "0", 1e3); ck.C("e", "e", "0", 100e-6)
    ck.Q("1", "c", "b", "e", Is=6.7e-15, BF=150, VAF=75)
    ck.C("out", "c", "out", 10e-6); ck.R("L", "out", "0", 10e3)
    return ck


def run(p):
    ck = build()
    op = ck.op()
    p.write("simulation/ce_amp.cir", ck.to_spice(), "SPICE netlist")
    VB_pred = 12 * 10 / 57
    IC_pred = (VB_pred - 0.65) / 1e3
    IC = (12 - op["c"]) / 4.7e3
    p.compare("Base voltage V_B", VB_pred, op["b"], "V", tol=5)
    p.compare("Collector current I_C", IC_pred, IC, "A", tol=10)
    p.compare("Collector voltage V_C", 12 - 4.7e3 * IC_pred, op["c"], "V", tol=10)
    VT = 0.025852
    RLp = 4.7e3 * 10e3 / 14.7e3
    ro = (75 + op["c"] - op["e"]) / IC
    Av_pred = -(IC_pred / VT) * RLp
    f = np.logspace(0, 6, 300)
    H = ck.ac(f).v("out")
    Av = np.interp(1000, f, np.abs(H))
    p.compare("Mid-band gain |A_v| at 1 kHz", abs(Av_pred), Av, "", tol=10)
    p.metric("Gain with measured I_C and r_o", (IC / VT) * 1 / (1 / RLp + 1 / ro), "", "refined prediction")
    amps = np.array([0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8]) * 1e-3
    fs = 400e3
    thds = []
    for a in amps:
        c2 = build(a)
        tr = c2.tran(5e-3, 1 / fs)
        x = tr.v("out")[len(tr.t) // 5:]
        n = int(fs / 1000) * ((len(x)) // int(fs / 1000))
        thds.append(thd(x[-n:], fs, 1000))
        if abs(a - 4e-3) < 1e-9:
            wave = (tr.t, tr.v("out"))
    thds = np.array(thds)
    a1 = np.interp(1.0, thds, amps)
    p.compare("Input amplitude for 1 % THD", 0.04 * VT, a1, "V", tol=20)
    p.csv("thd_vs_amplitude", input_amp_v=amps, thd_pct=thds)
    fig, ax = p.fig()
    ax.loglog(amps * 1e3, thds, "o-", color=C_MEAS, label="simulated THD")
    ax.loglog(amps * 1e3, amps / (4 * VT) * 100, "--", color=C_PRED, label="HD₂ ≈ v̂/(4V_T)")
    ax.axhline(1, color="gray", lw=.8)
    style_axes(ax, "input amplitude (mV)", "THD (%)", "Common-emitter stage: distortion vs drive")
    p.save(fig, "thd", "THD grows linearly with drive, as the exponential's second-order term predicts.")
    fig, ax = p.fig()
    ax.semilogx(f, db(H), color=C_MEAS, label="simulated")
    ax.axhline(db(Av_pred), ls="--", color=C_PRED, label="mid-band prediction")
    style_axes(ax, "frequency (Hz)", "gain (dB)", "Frequency response")
    p.save(fig, "bode", "Low-frequency roll-off set by the coupling and bypass capacitors.")
    t, v = wave
    fig, ax = p.fig()
    ax.plot(t[-800:] * 1e3, v[-800:], color=C_MEAS)
    style_axes(ax, "time (ms)", "v_out (V)", "Output at 4 mV input: visibly asymmetric", legend=False)
    p.save(fig, "waveform", "At 4 mV drive the positive and negative half-cycles differ in amplitude.")
    p.discuss(f"""The operating point is within a few percent: the prediction ignores base current (which loads
the 8.2 kΩ Thevenin divider) and assumes V_BE = 0.65 V. The gain error comes from the same I_C error
plus the Early resistance r_o = {ro/1e3:.0f} kΩ in parallel with R_C‖R_L. The distortion slope matches
v̂/(4V_T) — the 1 %-THD point differs from 1.03 mV because the bypass capacitor's residual impedance
provides a little local feedback, linearising the stage slightly.""")
