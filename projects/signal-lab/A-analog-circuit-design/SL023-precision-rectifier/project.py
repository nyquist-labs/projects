from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-023", title="Precision (super-diode) rectifier", level="M",
    tools="eelab mini-SPICE transient (op-amp macromodel)",
    summary="Put the diode inside an op-amp's feedback loop to rectify millivolt signals: measure the "
            "error vs a plain diode, and the frequency where slew rate breaks it.",
    problem="A silicon diode can't rectify anything smaller than ~0.6 V. How does an op-amp hide the "
            "diode drop, and what new limitation appears?",
    theory=r"""Plain diode half-wave rectifier: output ≈ $\max(v_{in}-V_D,0)$, so a 100 mV signal gives nothing.
Super-diode: the op-amp drives the diode until the output equals the input; the effective drop is
$V_D/A_0$ ≈ 3 µV. Mean of a half-wave-rectified sine: $\hat V/\pi$.
Limitation: when the input crosses zero, the op-amp output must slew from negative saturation up by
$V_D$ before conduction resumes — a dead time ≈ $(V_{int}+V_D)/SR$ each cycle, where $V_{int}$ is how far the op-amp's internal node has saturated (1.5·V_sat = 19.5 V in this macromodel), so error grows with frequency.""",
    method="""Super-diode (non-inverting, diode in feedback, 10 kΩ load) vs a plain diode into 10 kΩ. Sine inputs of 50 mV–2 V
at 1 kHz, and 1 V at 1–100 kHz. Output mean compared with V̂/π.""",
)


def build(kind, amp, f):
    ck = Circuit(kind)
    ck.V("in", "in", "0", wave=lambda t: amp * np.sin(2 * pi * f * t))
    if kind == "plain":
        ck.D("1", "in", "out", Is=2.5e-9, N=1.75)
    else:
        ck.OPAMP("U1", "in", "out", "oa", SR=0.5e6, GBW=1e6, VSAT=13)
        ck.D("1", "oa", "out", Is=2.5e-9, N=1.75)
    ck.R("L", "out", "0", 10e3)
    return ck


def run(p):
    amps = np.array([0.05, 0.1, 0.2, 0.5, 1, 2])
    res = {"plain": [], "precision": []}
    for kind in res:
        for a in amps:
            tr = build(kind, a, 1000).tran(5e-3, 1e-6, uic=True)
            v = tr.v("out")[tr.t >= 1e-3][:-1]
            res[kind].append(v.mean())
    ideal = amps / pi
    for kind in res:
        m = np.array(res[kind])
        p.compare(f"{kind}: mean output at 100 mV peak", ideal[1], m[1], "V", kind="rel")
        p.compare(f"{kind}: mean output at 1 V peak", ideal[4], m[4], "V", kind="rel")
    freqs = np.array([1e3, 3e3, 10e3, 30e3, 100e3])
    errs = []
    for f in freqs:
        tr = build("precision", 1.0, f).tran(8 / f, 1 / (f * 2000), uic=True)
        v = tr.v("out")[tr.t >= 3 / f][:-1]
        errs.append((v.mean() - 1 / pi) / (1 / pi) * 100)
        if f == 30e3:
            w30 = (tr.t, tr.v("out"), tr.v("in"))
    errs = np.array(errs)
    dead = (1.5 * 13 + 0.6) / 0.5e6    # internal node is clamped at 1.5·V_sat in saturation
    ph = np.minimum(2 * pi * freqs * dead, pi)
    pred_err = (np.cos(ph) - 1) / 2 * 100          # output misses sin from 0 to ω·t_dead
    for k in (0, 2, 3):
        p.compare(f"Super-diode error at {freqs[k]/1e3:g} kHz (slew dead-time model)", pred_err[k], errs[k], "%", kind="abs")
    fig, ax = p.fig(1, 2)
    ax[0].loglog(amps, ideal, "--", color=C_PRED, label="ideal V̂/π")
    ax[0].loglog(amps, np.maximum(res["plain"], 1e-6), "o-", color=COLORS[7], label="plain diode")
    ax[0].loglog(amps, res["precision"], "o-", color=C_MEAS, label="super-diode")
    style_axes(ax[0], "input peak (V)", "mean output (V)", "Rectifying small signals (1 kHz)")
    ax[1].semilogx(freqs, pred_err, "--", color=C_PRED, label="dead-time model (cos(ωt_d)−1)/2")
    ax[1].semilogx(freqs, errs, "o-", color=C_MEAS, label="super-diode error")
    style_axes(ax[1], "frequency (Hz)", "error (%)", "Slew-rate limit at high frequency")
    p.save(fig, "precision_vs_plain", "The op-amp hides the diode drop until slew rate runs out.")
    t, vo, vi = w30
    m = t > 5 / 30e3
    fig, ax = p.fig()
    ax.plot((t[m] - t[m][0]) * 1e6, vi[m], color="gray", lw=1, label="input 1 V, 30 kHz")
    ax.plot((t[m] - t[m][0]) * 1e6, vo[m], color=C_MEAS, label="super-diode output")
    style_axes(ax, "time (µs)", "V", "At 30 kHz the output starts late each half-cycle")
    p.save(fig, "slew_dead_time", "The op-amp must slew out of negative saturation before the diode conducts again.")
    p.csv("amplitude_sweep", amp_v=amps, ideal_v=ideal, plain_v=res["plain"], precision_v=res["precision"])
    p.discuss("""At 1 kHz the super-diode's error is tiny at any amplitude, while the plain diode's output is
essentially zero below ~0.4 V and still loses ~0.6 V at 2 V peak. At high frequency the op-amp spends
each negative half-cycle saturated at −13 V; recovering takes (19.5 V + V_D)/SR ≈ 40 µs, more than a
whole 33 µs period at 30 kHz. Missing the part of each positive half-cycle from 0 to ω·t_d gives an error of (cos ωt_d − 1)/2,
which reaches −100 % once t_d exceeds half a period; the model tracks the simulation, with the extra
error at low frequency coming from finite-bandwidth settling after recovery. Improved circuits clamp the op-amp output with a
second diode so it never saturates.""")
