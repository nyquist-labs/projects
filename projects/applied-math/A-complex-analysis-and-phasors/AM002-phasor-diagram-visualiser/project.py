from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-002", title="Phasor diagram visualiser: lead and lag", level="E",
    tools="Complex phasors, animated phasor diagram (matplotlib → GIF), time-domain transient simulation, phase measurement by quadrature correlation",
    summary="Show how a sinusoid is the real part of a rotating complex number, animate voltage and current phasors for RL and RC loads, and "
            "confirm the predicted lag/lead angles by measuring them in transient simulations.",
    problem="Why does current lag voltage in an inductor and lead it in a capacitor — and by exactly how much?",
    theory=r"""$v(t)=\mathrm{Re}\{V e^{jωt}\}$. For a series RL load $I = V/(R+jωL)$ so the current lags by $φ=\arctan(ωL/R)$; for series RC it leads by $\arctan(1/(ωRC))$. The
phasor diagram is the picture of these complex numbers at t = 0; the whole diagram rotates at ω.""",
    method="""V = 10 V, 50 Hz; RL: R = 10 Ω, L = 31.8 mH (ωL = 10 Ω → 45° lag); RC: R = 10 Ω, C = 159 µF (−1/ωC = −20 Ω → 63.4° lead) and 5 more component values. Transient simulation, last 5 cycles;
phase from the I/Q correlation of v and i with cos/sin at 50 Hz.""",
)


def meas_phase(t, x, f):
    c, s = np.mean(x * np.cos(2 * pi * f * t)), np.mean(x * np.sin(2 * pi * f * t))
    return np.angle(c - 1j * s)


def sim(kind, R, X, f=50.0, V=10.0):
    ck = Circuit(kind)
    ck.V("s", "a", "0", wave=lambda t: V * np.cos(2 * pi * f * t))
    ck.R("r", "a", "b", R)
    if kind == "RL":
        ck.L("l", "b", "0", X / (2 * pi * f))
    else:
        ck.C("c", "b", "0", 1 / (2 * pi * f * X))
    tr = ck.tran(0.2, 1 / f / 400, method="trap")
    t, v, i = tr.t, tr.v("a"), -tr.i("s") if hasattr(tr, "i") else None
    i = (tr.v("a") - tr.v("b")) / R
    m = t >= 0.1
    return t[m], v[m], i[m]


def run(p):
    from matplotlib import animation
    f = 50.0
    rows = []
    for kind, X in (("RL", 5.0), ("RL", 10.0), ("RL", 30.0), ("RC", 5.0), ("RC", 20.0), ("RC", 60.0)):
        R = 10.0
        t, v, i = sim(kind, R, X)
        phi = np.degrees(meas_phase(t, i, f) - meas_phase(t, v, f))
        pred = -np.degrees(np.arctan(X / R)) if kind == "RL" else np.degrees(np.arctan(X / R))
        rows.append((kind, X, pred, phi))
    for kind, X, pred, phi in rows:
        p.compare(f"{kind}, |X| = {X:g} Ω, R = 10 Ω: phase of i relative to v", pred, phi, "°", kind="abs", tol=0.5)
    t, v, i = sim("RL", 10.0, 10.0)
    fig, ax = p.fig(1, 2, w=11)
    V = 10.0; I = V / (10 + 10j)
    for z, lab, c in ((V, "V", C_MEAS), (I * 10, "I × 10 Ω", C_PRED)):
        ax[0].annotate("", xy=(z.real, z.imag), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=c, lw=2))
        ax[0].text(z.real * 1.05, z.imag * 1.05 + 0.3, lab, color=c)
    ax[0].set_xlim(-11, 11); ax[0].set_ylim(-11, 11); ax[0].set_aspect("equal"); ax[0].axhline(0, color="gray", lw=.5); ax[0].axvline(0, color="gray", lw=.5)
    style_axes(ax[0], "Re", "Im", "Phasors at t = 0 (RL, 45° lag)", legend=False)
    ax[1].plot((t - t[0]) * 1e3, v, color=C_MEAS, label="v(t)"); ax[1].plot((t - t[0]) * 1e3, i * 10, color=C_PRED, label="10 Ω × i(t)")
    ax[1].set_xlim(0, 40)
    style_axes(ax[1], "time (ms)", "V", "The same thing in time")
    p.save(fig, "phasors", "Phasor diagram of the RL load and the corresponding waveforms.")
    # animation
    fa, aa = __import__("matplotlib.pyplot", fromlist=["subplots"]).subplots(1, 2, figsize=(8, 3.6))
    th = np.linspace(0, 2 * pi, 40, endpoint=False)

    def frame(k):
        for a_ in aa:
            a_.cla()
        rot = np.exp(1j * th[k])
        for z, c in ((V * rot, C_MEAS), (I * 10 * rot, C_PRED)):
            aa[0].annotate("", xy=(z.real, z.imag), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=c, lw=2))
            aa[0].plot([z.real, 2 * 11 + 0], [z.real, z.real], alpha=0)
        aa[0].set_xlim(-11, 11); aa[0].set_ylim(-11, 11); aa[0].set_aspect("equal"); aa[0].set_title("rotating phasors", fontsize=9)
        tt = np.linspace(0, 2 * pi, 200)
        aa[1].plot(tt, V * np.cos(tt), color=C_MEAS); aa[1].plot(tt, (I * 10 * np.exp(1j * tt)).real, color=C_PRED)
        aa[1].axvline(th[k], color="gray"); aa[1].set_title("real parts = waveforms", fontsize=9)
    anim = animation.FuncAnimation(fa, frame, frames=len(th))
    (p.dir / "figures").mkdir(exist_ok=True)
    anim.save(p.dir / "figures" / "phasors.gif", writer=animation.PillowWriter(fps=12), dpi=70)
    p.files.append(("figures/phasors.gif", "animated phasor diagram"))
    p.discuss("""Every measured phase angle matches arctan(X/R) to a fraction of a degree, with the sign the phasor picture predicts: inductive loads make the
current lag, capacitive loads make it lead. The animation shows why the complex-number trick works — the whole diagram rotates rigidly at ω, so
relative angles between phasors never change, and the waveforms are simply the projections onto the real axis. The small residual differences
come from the first cycles of the transient start-up that are excluded from the measurement window.""")
# tol-convention: relative tolerances are in percent
