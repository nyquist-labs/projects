from eelab import *

META = dict(
    id="AM-095", title="Particle filter vs extended Kalman filter on a nonlinear benchmark", level="H",
    tools="Bootstrap particle filter (sequential importance resampling, systematic resampling, effective sample size), extended Kalman filter, the univariate nonstationary growth model",
    summary="Estimate the state of the classic strongly nonlinear benchmark x_k = x/2 + 25x/(1+x²) + 8cos(1.2k) + w, y = x²/20 + v with an EKF and a "
            "particle filter, and show that the particle filter handles the bimodal posterior (the sign ambiguity of x²) that makes the EKF fail.",
    problem="When the measurement is x² — the sign is invisible — can any filter track x?",
    theory=r"""Bootstrap PF: propagate N particles through the dynamics, weight by p(y|x), resample when the effective sample size $N_{eff}=1/\sum w_i^2$ drops. As N → ∞ it approximates the exact posterior, bimodal or not.
The EKF linearises y = x²/20 around its estimate; near x = 0 the derivative vanishes and the filter becomes overconfident, and it cannot represent the ±x ambiguity, so it jumps to the wrong sign. Expected: PF RMSE several
times smaller than EKF over 100 steps.""",
    method="""σ_w² = 10, σ_v² = 1, 100 steps, 50 Monte-Carlo runs. PF with N = 50, 200, 1000 particles; EKF with the same noise parameters. RMSE of the posterior mean; fraction of steps with the correct sign.""",
)


def f(x, k):
    return x / 2 + 25 * x / (1 + x * x) + 8 * np.cos(1.2 * k)


def run(p):
    r = p.rng; T, Q, R = 100, 10.0, 1.0
    res = {"EKF": [], "PF 50": [], "PF 200": [], "PF 1000": []}; sign = {k: [] for k in res}; neff_all = []
    for mc in range(50):
        x = 0.1; xs, ys = [], []
        for k in range(1, T + 1):
            x = f(x, k) + r.normal(0, np.sqrt(Q)); xs.append(x); ys.append(x * x / 20 + r.normal(0, np.sqrt(R)))
        xs, ys = np.array(xs), np.array(ys)
        m, P = 0.1, 2.0; est = []
        for k in range(1, T + 1):
            F = 0.5 + 25 * (1 - m * m) / (1 + m * m) ** 2
            m = f(m, k); P = F * P * F + Q
            H = m / 10; S = H * P * H + R; K = P * H / S
            m += K * (ys[k - 1] - m * m / 20); P *= (1 - K * H); est.append(m)
        est = np.array(est); res["EKF"].append(np.sqrt(np.mean((est - xs) ** 2))); sign["EKF"].append(np.mean(np.sign(est) == np.sign(xs)))
        for N in (50, 200, 1000):
            parts = r.normal(0.1, np.sqrt(2), N); est = []; ne = []
            for k in range(1, T + 1):
                parts = f(parts, k) + r.normal(0, np.sqrt(Q), N)
                w = np.exp(-0.5 * (ys[k - 1] - parts ** 2 / 20) ** 2 / R); w /= w.sum()
                est.append(np.sum(w * parts)); ne.append(1 / np.sum(w ** 2))
                u = (r.random() + np.arange(N)) / N
                parts = parts[np.minimum(np.searchsorted(np.cumsum(w), u), N - 1)]
            est = np.array(est); res[f"PF {N}"].append(np.sqrt(np.mean((est - xs) ** 2))); sign[f"PF {N}"].append(np.mean(np.sign(est) == np.sign(xs)))
            if N == 1000:
                neff_all.append(np.mean(ne))
    rm = {k: np.mean(v) for k, v in res.items()}
    p.compare("RMSE ratio EKF / PF(1000) (my guess ≥ 3)", 3.0, rm["EKF"] / rm["PF 1000"], "×", kind="abs", tol=10)
    p.compare("PF RMSE decreases with particle count (50 → 1000; 1 = yes)", 1, int(rm["PF 50"] > rm["PF 1000"]), "", kind="abs")
    p.metric("Mean RMSE: EKF / PF 50 / PF 200 / PF 1000", " / ".join(f"{rm[k]:.2f}" for k in res))
    p.metric("Fraction of steps with the correct sign: EKF / PF 1000", f"{np.mean(sign['EKF']) * 100:.0f} % / {np.mean(sign['PF 1000']) * 100:.0f} %")
    p.metric("Average effective sample size before resampling (N = 1000)", np.mean(neff_all), "particles")
    x = 0.1; xs, ys = [], []
    for k in range(1, T + 1):
        x = f(x, k) + r.normal(0, np.sqrt(Q)); xs.append(x); ys.append(x * x / 20 + r.normal(0, 1))
    N = 1000; parts = r.normal(0.1, np.sqrt(2), N); cloud = []; pe = []; m, P = 0.1, 2.0; ee = []
    for k in range(1, T + 1):
        parts = f(parts, k) + r.normal(0, np.sqrt(Q), N); w = np.exp(-0.5 * (ys[k - 1] - parts ** 2 / 20) ** 2); w /= w.sum()
        pe.append(np.sum(w * parts)); u = (r.random() + np.arange(N)) / N; parts = parts[np.minimum(np.searchsorted(np.cumsum(w), u), N - 1)]; cloud.append(parts[:200].copy())
        F = 0.5 + 25 * (1 - m * m) / (1 + m * m) ** 2; m = f(m, k); P = F * P * F + Q; H = m / 10; K = P * H / (H * P * H + 1); m += K * (ys[k - 1] - m * m / 20); P *= (1 - K * H); ee.append(m)
    fig, ax = p.fig(1, 1, w=10, h=4.5)
    for k in range(T):
        ax.plot([k + 1] * 200, cloud[k], ",", color=COLORS[7], alpha=.5)
    ax.plot(range(1, T + 1), xs, color="black", lw=1.5, label="true x"); ax.plot(range(1, T + 1), pe, color=C_MEAS, label="PF mean (1000)"); ax.plot(range(1, T + 1), ee, "--", color=C_PRED, label="EKF")
    ax.set_ylim(-30, 30)
    style_axes(ax, "step", "x", "Particle cloud (grey) holds both signs; the EKF picks one")
    p.save(fig, "particle_filter", "True state, EKF and particle-filter estimates on the nonlinear growth model, with the particle cloud.")
    p.discuss(f"""On this benchmark the EKF's average RMSE is {rm['EKF'] / rm['PF 1000']:.1f}× that of a 1000-particle filter. The picture shows why: because y ∝ x², every measurement is
equally consistent with ±x, and the particle cloud visibly splits into two branches whenever the dynamics bring x near zero; the posterior mean
(and a sign decision) comes from their relative weights. The EKF, carrying one Gaussian linearised at its current guess, commits to a single branch
and is often on the wrong one, with a variance that claims certainty. The particle filter's accuracy improves with the number of particles, at a
cost linear in N; resampling keeps the effective sample size from collapsing to a single particle.""")
# tol-convention: relative tolerances are in percent
