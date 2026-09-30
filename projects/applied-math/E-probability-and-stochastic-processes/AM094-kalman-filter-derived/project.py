from eelab import *
from scipy.linalg import solve_discrete_are
from scipy.stats import chi2

META = dict(
    id="AM-094", title="The Kalman filter, derived and tested for consistency", level="H",
    tools="Kalman filter as the linear minimum-variance estimator (own implementation), tracking an RC circuit's state and an unknown drifting input, NEES/NIS consistency tests, innovation whiteness, steady-state Riccati gain",
    summary="Estimate the hidden states of a noisy second-order RC network from a single noisy voltage measurement, check that the filter's "
            "reported uncertainty is honest (normalised estimation error follows a χ² distribution), that innovations are white, and that the gain converges to the algebraic Riccati solution.",
    problem="A filter that outputs a number and an error bar is only useful if the error bar is right. How do you prove a Kalman filter is consistent?",
    theory=r"""For x_{k+1} = Ax_k + w, y_k = Cx_k + v: predict $P^- = APA^T + Q$, gain $K = P^-C^T(CP^-C^T+R)^{-1}$, update $P = (I-KC)P^-$ — derived by minimising E‖x − x̂‖² over linear estimators. Consistency: normalised estimation error
squared $ε = (x-\hat x)^TP^{-1}(x-\hat x)$ ~ χ²(n), innovations ν = y − Cx̂⁻ are white with variance CP⁻Cᵀ + R. P converges to the DARE solution regardless of initial P.""",
    method="""Two-node RC ladder (τ ≈ 1 ms, sampled at 10 kHz) plus a third state: the unknown input voltage modelled as a random walk. Process noise on all states, measurement noise σ = 20 mV on the output node.
100 Monte-Carlo runs × 2000 steps: average NEES vs χ² 95 % bounds, innovation autocorrelation, gain vs DARE.""",
)


def model(dt=1e-4):
    R, C = 1e3, 1e-6
    Ac = np.array([[-2 / (R * C), 1 / (R * C), 1 / (R * C)], [1 / (R * C), -1 / (R * C), 0], [0, 0, 0]])
    from scipy.linalg import expm
    A = expm(Ac * dt)
    Q = np.diag([1e-8, 1e-8, 1e-5]); Cm = np.array([[0, 1.0, 0]]); Rm = np.array([[0.02 ** 2]])
    return A, Q, Cm, Rm


def run(p):
    A, Q, Cm, Rm = model(); r = p.rng
    n, K, M = 3, 2000, 100
    nees = np.zeros(K); innov_all = []
    for mc in range(M):
        x = np.array([0.0, 0.0, 1.0]); xh = np.zeros(3); P = np.eye(3)
        nu = []
        for k in range(K):
            x = A @ x + r.multivariate_normal(np.zeros(3), Q)
            y = Cm @ x + r.normal(0, 0.02, 1)
            xh = A @ xh; P = A @ P @ A.T + Q
            S = Cm @ P @ Cm.T + Rm; Kk = P @ Cm.T @ np.linalg.inv(S)
            v = y - Cm @ xh; xh = xh + (Kk @ v); P = (np.eye(3) - Kk @ Cm) @ P
            e = x - xh; nees[k] += e @ np.linalg.solve(P, e)
            nu.append((v / np.sqrt(S[0, 0]))[0])
        innov_all.append(np.array(nu))
    nees /= M
    lo, hi = chi2.ppf(0.025, M * n) / M, chi2.ppf(0.975, M * n) / M
    frac = np.mean((nees[200:] > lo) & (nees[200:] < hi))
    p.compare("Average NEES inside the 95 % χ² band (fraction of steps after convergence)", 0.95, frac, "", kind="abs", tol=0.05)
    p.compare("Mean NEES ≈ state dimension n = 3", 3.0, nees[200:].mean(), "", tol=5)
    nu = np.concatenate([v[200:] for v in innov_all])
    ac = [np.mean(nu[:-l] * nu[l:]) for l in (1, 2, 5)]
    p.compare("Normalised innovation variance = 1", 1.0, np.var(nu), "", tol=3)
    p.compare("Innovation autocorrelation at lags 1, 2, 5 (white → 0)", 0, max(abs(a) for a in ac), "", kind="abs", tol=0.02)
    Pd = solve_discrete_are(A.T, Cm.T, Q, Rm)
    Kd = Pd @ Cm.T @ np.linalg.inv(Cm @ Pd @ Cm.T + Rm)
    P = np.eye(3) * 100
    for _ in range(3000):
        P = A @ P @ A.T + Q; S = Cm @ P @ Cm.T + Rm; Kk = P @ Cm.T @ np.linalg.inv(S); P = (np.eye(3) - Kk @ Cm) @ P
    p.compare("Converged gain vs steady-state DARE gain (max relative)", 0, np.max(np.abs(Kk - Kd) / np.abs(Kd)), "", kind="abs", tol=1e-4)
    x = np.array([0.0, 0.0, 1.0]); xh = np.zeros(3); P = np.eye(3); X, XH, Y, SD = [], [], [], []
    for k in range(3000):
        if k == 1500:
            x[2] += 0.5
        x = A @ x + r.multivariate_normal(np.zeros(3), Q); y = Cm @ x + r.normal(0, 0.02, 1)
        xh = A @ xh; P = A @ P @ A.T + Q; S = Cm @ P @ Cm.T + Rm; Kk = P @ Cm.T @ np.linalg.inv(S); xh = xh + Kk @ (y - Cm @ xh); P = (np.eye(3) - Kk @ Cm) @ P
        X.append(x.copy()); XH.append(xh.copy()); Y.append(y[0]); SD.append(np.sqrt(np.diag(P)))
    X, XH, SD = map(np.array, (X, XH, SD)); t = np.arange(3000) * 0.1
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, Y, ".", ms=1, color=COLORS[7], label="measured v2"); ax[0].plot(t, X[:, 2], color="black", label="true input"); ax[0].plot(t, XH[:, 2], color=C_MEAS, label="estimated input")
    ax[0].fill_between(t, XH[:, 2] - 2 * SD[:, 2], XH[:, 2] + 2 * SD[:, 2], color=C_MEAS, alpha=.2)
    style_axes(ax[0], "t (ms)", "V", "Estimating an unmeasured input (±2σ band)")
    ax[1].plot(nees, color=C_MEAS, lw=.8, label="average NEES (100 runs)"); ax[1].axhline(lo, color=C_PRED, ls="--", label="95 % χ² bounds"); ax[1].axhline(hi, color=C_PRED, ls="--")
    style_axes(ax[1], "step", "NEES", "Consistency: honest error bars")
    p.save(fig, "kalman", "Kalman estimate of an unmeasured input voltage with its uncertainty band, and the NEES consistency test.")
    p.discuss(f"""From one noisy node voltage the filter reconstructs all three states, including the unmeasured input voltage, and tracks its step change within
milliseconds. More importantly it is *consistent*: averaged over 100 runs the normalised estimation error squared sits inside the 95 % χ² band
{frac * 100:.0f} % of the time with mean ≈ 3 = the state dimension, and the normalised innovations have unit variance and no autocorrelation. Those checks
are what distinguish a correctly tuned filter from one that merely looks smooth — mis-set Q or R shows up immediately as NEES outside the band.
The gain converges to the discrete algebraic Riccati solution, so for time-invariant problems the steady-state gain can be precomputed.""")
# tol-convention: relative tolerances are in percent
