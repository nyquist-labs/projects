from eelab import *
from eelab.control import zoh
from scipy import signal
from scipy.linalg import solve_discrete_lyapunov

META = dict(
    id="AM-161", title="Observer design and the separation principle", level="H",
    tools="Discrete-time Luenberger observer by duality with pole placement, combined controller–observer eigenvalues, estimation-error decay fitted from simulation, steady-state error covariance from a discrete Lyapunov equation versus Monte-Carlo with sensor noise",
    summary="Reconstruct unmeasured states from the output with a Luenberger observer, verify that the observer-based controller's poles are exactly the "
            "union of the state-feedback and observer poles, that the estimation error decays at the designed rate, and quantify the speed-versus-noise trade-off.",
    problem="State feedback needs every state, but only the position is measured. Can an estimate be used instead — and how fast should the estimator be?",
    theory=r"""Plant $x^+=Ax+Bu$, $y=Cx+v$. Observer $\hat x^+=A\hat x+Bu+L(y-C\hat x)$ gives error dynamics $e^+=(A-LC)e-Lv$, independent of u. With $u=-K\hat x$ the closed-loop matrix is block-triangular in (x, e): its eigenvalues are
eig(A − BK) ∪ eig(A − LC) — controller and observer can be designed separately. L follows from pole placement on the dual pair (Aᵀ, Cᵀ). With sensor-noise variance R the steady-state error covariance solves $Σ=(A-LC)Σ(A-LC)^T+LRL^T$:
faster observer poles ⇒ larger L ⇒ more noise passed into the estimate.""",
    method="""DC-motor position servo (states: angle, speed, current), sampled at 1 kHz by exact ZOH; only the angle is measured. Controller poles at radius ≈ 0.98; observer: two real poles at radius 0.95 / 0.85 / 0.7 (slow / medium / fast) — all faster than the plant's mechanical modes (z = 1 and 0.973) — with the third pole left next to the plant's own electrical mode (z ≈ 0.62).
Error decay from a noiseless simulation with a wrong initial estimate; noise study with σ = 1 mrad over 200 000 steps.""",
)


