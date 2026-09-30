from eelab import *
from eelab.circuit import Circuit
from scipy import signal

META = dict(
    id="AM-049", title="State-variable formulation of circuits", level="M",
    tools="Systematic state equations from capacitor voltages and inductor currents (KCL/KVL on a normal tree), state matrix eigenvalues, comparison with MNA AC/transient simulation",
    summary="Convert a 5th-order LC ladder low-pass into first-order state equations by hand-derivable rules, show that the state matrix's "
            "eigenvalues are the transfer-function poles, and check the state-space model against the circuit simulator in time and frequency.",
    problem="How does a circuit become ẋ = Ax + Bu — and is that model identical to what a simulator computes?",
    theory=r"""Pick states = capacitor voltages and inductor currents (a normal tree puts all C in the tree, all L in the co-tree). Each capacitor current follows from KCL at its node, each inductor
voltage from KVL around its loop, giving $\dot x=Ax+Bu$, $y=Cx$. Then $H(s)=C(sI-A)^{-1}B$ and the poles of H are eig(A). For a doubly terminated 5th-order Butterworth ladder
(R_s = R_L = 1 Ω, normalised values 0.618, 1.618, 2, 1.618, 0.618) the poles should lie on the unit circle.""",
    method="""Ladder: R_s – C1 – L2 – C3 – L4 – C5 – R_L, scaled to 1 kHz / 50 Ω. A built by the rules; eig(A) vs Butterworth poles; Bode from the state model vs MNA AC; step response from
the state model vs MNA transient.""",
)


def run(p):
    g = [0.618, 1.618, 2.0, 1.618, 0.618]
    R0, w0 = 50.0, 2 * pi * 1e3
    C1, C3, C5 = g[0] / (R0 * w0), g[2] / (R0 * w0), g[4] / (R0 * w0)
    L2, L4 = g[1] * R0 / w0, g[3] * R0 / w0
    Rs = Rl = R0
    # states: v1, i2, v3, i4, v5
    A = np.array([
        [-1 / (Rs * C1), -1 / C1, 0, 0, 0],
        [1 / L2, 0, -1 / L2, 0, 0],
        [0, 1 / C3, 0, -1 / C3, 0],
        [0, 0, 1 / L4, 0, -1 / L4],
        [0, 0, 0, 1 / C5, -1 / (Rl * C5)],
    ])
    B = np.array([1 / (Rs * C1), 0, 0, 0, 0])[:, None]; Cm = np.array([[0, 0, 0, 0, 1.0]])
    ev = np.linalg.eigvals(A)
    pb = signal.butter(5, w0, analog=True, output="zpk")[1]
    p.compare("eig(A) vs 5th-order Butterworth poles (max relative distance)", 0, max(np.min(np.abs(ev - q)) / w0 for q in pb), "", kind="abs", tol=5e-3)
    ck = Circuit("ladder"); ck.V("s", "in", "0", ac=1.0, dc=1.0); ck.R("s", "in", "n1", Rs); ck.C("1", "n1", "0", C1); ck.L("2", "n1", "n3", L2)
    ck.C("3", "n3", "0", C3); ck.L("4", "n3", "n5", L4); ck.C("5", "n5", "0", C5); ck.R("l", "n5", "0", Rl)
    f = np.logspace(1, 5, 800); s = 2j * pi * f
    Hss = np.array([(Cm @ np.linalg.solve(si * np.eye(5) - A, B))[0, 0] for si in s])
    Hmna = ck.ac(f).v("n5")
    p.compare("Frequency response: state model vs MNA (max |ΔH|)", 0, np.max(np.abs(Hss - Hmna)), "", kind="abs", tol=1e-9)
    p.compare("DC gain = R_L/(R_s+R_L)", 0.5, abs(Hss[0]), "", tol=0.1)
    t = np.linspace(0, 5e-3, 5001)
    _, ys, _ = signal.lsim((A, B, Cm, np.zeros((1, 1))), np.ones_like(t), t)
    ck2 = Circuit("ladder"); ck2.V("s", "in", "0", dc=1.0); ck2.R("s", "in", "n1", Rs); ck2.C("1", "n1", "0", C1); ck2.L("2", "n1", "n3", L2)
    ck2.C("3", "n3", "0", C3); ck2.L("4", "n3", "n5", L4); ck2.C("5", "n5", "0", C5); ck2.R("l", "n5", "0", Rl)
    tr = ck2.tran(5e-3, 1e-6, method="trap", ic={"n1": 0, "n3": 0, "n5": 0, "I(2)": 0, "I(4)": 0})
    p.compare("Step response: state model vs MNA transient (max difference)", 0, np.max(np.abs(np.interp(tr.t, t, ys) - tr.v("n5"))), "V", kind="abs", tol=1e-3)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    th = np.linspace(pi / 2, 3 * pi / 2, 100)
    ax[0].plot(np.cos(th), np.sin(th), ":", color="gray"); ax[0].plot(ev.real / w0, ev.imag / w0, "x", color=C_MEAS, ms=10, mew=2, label="eig(A)")
    ax[0].plot(pb.real / w0, pb.imag / w0, "o", mfc="none", color=C_PRED, ms=12, label="Butterworth poles"); ax[0].set_aspect("equal")
    style_axes(ax[0], "Re s / ω0", "Im s / ω0", "State-matrix eigenvalues")
    ax[1].semilogx(f, db(Hss), color=C_MEAS, lw=3, alpha=.5, label="state model"); ax[1].semilogx(f, db(Hmna), "--", color=C_PRED, label="MNA")
    style_axes(ax[1], "frequency (Hz)", "|H| (dB)", "Frequency response")
    ax[2].plot(t * 1e3, ys, color=C_MEAS, lw=3, alpha=.5, label="state model"); ax[2].plot(tr.t * 1e3, tr.v("n5"), "--", color=C_PRED, label="MNA transient")
    style_axes(ax[2], "t (ms)", "v_out (V)", "Step response")
    p.save(fig, "state_space", "Eigenvalues of the hand-built state matrix, and agreement of the state model with the circuit simulator.")
    p.discuss("""Built only from KCL at the three capacitor nodes and KVL around the two inductor loops, the 5×5 state matrix has eigenvalues on the unit circle at
the Butterworth angles (to the 3-digit precision of the tabulated element values), and its frequency and step responses coincide with the
independent nodal simulation. The state form is what makes the rest of control and numerical analysis applicable to circuits: stability is
eig(A), transient simulation is an ODE solve, and reduced-order models (AM-079) are projections of A. MNA is more convenient for large, arbitrary
netlists — it does not require choosing a tree — but for a ladder the two are the same system of equations written in different coordinates.""")
# tol-convention: relative tolerances are in percent
