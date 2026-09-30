from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-005", title="Bode plots from H(s): asymptotes vs exact", level="M",
    tools="Analytic magnitude/phase of H(jω), straight-line Bode asymptotes, numerical evaluation, AC simulation of an RLC realisation",
    summary="Derive the straight-line Bode approximation for first- and second-order factors, predict exactly where and by how much it is wrong, "
            "and verify both the exact curves and the error predictions numerically and with a circuit simulation.",
    problem="Engineers sketch Bode plots with straight lines. How wrong are they, and where?",
    theory=r"""A simple pole $1/(1+jω/ω_p)$ has asymptotes 0 dB then −20 dB/dec; the worst error is 20·log√2 = −3.01 dB exactly at ω_p (and −0.97 dB an octave away). A second-order
factor $1/(1+2ζ jω/ω_n-(ω/ω_n)^2)$ has asymptotes 0 and −40 dB/dec, and at ω_n the exact magnitude is $1/(2ζ)$ → the error is $-20\log(2ζ)$ dB: +13.98 dB for ζ = 0.1,
0 dB for ζ = 0.5, −3.01 dB for ζ = 0.707. The resonant peak itself is at $ω_n\sqrt{1-2ζ^2}$ with height $1/(2ζ\sqrt{1-ζ^2})$.""",
    method="""Exact |H(jω)| on 20,000 points vs piecewise-linear asymptotes; the 2nd-order factor realised as a series RLC (output across C) with R set for ζ, simulated with the MNA AC analysis.""",
)


def run(p):
    w = np.logspace(-2, 2, 20001)
    H1 = 1 / (1 + 1j * w)
    asym1 = np.where(w < 1, 0, -20 * np.log10(w))
    p.compare("Simple pole: asymptote error at the corner", -3.0103, db(H1)[np.argmin(abs(w - 1))] - asym1[np.argmin(abs(w - 1))], "dB", kind="abs", tol=1e-3)
    p.compare("Simple pole: error one octave above the corner", -0.9691, np.interp(2, w, db(H1) - asym1), "dB", kind="abs", tol=1e-3)
    fig, ax = p.fig(1, 2, w=11)
    L, C = 1e-3, 1e-6; wn = 1 / np.sqrt(L * C)
    rows = []
    for z, c in zip((0.1, 0.3, 0.5, 0.707, 1.0), COLORS):
        H2 = 1 / (1 + 2j * z * w - w ** 2)
        asym2 = np.where(w < 1, 0, -40 * np.log10(w))
        err_n = db(H2)[np.argmin(abs(w - 1))]
        R = 2 * z * np.sqrt(L / C)
        ck = Circuit("rlc"); ck.V("s", "a", "0", ac=1); ck.R("r", "a", "b", R); ck.L("l", "b", "c", L); ck.C("c", "c", "0", C)
        fs = w * wn / (2 * pi)
        Hs = ck.ac(fs[::20]).v("c")
        rows.append((z, -20 * np.log10(2 * z), err_n, db(Hs)[np.argmin(abs(w[::20] - 1))]))
        ax[0].semilogx(w, db(H2), color=c, label=f"ζ = {z}"); ax[0].semilogx(w[::20], db(Hs), ".", color=c, ms=3)
        if z < 0.7:
            wr = np.sqrt(1 - 2 * z * z); pk = 1 / (2 * z * np.sqrt(1 - z * z))
            p.compare(f"ζ = {z}: resonant peak height (exact formula vs numerical max)", db(pk), db(H2).max(), "dB", kind="abs", tol=1e-3)
    ax[0].semilogx(w, np.where(w < 1, 0, -40 * np.log10(w)), "--", color="black", lw=1, label="asymptotes")
    ax[0].set_ylim(-60, 20)
    style_axes(ax[0], "ω/ωn", "|H| (dB)", "2nd-order: exact (lines), circuit simulation (dots)")
    for z, pred, meas, sim in rows:
        p.compare(f"ζ = {z}: error of the asymptote at ωn = −20 log(2ζ)", pred, meas, "dB", kind="abs", tol=1e-3)
    p.compare("Circuit simulation vs formula at ωn, worst over ζ", 0, max(abs(r[3] - r[2]) for r in rows), "dB", kind="abs", tol=0.01)
    zz = np.linspace(0.05, 1.2, 200)
    ax[1].plot(zz, -20 * np.log10(2 * zz), color=C_PRED, label="−20 log(2ζ)")
    ax[1].plot([r[0] for r in rows], [r[2] for r in rows], "o", color=C_MEAS, label="measured at ωn")
    ax[1].axhline(0, color="gray", lw=.6)
    style_axes(ax[1], "damping ratio ζ", "exact − asymptote at ωn (dB)", "How wrong the straight-line sketch is")
    p.save(fig, "bode", "Exact vs asymptotic Bode magnitude and the error of the sketch at the natural frequency.")
    p.discuss("""The famous numbers come out exactly: −3.01 dB at a simple pole's corner, −0.97 dB an octave away, and for a quadratic the sketch's error at
ω_n is −20 log(2ζ) — negligible near ζ = 0.5, disastrous for lightly damped systems (+14 dB at ζ = 0.1). The circuit simulation of an RLC with the
same ζ lands on the analytic curve, so the algebra describes a real circuit, not just a formula. Lesson: straight lines are fine for first-order
factors and well-damped pairs; for ζ < 0.3 always add the resonant peak, or the sketch will badly understate gain near ω_n — exactly where
stability margins are decided.""")
# tol-convention: relative tolerances are in percent
