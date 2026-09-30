from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-031", title="Boost power-factor-correction stage", level="H",
    tools="eelab mini-SPICE with feedback controller (hysteretic current mode)",
    summary="Compare a plain rectifier-capacitor front end with a boost PFC stage whose inductor current "
            "is forced to follow the rectified line voltage: measure power factor and current THD.",
    problem="Why do mains-powered supplies above 75 W need power-factor correction, and how does a "
            "boost converter make the input look like a resistor?",
    theory=r"""Power factor $PF=\frac{P}{V_{rms}I_{rms}}=\frac{\cos\phi}{\sqrt{1+THD_i^2}}$. A peak-rectifier draws short current
pulses near the voltage peaks, giving PF ≈ 0.5–0.7. The PFC controller sets the inductor current
reference $i_{ref}=k|v_{in}|$, so the line current is sinusoidal and in phase: PF → 1. The multiplier
$k$ comes from the output power: $k = 2P_{out}/(\eta V_p^2)$.""",
    method="""120 V RMS / 60 Hz source through an ideal rectifier. (a) Plain: rectified voltage → 470 µF ‖ 320 Ω.
(b) PFC: rectified voltage → 1 mH → synchronous switch pair → 470 µF ‖ 320 Ω (~400 V bus, 500 W).
Hysteretic control holds i_L within ±0.3 A of k|v_in|; k is updated each half-cycle by a slow PI loop on
V_out. 100 ms transients, PF and THD over the last two line cycles.""",
)


def metrics(i, v, dt):
    P = np.mean(v * i)
    pf = P / (np.sqrt(np.mean(v * v)) * np.sqrt(np.mean(i * i)))
    n = len(i)
    X = np.abs(np.fft.rfft(i)); fr = np.fft.rfftfreq(n, dt)
    k1 = np.argmin(abs(fr - 60))
    h = X[(fr > 90) & (fr < 3000)]
    return pf, np.sqrt(np.sum(h**2)) / X[k1] * 100, P


def run(p):
    Vp, f = 120 * np.sqrt(2), 60.0
    dt = 2e-6
    vline = lambda t: Vp * np.sin(2 * pi * f * t)
    # (a) plain rectifier + capacitor (ideal rectifier modelled with a diode from |v| source)
    ck = Circuit("rectifier-cap")
    ck.V("r", "rect", "0", wave=lambda t: abs(vline(t)))
    ck.R("w", "rect", "a", 0.5)
    ck.D("1", "a", "out", Is=1e-9, N=1.5)
    ck.C("o", "out", "0", 470e-6); ck.R("L", "out", "0", 60.0)
    tr = ck.tran(0.1, 20e-6, method="be", ic={"out": Vp * 0.9})
    m = tr.t >= 0.1 - 2 / f
    i_rect = -tr.i("r")[m]
    tt = tr.t[m]
    i_line = i_rect * np.sign(np.sin(2 * pi * f * tt))
    pf_a, thd_a, Pa = metrics(i_line, vline(tt), 20e-6)
    # (b) PFC boost with hysteretic current control
    Vref, RL = 400.0, 320.0
    st = dict(k=2 * (Vref**2 / RL) / Vp**2, integ=0.0, on=True, last_half=0)
    ck2 = Circuit("PFC boost")
    ck2.V("r", "rect", "0", wave=lambda t: abs(vline(t)))
    ck2.L("b", "rect", "sw", 1e-3)
    ck2.SW("lo", "sw", "0", lambda t: True, ron=0.05, roff=1e6)
    ck2.SW("hi", "sw", "out", lambda t: False, ron=0.05, roff=1e6)
    ck2.C("o", "out", "0", 470e-6); ck2.R("L", "out", "0", RL)

    def ctrl(t, v, i):
        half = int(t * 2 * f)
        if half != st["last_half"]:
            st["last_half"] = half
            err = Vref - v("out")
            st["integ"] += err
            st["k"] = max(0.0, 2 * (Vref**2 / RL) / Vp**2 + 1e-4 * err + 2e-5 * st["integ"])
        iref = st["k"] * abs(vline(t))
        il = i("b")
        if il < iref - 0.3:
            st["on"] = True
        elif il > iref + 0.3:
            st["on"] = False
        return {"lo": st["on"], "hi": not st["on"]}

    tr2 = ck2.tran(0.1, dt, method="be", ic={"out": Vref}, controller=ctrl)
    m2 = tr2.t >= 0.1 - 2 / f
    tt2 = tr2.t[m2]
    il = tr2.i("b")[m2]
    i_line2 = il * np.sign(np.sin(2 * pi * f * tt2))
    pf_b, thd_b, Pb = metrics(i_line2, vline(tt2), dt)
    p.compare("PFC power factor", 1.0, pf_b, "", tol=2)
    p.compare("Plain rectifier PF (textbook range 0.5–0.7)", 0.6, pf_a, "", kind="abs")
    p.metric("Line-current THD, plain rectifier", thd_a, "%")
    p.metric("Line-current THD, PFC", thd_b, "%")
    p.metric("PFC output voltage (mean)", tr2.v("out")[m2].mean(), "V")
    p.metric("Input power, PFC", Pb, "W")
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    ax[0].plot((tt - tt[0]) * 1e3, i_line, color=COLORS[7], label=f"line current (PF = {pf_a:.2f})")
    ax[0].plot((tt - tt[0]) * 1e3, vline(tt) / 20, ":", color="gray", label="line voltage / 20")
    style_axes(ax[0], None, "A", "Rectifier + capacitor: current pulses at the peaks")
    ax[1].plot((tt2 - tt2[0]) * 1e3, i_line2, color=C_MEAS, lw=.6, label=f"line current (PF = {pf_b:.3f})")
    ax[1].plot((tt2 - tt2[0]) * 1e3, vline(tt2) / 20, ":", color="gray", label="line voltage / 20")
    style_axes(ax[1], "time (ms)", "A", "Boost PFC: current follows the voltage")
    p.save(fig, "line_current", "PFC turns the pulsed input current into a sine in phase with the line.")
    p.csv("pfc_current", t_s=tt2, i_line_a=i_line2, v_line_v=vline(tt2))
    p.discuss(f"""The rectifier-capacitor front end conducts only for a few milliseconds near each peak, so its
current is rich in 3rd, 5th, 7th harmonics (THD {thd_a:.0f} %) and PF ≈ {pf_a:.2f}. The PFC stage forces the
inductor current to track k·|v_in| within a ±0.3 A hysteresis band, so the line sees a nearly resistive
load. PF falls short of 1 because of the hysteresis ripple, a small phase distortion near the zero
crossings (where the boost cannot source current when |v_in| is tiny) and the 120 Hz ripple on k
introduced by the voltage loop.""")
