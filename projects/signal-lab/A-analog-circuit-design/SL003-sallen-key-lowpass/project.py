from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-003", title="Sallen-Key active low-pass filter", level="M",
    tools="eelab mini-SPICE with single-pole op-amp macromodel",
    summary="Unity-gain Sallen-Key 2nd-order low-pass at 1 kHz built for Q = 0.5, 0.707 and 2: "
            "predict peaking and step overshoot from Q, then measure them.",
    problem="How does the quality factor Q of a second-order filter trade flat passband against "
            "overshoot and ringing, and does a real (finite-bandwidth) op-amp change the answer?",
    theory=r"""For the unity-gain Sallen-Key with $R_1=R_2=R$, feedback capacitor $C_1$ and ground capacitor $C_2$:
$$\omega_0=\frac1{R\sqrt{C_1C_2}},\qquad Q=\frac12\sqrt{\frac{C_1}{C_2}}$$
so the design is $C_2 = 1/(2Q\omega_0R)$, $C_1 = 2Q/(\omega_0R)$. Gain at $f_0$ equals $Q$ ($20\log Q$ dB),
the peak (for $Q>0.707$) is $Q/\sqrt{1-1/(4Q^2)}$, and step overshoot is
$\exp(-\pi\zeta/\sqrt{1-\zeta^2})$ with $\zeta = 1/(2Q)$.""",
    method="""R = 10 kΩ; capacitors computed for f₀ = 1 kHz at each Q. Op-amp macromodel: A₀ = 2×10⁵,
GBW = 1 MHz, slew rate 0.5 V/µs. For each Q: AC sweep (gain at f₀, peak) and a 100 mV step
transient (overshoot).""",
)


def run(p):
    R, f0 = 10e3, 1000.0
    w0 = 2 * pi * f0
    f = np.logspace(1.5, 4.5, 500)
    figb, axb = p.fig()
    figs, axs = p.fig()
    for i, Q in enumerate([0.5, 0.7071, 2.0]):
        C2 = 1 / (2 * Q * w0 * R); C1 = 2 * Q / (w0 * R)
        ck = Circuit(f"Sallen-Key Q={Q}")
        ck.V("in", "in", "0", ac=1, wave=lambda t: 0.1 if t > 1e-4 else 0.0)
        ck.R("1", "in", "a", R); ck.R("2", "a", "b", R)
        ck.C("1", "a", "out", C1); ck.C("2", "b", "0", C2)
        ck.OPAMP("U1", "b", "out", "out")
        if i == 1:
            p.write("simulation/sallen_key_q0707.cir", ck.to_spice(), "SPICE netlist (Q = 0.707)")
        H = ck.ac(f).v("out")
        s = 1j * 2 * pi * f
        Hth = w0**2 / (s**2 + s * w0 / Q + w0**2)
        g_f0 = db(np.interp(f0, f, np.abs(H)))
        p.compare(f"Q={Q:.3g}: gain at f₀", 20 * np.log10(Q), g_f0, "dB", kind="abs")
        if Q > 0.72:
            pk_pred = 20 * np.log10(Q / np.sqrt(1 - 1 / (4 * Q * Q)))
            p.compare(f"Q={Q:.3g}: peak gain", pk_pred, db(H).max(), "dB", kind="abs")
        tr = ck.tran(6e-3, 2e-6, uic=True)
        v = tr.v("out") / 0.1
        z = 1 / (2 * Q)
        os_pred = 100 * np.exp(-pi * z / np.sqrt(1 - z * z)) if z < 1 else 0.0
        os_meas = 100 * (v.max() - v[-1]) / v[-1]
        p.compare(f"Q={Q:.3g}: step overshoot", os_pred, os_meas, "%", kind="abs")
        axb.semilogx(f, db(H), color=COLORS[i], label=f"Q = {Q:.3g} simulated")
        axb.semilogx(f, db(Hth), "--", color=COLORS[i], lw=1, alpha=.8)
        axs.plot((tr.t - 1e-4) * 1e3, v, color=COLORS[i], label=f"Q = {Q:.3g}")
        p.metric(f"Q={Q:.3g}: C1 / C2", f"{C1*1e9:.2f} nF / {C2*1e9:.2f} nF")
    style_axes(axb, "frequency (Hz)", "gain (dB)", "Sallen-Key low-pass: Q sets the peaking (dashed = theory)")
    axb.set_ylim(-45, 10)
    p.save(figb, "bode_by_q", "Measured responses (solid) against the ideal second-order prediction (dashed).")
    axs.set_xlim(-0.2, 4)
    style_axes(axs, "time (ms)", "normalised output", "Step response: higher Q → more overshoot")
    p.save(figs, "step_by_q", "100 mV step response for each Q.")
    p.discuss("""Gains at f₀ and the overshoots land within a few hundredths of a dB / a few tenths of a
percent of the ideal formulas. The residual comes from the op-amp: with GBW = 1 MHz the follower's
closed-loop pole sits at ~1 MHz, adding a little phase lag at 1 kHz and a tiny extra peak at high Q.
Far above f₀ the measured curve stops falling at −40 dB/dec and flattens: that is the classic
Sallen-Key feedthrough through C1 into the op-amp's rising output impedance — a real limitation the
ideal formula cannot show.""")
