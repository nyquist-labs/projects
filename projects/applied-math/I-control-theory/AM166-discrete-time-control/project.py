from eelab import *
from eelab.control import zoh
from scipy import signal

META = dict(
    id="AM-166", title="Discrete-time control: ZOH models, deadbeat response and controller emulation", level="H",
    tools="Exact zero-order-hold discretisation (matrix exponential) checked against scipy.signal.cont2discrete, pole mapping z = e^{sT}, deadbeat state feedback by discrete Ackermann, inter-sample simulation of the continuous plant, forward-Euler / backward-Euler / Tustin emulation of a continuous compensator",
    summary="Model a continuous plant as seen by a computer, design a deadbeat controller that settles in exactly n samples (something no continuous "
            "linear controller can do), look between the samples, and show how the choice of discretisation rule decides whether an emulated analog controller stays stable.",
    problem="A digital controller only sees samples and only changes its output at sample instants. What is the plant from its point of view, and what can it do that an analog one cannot?",
    theory=r"""With a zero-order hold, $x_{k+1}=e^{AT}x_k+\int_0^Te^{Aτ}dτ\,B\,u_k$ exactly; poles map as $z=e^{sT}$. State feedback placing all n poles at z = 0 makes $(A_d-B_dK)^n=0$: any initial state is driven to zero in n steps (deadbeat). The required
effort grows roughly as $1/T^2$ for a double-integrator-like plant. Emulating a compensator pole s = −a: forward Euler $z=1-aT$ (unstable for $aT>2$), backward Euler $z=1/(1+aT)$ and Tustin $z=\frac{1-aT/2}{1+aT/2}$ (always stable).""",
    method="""Plant $G=\frac{1}{s(s+1)}$ (motor with inertia), T = 0.2 s. Deadbeat gain by Ackermann on (A_d, B_d); plant simulated continuously between samples (100 sub-steps). Effort scaling for T = 0.2, 0.1, 0.05. Emulation: lead compensator
$C=\frac{10(s+1)}{s+20}$ at T = 0.02…0.2 s with the three rules; stability of the discrete compensator and of the closed loop.""",
)


def ackermann_d(Ad, Bd, poles):
    n = Ad.shape[0]; C = np.hstack([np.linalg.matrix_power(Ad, k) @ Bd for k in range(n)])
    c = np.real(np.poly(poles)); phi = sum(c[k] * np.linalg.matrix_power(Ad, n - k) for k in range(n + 1))
    e = np.zeros((1, n)); e[0, -1] = 1
    return e @ np.linalg.solve(C, phi)


