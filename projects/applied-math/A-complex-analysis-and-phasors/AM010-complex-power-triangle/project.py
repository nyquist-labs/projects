from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-010", title="Complex power: P, Q and S as one complex number", level="E",
    tools="Phasor power S = V·I*, time-domain simulation of instantaneous power, power-factor correction design",
    summary="Compute real, reactive and apparent power of an inductive load as a single complex number, confirm each part from the simulated "
            "instantaneous power p(t) = v(t)i(t), then size a power-factor-correction capacitor and verify that it works.",
    problem="What is 'reactive power' physically, and how does a capacitor cancel it?",
    theory=r"""With rms phasors, $S = VI^* = P + jQ$; |S| is apparent power, P/|S| the power factor. In time, $p(t)=P\,[1+\cos 2ωt] + Q\sin 2ωt$ (for v = √2V cos ωt): P is the average,
and Q the amplitude of the part that sloshes back and forth at 2ω without net transfer. A parallel capacitor supplying $Q_C = V^2ωC$ cancels the load's Q:
$C = Q/(ωV^2)$ gives unity power factor, reducing the line current by the factor pf.""",
    method="""230 V rms, 50 Hz source into R = 20 Ω in series with L = 50 mH (Z = 20 + j15.7 Ω). Transient simulation for 0.5 s; P from mean(v·i), Q from the 2ω quadrature component of p(t);
then the computed PFC capacitor in parallel and the line current re-measured.""",
)


def sim(C=None):
    f = 50.0; Vr = 230.0
    ck = Circuit("load")
    ck.V("s", "a", "0", wave=lambda t: np.sqrt(2) * Vr * np.cos(2 * pi * f * t))
    ck.R("line", "a", "b", 1e-3); ck.R("r", "b", "c", 20.0); ck.L("l", "c", "0", 50e-3)
    if C:
        ck.C("pfc", "b", "0", C)
    tr = ck.tran(0.5, 1 / f / 400, method="trap")
    t = tr.t; v = tr.v("b"); i = (tr.v("a") - tr.v("b")) / 1e-3
    m = t >= 0.3
    return t[m], v[m], i[m]


def run(p):
    f = 50.0; w = 2 * pi * f; Vr = 230.0
    Z = 20 + 1j * w * 50e-3
    I = Vr / Z; S = Vr * np.conj(I)
    t, v, i = sim()
    pt = v * i
    P = np.mean(pt); Q = 2 * np.mean(pt * np.sin(2 * w * t))
    p.compare("Real power P (mean of v·i)", S.real, P, "W", tol=0.5)
    p.compare("Reactive power Q (2ω quadrature amplitude of p(t))", S.imag, Q, "var", tol=1)
    p.compare("Apparent power |S| = Vrms·Irms", abs(S), np.sqrt(np.mean(v ** 2)) * np.sqrt(np.mean(i ** 2)), "VA", tol=0.5)
    pf = S.real / abs(S)
    C = S.imag / (w * Vr ** 2)
    p.metric("Power factor before correction", pf, "")
    p.metric("PFC capacitor C = Q/(ωV²)", C * 1e6, "µF")
    t2, v2, i2 = sim(C)
    pf2 = np.mean(v2 * i2) / (np.sqrt(np.mean(v2 ** 2)) * np.sqrt(np.mean(i2 ** 2)))
    p.compare("Power factor after correction", 1.0, pf2, "", tol=0.2)
    p.compare("Line current reduction factor (= pf)", pf, np.sqrt(np.mean(i2 ** 2)) / np.sqrt(np.mean(i ** 2)), "", tol=1)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot((t - t[0]) * 1e3, pt / 1e3, color=C_MEAS, label="p(t) = v·i")
    ax[0].axhline(P / 1e3, color=C_PRED, ls="--", label=f"P = {P / 1e3:.2f} kW")
    ax[0].set_xlim(0, 40)
    style_axes(ax[0], "time (ms)", "instantaneous power (kW)", "Power sloshes at 2ω around its mean")
    for z, lab, c in ((S.real, "P", C_MEAS), (1j * S.imag, "jQ", C_PRED), (S, "S", COLORS[2])):
        start = 0 if lab != "jQ" else S.real
        ax[1].annotate("", xy=((start + z).real if lab == "jQ" else z.real, (z).imag if lab != "P" else 0), xytext=(start, 0),
                       arrowprops=dict(arrowstyle="->", lw=2, color=c))
        ax[1].text((start + z.real) / 2 if lab != "jQ" else start + 50, (z.imag / 2) if lab != "P" else -150, lab, color=c, fontsize=11)
    ax[1].set_xlim(-100, S.real * 1.2); ax[1].set_ylim(-400, S.imag * 1.3); ax[1].set_aspect("equal")
    style_axes(ax[1], "P (W)", "Q (var)", "The power triangle is one complex number", legend=False)
    p.save(fig, "power", "Instantaneous power of the inductive load and the complex power triangle.")
    p.discuss(f"""P, Q and |S| extracted from the simulated waveforms match V·I* to well under 1 %, which makes the physical meaning concrete: P is the average
of p(t), Q is the amplitude of the part that flows back and forth at twice the line frequency. A {C * 1e6:.0f} µF capacitor, sized from Q/(ωV²),
raises the power factor from {pf:.3f} to {pf2:.4f} and cuts the line current by the factor pf, while the load itself is unchanged —
the capacitor now supplies the reactive current locally. This is why utilities penalise low power factor: the extra current heats their cables without
delivering energy.""")
# tol-convention: relative tolerances are in percent
