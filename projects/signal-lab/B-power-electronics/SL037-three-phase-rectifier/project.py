from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-037", title="Three-phase vs single-phase bridge rectifier", level="M",
    tools="eelab mini-SPICE (6-diode bridge, RL load), FFT harmonic analysis",
    summary="Compare output ripple and line-current harmonics of a 6-pulse three-phase bridge and a "
            "single-phase bridge feeding a highly inductive load.",
    problem="Why do industrial drives rectify three phases instead of one, and what harmonics do they "
            "still inject into the grid?",
    theory=r"""Six-pulse bridge: $V_{dc}=\frac{3\sqrt2}{\pi}V_{LL,rms}=1.35V_{LL}$, ripple at 6f with
pk-pk $=\sqrt2V_{LL}(1-\cos30°)$ = 13.4 % of peak. With a constant DC current the line current is a
120° quasi-square wave: harmonics $h=6k\pm1$ with $I_h=I_1/h$, THD = 31.1 %.
Single-phase bridge: $V_{dc}=\frac{2\sqrt2}{\pi}V_{rms}$, ripple 100 % at 2f, square-wave line current, THD = 48.3 %.""",
    method="""400 V line-to-line, 50 Hz (230 V phase). Load: 20 Ω + 200 mH (L/R ≫ 1/300 Hz). Diodes Is = 1e-9, N = 1.5.
100 ms transients (50 µs steps), last 40 ms analysed.""",
)


def run(p):
    f, Vll = 50.0, 400.0
    Vph = Vll / np.sqrt(3) * np.sqrt(2)
    Dm = dict(Is=1e-9, N=1.5)
    ck = Circuit("6-pulse")
    for k, ph in enumerate("abc"):
        ck.V(ph, ph, "0", wave=lambda t, k=k: Vph * np.sin(2 * pi * f * t - 2 * pi * k / 3))
        ck.D(f"{ph}p", ph, "pos", **Dm); ck.D(f"{ph}n", "neg", ph, **Dm)
    ck.R("L", "pos", "m", 20); ck.L("L", "m", "neg", 0.2)
    p.write("simulation/six_pulse.cir", ck.to_spice(), "SPICE netlist")
    Idc0 = 1.35 * Vll / 20
    tr = ck.tran(0.1, 50e-6, method="be", ic={"I(L)": Idc0 * 0.98, "pos": 270, "neg": -270})
    m = tr.t >= 0.06
    vdc = (tr.v("pos") - tr.v("neg"))[m][:-1]
    ia = -tr.i("a")[m][:-1]
    p.compare("6-pulse DC voltage", 3 * np.sqrt(2) / pi * Vll, vdc.mean(), "V", tol=3)
    p.compare("6-pulse ripple (pk-pk)", np.sqrt(2) * Vll * (1 - np.cos(pi / 6)), vdc.max() - vdc.min(), "V", tol=8)
    n = len(ia); X = np.abs(np.fft.rfft(ia)); fr = np.fft.rfftfreq(n, 50e-6)
    I1 = X[np.argmin(abs(fr - f))]
    hs = {h: X[np.argmin(abs(fr - h * f))] / I1 for h in (5, 7, 11, 13)}
    thd6 = np.sqrt(np.sum(X[(fr > 1.5 * f) & (fr < 2500)]**2)) / I1 * 100
    p.compare("6-pulse line-current THD", 31.08, thd6, "%", kind="abs")
    for h in (5, 7):
        p.compare(f"6-pulse I_{h}/I_1", 1 / h, hs[h], "", kind="abs")
    # single phase
    ck1 = Circuit("1-phase")
    Vs = 230 * np.sqrt(2)
    ck1.V("s", "a", "b", wave=lambda t: Vs * np.sin(2 * pi * f * t))
    ck1.D("1", "a", "pos", **Dm); ck1.D("2", "b", "pos", **Dm); ck1.D("3", "neg", "a", **Dm); ck1.D("4", "neg", "b", **Dm)
    ck1.R("L", "pos", "m", 20); ck1.L("L", "m", "neg", 0.2); ck1.R("ref", "b", "0", 1e6)
    Idc1 = 2 * Vs / pi / 20
    tr1 = ck1.tran(0.1, 50e-6, method="be", ic={"I(L)": Idc1})
    m1 = tr1.t >= 0.06
    v1 = (tr1.v("pos") - tr1.v("neg"))[m1][:-1]
    i1 = tr1.i("s")[m1][:-1]
    X1 = np.abs(np.fft.rfft(i1)); I11 = X1[np.argmin(abs(fr - f))]
    thd1 = np.sqrt(np.sum(X1[(fr > 1.5 * f) & (fr < 2500)]**2)) / I11 * 100
    p.compare("1-phase DC voltage", 2 * Vs / pi, v1.mean(), "V", tol=3)
    p.compare("1-phase line-current THD", 48.34, thd1, "%", kind="abs")
    t = (tr.t[m][:-1] - 0.06) * 1e3
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    ax[0].plot(t, vdc, color=C_MEAS, label="3-phase 6-pulse"); ax[0].plot(t, v1, color=COLORS[1], label="1-phase bridge")
    style_axes(ax[0], None, "V_dc (V)", "Rectified output voltage")
    ax[1].plot(t, ia, color=C_MEAS, label="phase-a current (6-pulse)"); ax[1].plot(t, i1, color=COLORS[1], label="line current (1-phase)")
    style_axes(ax[1], "time (ms)", "A", "Line currents: 120° blocks vs square wave")
    p.save(fig, "waveforms", "Six pulses per cycle give a far smoother DC bus.")
    fig, ax = p.fig()
    hh = np.arange(1, 26)
    ax.bar(hh - 0.2, [X[np.argmin(abs(fr - h * f))] / I1 for h in hh], 0.4, color=C_MEAS, label="6-pulse")
    ax.bar(hh + 0.2, [X1[np.argmin(abs(fr - h * f))] / I11 for h in hh], 0.4, color=COLORS[1], label="1-phase")
    ax.plot(hh, np.where((hh % 6 == 1) | (hh % 6 == 5), 1 / hh, np.nan), "_", color=C_PRED, ms=14, mew=2, label="theory 1/h (6k±1)")
    style_axes(ax, "harmonic order", "I_h / I_1", "Line-current harmonic spectrum")
    p.save(fig, "harmonics", "The 6-pulse bridge cancels triplen and even harmonics; 5th and 7th remain.")
    p.csv("waveforms", t_ms=t, vdc_6p=vdc, ia_6p=ia, vdc_1p=v1, i_1p=i1)
    p.discuss("""DC levels come out a couple of volts under the ideal formulas: the ideal assumes instant commutation
and zero diode drop, whereas each current path crosses two diodes (≈ 2 V). With 200 mH the DC current is
nearly flat so the harmonic ratios approach the classic 1/h law; the residual difference is because the
current still carries a small 300 Hz ripple. The 5th and 7th harmonics (20 % and 14 %) are why large drives
use 12-pulse rectifiers or active front ends.""")
