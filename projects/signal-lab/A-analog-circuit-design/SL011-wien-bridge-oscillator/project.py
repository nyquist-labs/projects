from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-011", title="Wien bridge oscillator", level="M",
    tools="eelab mini-SPICE transient (op-amp + diode amplitude limiter)",
    summary="A 1 kHz Wien bridge sine oscillator with diode amplitude stabilisation: predict "
            "frequency and required gain, then measure start-up, frequency and distortion.",
    problem="An oscillator needs loop gain exactly 1. Too little and it dies, too much and it clips. "
            "How do two diodes solve the amplitude problem, and at what cost in distortion?",
    theory=r"""The RC series–parallel network has $\beta(j\omega_0)=1/3$ at $\omega_0 = 1/(RC)$ with zero phase,
so the amplifier needs gain exactly 3 (Barkhausen). R = 10 kΩ, C = 15.9 nF → f₀ = 1.00 kHz.
Amplifier: $1+R_f/R_g$ with R_g = 10 kΩ, R_f = 15 kΩ + (12 kΩ ‖ diodes): small signals see gain 3.7
(start-up guaranteed), large signals switch the diodes on and gain falls toward 2.5, so amplitude
settles where the *average* gain is 3 — roughly where the diodes start conducting on the 12 kΩ.""",
    method="""Transient 60 ms at 2 µs step (trapezoidal). A 1 µA, 50 µs current kick starts the oscillation.
Frequency from zero crossings over the last 20 ms; THD from an FFT of the settled waveform.""",
)


def run(p):
    R, C = 10e3, 15.915e-9
    f0 = 1 / (2 * pi * R * C)
    ck = Circuit("Wien bridge")
    ck.R("s", "out", "a", R); ck.C("s", "a", "p", C)
    ck.R("p", "p", "0", R); ck.C("p", "p", "0", C)
    ck.OPAMP("U1", "p", "n", "out", GBW=10e6, SR=10e6)
    ck.R("g", "n", "0", 10e3); ck.R("f1", "n", "m", 15e3); ck.R("f2", "m", "out", 12e3)
    ck.D("1", "m", "out", Is=2.5e-9, N=1.75); ck.D("2", "out", "m", Is=2.5e-9, N=1.75)
    ck.I("kick", "0", "p", wave=lambda t: 1e-6 if t < 5e-5 else 0.0)
    p.write("simulation/wien_bridge.cir", ck.to_spice(), "SPICE netlist")
    tr = ck.tran(0.06, 2e-6, uic=True)
    t, v = tr.t, tr.v("out")
    m = t > 0.04
    tt, vv = t[m], v[m]
    zc = tt[1:][(vv[:-1] < 0) & (vv[1:] >= 0)]
    # refine zero crossings by linear interpolation
    idx = np.where((vv[:-1] < 0) & (vv[1:] >= 0))[0]
    zc = tt[idx] - vv[idx] * (tt[idx + 1] - tt[idx]) / (vv[idx + 1] - vv[idx])
    f_meas = (len(zc) - 1) / (zc[-1] - zc[0])
    p.compare("Oscillation frequency", f0, f_meas, "Hz", tol=2)
    p.metric("Small-signal amplifier gain (start-up)", 1 + 27 / 10, "", "must exceed 3 for start-up")
    amp = (vv.max() - vv.min()) / 2
    n = int(round(20e-3 * f_meas)) * int(round(1 / (f_meas * 2e-6)))
    seg = vv[-n:]
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fr = np.fft.rfftfreq(len(seg), 2e-6)
    h = [X[np.argmin(abs(fr - k * f_meas))] for k in range(1, 8)]
    thd = np.sqrt(np.sum(np.square(h[1:]))) / h[0] * 100
    p.metric("Settled amplitude", amp, "V")
    p.metric("THD of settled sine", thd, "%")
    env_t = t[::500]; env = np.array([np.max(np.abs(v[i:i + 500])) for i in range(0, len(v), 500)])
    start = env_t[np.argmax(env > 0.9 * amp)]
    p.metric("Start-up time to 90 % amplitude", start, "s")
    fig, ax = p.fig(2, 1, h=6)
    ax[0].plot(t * 1e3, v, color=C_MEAS, lw=.8)
    style_axes(ax[0], "time (ms)", "v_out (V)", "Start-up: exponential growth until the diodes clamp the gain", legend=False)
    ax[1].plot((tt[-2500:] - tt[-2500]) * 1e3, vv[-2500:], color=C_MEAS, label="simulated")
    ax[1].plot((tt[-2500:] - tt[-2500]) * 1e3, amp * np.sin(2 * pi * f0 * (tt[-2500:] - tt[-2500]) + np.arcsin(np.clip(vv[-2500] / amp, -1, 1))), "--", color=C_PRED, label=f"ideal sine at {f0:.0f} Hz")
    style_axes(ax[1], "time (ms)", "v_out (V)")
    p.save(fig, "waveform", "Growth from a 1 µA kick, then a stable ~sine at the predicted frequency.")
    fig, ax = p.fig()
    ax.semilogy(fr / 1e3, X / X.max(), color=C_MEAS)
    ax.set_xlim(0, 8)
    style_axes(ax, "frequency (kHz)", "relative amplitude", "Output spectrum: odd harmonics from the symmetric diodes", legend=False)
    p.save(fig, "spectrum", "Symmetric soft clipping produces mostly odd harmonics.")
    p.csv("waveform", t_s=t, vout_v=v)
    p.discuss(f"""The measured frequency lands {pct_err(f0, f_meas):+.2f} % from 1/(2πRC): the op-amp's finite bandwidth adds a
small phase shift so the loop settles slightly off ω₀ to make total phase zero. The diodes solve the
amplitude problem by making gain amplitude-dependent — but a gain that changes *within* each cycle is
nonlinearity, so the sine carries {thd:.1f} % THD of mostly odd harmonics. Classic designs (Hewlett's
1939 HP200A) used a lamp or later a JFET, whose resistance responds to the *average* amplitude over
many cycles, to get THD below 0.01 %.""")
