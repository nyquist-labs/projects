from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-012", title="Colpitts LC oscillator", level="M",
    tools="eelab mini-SPICE transient (BJT common-base Colpitts)",
    summary="Build a common-base Colpitts oscillator for three inductor values and compare the "
            "measured frequency with 1/(2π√(L·C₁C₂/(C₁+C₂))).",
    problem="How accurately does the ideal tank formula predict an LC oscillator, and what does the "
            "transistor itself do to the frequency?",
    theory=r"""The tank inductor resonates with the series combination of the divider capacitors:
$$f_0=\frac{1}{2\pi\sqrt{L\,C_{eq}}},\qquad C_{eq}=\frac{C_1C_2}{C_1+C_2}$$
The divider C₁/C₂ feeds back a fraction $C_1/(C_1+C_2)$ of the collector swing to the emitter; start-up
requires roughly $g_m R_{tank} > C_2/C_1$. C₁ = 1 nF, C₂ = 4.7 nF → C_eq = 824.6 pF.""",
    method="""9 V supply, base biased at 3 V and AC-grounded by 100 nF, R_E = 2.2 kΩ, tank L from V_CC to collector
(with 2 Ω series loss), C₁ collector–emitter, C₂ emitter–ground. L ∈ {4.7, 10, 22} µH. A short
current kick starts oscillation; 40 µs transient at ~1/150 of the period; frequency from zero
crossings of the collector swing in the last 10 µs.""",
)


def run(p):
    C1, C2 = 1e-9, 4.7e-9
    Ceq = C1 * C2 / (C1 + C2)
    fig, ax = p.fig()
    Ls, fp, fm = [4.7e-6, 10e-6, 22e-6], [], []
    for i, L in enumerate(Ls):
        f0 = 1 / (2 * pi * np.sqrt(L * Ceq))
        ck = Circuit(f"Colpitts L={L}")
        ck.V("cc", "vcc", "0", dc=9)
        ck.R("b1", "vcc", "b", 20e3); ck.R("b2", "b", "0", 10e3); ck.C("b", "b", "0", 100e-9)
        ck.L("t", "vcc", "lr", L); ck.R("loss", "lr", "c", 2.0)
        ck.Q("1", "c", "b", "e", Is=1e-14, BF=150, VAF=100, Cbe=5e-12, Cbc=2e-12)
        ck.C("1", "c", "e", C1); ck.C("2", "e", "0", C2); ck.R("e", "e", "0", 2.2e3)
        ck.I("kick", "c", "0", wave=lambda t: 1e-3 if t < 2e-8 else 0.0)
        if i == 1:
            p.write("simulation/colpitts_10uH.cir", ck.to_spice(), "SPICE netlist (L = 10 µH)")
        dt = 1 / (f0 * 150)
        tr = ck.tran(40e-6, dt)
        t, v = tr.t, tr.v("c")
        m = t > 30e-6
        vv = v[m] - v[m].mean(); tt = t[m]
        idx = np.where((vv[:-1] < 0) & (vv[1:] >= 0))[0]
        zc = tt[idx] - vv[idx] * (tt[idx + 1] - tt[idx]) / (vv[idx + 1] - vv[idx])
        f_meas = (len(zc) - 1) / (zc[-1] - zc[0])
        fp.append(f0); fm.append(f_meas)
        p.compare(f"L = {L*1e6:g} µH: frequency", f0, f_meas, "Hz", tol=5)
        p.metric(f"L = {L*1e6:g} µH: collector swing (pk-pk)", vv.max() - vv.min(), "V")
        if i == 1:
            fig2, ax2 = p.fig()
            ax2.plot(t * 1e6, v, color=C_MEAS, lw=.7)
            style_axes(ax2, "time (µs)", "V_C (V)", "Start-up of the 10 µH oscillator", legend=False)
            p.save(fig2, "startup", "Oscillation builds from a 20 ns kick and settles as the transistor limits.")
    Lf = np.linspace(3e-6, 25e-6, 100)
    ax.plot(Lf * 1e6, 1 / (2 * pi * np.sqrt(Lf * Ceq)) / 1e6, "--", color=C_PRED, label="1/(2π√(L·C_eq))")
    ax.plot(np.array(Ls) * 1e6, np.array(fm) / 1e6, "o", color=C_MEAS, ms=8, label="simulated oscillator")
    style_axes(ax, "L (µH)", "frequency (MHz)", "Colpitts frequency vs tank inductance")
    p.save(fig, "freq_vs_L", "Measured oscillation frequencies against the tank formula.")
    fig.savefig
    p.csv("freq_vs_L", L_uH=np.array(Ls) * 1e6, predicted_hz=fp, measured_hz=fm)
    p.discuss("""Every measured frequency is slightly *below* the tank formula. The transistor adds capacitance
(C_be = 5 pF appears in parallel with C₂, C_bc = 2 pF across the tank via the AC-grounded base) and
the emitter's low input impedance loads C₂, so the effective C_eq is larger than 824.6 pF. The finite
tank Q (2 Ω loss) also pulls the frequency down slightly. This is why precision LC oscillators use
large tank capacitors that swamp the transistor's parasitics, or a crystal instead of L.""")
