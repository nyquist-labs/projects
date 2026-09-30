from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-022", title="Envelope (AM peak) detector", level="E",
    tools="eelab mini-SPICE transient, FFT distortion measurement",
    summary="Recover a 1 kHz tone from a 50 kHz AM carrier with a diode + RC; tune the time constant "
            "between ripple (too small) and diagonal clipping (too large).",
    problem="An AM radio's detector is one diode and one RC. How do you choose RC so the output "
            "follows the envelope without carrier ripple and without missing the falling edges?",
    theory=r"""Need $1/f_c \ll RC$ (smooth carrier) but the capacitor must discharge as fast as the envelope falls.
For modulation index m and modulating frequency $\omega_m$ the no-diagonal-clipping condition is
$$RC\le\frac{\sqrt{1-m^2}}{\omega_m m}$$
For m = 0.5, f_m = 1 kHz: RC ≤ 276 µs. Carrier period is 20 µs.""",
    method="""AM source 2(1 + 0.5·sin 2π·1kHz·t)·sin 2π·50kHz·t, germanium-like diode (Is = 1 µA), C = 10 nF, R chosen for
RC = 30 µs, 150 µs and 1 ms. 6 ms transients; output distortion measured by fitting the ideal
envelope shape; audio THD by FFT after removing the carrier.""",
)


def run(p):
    fc, fm, mm = 50e3, 1e3, 0.5
    lim = np.sqrt(1 - mm**2) / (2 * pi * fm * mm)
    p.metric("Maximum RC for no diagonal clipping", lim, "s", "√(1−m²)/(ω_m·m)")
    fig, ax = p.fig()
    rows = []
    for i, RC in enumerate([30e-6, 150e-6, 1e-3]):
        C = 10e-9; R = RC / C
        ck = Circuit("envelope")
        ck.V("am", "in", "0", wave=lambda t: 2 * (1 + mm * np.sin(2 * pi * fm * t)) * np.sin(2 * pi * fc * t))
        ck.D("1", "in", "out", Is=1e-6, N=1.1)
        ck.C("1", "out", "0", C); ck.R("1", "out", "0", R)
        if i == 1:
            p.write("simulation/envelope.cir", ck.to_spice(), "SPICE netlist (RC = 150 µs)")
        tr = ck.tran(6e-3, 0.2e-6, uic=True)
        t, v = tr.t, tr.v("out")
        m = t >= 2e-3
        tt, vv = t[m][:-1], v[m][:-1]
        n = len(tt)
        X = np.fft.rfft(vv - vv.mean()) / (n / 2)
        fr = np.fft.rfftfreq(n, tt[1] - tt[0])
        a1 = abs(X[np.argmin(abs(fr - fm))])
        harm = [abs(X[np.argmin(abs(fr - k * fm))]) for k in range(2, 8)]
        thd = np.sqrt(np.sum(np.square(harm))) / a1 * 100
        car = abs(X[np.argmin(abs(fr - fc))])
        rows.append((RC, a1, thd, car))
        p.metric(f"RC = {RC*1e6:g} µs: audio THD", thd, "%")
        p.metric(f"RC = {RC*1e6:g} µs: 50 kHz ripple amplitude", car, "V")
        ax.plot((tt - 2e-3) * 1e3, vv, color=COLORS[i], label=f"RC = {RC*1e6:g} µs")
    env = 2 * (1 + mm * np.sin(2 * pi * fm * t[m])) - 0.35
    ax.plot((t[m] - 2e-3) * 1e3, env, "--", color="gray", lw=1, label="ideal envelope (− V_D)")
    ax.set_xlim(0, 3)
    style_axes(ax, "time (ms)", "V_out (V)", "Envelope detector: too fast, just right, too slow")
    p.save(fig, "envelopes", "Small RC leaves ripple; large RC cannot follow the falling envelope (diagonal clipping).")
    best = min(rows, key=lambda r: r[2] + 20 * r[3])
    p.compare("Best RC is within the no-clipping bound", 1.0, float(best[0] <= lim), "", kind="abs")
    p.compare("Recovered audio amplitude (RC=150 µs)", 2 * mm * 0.93, rows[1][1], "V", tol=15,
              note="≈ m·A·(detector efficiency ~0.93)")
    p.csv("sweep", rc_s=[r[0] for r in rows], audio_amp_v=[r[1] for r in rows], thd_pct=[r[2] for r in rows], carrier_v=[r[3] for r in rows])
    p.discuss("""RC = 30 µs follows the envelope but leaves visible carrier ripple (it discharges noticeably in each
20 µs carrier period). RC = 1 ms is far beyond the 276 µs limit: on the falling side of the envelope
the capacitor decays slower than the envelope, so the output cuts diagonally across the troughs —
high harmonic distortion. The middle value sits inside the window predicted by the two inequalities.""")
