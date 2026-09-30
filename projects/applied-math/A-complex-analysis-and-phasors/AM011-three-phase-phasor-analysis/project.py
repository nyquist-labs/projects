from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-011", title="Three-phase systems with the rotation operator a = e^{j2π/3}", level="M",
    tools="Complex rotation operator, symmetrical components (Fortescue transform), nodal analysis of an unbalanced star load, time-domain verification",
    summary="Analyse balanced and unbalanced star loads with phasors and the operator a, decompose the unbalanced currents into zero-, positive- and "
            "negative-sequence parts, and confirm the neutral current and line voltages with a transient simulation.",
    problem="Why does a balanced three-phase system need no neutral wire — and what flows in it when the load is unbalanced?",
    theory=r"""Phase voltages $V, a^2V, aV$ with $a=e^{j2π/3}$, $1+a+a^2=0$. Line-to-line voltage $V_{ab}=V(1-a^2)=\sqrt3 V∠30°$. With a neutral wire, $I_N=I_a+I_b+I_c$ vanishes for a balanced load
and equals 3× the zero-sequence current $I_0=(I_a+I_b+I_c)/3$ otherwise. Fortescue: $[I_0,I_1,I_2]^T=\tfrac13[[1,1,1],[1,a,a^2],[1,a^2,a]]\,[I_a,I_b,I_c]^T$.""",
    method="""230 V rms phase voltage, 50 Hz. Balanced load 10 + j5 Ω per phase; unbalanced 10 Ω, 20 + j10 Ω, 5 − j8 Ω. Phasor predictions vs transient simulation (0.3 s, last 0.1 s used);
rms and phase of the neutral current and a line-to-line voltage measured from waveforms.""",
)


def meas(t, x, f=50.0):
    c = 2 * np.mean(x * np.cos(2 * pi * f * t)); s = 2 * np.mean(x * np.sin(2 * pi * f * t))
    return (c - 1j * s) / np.sqrt(2)          # rms phasor


def sim(Zs, f=50.0, V=230.0):
    ck = Circuit("3ph")
    names = "abc"
    for k, (nm, Z) in enumerate(zip(names, Zs)):
        ph = -2 * pi * k / 3
        ck.V(nm, nm, "0", wave=lambda t, ph=ph: np.sqrt(2) * V * np.cos(2 * pi * f * t + ph))
        ck.R(f"r{nm}", nm, f"x{nm}", Z.real)
        if Z.imag > 0:
            ck.L(f"l{nm}", f"x{nm}", "n", Z.imag / (2 * pi * f))
        elif Z.imag < 0:
            ck.C(f"c{nm}", f"x{nm}", "n", -1 / (Z.imag * 2 * pi * f))
        else:
            ck.R(f"z{nm}", f"x{nm}", "n", 1e-6)
    ck.R("neutral", "n", "0", 1e-3)
    tr = ck.tran(0.3, 1 / f / 400, method="trap")
    m = tr.t >= 0.2
    t = tr.t[m]
    IN = tr.v("n")[m] / 1e-3
    Vab = tr.v("a")[m] - tr.v("b")[m]
    Ia = (tr.v("a")[m] - tr.v("xa")[m]) / Zs[0].real
    return t, IN, Vab, Ia


def run(p):
    a = np.exp(2j * pi / 3); V = 230.0
    Vp = np.array([V, V * a ** 2, V * a])
    p.compare("1 + a + a² (should vanish)", 0, abs(1 + a + a * a), "", kind="abs", tol=1e-12)
    for label, Zs in (("balanced", [10 + 5j] * 3), ("unbalanced", [10 + 0j, 20 + 10j, 5 - 8j])):
        Zs = np.array(Zs); I = Vp / Zs; IN = I.sum()
        F = np.array([[1, 1, 1], [1, a, a * a], [1, a * a, a]]) / 3
        I012 = F @ I
        t, iN, vab, ia = sim(Zs)
        INm = meas(t, iN)
        if label == "balanced":
            p.compare("Balanced: neutral current rms (predicted 0)", 0, abs(INm), "A", kind="abs", tol=0.05)
            Vabm = meas(t, vab)
            p.compare("Line-to-line voltage magnitude = √3 × 230 V", np.sqrt(3) * V, abs(Vabm), "V", tol=0.2)
            p.compare("Line-to-line voltage V_ab leads phase a by 30°", 30.0, np.degrees(np.angle(Vabm)), "°", kind="abs", tol=0.3)
        else:
            p.compare("Unbalanced: neutral current rms, phasor sum vs simulation", abs(IN), abs(INm), "A", tol=1)
            p.compare("Neutral current = 3 × zero-sequence current", abs(3 * I012[0]), abs(IN), "A", tol=1e-07)
            p.metric("Sequence currents |I0| / |I1| / |I2|", f"{abs(I012[0]):.2f} / {abs(I012[1]):.2f} / {abs(I012[2]):.2f} A")
            Iu, I012u = I, I012
    fig, ax = p.fig(1, 2, w=11)
    for k, (z, lab) in enumerate(zip(Iu, "abc")):
        ax[0].annotate("", xy=(z.real, z.imag), xytext=(0, 0), arrowprops=dict(arrowstyle="->", lw=2, color=COLORS[k])); ax[0].text(z.real * 1.08, z.imag * 1.08, f"I_{lab}", color=COLORS[k])
    s = Iu.sum(); ax[0].annotate("", xy=(s.real, s.imag), xytext=(0, 0), arrowprops=dict(arrowstyle="->", lw=2.5, color="black")); ax[0].text(s.real * 1.1, s.imag * 1.1, "I_N")
    lim = np.abs(Iu).max() * 1.3; ax[0].set_xlim(-lim, lim); ax[0].set_ylim(-lim, lim); ax[0].set_aspect("equal")
    style_axes(ax[0], "Re (A)", "Im (A)", "Unbalanced phase currents and their sum", legend=False)
    names = ["zero", "positive", "negative"]
    ax[1].bar(names, np.abs(I012u), color=[COLORS[3], COLORS[0], COLORS[1]])
    style_axes(ax[1], None, "|I| (A)", "Symmetrical components of the unbalanced load", legend=False)
    p.save(fig, "three_phase", "Phase currents of the unbalanced load, their sum (neutral), and the Fortescue decomposition.")
    p.discuss("""With a balanced load the three current phasors are a rotated copy of each other, so their sum is (1 + a + a²)·I = 0 and the simulated
neutral carries essentially nothing — the reason long-distance transmission can omit the neutral. Unbalance breaks the symmetry: the simulated
neutral current matches the phasor sum to under 1 %, and it is exactly three times the zero-sequence component from the Fortescue transform.
The negative-sequence part is what heats three-phase motors on unbalanced supplies; symmetrical components are how protection engineers
detect such faults from measured phasors.""")
# tol-convention: relative tolerances are in percent