def run(p):
    A = np.array([[0, 1.0], [0, -1.0]]); B = np.array([[0], [1.0]]); C = np.array([[1.0, 0]]); T = 0.2
    Ad, Bd = zoh(A, B, T)
    ref = signal.cont2discrete((A, B, C, np.zeros((1, 1))), T, method="zoh")
    p.compare("Own ZOH discretisation vs scipy.signal.cont2discrete (max difference)", 0.0, float(max(np.max(np.abs(Ad - ref[0])), np.max(np.abs(Bd - ref[1])))), "", kind="abs", tol=1e-12)
    p.compare("Discrete poles = e^{sT}: second pole e^{−T}", np.exp(-T), float(np.min(np.linalg.eigvals(Ad).real)), "", tol=1e-9)
    numd, dend = signal.ss2tf(Ad, Bd, C, np.zeros((1, 1)))
    p.compare("ZOH adds a sampling zero: zero of the pulse transfer function (≈ −1 for small T; exact value from the formula)", -(1 - np.exp(-T) - T * np.exp(-T)) / (T - 1 + np.exp(-T)), float(np.roots(numd[0])[-1].real), "", tol=1e-6)
    K = ackermann_d(Ad, Bd, [0, 0])
    p.compare("Deadbeat: (A_d − B_dK)² = 0 (largest element)", 0.0, float(np.max(np.abs(np.linalg.matrix_power(Ad - Bd @ K, 2)))), "", kind="abs", tol=1e-12)
    sub = 100; As, Bs = zoh(A, B, T / sub); x = np.array([-1.0, 0.0]); ys = []; us = []; xk = []
    for k in range(8):
        u = -(K @ x)[0]; us.append(u); xk.append(x.copy())
        for _ in range(sub):
            ys.append(x[0] + 1); x = As @ x + Bs[:, 0] * u
    ys = np.array(ys); tt = np.arange(len(ys)) * T / sub
    p.compare("Deadbeat step: position error after exactly 2 samples", 0.0, abs(xk[2][0]), "", kind="abs", tol=1e-12)
    p.compare("… and no inter-sample ripple afterwards (max |y − 1| for t > 2T)", 0.0, float(np.max(np.abs(ys[tt >= 2 * T] - 1))), "", kind="abs", tol=1e-9)
    peaks = []
    for Tq in (0.2, 0.1, 0.05):
        Aq, Bq = zoh(A, B, Tq); Kq = ackermann_d(Aq, Bq, [0, 0]); peaks.append(abs((Kq @ np.array([-1.0, 0.0]))[0]))
    p.compare("Deadbeat effort: peak |u| ratio when T is halved (≈ 4× for a double-integrator-like plant)", 4.0, peaks[1] / peaks[0], "×", tol=8)
    p.metric("Peak control for a unit step, T = 0.2 / 0.1 / 0.05 s", " / ".join(f"{v:.0f}" for v in peaks), "", "settling time 2T — speed is bought with actuator effort")
    # emulation of C(s) = 10 (s + 1)/(s + 20)
    a = 20.0; res = {}
    for meth in ("euler", "backward_diff", "bilinear"):
        first_unstable_c = None; first_unstable_cl = None
        for Tq in np.arange(0.02, 0.2001, 0.002):
            cd = signal.cont2discrete(([10.0, 10.0], [1.0, a]), Tq, method=meth)
            nc, dc = cd[0][0], cd[1]
            pz = np.max(np.abs(np.roots(dc)))
            Aq, Bq = zoh(A, B, Tq); ng, dg = signal.ss2tf(Aq, Bq, C, np.zeros((1, 1)))
            cl = np.polyadd(np.polymul(dc, dg), np.polymul(nc, ng[0]))
            rho = np.max(np.abs(np.roots(cl)))
            if pz > 1 and first_unstable_c is None:
                first_unstable_c = Tq
            if rho > 1 and first_unstable_cl is None:
                first_unstable_cl = Tq
        res[meth] = (first_unstable_c, first_unstable_cl)
    p.compare("Forward Euler: compensator pole leaves the unit circle at T = 2/a", 2 / a, res["euler"][0], "s", tol=2.5)
    p.compare("Backward Euler and Tustin: compensator stable at every tested T (1 = yes)", 1, int(res["backward_diff"][0] is None and res["bilinear"][0] is None), "", kind="abs")
    p.metric("Closed loop first unstable at T (forward Euler / backward Euler / Tustin)", " / ".join("stable to 0.2 s" if res[m][1] is None else f"{res[m][1]:.3f} s" for m in ("euler", "backward_diff", "bilinear")))
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(tt, ys, color=C_MEAS, label="continuous output"); ax[0].step(np.arange(8) * T, np.array(us) / max(np.abs(us)), where="post", color=C_PRED, label="control (normalised)")
    ax[0].plot(np.arange(8) * T, [q[0] + 1 for q in xk], "o", color=COLORS[2], label="samples")
    style_axes(ax[0], "time (s)", "output / control", "Deadbeat: settled after two samples")
    Ts = np.arange(0.02, 0.2001, 0.002)
    for meth, c, lab in (("euler", COLORS[1], "forward Euler: 1 − aT"), ("backward_diff", COLORS[2], "backward Euler"), ("bilinear", C_MEAS, "Tustin")):
        ax[1].plot(Ts, [np.max(np.abs(np.roots(signal.cont2discrete(([10.0, 10.0], [1.0, a]), q, method=meth)[1]))) for q in Ts], color=c, label=lab)
    ax[1].axhline(1, color="gray", lw=.6); ax[1].axvline(2 / a, color="gray", ls=":")
    style_axes(ax[1], "sample period T (s)", "|z| of the compensator pole", "Emulating the pole s = −20")
    p.save(fig, "discrete", "Deadbeat response with inter-sample behaviour, and the magnitude of an emulated compensator pole under three discretisation rules.")
    p.discuss(f"""Seen through a sampler and hold, the plant is an exact difference equation: the matrix-exponential model matches SciPy's, its poles are
e^{{sT}}, and it acquires a 'sampling zero' near −1 that has no continuous counterpart. That exactness allows something impossible in continuous
time: with both closed-loop poles at z = 0 the error is *exactly* zero after two samples and stays zero between them. The catch is effort — the first
control move is {peaks[0]:.0f} for T = 0.2 s and quadruples each time T is halved, so deadbeat control is limited by the actuator, not by theory.
When a continuous design is simply emulated instead, the integration rule matters: forward Euler maps the compensator pole at −20 to 1 − 20T and
becomes unstable beyond T = 0.1 s, while backward Euler and Tustin map the whole left half-plane inside the unit circle and cannot fail that way.""")
# tol-convention: relative tolerances are in percent
