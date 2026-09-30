from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-030", title="Full-bridge SPWM inverter", level="H",
    tools="eelab mini-SPICE (4 switches, LC filter), FFT THD",
    summary="Turn 200 V DC into a 50 Hz sine with sinusoidal PWM on an H-bridge: predict the "
            "fundamental amplitude m·V_dc and compare output THD before and after the LC filter.",
    problem="How does a solar or UPS inverter make a clean mains sine wave out of DC with switches that "
            "are only ever on or off?",
    theory=r"""Bipolar SPWM on a full bridge: the bridge output's local average is $m V_{dc}\sin\omega_1t$, so
$\hat V_1 = mV_{dc}$ for $m\le1$ (linear modulation). Harmonics cluster around the carrier $f_c$ and its
multiples; an LC filter with $f_0 = 1/(2\pi\sqrt{LC})$ ≪ $f_c$ attenuates them by $(f_c/f_0)^2$ while
passing 50 Hz (fundamental gain $\approx 1/(1-\omega_1^2LC)$).""",
    method="""V_dc = 200 V, f_c = 10 kHz, m = 0.8, L = 5 mH (0.1 Ω), C = 10 µF, R = 20 Ω. Diagonal switch pairs driven by
the comparison sin vs triangle. 60 ms (3 cycles) at 1 µs steps; THD of bridge voltage and of load voltage
over the last 40 ms.""",
)


def thd(x, dt, f1=50.0, nmax=400):
    n = len(x)
    X = np.abs(np.fft.rfft(x)) / (n / 2)
    fr = np.fft.rfftfreq(n, dt)
    k1 = np.argmin(abs(fr - f1))
    harm = X[(fr > 1.5 * f1) & (fr < nmax * f1)]
    return X[k1], np.sqrt(np.sum(harm**2)) / X[k1] * 100, fr, X


def run(p):
    Vdc, fc, m, f1 = 200.0, 10e3, 0.8, 50.0
    L, C, R = 5e-3, 10e-6, 20.0
    tri = lambda t: 4 * np.abs((t * fc) % 1 - 0.5) - 1
    pos = lambda t: m * np.sin(2 * pi * f1 * t) > tri(t)
    ck = Circuit("H-bridge")
    ck.V("dc", "p", "0", dc=Vdc)
    ck.SW("a_hi", "p", "a", pos, ron=0.05, roff=1e6); ck.SW("a_lo", "a", "0", lambda t: not pos(t), ron=0.05, roff=1e6)
    ck.SW("b_hi", "p", "b", lambda t: not pos(t), ron=0.05, roff=1e6); ck.SW("b_lo", "b", "0", pos, ron=0.05, roff=1e6)
    ck.L("f", "a", "lx", L); ck.R("dcr", "lx", "o", 0.1)
    ck.C("f", "o", "b", C); ck.R("L", "o", "b", R)
    ck.R("ref", "b", "0", 1e7)
    p.write("simulation/h_bridge.cir", ck.to_spice(), "SPICE netlist (switches as comments)")
    dt = 1e-6
    tr = ck.tran(0.06, dt, method="be", uic=True)
    msk = tr.t >= 0.02
    vbr = (tr.v("a") - tr.v("b"))[msk][:-1]
    vo = (tr.v("o") - tr.v("b"))[msk][:-1]
    a_br, thd_br, fr, Xb = thd(vbr, dt)
    a_o, thd_o, _, Xo = thd(vo, dt)
    w = 2 * pi * f1
    Z = 1j * w * L + 0.1
    Hf = 1 / (1 + Z * (1 / R + 1j * w * C))
    p.compare("Bridge fundamental amplitude (m·V_dc)", m * Vdc, a_br, "V", tol=2)
    p.compare("Load fundamental amplitude (m·V_dc·|H(50 Hz)|)", m * Vdc * abs(Hf), a_o, "V", tol=3)
    f0 = 1 / (2 * pi * np.sqrt(L * C))
    p.metric("LC corner frequency", f0, "Hz")
    p.metric("THD of bridge voltage (unfiltered)", thd_br, "%")
    p.metric("THD of load voltage (filtered)", thd_o, "%")
    Zc = 1j * 2 * pi * fc * L
    Hc = 1 / (1 + Zc * (1 / R + 1j * 2 * pi * fc * C))
    p.compare("Carrier-band attenuation by LC filter", db(Hc), db(np.max(Xo[(fr > 0.8 * fc) & (fr < 1.2 * fc)]) / np.max(Xb[(fr > 0.8 * fc) & (fr < 1.2 * fc)])), "dB", kind="abs")
    t = (tr.t[msk][:-1] - 0.02) * 1e3
    fig, ax = p.fig(2, 1, h=6, sharex=True)
    ax[0].plot(t, vbr, color=COLORS[1], lw=.4); style_axes(ax[0], None, "bridge V (V)", "SPWM bridge voltage", legend=False)
    ax[1].plot(t, vo, color=C_MEAS, label="load voltage"); ax[1].plot(t, a_o * np.sin(2 * pi * f1 * (t / 1e3 + 0.02) + np.angle(Hf)), "--", color=C_PRED, lw=1, label="predicted fundamental")
    style_axes(ax[1], "time (ms)", "V_load (V)")
    p.save(fig, "waveforms", "±200 V switching becomes a 50 Hz sine after the LC filter.")
    fig, ax = p.fig()
    ax.semilogy(fr / 1e3, Xb + 1e-6, color=COLORS[1], lw=.8, label="bridge")
    ax.semilogy(fr / 1e3, Xo + 1e-6, color=C_MEAS, lw=.8, label="load (filtered)")
    ax.set_xlim(0, 45); ax.set_ylim(1e-3, 300)
    style_axes(ax, "frequency (kHz)", "amplitude (V)", "Spectrum: harmonics sit around multiples of the 10 kHz carrier")
    p.save(fig, "spectrum", "The LC filter removes ~40 dB of the carrier-band harmonics.")
    p.csv("output", t_ms=t, v_bridge=vbr, v_load=vo)
    p.discuss("""The bridge fundamental equals m·V_dc to within the switch-resistance drop, confirming the linear-
modulation result. Bipolar SPWM puts large harmonic sidebands at f_c ± 2f₁, ± 4f₁…, and 2f_c; the LC
filter (f₀ = 712 Hz) removes them at 40 dB/decade, taking THD from >100 % to a few percent. Unipolar
(three-level) SPWM would double the effective ripple frequency and shrink the filter further.""")
