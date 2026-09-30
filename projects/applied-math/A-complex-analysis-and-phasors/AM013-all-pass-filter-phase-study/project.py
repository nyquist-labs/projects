from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-013", title="All-pass filters: unity magnitude, useful phase", level="M",
    tools="Pole-zero mirroring, analytic phase and group delay, op-amp all-pass circuit simulated with the MNA solver",
    summary="Show that mirroring every pole into a zero across the jω axis gives |H| = 1 at all frequencies, derive the phase and group delay "
            "of first- and second-order sections, and verify them on a simulated op-amp all-pass circuit.",
    problem="How can a filter change a signal without changing any frequency's amplitude — and what is that good for?",
    theory=r"""$H(s)=\frac{a-s}{a+s}$: for s = jω numerator and denominator are complex conjugates' mirror images, so |H| = 1 exactly; phase $-2\arctan(ω/a)$, group delay $τ=\frac{2a}{a^2+ω^2}$
(2/a at DC). The op-amp realisation (R, R on the inverting path; R_1, C on the non-inverting input) has $a = 1/(R_1C)$. Second order: $\frac{s^2-(ω_0/Q)s+ω_0^2}{s^2+(ω_0/Q)s+ω_0^2}$,
phase −2π total, delay peaking at ω0 with $τ(ω_0)=4Q/ω_0$.""",
    method="""First-order op-amp all-pass: R = 10 kΩ (gain resistors), R1 = 15.9 kΩ, C = 10 nF (a = 2π·1 kHz); AC analysis with op-amp A0 = 10⁶, GBW = 100 MHz. Group delay by numerical differentiation
of the unwrapped phase. Second-order section evaluated analytically and numerically.""",
)


def run(p):
    R, R1, C = 10e3, 15.9155e3, 10e-9
    a = 1 / (R1 * C)
    ck = Circuit("ap")
    ck.V("s", "in", "0", ac=1); ck.R("i", "in", "m", R); ck.R("f", "m", "out", R); ck.R("1", "in", "p", R1); ck.C("1", "p", "0", C)
    ck.OPAMP("U", "p", "m", "out", A0=1e6, GBW=100e6)
    f = np.logspace(1, 5, 4000); w = 2 * pi * f
    H = ck.ac(f).v("out")
    p.compare("Max deviation of |H| from 1 (0 dB) over 10 Hz–100 kHz", 0, np.max(np.abs(db(H))), "dB", kind="abs", tol=0.01)
    ph = np.unwrap(np.angle(H))
    p.compare("Phase at ω = a (−90°)", -90.0, np.degrees(np.interp(a, w, ph)), "°", kind="abs", tol=0.5)
    tau = -np.gradient(ph, w)
    p.compare("Group delay at DC = 2/a", 2 / a, tau[0], "s", tol=1)
    p.compare("Group delay at ω = a = 1/a", 1 / a, np.interp(a, w, tau), "s", tol=1)
    w0, Q = 2 * pi * 1e3, 2.0
    s = 1j * w
    H2 = (s * s - w0 / Q * s + w0 ** 2) / (s * s + w0 / Q * s + w0 ** 2)
    tau2 = -np.gradient(np.unwrap(np.angle(H2)), w)
    p.compare("2nd order: peak group delay at ω0 = 4Q/ω0", 4 * Q / w0, np.interp(w0, w, tau2), "s", tol=1)
    p.compare("2nd order: total phase change over the band (−360°)", -360.0, np.degrees(np.unwrap(np.angle(H2))[-1] - np.unwrap(np.angle(H2))[0]), "°", kind="abs", tol=5)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    ax[0].semilogx(f, db(H), color=C_MEAS); ax[0].set_ylim(-1, 1)
    style_axes(ax[0], "frequency (Hz)", "|H| (dB)", "Op-amp all-pass: flat magnitude", legend=False)
    ax[1].semilogx(f, np.degrees(ph), color=C_MEAS, label="simulated"); ax[1].semilogx(f, -2 * np.degrees(np.arctan(w / a)), "--", color=C_PRED, label="−2 arctan(ω/a)")
    style_axes(ax[1], "frequency (Hz)", "phase (°)", "Phase")
    ax[2].semilogx(f, tau * 1e6, color=C_MEAS, label="1st order (sim)"); ax[2].semilogx(f, tau2 * 1e6, color=COLORS[2], label="2nd order, Q = 2")
    ax[2].semilogx(f, 2 * a / (a * a + w * w) * 1e6, "--", color=C_PRED, label="2a/(a²+ω²)")
    style_axes(ax[2], "frequency (Hz)", "group delay (µs)", "Group delay")
    p.save(fig, "allpass", "The simulated all-pass keeps |H| = 1 while its phase and group delay follow the pole-zero geometry.")
    p.discuss("""The simulated circuit is flat to a few thousandths of a dB across four decades, while its phase sweeps from 0 to −180° and its group delay follows
2a/(a²+ω²): the mirrored zero cancels the pole's effect on magnitude but doubles its effect on phase. That is exactly what all-pass sections are for —
equalising the group delay of a sharp filter, building phasers and 90° networks for SSB — none of which touch the amplitude spectrum. The tiny
residual magnitude error comes from the finite op-amp gain and gain-bandwidth, which slightly unbalance the mirror at high frequency.""")
# tol-convention: relative tolerances are in percent
