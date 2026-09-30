from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-003", title="RLC resonance: Q is the pole's distance from the jω axis", level="M",
    tools="Characteristic-polynomial roots (NumPy), AC simulation of a series RLC, bandwidth measurement",
    summary="Locate the poles of a series RLC circuit in the complex plane, predict the quality factor from their geometry, and confirm it by "
            "measuring the −3 dB bandwidth of the simulated resonance for resistances spanning Q = 0.5 to 50.",
    problem="What does 'high Q' look like in the s-plane?",
    theory=r"""The current in a series RLC obeys $Ls^2+Rs+1/C=0$: poles $s=-α\pm jω_d$ with $α=R/2L$, $ω_0=1/\sqrt{LC}$ = |s|. Hence $Q=\frac{ω_0}{2α}=\frac{|s|}{2|\mathrm{Re}\,s|}$ —
a pole close to the imaginary axis relative to its distance from the origin means a sharp resonance. The −3 dB bandwidth of the current response is exactly
$Δω = 2α = ω_0/Q$ (for any Q, since the admittance is a band-pass with that bandwidth).""",
    method="""L = 1 mH, C = 1 µF (f0 = 5.03 kHz), R from 0.63 Ω to 63 Ω. Poles from numpy.roots; AC sweep of the loop current; bandwidth from the two −3 dB crossings.""",
)


def run(p):
    L, C = 1e-3, 1e-6
    w0 = 1 / np.sqrt(L * C); f0 = w0 / (2 * pi)
    Qs = np.array([0.5, 1, 2, 5, 10, 20, 50])
    Rs = w0 * L / Qs
    rows = []
    f = np.logspace(np.log10(f0) - 2.5, np.log10(f0) + 2.5, 20000)
    for R, Qn in zip(Rs, Qs):
        poles = np.roots([L, R, 1 / C])
        Qp = np.abs(poles[0]) / (2 * abs(poles[0].real))
        ck = Circuit("rlc"); ck.V("s", "a", "0", ac=1); ck.R("r", "a", "b", R); ck.L("l", "b", "c", L); ck.C("c", "c", "0", C)
        I = np.abs(ck.ac(f).v("a") - ck.ac(f).v("b")) / R
        pk = np.argmax(I); lvl = I[pk] / np.sqrt(2)
        lo = np.exp(np.interp(lvl, I[:pk], np.log(f[:pk]))); hi = np.exp(np.interp(-lvl, -I[pk:], np.log(f[pk:])))
        Qm = f[pk] / (hi - lo)
        rows.append((R, Qn, Qp, Qm, poles[0]))
    for R, Qn, Qp, Qm, pl in rows:
        if Qn in (0.5, 5, 50):
            p.compare(f"R = {R:.3g} Ω: Q from pole geometry vs from simulated bandwidth", Qp, Qm, "", tol=1)
    p.compare("Pole magnitude |s| = ω0 for every R (worst deviation)", 0, max(abs(abs(r[4]) - w0) / w0 for r in rows), "", kind="abs", tol=1e-9)
    fig, ax = p.fig(1, 2, w=11)
    th = np.linspace(pi / 2, 3 * pi / 2, 100)
    ax[0].plot(w0 * np.cos(th) / 1e3, w0 * np.sin(th) / 1e3, ":", color="gray", label="|s| = ω0")
    for (R, Qn, Qp, Qm, pl), c in zip(rows, COLORS):
        pp = np.roots([L, R, 1 / C])
        ax[0].plot(pp.real / 1e3, pp.imag / 1e3, "x", color=c, ms=9, mew=2, label=f"Q = {Qn:g}")
    ax[0].set_aspect("equal")
    style_axes(ax[0], "Re s (krad/s)", "Im s (krad/s)", "Poles slide along a circle as R changes")
    for (R, Qn, Qp, Qm, pl), c in zip(rows, COLORS):
        ck = Circuit("rlc"); ck.V("s", "a", "0", ac=1); ck.R("r", "a", "b", R); ck.L("l", "b", "c", L); ck.C("c", "c", "0", C)
        I = np.abs(ck.ac(f).v("a") - ck.ac(f).v("b")) / R
        ax[1].semilogx(f, db(I / I.max()), color=c, label=f"Q = {Qn:g}")
    ax[1].set_ylim(-40, 2)
    style_axes(ax[1], "frequency (Hz)", "normalised current (dB)", "Sharper resonance for poles nearer the axis")
    p.save(fig, "poles_q", "Pole locations for seven Q values and the corresponding simulated resonance curves.")
    p.csv("q", R_ohm=[r[0] for r in rows], Q_pole=[r[2] for r in rows], Q_bandwidth=[r[3] for r in rows])
    p.discuss("""The pole-geometry Q and the bandwidth-measured Q agree across two decades, from an over-damped Q = 0.5 (real poles would appear below
Q = 0.5) to a razor-sharp Q = 50. All poles lie on the circle |s| = ω0: changing R only moves them *around* the circle toward the jω axis, which is
the geometric statement that resistance sets damping but not the natural frequency. For Q = 0.5 the two poles meet on the real axis (critical
damping), and the 'bandwidth' is still ω0/Q — the definition that makes this exact is the admittance's band-pass shape, not the peak sharpness.""")
# tol-convention: relative tolerances are in percent
