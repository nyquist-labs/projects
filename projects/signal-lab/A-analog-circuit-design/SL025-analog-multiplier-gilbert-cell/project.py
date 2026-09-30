from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-025", title="Four-quadrant analog multiplier (Gilbert cell)", level="H",
    tools="eelab mini-SPICE (6-transistor Gilbert cell), DC sweeps + FFT of mixing products",
    summary="Build a Gilbert cell, verify ΔI = I_EE·tanh(v₁/2V_T)·tanh(v₂/2V_T) in all four quadrants, "
            "then use it to mix 10 kHz and 11 kHz into 1 kHz and 21 kHz.",
    problem="How do six transistors multiply two voltages, and how clean are the sum and difference "
            "frequencies when the multiplier is used as a mixer?",
    theory=r"""The lower pair splits $I_{EE}$ by $\tanh(v_2/2V_T)$; each upper pair splits its share by $\tanh(v_1/2V_T)$,
and the cross-coupled collectors subtract:
$$\Delta I = \alpha^2 I_{EE}\tanh\frac{v_1}{2V_T}\tanh\frac{v_2}{2V_T}\approx \frac{I_{EE}}{4V_T^2}v_1v_2$$
Mixing $v_1=A\cos\omega_1t$, $v_2=B\cos\omega_2t$ gives $\frac{AB}{2}[\cos(\omega_1-\omega_2)t+\cos(\omega_1+\omega_2)t]$,
so each product's output amplitude is $R_C\frac{I_{EE}}{4V_T^2}\frac{AB}{2}$.""",
    method="""V_CC = 12 V, R_C = 2 kΩ, I_EE = 1 mA, upper bases at 6 V, lower at 3 V, β = 200. DC sweeps of v₁ for five v₂
values; then a transient with A = B = 10 mV at 10 kHz and 11 kHz, spectrum of the differential output.""",
)


def build(v1, v2, w1=None, w2=None):
    Q = dict(Is=1e-15, BF=200)
    ck = Circuit("Gilbert")
    ck.V("cc", "vcc", "0", dc=12)
    ck.V("u1", "up", "0", dc=6 + v1 / 2, wave=(lambda t: 6 + w1(t) / 2) if w1 else None)
    ck.V("u2", "un", "0", dc=6 - v1 / 2, wave=(lambda t: 6 - w1(t) / 2) if w1 else None)
    ck.V("l1", "lp", "0", dc=3 + v2 / 2, wave=(lambda t: 3 + w2(t) / 2) if w2 else None)
    ck.V("l2", "ln", "0", dc=3 - v2 / 2, wave=(lambda t: 3 - w2(t) / 2) if w2 else None)
    ck.R("c1", "vcc", "o1", 2e3); ck.R("c2", "vcc", "o2", 2e3)
    ck.Q("1", "o1", "up", "e1", **Q); ck.Q("2", "o2", "un", "e1", **Q)
    ck.Q("3", "o2", "up", "e2", **Q); ck.Q("4", "o1", "un", "e2", **Q)
    ck.Q("5", "e1", "lp", "t", **Q); ck.Q("6", "e2", "ln", "t", **Q)
    ck.I("ee", "t", "0", dc=1e-3)
    return ck


def run(p):
    VT = 0.025852; IEE = 1e-3; RC = 2e3; a = 200 / 201
    v1s = np.linspace(-0.15, 0.15, 41)
    fig, ax = p.fig()
    for i, v2 in enumerate([-0.1, -0.03, 0.0, 0.03, 0.1]):
        dv = []
        for v1 in v1s:
            o = build(v1, v2).op()
            dv.append(o["o2"] - o["o1"])
        dv = np.array(dv)
        th = RC * a * a * IEE * np.tanh(v1s / (2 * VT)) * np.tanh(v2 / (2 * VT))
        ax.plot(v1s * 1e3, dv, color=COLORS[i], label=f"v₂ = {v2*1e3:+.0f} mV")
        ax.plot(v1s * 1e3, th, "--", color=COLORS[i], lw=1)
        if v2 == 0.03:
            p.compare("ΔV_out at v₁ = 20 mV, v₂ = 30 mV", float(np.interp(0.02, v1s, th)), float(np.interp(0.02, v1s, dv)), "V", tol=3)
    style_axes(ax, "v₁ (mV)", "ΔV_out (V)", "Gilbert cell: four-quadrant multiplication (dashed = tanh·tanh theory)")
    p.save(fig, "transfer", "Output sign follows sign(v₁)·sign(v₂) in all four quadrants.")
    p.write("simulation/gilbert.cir", build(0, 0).to_spice(), "SPICE netlist")
    A = B = 0.01
    ck = build(0, 0, w1=lambda t: A * np.cos(2 * pi * 10e3 * t), w2=lambda t: B * np.cos(2 * pi * 11e3 * t))
    fs = 2e6
    tr = ck.tran(3e-3, 1 / fs)
    m = tr.t >= 1e-3
    d = (tr.v("o2") - tr.v("o1"))[m][:-1]
    n = len(d)
    X = np.abs(np.fft.rfft(d * np.hanning(n))) / (n / 4)
    fr = np.fft.rfftfreq(n, 1 / fs)
    amp = lambda f: X[np.argmin(abs(fr - f))]
    K = RC * a * a * IEE / (4 * VT**2)
    pred = K * A * B / 2
    p.compare("Difference product (1 kHz) amplitude", pred, amp(1e3), "V", tol=5)
    p.compare("Sum product (21 kHz) amplitude", pred, amp(21e3), "V", tol=5)
    p.metric("Feedthrough of 10 kHz input", amp(10e3), "V", "ideal balanced cell: 0")
    p.metric("Multiplier constant K = R_C·I_EE/(4V_T²)", K, "1/V")
    fig, ax = p.fig()
    ax.semilogy(fr / 1e3, X + 1e-9, color=C_MEAS)
    for f in (1, 21):
        ax.axvline(f, color=C_PRED, ls="--", lw=.8)
    ax.set_xlim(0, 45); ax.set_ylim(1e-6, 1e-1)
    style_axes(ax, "frequency (kHz)", "amplitude (V)", "Mixer output: only sum and difference frequencies", legend=False)
    p.save(fig, "mixer_spectrum", "10 kHz × 11 kHz → 1 kHz and 21 kHz; the inputs themselves cancel.")
    p.discuss("""The DC sweeps follow α²·I_EE·tanh·tanh closely; small deviations come from the base currents of the
upper quad and the Early-free model's exact symmetry. As a mixer the cell produces the two predicted
products with the amplitude K·AB/2, while the inputs themselves cancel because the cell is perfectly
balanced in simulation — in silicon, V_BE mismatch leaves some carrier feedthrough, which is why
real mixers specify LO-to-IF isolation.""")
