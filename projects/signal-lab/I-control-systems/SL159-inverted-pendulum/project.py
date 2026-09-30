from eelab import *
from eelab.control import zoh
from scipy.linalg import solve_continuous_are
from scipy.integrate import solve_ivp

META = dict(
    id="SL-159", title="Inverted pendulum on a cart: LQR stabilisation", level="H",
    tools="Nonlinear cart-pole equations (SciPy ODE), linearisation, LQR (continuous ARE), animation frames",
    summary="Linearise the cart-pole, design an LQR controller, and test it on the full nonlinear model: verify the closed-loop "
            "eigenvalues, the predicted cost, and find the largest initial angle it can recover from.",
    problem="Balancing a broomstick is the classic hard control problem. Does a controller designed on a linear model work on "
            "the real nonlinear dynamics, and how far can it be pushed?",
    theory=r"""Cart mass M = 1 kg, pole m = 0.2 kg (point mass at ℓ = 0.5 m). Linearised about upright: $\dot x=Ax+Bu$ with an unstable pole at $+\sqrt{g(M+m)/(M\ell)}$ ≈ 4.8 s⁻¹.
LQR minimises $J=\int x^TQx+u^TRu$: $K=R^{-1}B^TP$ where P solves the ARE; the optimal cost from $x_0$ is $x_0^TPx_0$.""",
    method="""Q = diag(10, 1, 100, 1), R = 0.1. Nonlinear simulation (RK45, 5 s) from θ₀ = 10°; cost integrated and compared with x₀ᵀPx₀; recovery tested for θ₀ up to
60° with the force saturated at ±40 N.""",
)

g, M, m, l = 9.81, 1.0, 0.2, 0.5


def f(t, s, K, umax=np.inf):
    x, xd, th, thd = s
    u = float(np.clip(-K @ s, -umax, umax))
    sn, cs = np.sin(th), np.cos(th)
    den = M + m * sn * sn
    xdd = (u + m * sn * (l * thd * thd - g * cs)) / den
    thdd = (-u * cs - m * l * thd * thd * sn * cs + (M + m) * g * sn) / (l * den)
    return [xd, xdd, thd, thdd]


def run(p):
    A = np.array([[0, 1, 0, 0], [0, 0, -m * g / M, 0], [0, 0, 0, 1], [0, 0, (M + m) * g / (M * l), 0]])
    B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
    Q = np.diag([10, 1, 100, 1.0]); R = np.array([[0.1]])
    P = solve_continuous_are(A, B, Q, R)
    K = (np.linalg.inv(R) @ B.T @ P).ravel()
    ev_ol = np.linalg.eigvals(A)
    p.compare("Unstable open-loop pole √(g(M+m)/(Mℓ))", np.sqrt(g * (M + m) / (M * l)), ev_ol.real.max(), "1/s", tol=0.5)
    ev = np.linalg.eigvals(A - B @ K[None, :])
    p.compare("All closed-loop poles in the left half-plane (max real part < 0)", 1, int(ev.real.max() < 0), "", kind="abs")
    p.metric("LQR gains K", ", ".join(f"{k:.2f}" for k in K))
    x0 = np.array([0, 0, np.radians(10), 0])
    sol = solve_ivp(f, (0, 8), x0, args=(K,), max_step=0.002, dense_output=True)
    ts = np.linspace(0, 8, 4001); S = sol.sol(ts)
    u = -(K @ S)
    J = np.trapezoid(np.einsum("ij,ik,kj->j", S, Q, S) + 0.1 * u * u, ts)
    p.compare("Cost from θ₀ = 10° (nonlinear sim vs x₀ᵀPx₀)", x0 @ P @ x0, J, "", tol=5)
    ok = []
    angles = np.arange(5, 65, 5)
    for a in angles:
        s = solve_ivp(f, (0, 8), [0, 0, np.radians(a), 0], args=(K, 40.0), max_step=0.002)
        ok.append(abs(s.y[2, -1]) < 0.02 and np.all(np.abs(s.y[2]) < pi / 2))
    maxang = angles[np.array(ok)].max() if any(ok) else 0
    p.metric("Largest recoverable initial angle (|F| ≤ 40 N)", maxang, "°")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(ts, np.degrees(S[2]), color=C_MEAS, label="pole angle (°)"); ax[0].plot(ts, S[0] * 100, color=COLORS[1], label="cart position (cm)")
    style_axes(ax[0], "time (s)", "", "Recovery from 10° (nonlinear model)")
    for k, tt in enumerate(np.linspace(0, 2, 9)):
        s = sol.sol(tt); x, th = s[0], s[2]
        ax[1].plot([x - 0.15, x + 0.15], [0, 0], color="gray", lw=4)
        ax[1].plot([x, x + l * np.sin(th)], [0, l * np.cos(th)], color=plt_c(k), lw=2)
    ax[1].set_aspect("equal"); ax[1].set_title("snapshots t = 0 … 2 s", loc="left", fontsize=10); ax[1].set_ylim(-0.1, 0.6)
    p.save(fig, "pendulum", "The cart first moves toward the fall to get under the pole, then returns to the origin.")
    p.csv("response", t_s=ts, x_m=S[0], theta_rad=S[2], force_N=u)
    p.discuss("""The LQR gains computed from the linear model stabilise the full nonlinear dynamics, and from 10° the realised cost equals x₀ᵀPx₀ within a few
percent — the linearisation is excellent at small angles. The characteristic 'non-minimum-phase' motion is visible: to catch a pole falling
right, the cart must first accelerate right, underneath it. Larger initial angles eventually fail because of the ±40 N force limit and the
growing nonlinearity, which the linear design does not know about.""")


def plt_c(k):
    return COLORS[k % 8]
