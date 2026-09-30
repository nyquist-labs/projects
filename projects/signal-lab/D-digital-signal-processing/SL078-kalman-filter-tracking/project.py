from eelab import *
from scipy.linalg import solve_discrete_are

META = dict(
    id="SL-078", title="Kalman filter vs moving average", level="H",
    tools="NumPy Kalman filter, discrete algebraic Riccati equation (SciPy) for the prediction",
    summary="Track a manoeuvring 1-D target from noisy position measurements with a constant-velocity Kalman "
            "filter; predict the steady-state error from the Riccati equation and compare with the measured "
            "RMSE and with a moving average of the best length.",
    problem="How much better than simple averaging can a model-based estimator do, and can its accuracy be "
            "predicted before running it?",
    theory=r"""State $[p, v]$, $F=\begin{bmatrix}1&T\\0&1\end{bmatrix}$, white-acceleration process noise
$Q=q\begin{bmatrix}T^3/3&T^2/2\\T^2/2&T\end{bmatrix}$, measurement $H=[1\ 0]$ with variance r.
The steady-state *prior* covariance P solves the DARE $P=FPF^T-FPH^T(HPH^T+r)^{-1}HPF^T+Q$; the posterior
position variance is $P_{11}-P_{11}^2/(P_{11}+r)$ — its square root is the predicted RMSE. A moving average of
length M has noise variance r/M plus a lag bias growing with velocity and M.""",
    method="""T = 0.1 s, true motion simulated from the same model (q = 0.5 m²/s³), r = 4 m² (σ = 2 m), 20,000 steps. Kalman
RMSE vs the DARE prediction; moving averages M = 1…60, best M; also a model-mismatch run (true q ×10).""",
)


def simulate(q, r, T, n, rng_):
    F = np.array([[1, T], [0, 1]]); Q = q * np.array([[T**3 / 3, T**2 / 2], [T**2 / 2, T]])
    Lq = np.linalg.cholesky(Q)
    x = np.zeros(2); xs, zs = [], []
    for _ in range(n):
        x = F @ x + Lq @ rng_.normal(size=2)
        xs.append(x.copy()); zs.append(x[0] + np.sqrt(r) * rng_.normal())
    return np.array(xs), np.array(zs), F, Q


def kalman(z, F, Q, r):
    H = np.array([[1.0, 0.0]]); x = np.zeros(2); P = np.eye(2) * 100; out = []
    for zk in z:
        x = F @ x; P = F @ P @ F.T + Q
        S = H @ P @ H.T + r; K = P @ H.T / S
        x = x + (K * (zk - H @ x)).ravel(); P = (np.eye(2) - K @ H) @ P
        out.append(x[0])
    return np.array(out)


def run(p):
    T, q, r, n = 0.1, 0.5, 4.0, 20000
    xs, z, F, Q = simulate(q, r, T, n, p.rng)
    H = np.array([[1.0, 0.0]])
    Pp = solve_discrete_are(F.T, H.T, Q, np.array([[r]]))
    post = Pp[0, 0] - Pp[0, 0] ** 2 / (Pp[0, 0] + r)
    est = kalman(z, F, Q, r)
    rmse = np.sqrt(np.mean((est[200:] - xs[200:, 0]) ** 2))
    p.compare("Kalman position RMSE (DARE prediction)", np.sqrt(post), rmse, "m", tol=5)
    Ms = np.arange(1, 61)
    ma = []
    for M in Ms:
        k = np.ones(M) / M
        e = np.convolve(z, k, "full")[:n]
        ma.append(np.sqrt(np.mean((e[200:] - xs[200:, 0]) ** 2)))
    ma = np.array(ma)
    Mb = Ms[np.argmin(ma)]
    p.metric("Best moving-average length", Mb, "samples")
    p.metric("Accuracy gain over the best moving average", ma.min() / rmse, "×")
    p.metric("Raw measurement RMSE", np.sqrt(np.mean((z - xs[:, 0]) ** 2)), "m")
    xs2, z2, _, _ = simulate(10 * q, r, T, n, np.random.default_rng(3))
    e2 = kalman(z2, F, Q, r)
    rm2 = np.sqrt(np.mean((e2[200:] - xs2[200:, 0]) ** 2))
    Pp2 = solve_discrete_are(F.T, H.T, 10 * Q, np.array([[r]]))
    p.metric("Model mismatch (true q ×10): RMSE", rm2, "m", f"vs {np.sqrt(Pp2[0,0]-Pp2[0,0]**2/(Pp2[0,0]+r)):.2f} m if the filter knew q")
    fig, ax = p.fig(1, 2)
    k = slice(1000, 1400)
    tt = np.arange(n) * T
    ax[0].plot(tt[k], z[k], ".", color="gray", ms=3, label="measurements")
    ax[0].plot(tt[k], xs[k, 0], color="black", lw=1, label="truth")
    ax[0].plot(tt[k], est[k], color=C_MEAS, label="Kalman")
    e_ma = np.convolve(z, np.ones(Mb) / Mb, "full")[:n]
    ax[0].plot(tt[k], e_ma[k], color=COLORS[1], lw=1, label=f"moving average (M={Mb})")
    style_axes(ax[0], "time (s)", "position (m)", "Tracking a random-walk-velocity target")
    ax[1].plot(Ms, ma, color=COLORS[1], label="moving average RMSE")
    ax[1].axhline(rmse, color=C_MEAS, label="Kalman RMSE")
    ax[1].axhline(np.sqrt(post), color=C_PRED, ls="--", label="DARE prediction")
    style_axes(ax[1], "averaging length M", "RMSE (m)", "Noise-vs-lag trade-off")
    p.save(fig, "tracking", "The moving average must trade lag against noise; the Kalman filter uses the motion model to do both.")
    p.csv("ma_sweep", M=Ms, rmse_m=ma)
    p.discuss("""The Kalman filter's RMSE lands on the Riccati prediction — the filter's accuracy is known before seeing a single
measurement, one of its most useful properties for system design. The moving average must choose between
noise (short M) and lag (long M, since the target keeps moving); even at the best M it is clearly worse because
it has no notion of velocity. With the wrong process-noise model (true manoeuvres 10× stronger) the filter
still works but degrades — tuning Q is the practical art of Kalman filtering.""")
