from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-020", title="Class-D switching amplifier", level="H",
    tools="eelab mini-SPICE (switch-level half bridge + LC filter)",
    summary="A 250 kHz PWM half-bridge with a 2nd-order LC output filter driving 8 Ω: predict "
            "output amplitude, carrier ripple and efficiency, then measure them.",
    problem="A class-D amplifier only ever switches its transistors fully on or off. How does an LC "
            "filter turn that square wave back into audio, and what does the filter leave behind?",
    theory=r"""Natural-sampling PWM of $m\sin(\omega t)$ against a triangle gives a switch node whose *average* is
$m V_S\sin\omega t$, so $\hat V_{out}=mV_S\,|H(j\omega)|$. The LC filter ($L$ = 22 µH, $C$ = 680 nF,
$f_c=1/(2\pi\sqrt{LC})$ = 41.1 kHz) passes audio and attenuates the carrier by ≈ $(f_{sw}/f_c)^2$
(40 dB/decade). For a switch node swinging $2V_S$ with duty D the output ripple is
$\Delta V_{pp}=\frac{2V_S\,D(1-D)}{8LCf_{sw}^2}$, largest ($D=\tfrac12$) at the audio zero crossings: 1.34 V.
Efficiency: only $I^2R_{on}$ conduction loss in this idealised model → η ≈ $R_L/(R_L+R_{on}+R_{DCR})$.""",
    method="""Supplies ±20 V, switches with R_on = 0.1 Ω (complementary, controlled by the PWM comparator), L with
50 mΩ DCR, 8 Ω load, m = 0.6 at 1 kHz. 3 ms transient at 20 ns steps. Measured: 1 kHz amplitude by FFT,
carrier ripple, THD and efficiency from supply and load power.""",
)


def run(p):
    Vs, fsw, m, f0 = 20.0, 250e3, 0.6, 1000.0
    L, C, RL = 22e-6, 680e-9, 8.0
    tri = lambda t: 4 * np.abs((t * fsw) % 1 - 0.5) - 1
    hi = lambda t: m * np.sin(2 * pi * f0 * t) > tri(t)
    ck = Circuit("class D")
    ck.V("p", "vp", "0", dc=Vs); ck.V("n", "vn", "0", dc=-Vs)
    ck.SW("hi", "vp", "sw", hi, ron=0.1, roff=1e6)
    ck.SW("lo", "sw", "vn", lambda t: not hi(t), ron=0.1, roff=1e6)
    ck.L("f", "sw", "lx", L); ck.R("dcr", "lx", "out", 0.05)
    ck.C("f", "out", "0", C); ck.R("L", "out", "0", RL)
    p.write("simulation/class_d.cir", ck.to_spice(), "SPICE netlist (switches listed as comments)")
    dt = 20e-9
    tr = ck.tran(3e-3, dt, method="be", uic=True)
    t, vo = tr.t, tr.v("out")
    msk = t >= 1e-3
    tt, vv = t[msk], vo[msk]
    n = int(round(2e-3 / dt))
    tt, vv = tt[:n], vv[:n]
    X = np.fft.rfft(vv) / (n / 2)
    fr = np.fft.rfftfreq(n, dt)
    a1 = abs(X[np.argmin(abs(fr - f0))])
    w0 = 1 / np.sqrt(L * C)
    s = 1j * 2 * pi * f0
    H = RL / (RL + 0.05 + s * L + (RL * 0.05 + s * L * RL) * s * C) if False else 1 / (1 + (s * L + 0.05) * (1 / RL + s * C))
    pred_amp = m * Vs * abs(H) * (RL / (RL + 0.1)) if False else m * Vs * abs(1 / (1 + (s * L + 0.15) * (1 / RL + s * C)))
    p.compare("1 kHz output amplitude", pred_amp, a1, "V", tol=3)
    harm = [abs(X[np.argmin(abs(fr - k * f0))]) for k in range(2, 10)]
    thd = np.sqrt(np.sum(np.square(harm))) / a1 * 100
    p.metric("THD (harmonics 2–9)", thd, "%")
    # carrier ripple: high-pass the output by removing audio band
    Xf = np.fft.rfft(vv); Xf[fr < 100e3] = 0
    rip = np.fft.irfft(Xf, n)
    rip_pp = rip.max() - rip.min()
    fc = 1 / (2 * pi * np.sqrt(L * C))
    rip_pred = 2 * Vs * 0.25 / (8 * L * C * fsw**2)     # worst case D(1-D) = 1/4 at zero crossings
    p.compare("Carrier ripple (pk-pk)", rip_pred, rip_pp, "V", tol=40)
    p.metric("LC filter corner frequency", fc, "Hz")
    ip = -tr.i("p")[msk][:n]; inn = tr.i("n")[msk][:n]
    Psup = np.mean(Vs * ip) + np.mean(Vs * inn)
    PL = np.mean(vv**2) / RL
    p.compare("Efficiency", RL / (RL + 0.1 + 0.05) * 100, PL / Psup * 100, "%", kind="abs")
    p.metric("Output power", PL, "W")
    fig, ax = p.fig(2, 1, h=6)
    k = tt < 1.05e-3 + 0.0
    ax[0].plot((tt[:600] - tt[0]) * 1e6, tr.v("sw")[msk][:600], color=COLORS[1], lw=.8, label="switch node")
    ax[0].plot((tt[:600] - tt[0]) * 1e6, vv[:600], color=C_MEAS, label="filtered output")
    style_axes(ax[0], "time (µs)", "V", "PWM switch node vs LC output (12 µs)")
    ax[1].plot((tt - tt[0]) * 1e3, vv, color=C_MEAS, label="output")
    ax[1].plot((tt - tt[0]) * 1e3, pred_amp * np.sin(2 * pi * f0 * tt + np.angle(1 / (1 + (s * L + 0.15) * (1 / RL + s * C)))), "--", color=C_PRED, lw=1, label="predicted sine")
    style_axes(ax[1], "time (ms)", "V", "Two audio cycles")
    p.save(fig, "waveforms", "The LC filter extracts the 1 kHz average from ±20 V PWM.")
    fig, ax = p.fig()
    ax.semilogy(fr / 1e3, np.abs(X) + 1e-9, color=C_MEAS)
    ax.set_xlim(0, 800)
    style_axes(ax, "frequency (kHz)", "amplitude (V)", "Output spectrum: audio + carrier residue at 250 kHz and sidebands", legend=False)
    p.save(fig, "spectrum", "Carrier and its sidebands are attenuated ~40 dB by the LC filter.")
    p.csv("output", t_s=tt, vout_v=vv)
    p.discuss("""The audio amplitude matches m·V_S·|H(j2π·1kHz)| within the switch-resistance loss. The ripple
formula gives the worst case (D = ½, at the audio zero crossings); with modulation the duty swings from
20 % to 80 % and the ripple shrinks toward the audio peaks, so the envelope of the residue breathes at
2 kHz. The measured maximum lands close to the D = ½ prediction. Efficiency in
this model counts only conduction loss — real class-D stages are ~90 % because of switching loss
(charging MOSFET capacitances every edge) and dead-time, which a switch-level model does not include.""")
