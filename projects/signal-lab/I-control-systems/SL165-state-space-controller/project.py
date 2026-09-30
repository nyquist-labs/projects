from eelab import *
from eelab.control import zoh
from scipy.signal import place_poles

META = dict(
    id="SL-165", title="State-feedback pole placement for a two-mass system", level="H",
    tools="State-space model of two masses and a spring, Ackermann/pole placement (SciPy place_poles), simulation",
    summary="Place all four closed-loop poles of a flexible two-mass system (force on mass 1, position of mass 2 controlled) and "
            "verify the realised eigenvalues, the reference tracking and the suppression of the resonance.",
    problem="A flexible link rings when you move it. How does full state feedback move every pole — including the resonance — "
            "where you want it?",
    theory=r"""x = [x₁, v₁, x₂, v₂]; m₁ = m₂ = 1 kg, k = 100 N/m, light damping c = 0.2 N·s/m ⇒ a lightly damped mode at √(2k/m) ≈ 14.1 rad/s. u = −Kx + N r places
eig(A − BK) anywhere (controllable). Chosen poles: −4 ± 4j, −10 ± 10j. A pre-gain $N = -1/(C(A-BK)^{-1}B)$ gives unit steady-state gain.""",
    method="""Controllability rank checked; K from place_poles; closed-loop eigenvalues compared; 5 s step of the mass-2 position simulated with exact ZOH at 1 ms,
compared with open-loop (force step) ringing.""",
)


def run(p):
    m1 = m2 = 1.0; k = 100.0; c = 0.2
    A = np.array([[0, 1, 0, 0], [-k / m1, -c / m1, k / m1, c / m1], [0, 0, 0, 1], [k / m2, c / m2, -k / m2, -c / m2]])
    B = np.array([[0], [1 / m1], [0], [0]]); C = np.array([[0, 0, 1, 0]])
    Wc = np.hstack([np.linalg.matrix_power(A, i) @ B for i in range(4)])
    p.compare("Controllability matrix rank", 4, np.linalg.matrix_rank(Wc), "", kind="abs")
    ol = np.linalg.eigvals(A)
    p.compare("Open-loop resonance √(2k/m)", np.sqrt(2 * k / m1), np.max(np.abs(ol.imag)), "rad/s", tol=0.5)
    want = np.array([-4 + 4j, -4 - 4j, -10 + 10j, -10 - 10j])
    K = place_poles(A, B, want).gain_matrix
    got = np.sort_complex(np.linalg.eigvals(A - B @ K))
    p.compare("Max |placed − desired| eigenvalue error", 0, np.max(np.abs(got - np.sort_complex(want))), "", kind="abs")
    Acl = A - B @ K
    N = -1 / (C @ np.linalg.inv(Acl) @ B)[0, 0]
    dt = 1e-3; Ad, Bd = zoh(Acl, B * N, dt)
    x = np.zeros(4); ys = []
    for _ in range(5000):
        x = Ad @ x + Bd[:, 0] * 1.0; ys.append(x[2])
    ys = np.array(ys)
    p.compare("Steady-state tracking of mass-2 position", 1.0, ys[-1], "m", tol=0.5)
    Ao, Bo = zoh(A, B, dt); xo = np.zeros(4); yo = []
    for kk in range(5000):
        xo = Ao @ xo + Bo[:, 0] * (1.0 if kk < 200 else 0.0); yo.append(xo[2] - xo[0])
    p.metric("Open-loop spring deflection ringing after a 0.2 s push (peak)", np.max(np.abs(yo[300:])), "m")
    p.metric("State-feedback gains K", ", ".join(f"{v:.1f}" for v in K.ravel()))
    t = np.arange(5000) * dt
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, ys, color=C_MEAS, label="closed loop (mass 2)"); ax[0].axhline(1, color="gray", ls=":")
    style_axes(ax[0], "time (s)", "position (m)", "Step with pole placement")
    ax[1].plot(t, yo, color=COLORS[1], label="open loop: spring deflection after a push")
    style_axes(ax[1], "time (s)", "x₂ − x₁ (m)", "Uncontrolled resonance")
    p.save(fig, "two_mass", "State feedback damps the 14 rad/s resonance the open-loop system rings at.")
    p.discuss("""The system is fully controllable from the force on mass 1, so pole placement can put all four eigenvalues exactly where requested — including
turning the barely-damped 14 rad/s structural mode into a well-damped pair. The step reaches the target with no steady-state error thanks
to the pre-gain N. The catch is that full state feedback needs all four states; SL-167 estimates the unmeasured ones with an observer.""")
