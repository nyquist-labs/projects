from eelab import *
from eelab.circuit import Circuit, e_series

META = dict(
    id="SL-004", title="Multiple-feedback band-pass filter", level="M",
    tools="eelab mini-SPICE, E24 component rounding",
    summary="Design an MFB band-pass for f₀ = 1 kHz, Q = 5, gain 2 from equations; round to E24 parts "
            "and measure centre frequency, bandwidth and gain.",
    problem="Given a target centre frequency and bandwidth, compute the three resistors of an MFB "
            "band-pass, then check what real (E24) values and a real op-amp deliver.",
    theory=r"""With $C_1=C_2=C$ (TI design equations):
$$R_1=\frac{Q}{2\pi f_0 C A_0},\quad R_2=\frac{Q}{2\pi f_0C(2Q^2-A_0)},\quad R_3=\frac{Q}{\pi f_0 C}$$
and the analysis formulas $f_0=\frac1{2\pi C}\sqrt{\frac{R_1+R_2}{R_1R_2R_3}}$, $Q=\pi f_0 R_3 C$,
$|A_0| = R_3/(2R_1)$, bandwidth $=f_0/Q$. For C = 10 nF: R₁ = 39.8 kΩ, R₂ = 8.84 kΩ, R₃ = 159 kΩ.""",
    method="""Components rounded to the nearest E24 value, the prediction re-evaluated with those values,
then an AC sweep (1 MHz GBW op-amp) measures the peak, the two −3 dB points and Q = f₀/BW.""",
)


def run(p):
    f0t, Qt, A0t, C = 1000.0, 5.0, 2.0, 10e-9
    R1i = Qt / (2 * pi * f0t * C * A0t); R2i = Qt / (2 * pi * f0t * C * (2 * Qt**2 - A0t)); R3i = Qt / (pi * f0t * C)
    R1, R2, R3 = (e_series(x) for x in (R1i, R2i, R3i))
    f0p = 1 / (2 * pi * C) * np.sqrt((R1 + R2) / (R1 * R2 * R3))
    Qp = pi * f0p * R3 * C
    Ap = R3 / (2 * R1)
    ck = Circuit("MFB band-pass")
    ck.V("in", "in", "0", ac=1)
    ck.R("1", "in", "a", R1); ck.R("2", "a", "0", R2)
    ck.C("1", "a", "out", C); ck.C("2", "a", "b", C); ck.R("3", "b", "out", R3)
    ck.OPAMP("U1", "0", "b", "out")
    p.write("simulation/mfb_bandpass.cir", ck.to_spice(), "SPICE netlist")
    f = np.logspace(2.3, 3.7, 1500)
    H = ck.ac(f).v("out")
    g = np.abs(H)
    k = np.argmax(g)
    f0m, Am = f[k], g[k]
    lo = find_crossing(f[:k + 1], db(g[:k + 1]), db(Am) - 3.0103)
    hi = find_crossing(f[k:], db(g[k:]), db(Am) - 3.0103)
    p.metric("Ideal R1, R2, R3", f"{R1i/1e3:.2f} k, {R2i/1e3:.2f} k, {R3i/1e3:.1f} k")
    p.metric("E24 R1, R2, R3", f"{R1/1e3:.3g} k, {R2/1e3:.3g} k, {R3/1e3:.3g} k")
    p.compare("Centre frequency f₀", f0p, f0m, "Hz", tol=2)
    p.compare("Quality factor Q", Qp, f0m / (hi - lo), "", tol=5)
    p.compare("Peak gain |A₀|", Ap, Am, "", tol=2)
    p.compare("−3 dB bandwidth", f0p / Qp, hi - lo, "Hz", tol=5)
    p.compare("Centre frequency vs original spec", f0t, f0m, "Hz")
    s = 1j * 2 * pi * f
    w0 = 2 * pi * f0p
    Hth = -Ap * (w0 / Qp) * s / (s**2 + s * w0 / Qp + w0**2)
    fig, ax = p.fig()
    ax.semilogx(f, db(Hth), "--", color=C_PRED, label="prediction (E24 values)")
    ax.semilogx(f, db(H), color=C_MEAS, label="simulated")
    ax.axvspan(lo, hi, color=COLORS[2], alpha=.12, label="measured −3 dB band")
    style_axes(ax, "frequency (Hz)", "gain (dB)", "MFB band-pass, target f₀ = 1 kHz, Q = 5")
    p.save(fig, "response", "Band-pass response with the measured −3 dB bandwidth shaded.")
    p.csv("response", freq_hz=f, gain_db=db(H))
    p.discuss(f"""Rounding to E24 moves the design before any simulation: the E24 parts predict f₀ = {f0p:.1f} Hz
instead of 1000 Hz. The simulation then agrees with that corrected prediction to within a fraction of a
percent — the op-amp's finite gain-bandwidth (GBW = 1 MHz vs. the needed ~2Q²·A₀·f₀ = 100 kHz) lowers
Q and gain slightly. So the "error" against the original spec is dominated by component availability,
not by the theory.""")