def run(p):
    Rm, Lm, Kt, J, bf = 1.0, 2e-3, 0.05, 1e-4, 1e-4
    A = np.array([[0, 1, 0], [0, -bf / J, Kt / J], [0, -Kt / Lm, -Rm / Lm]]); B = np.array([[0], [0], [1 / Lm]]); C = np.array([[1.0, 0, 0]])
    Ts = 1e-3; Ad, Bd = zoh(A, B, Ts)
    kp = np.array([0.98 * np.exp(1j * 0.02), 0.98 * np.exp(-1j * 0.02), 0.90])
    K = signal.place_poles(Ad, Bd, kp).gain_matrix
    rows = {}
    p_el = float(np.min(np.abs(np.linalg.eigvals(Ad))))           # the plant's own fast (electrical) mode, z ≈ 0.6
    for name, rad in (("slow", 0.95), ("medium", 0.85), ("fast", 0.7)):
        op = np.array([0.98 * p_el, rad, 0.97 * rad])
        L = signal.place_poles(Ad.T, C.T, op).gain_matrix.T
        full = np.block([[Ad - Bd @ K, Bd @ K], [np.zeros((3, 3)), Ad - L @ C]])
        ev = np.linalg.eigvals(full); want = list(np.r_[kp, op]); err = 0
        for q in ev:
            i = int(np.argmin([abs(q - w_) for w_ in want])); err = max(err, abs(q - want[i])); want.pop(i)
        rows[name] = dict(L=L, op=op, sep=err, rad=rad)
    p.compare("Separation principle: eigenvalues of the observer-based loop vs eig(A−BK) ∪ eig(A−LC) (worst distance, 3 designs)", 0.0, max(v["sep"] for v in rows.values()), "", kind="abs", tol=1e-6)
    # noiseless error decay
    for name in ("slow", "fast"):
        L = rows[name]["L"]; x = np.array([0.5, 0, 0.0]); xh = np.zeros(3); en = []
        for k in range(400):
            u = -(K @ xh)[0]; y = C @ x
            xh = Ad @ xh + Bd[:, 0] * u + L[:, 0] * (y - C @ xh)[0]; x = Ad @ x + Bd[:, 0] * u
            en.append(np.linalg.norm(x - xh))
        en = np.array(en); m = (en > 1e-9 * en[0]) & (en < 1e-4 * en[0])
        if m.sum() < 8:
            m = (en > 1e-8 * en[0]) & (np.arange(400) > 60)
        k_ = np.arange(400)[m]; slope = np.polyfit(k_, np.log(en[m]), 1)[0]
        p.compare(f"{name} observer: estimation-error decay per step = spectral radius of A − LC", rows[name]["rad"], np.exp(slope), "", tol=2)
        rows[name]["en"] = en
    r = p.rng; sig = 1e-3; N = 200_000
    for name in ("slow", "medium", "fast"):
        L = rows[name]["L"]; F = Ad - L @ C
        S = solve_discrete_lyapunov(F, L @ L.T * sig ** 2)
        e = np.zeros(3); acc = np.zeros(3); v = r.normal(0, sig, N)
        for k in range(N):
            e = F @ e - L[:, 0] * v[k]
            if k > 2000:
                acc += e * e
        var = acc / (N - 2001)
        rows[name]["pred"] = np.sqrt(np.diag(S)); rows[name]["meas"] = np.sqrt(var)
        p.compare(f"{name} observer: rms speed-estimate error from sensor noise (Lyapunov vs simulation)", np.sqrt(S[1, 1]), np.sqrt(var[1]), "rad/s", tol=6)
    p.compare("Noise amplification: fast observer's speed-estimate error is larger than the slow one's (ratio > 5; 1 = yes)", 1, int(rows["fast"]["meas"][1] / rows["slow"]["meas"][1] > 5), "", kind="abs")
    Lbad = signal.place_poles(Ad.T, C.T, np.array([0.95, 0.95 * np.exp(0.1j), 0.95 * np.exp(-0.1j)])).gain_matrix.T
    Sbad = solve_discrete_lyapunov(Ad - Lbad @ C, Lbad @ Lbad.T * sig ** 2)
    p.metric("First attempt: all three observer poles at radius 0.95 (slower than the plant's own electrical mode)", f"‖L‖ = {np.linalg.norm(Lbad):.0f}, rms speed error {np.sqrt(Sbad[1, 1]):.3f} rad/s", "",
             "slow poles but a large gain and more noise than the faster designs")
    p.metric("rms speed-estimate error, slow / medium / fast", " / ".join(f"{rows[k]['meas'][1]:.3g}" for k in ("slow", "medium", "fast")), "rad/s", "for 1 mrad rms angle noise")
    p.metric("Observer gain ‖L‖, slow / fast", f"{np.linalg.norm(rows['slow']['L']):.3g} / {np.linalg.norm(rows['fast']['L']):.3g}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(rows["slow"]["en"], color=C_PRED, label="slow (|z| = 0.95)"); ax[0].semilogy(rows["fast"]["en"], color=C_MEAS, label="fast (|z| = 0.7)")
    ax[0].set_ylim(1e-10, 10)
    style_axes(ax[0], "sample", "‖x − x̂‖", "Estimation error after a wrong initial guess")
    names = ["slow", "medium", "fast"]
    ax[1].bar(np.arange(3) - 0.2, [rows[k]["pred"][1] for k in names], 0.4, color=C_PRED, label="Lyapunov prediction")
    ax[1].bar(np.arange(3) + 0.2, [rows[k]["meas"][1] for k in names], 0.4, color=C_MEAS, label="simulated")
    ax[1].set_xticks(range(3)); ax[1].set_xticklabels(names); ax[1].set_yscale("log")
    style_axes(ax[1], "observer speed", "rms speed-estimate error (rad/s)", "Fast observers amplify sensor noise")
    p.save(fig, "observer", "Convergence of the state estimate for two observer speeds, and the noise each design lets through.")
    p.discuss(f"""The combined controller–observer loop has exactly the six eigenvalues that were designed separately — three from state feedback, three from the
observer — so estimation and control really can be designed independently. The estimation error decays at the observer's spectral radius whatever
the control input does. What separation does *not* say is how fast the observer should be: moving its dominant poles from radius 0.95 to 0.7 multiplies
the sensor noise reaching the speed estimate by {rows['fast']['meas'][1] / rows['slow']['meas'][1]:.0f}×, exactly as the Lyapunov equation predicts. A fast observer
forgets wrong initial conditions quickly but believes every noisy sample. My first set of designs taught a second lesson: I put all three observer
poles at the same radius, and the 'slow' design (0.95) turned out to need a *larger* gain and pass *more* noise than faster ones — because it
dragged the plant's naturally fast electrical mode (z ≈ 0.62) to a slower location, which costs gain just as speeding a mode up does. Observer poles
should be placed relative to the plant's own modes, not on a uniform circle. Choosing that compromise optimally, given the actual noise levels, is
the Kalman filter (AM-162).""")
# tol-convention: relative tolerances are in percent
