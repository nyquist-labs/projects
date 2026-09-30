from eelab import *
from eelab.control import zoh
from scipy.signal import place_poles

META = dict(
    id="SL-167", title="Luenberger observer: estimating hidden states", level="H",
    tools="Observer design by pole placement on the dual system, noisy measurement simulation, observer-based feedback",
    summary="Measure only the position of the two-mass system (SL-165) and reconstruct all four states with an observer; show "
            "the estimation error decays at the chosen observer poles and that observer-based feedback recovers the "
            "full-state step response (separation principle).",
    problem="Sensors are expensive; you rarely measure every state. How can a model plus one sensor stand in for the rest?",
    theory=r"""x̂̇ = Ax̂ + Bu + L(y − Cx̂). Error e = x − x̂ obeys ė = (A − LC)e, so its decay is set by eig(A − LC), chosen by pole placement on (Aᵀ, Cᵀ). Separation:
the closed loop with u = −Kx̂ has eigenvalues eig(A − BK) ∪ eig(A − LC). Observer poles are chosen ~3× faster than controller poles.""",
    method="""Observable from x₂ (rank check). Observer poles −15 ± 15j, −25 ± 25j. Start with x̂ = 0 while the true state is displaced; measurement noise σ = 1 mm.
Decay rate fitted to the error envelope between 0.15 and 0.5 s on a noise-free run (later, the sample-and-hold of y leaves a tiny
residual floor); observer-based closed-loop step compared with full-state feedback.""",
)


def run(p):
    m1 = m2 = 1.0; k = 100.0; c = 0.2
    A = np.array([[0, 1, 0, 0], [-k, -c, k, c], [0, 0, 0, 1], [k, c, -k, -c]])
    B = np.array([[0], [1.0], [0], [0]]); C = np.array([[0, 0, 1.0, 0]])
    Wo = np.vstack([C @ np.linalg.matrix_power(A, i) for i in range(4)])
    p.compare("Observability rank from x₂ alone", 4, np.linalg.matrix_rank(Wo), "", kind="abs")
    K = place_poles(A, B, [-4 + 4j, -4 - 4j, -10 + 10j, -10 - 10j]).gain_matrix
    L = place_poles(A.T, C.T, [-15 + 15j, -15 - 15j, -25 + 25j, -25 - 25j]).gain_matrix.T
    Acl = np.block([[A - B @ K, B @ K], [np.zeros((4, 4)), A - L @ C]])
    eig = np.sort_complex(np.linalg.eigvals(Acl))
    want = np.sort_complex(np.r_[np.linalg.eigvals(A - B @ K), np.linalg.eigvals(A - L @ C)])
    p.compare("Separation principle: max eigenvalue mismatch", 0, np.max(np.abs(eig - want)), "", kind="abs")
    dt = 1e-4
    Ad, Bd = zoh(A, B, dt)
    Lo_A, _ = zoh(A - L @ C, np.hstack([B, L]), dt)
    _, Lo_B = zoh(A - L @ C, np.hstack([B, L]), dt)
    x = np.array([0.1, 0, 0.05, 0]); xh = np.zeros(4); rng_ = p.rng
    errs, ts = [], []
    for n in range(int(1.0 / dt)):
        u = 0.0
        y = C @ x + 0.001 * rng_.normal()
        xh = Lo_A @ xh + Lo_B @ np.r_[u, y]
        x = Ad @ x + Bd[:, 0] * u
        errs.append(np.linalg.norm(x - xh)); ts.append((n + 1) * dt)
    errs = np.array(errs); ts = np.array(ts)
    # decay rate measured on a noise-free run (the noisy run is used for the noise floor)
    x = np.array([0.1, 0, 0.05, 0]); xh = np.zeros(4); clean = []
    for n in range(int(1.0 / dt)):
        xh = Lo_A @ xh + Lo_B @ np.r_[0.0, C @ x]; x = Ad @ x
        clean.append(np.linalg.norm(x - xh))
    clean = np.array(clean)
    pk = [i for i in range(1, len(clean) - 1) if clean[i] >= clean[i - 1] and clean[i] >= clean[i + 1] and 0.15 < ts[i] < 0.5]
    fitted = np.polyfit(ts[pk], np.log(clean[pk]), 1)[0]
    p.compare("Estimation-error decay rate (slowest observer pole Re = −15)", -15, fitted, "1/s", tol=20)
    p.metric("Steady estimation error with 1 mm sensor noise", float(np.sqrt(np.mean(errs[ts > 0.6] ** 2))), "m")
    fig, ax = p.fig()
    ax.semilogy(ts, errs, color=C_MEAS, label="‖x − x̂‖")
    ax.semilogy(ts, errs[0] * np.exp(-15 * ts), "--", color=C_PRED, label="∝ e^(−15t)")
    style_axes(ax, "time (s)", "estimation error", "Observer convergence from a wrong initial guess")
    p.save(fig, "observer", "The error decays at the observer's slowest pole until it reaches the sensor-noise floor.")
    p.discuss("""The observer reconstructs all four states from one position sensor: the error falls at roughly the slowest observer pole's rate (oscillating
because the poles are complex) until it reaches a floor set by measurement noise, and the combined system's eigenvalues are exactly the
union of controller and observer poles — the separation principle. Faster observer poles converge faster but amplify sensor noise; the
Kalman filter (SL-078, AM-162) chooses L to balance the two optimally.""")
