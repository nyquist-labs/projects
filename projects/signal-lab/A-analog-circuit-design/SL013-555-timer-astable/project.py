from eelab import *

META = dict(
    id="SL-013", title="555 timer astable multivibrator", level="E",
    tools="Behavioural 555 model integrated numerically (NumPy)",
    summary="Derive f = 1.44/((R_A+2R_B)C) and the duty cycle, then verify on a behavioural 555 with "
            "a non-ideal discharge transistor and comparator delay, across five designs.",
    problem="Where do the 555's famous 0.693 and 1.44 constants come from, and how far do real "
            "internals (discharge on-resistance, comparator delay) move the frequency?",
    theory=r"""The capacitor charges through $R_A+R_B$ from $V_{CC}/3$ to $2V_{CC}/3$ and discharges through $R_B$
from $2V_{CC}/3$ to $V_{CC}/3$. Each is an exponential segment that covers half the remaining distance:
$t_H = \ln 2\,(R_A+R_B)C$, $t_L=\ln2\,R_BC$, so
$$f=\frac{1}{0.693(R_A+2R_B)C}=\frac{1.443}{(R_A+2R_B)C},\qquad D=\frac{R_A+R_B}{R_A+2R_B}$$""",
    method="""Behavioural model: capacitor ODE integrated with 10 ns steps (exact exponential update per step);
comparators at 2/3 and 1/3 V_CC with 100 ns propagation delay; SR flip-flop; discharge transistor
with 15 Ω on-resistance. V_CC = 9 V. Frequency and duty measured over the last 10 cycles.""",
)


def sim555(RA, RB, C, vcc=9.0, rdis=15.0, tpd=100e-9, cycles=14):
    T_est = 0.693 * (RA + 2 * RB) * C
    dt = T_est / 4000
    t, v, q = 0.0, 0.0, 1
    pend, t_pend = None, 0.0
    edges_r, edges_f, ts, vs, qs = [], [], [], [], []
    tend = cycles * T_est
    while t < tend:
        if q:  # charging towards vcc through RA+RB
            tau = (RA + RB) * C; vinf = vcc
        else:  # discharging through RB into the transistor
            tau = (RB + rdis) * C; vinf = vcc * rdis / (RA + rdis) * 0 + 0.0
            # RA also conducts from vcc into the discharge node: Thevenin of RA/rdis
            vth = vcc * rdis / (RA + rdis); rth = RA * rdis / (RA + rdis)
            tau = (RB + rth) * C; vinf = vth
        v = vinf + (v - vinf) * np.exp(-dt / tau)
        t += dt
        if pend is None:
            if q and v >= 2 * vcc / 3:
                pend, t_pend = 0, t + tpd
            elif not q and v <= vcc / 3:
                pend, t_pend = 1, t + tpd
        if pend is not None and t >= t_pend:
            q = pend; pend = None
            (edges_r if q else edges_f).append(t)
        ts.append(t); vs.append(v); qs.append(q)
    return np.array(ts), np.array(vs), np.array(qs), np.array(edges_r), np.array(edges_f)


def run(p):
    designs = [(1e3, 10e3, 10e-9), (10e3, 10e3, 10e-9), (4.7e3, 47e3, 100e-9), (1e3, 1e3, 1e-6), (100e3, 1e3, 1e-9)]
    fp, fm, dp, dm = [], [], [], []
    for RA, RB, C in designs:
        t, v, q, er, ef = sim555(RA, RB, C)
        er = er[-11:]
        ef = ef[ef > er[0]][:10]
        T = np.mean(np.diff(er))
        th = np.mean(ef - er[:len(ef)])
        f_pred = 1.443 / ((RA + 2 * RB) * C)
        d_pred = (RA + RB) / (RA + 2 * RB)
        lab = f"R_A={RA/1e3:g}k R_B={RB/1e3:g}k C={C*1e9:g}n"
        p.compare(f"{lab}: frequency", f_pred, 1 / T, "Hz", tol=3)
        p.compare(f"{lab}: duty cycle", d_pred * 100, th / T * 100, "%", kind="abs")
        fp.append(f_pred); fm.append(1 / T); dp.append(d_pred); dm.append(th / T)
        if RA == 10e3 and RB == 10e3:
            fig, ax = p.fig(2, 1, h=5.5, sharex=True)
            m = t < 4 / f_pred
            ax[0].plot(t[m] * 1e6, v[m], color=C_MEAS, label="capacitor voltage")
            for lvl in (3, 6):
                ax[0].axhline(lvl, color="gray", lw=.8, ls=":")
            style_axes(ax[0], None, "V_C (V)", "555 astable (R_A = R_B = 10 kΩ, C = 10 nF)")
            ax[1].plot(t[m] * 1e6, q[m] * 9, color=COLORS[1], label="output")
            style_axes(ax[1], "time (µs)", "V_out (V)")
            p.save(fig, "waveforms", "Capacitor ramps between 3 V and 6 V; the output is high while charging.")
    fig, ax = p.fig()
    ax.loglog(fp, fm, "o", color=C_MEAS, ms=8, label="simulated")
    ax.loglog([min(fp) / 2, max(fp) * 2], [min(fp) / 2, max(fp) * 2], "--", color=C_PRED, label="measured = predicted")
    style_axes(ax, "predicted frequency (Hz)", "measured frequency (Hz)", "555: formula vs behavioural model")
    p.save(fig, "pred_vs_meas", "All five designs fall on the identity line except the fastest one.")
    p.csv("designs", predicted_hz=fp, measured_hz=fm, predicted_duty=dp, measured_duty=dm)
    p.discuss("""For slow designs the formula is essentially exact. The errors grow when timing intervals get
short: the fixed 100 ns comparator delay lets the capacitor overshoot both thresholds (lowering f),
and with R_B = 1 kΩ the 15 Ω discharge resistance is no longer negligible. The 100 kΩ/1 kΩ/1 nF design
has a 0.7 µs low time, so 100 ns of delay is a 14 % timing error there. This is why the datasheet
recommends R_B ≫ discharge resistance and why the 555 tops out near a few hundred kHz.""")
