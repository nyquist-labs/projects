from eelab import *
from eelab.data import nasa_battery
from scipy import stats
from scipy.optimize import minimize

META = dict(
    id="AM-183", title="Forecasting battery ageing: ARIMA and state-space models with honest intervals", level="H",
    tools="Own AR fitting (Yule–Walker and least squares), random walk with drift, ARIMA(p,1,0), local-linear-trend Kalman filter with maximum-likelihood noise variances, rolling-origin evaluation, prediction-interval coverage, Ljung–Box residual test, remaining-useful-life forecasts on four real cells",
    summary="Forecast the capacity fade of NASA lithium-ion cells many cycles ahead, and evaluate the forecasts the way forecasts should be evaluated: "
            "out of sample from rolling origins, against a naive baseline, and by checking whether the '95 %' intervals actually contain the future 95 % of the time.",
    problem="A fitted curve through past capacity looks convincing. How good are forecasts made *before* the data existed, and can their uncertainty be trusted?",
    theory=r"""Random walk with drift: $c_t=c_{t-1}+δ+ε_t$; the h-step forecast is $c_t+hδ$ with variance $hσ^2$ (plus drift uncertainty $h^2σ^2/n$): intervals widen as √h. ARIMA(p,1,0) models the differences as AR(p): $Δc_t=δ+\sum φ_iΔc_{t-i}+ε_t$.
Local linear trend (state space): level and slope follow random walks, observed with noise; the Kalman filter gives forecasts and variances, and the likelihood for estimating the three noise variances. Scaled error: MASE = MAE / MAE of the
naive (last-value) forecast; < 1 beats naive. A well-specified model has white one-step residuals (Ljung–Box) and nominal interval coverage. Capacity data are not so polite: rest periods cause 'regeneration' jumps.""",
    method="""Capacity per discharge cycle of cells B0005, B0006, B0007, B0018 (NASA Ames). Rolling origins from cycle 40 onwards, horizons 1, 10, 30 cycles; parameters re-estimated at each origin on past data only. Coverage of nominal 95 % intervals pooled over
origins and cells. Remaining useful life: first cycle below 1.4 Ah (B0005). AR estimators validated on a synthetic AR(2) series.""",
    data="NASA Ames Prognostics Center of Excellence Li-ion Battery Aging Datasets (Saha & Goebel), fetched on first run.",
)


def capacity(cell):
    return np.array([float(np.ravel(c["data"]["Capacity"])[0]) for c in nasa_battery(cell) if c["type"] == "discharge"])


def ar_ls(x, pord):
    X = np.column_stack([np.ones(len(x) - pord)] + [x[pord - i - 1: len(x) - i - 1] for i in range(pord)])
    beta, *_ = np.linalg.lstsq(X, x[pord:], rcond=None); res = x[pord:] - X @ beta
    return beta, res


def yule_walker(x, pord):
    x = x - x.mean(); r = np.array([np.mean(x[: len(x) - k] * x[k:]) for k in range(pord + 1)])
    return np.linalg.solve(np.array([[r[abs(i - j)] for j in range(pord)] for i in range(pord)]), r[1:])


def fc_drift(y, h):
    d = np.diff(y); n = len(d); mu = d.mean(); s2 = d.var(ddof=1)
    return y[-1] + mu * h, np.sqrt(s2 * h + s2 * h * h / n)


def fc_arima(y, h, pord=2):
    d = np.diff(y); beta, res = ar_ls(d, pord); s2 = res.var(ddof=pord + 1); hist = list(d[-pord:]); psi = [1.0]
    for k in range(1, h):
        psi.append(sum(beta[i + 1] * psi[k - i - 1] for i in range(min(pord, k))))
    f = []
    for _ in range(h):
        nxt = beta[0] + sum(beta[i + 1] * hist[-i - 1] for i in range(pord)); f.append(nxt); hist.append(nxt)
    cpsi = np.cumsum(psi)                                       # integrate the MA(∞) weights for the level forecast
    return y[-1] + np.sum(f), np.sqrt(s2 * np.sum(cpsi ** 2))


def llt_filter(y, q):
    """Local linear trend. q = (log var obs, log var level, log var slope). Returns (neg log-lik, state, cov)."""
    R, Q = np.exp(q[0]), np.diag(np.exp(q[1:])); F = np.array([[1, 1.0], [0, 1]]); Hm = np.array([1.0, 0])
    x = np.array([y[0], y[1] - y[0]]); P = np.eye(2) * 1e-2; nll = 0.0
    for t in range(1, len(y)):
        x = F @ x; P = F @ P @ F.T + Q; S = P[0, 0] + R; v = y[t] - x[0]
        nll += 0.5 * (np.log(2 * pi * S) + v * v / S); K = P[:, 0] / S; x = x + K * v; P = P - np.outer(K, P[0])
    return nll, x, P, (R, Q, F)


def fc_llt(y, hs, q0=None):
    """Fit the noise variances by maximum likelihood once, then forecast every horizon in hs. Returns ({h: (mean, sd)}, q)."""
    q0 = np.log([1e-4, 1e-5, 1e-7]) if q0 is None else q0
    opt = minimize(lambda q: llt_filter(y, q)[0], q0, method="Nelder-Mead", options=dict(xatol=5e-2, fatol=1e-2, maxiter=90))
    _, x, P, (R, Q, F) = llt_filter(y, opt.x); out = {}
    for h in range(1, max(hs) + 1):
        x = F @ x; P = F @ P @ F.T + Q
        if h in hs:
            out[h] = (x[0], np.sqrt(P[0, 0] + R))
    return out, opt.x


def ljung_box(res, lags=10):
    n = len(res); r = res - res.mean(); ac = np.array([np.sum(r[:-k] * r[k:]) / np.sum(r * r) for k in range(1, lags + 1)])
    Qs = n * (n + 2) * np.sum(ac ** 2 / (n - np.arange(1, lags + 1)))
    return Qs, stats.chi2.sf(Qs, lags)


def run(p):
    r = p.rng
    e = r.normal(size=20000); x = np.zeros(20000)
    for t in range(2, 20000):
        x[t] = 1.2 * x[t - 1] - 0.5 * x[t - 2] + e[t]
    p.compare("Synthetic AR(2), φ₁ = 1.2: least-squares estimate", 1.2, ar_ls(x, 2)[0][1], "", tol=2)
    p.compare("Synthetic AR(2), φ₂ = −0.5: Yule–Walker estimate", -0.5, yule_walker(x, 2)[1], "", tol=4)
    rw = np.cumsum(0.3 + r.normal(size=(4000, 150)), axis=1); hit = 0
    for row in rw:
        f, s = fc_drift(row[:100], 30); hit += abs(row[129] - f) < 1.96 * s
    p.compare("Synthetic random walk with drift: coverage of the 95 % interval at h = 30 (validates the formula)", 95.0, hit / 40, "%", kind="abs", tol=1.5)
    cells = {c: capacity(c) for c in ("B0005", "B0006", "B0007", "B0018")}
    models = {"naive": lambda y, h: (y[-1], np.sqrt(np.diff(y).var(ddof=1) * h)), "drift": fc_drift, "ARIMA(2,1,0)": fc_arima, "local linear trend": None}
    HS = (1, 10, 30)
    err = {m: {h: [] for h in HS} for m in models}; cov = {m: {h: [] for h in HS} for m in models}; cov50 = {m: {h: [] for h in HS} for m in models}
    z50 = stats.norm.ppf(0.75)
    for cname, y in cells.items():
        q = None
        for t0 in range(40, len(y) - 1, 6):
            hs = [h for h in HS if t0 + h <= len(y)]
            llt, q = fc_llt(y[:t0], hs, q)
            for h in hs:
                for m in models:
                    f, s = llt[h] if m == "local linear trend" else models[m](y[:t0], h)
                    e_ = abs(y[t0 + h - 1] - f); err[m][h].append(e_); cov[m][h].append(e_ < 1.96 * s); cov50[m][h].append(e_ < z50 * s)
    mase = {m: {h: np.mean(err[m][h]) / np.mean(err["naive"][h]) for h in (1, 10, 30)} for m in models}
    cv = {m: {h: np.mean(cov[m][h]) * 100 for h in (1, 10, 30)} for m in models}
    p.compare("Drift model beats the naive forecast 30 cycles ahead (MASE < 1; 1 = yes)", 1, int(mase["drift"][30] < 1), "", kind="abs")
    p.compare("At one step ahead no model beats 'tomorrow = today' by much: best MASE at h = 1 (my expectation ≈ 1)", 1.0, min(mase[m][1] for m in models), "", tol=15)
    c50 = {m: {h: np.mean(cov50[m][h]) * 100 for h in HS} for m in models}
    p.compare("Coverage of nominal 95 % intervals on real capacity data, drift model, h = 30", 95.0, cv["drift"][30], "%", kind="abs", tol=4)
    p.compare("Coverage of nominal 50 % intervals, drift model, h = 10 (a sharper test of calibration)", 50.0, c50["drift"][10], "%", kind="abs", tol=10)
    p.compare("Coverage of nominal 50 % intervals, local linear trend, h = 10", 50.0, c50["local linear trend"][10], "%", kind="abs", tol=10)
    p.section("Rolling-origin evaluation (4 cells pooled)", "| model | MASE h=1 | MASE h=10 | MASE h=30 | 95 % interval coverage h=1 | h=10 | h=30 | 50 % interval coverage h=10 |\n|---|---|---|---|---|---|---|---|\n" + "\n".join(
        f"| {m} | {mase[m][1]:.2f} | {mase[m][10]:.2f} | {mase[m][30]:.2f} | {cv[m][1]:.0f} % | {cv[m][10]:.0f} % | {cv[m][30]:.0f} % | {c50[m][10]:.0f} % |" for m in models))
    y = cells["B0005"]; d = np.diff(y)
    Q1, p1 = ljung_box(d - d.mean()); _, res2 = ar_ls(d, 2); Q2, p2 = ljung_box(res2)
    p.metric("Ljung–Box p-value of one-step residuals: drift model / ARIMA(2,1,0)", f"{p1:.2f} / {p2:.2f}", "", "p > 0.05: no linear autocorrelation left — the residuals are 'white' but, as the kurtosis shows, far from Gaussian")
    p.metric("Kurtosis of the capacity increments (Gaussian = 3)", float(stats.kurtosis(d, fisher=False)), "", "regeneration jumps after rest periods — heavy tails")
    eol = int(np.argmax(y < 1.4)); rows = []
    for t0 in (50, 70, 90, 110):
        if t0 >= eol:
            continue
        dd = np.diff(y[:t0]); mu, s = dd.mean(), dd.std(ddof=1)
        hs = np.arange(1, 400); mean = y[t0 - 1] + mu * hs; sd = s * np.sqrt(hs + hs ** 2 / len(dd))
        est = t0 - 1 + int(hs[np.argmax(mean < 1.4)]); lo = t0 - 1 + int(hs[np.argmax(mean - 1.96 * sd < 1.4)])
        up = mean + 1.96 * sd; hi = t0 - 1 + int(hs[np.argmax(up < 1.4)]) if np.any(up < 1.4) else np.inf
        rows.append((t0, est, lo, hi))
    p.section(f"Remaining-useful-life forecasts for B0005 (actual end of life: cycle {eol})", "| forecast made at cycle | predicted EOL | 95 % interval | error (cycles) |\n|---|---|---|---|\n" + "\n".join(
        f"| {a} | {b} | {c} – {d_ if np.isfinite(d_) else '∞'} | {b - eol:+d} |" for a, b, c, d_ in rows))
    p.compare("End-of-life of B0005 lies inside the 95 % interval of every forecast (count)", len(rows), sum(c <= eol <= d_ for _, _, c, d_ in rows), "", kind="abs")
    p.compare("Forecast error shrinks as the origin approaches end of life: |error| at the last origin < at the first (1 = yes)", 1, int(abs(rows[-1][1] - eol) < abs(rows[0][1] - eol)), "", kind="abs")
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    for c, yy in cells.items():
        ax[0].plot(yy, lw=1, label=c)
    ax[0].axhline(1.4, color="gray", ls=":")
    style_axes(ax[0], "discharge cycle", "capacity (Ah)", "Four cells, with regeneration jumps")
    t0 = 70; hs = np.arange(1, 90); dd = np.diff(y[:t0]); mean = y[t0 - 1] + dd.mean() * hs; sd = dd.std(ddof=1) * np.sqrt(hs + hs ** 2 / len(dd))
    ax[1].plot(np.arange(len(y)), y, color="gray", lw=1, label="measured"); ax[1].plot(t0 - 1 + hs, mean, color=C_MEAS, label="forecast from cycle 70")
    ax[1].fill_between(t0 - 1 + hs, mean - 1.96 * sd, mean + 1.96 * sd, color=C_MEAS, alpha=.2, label="95 % interval"); ax[1].axhline(1.4, color="gray", ls=":"); ax[1].axvline(eol, color=C_PRED, ls="--", label="actual end of life")
    style_axes(ax[1], "discharge cycle", "capacity (Ah)", "B0005: forecast made 50+ cycles early")
    for m, c in zip(models, (COLORS[7], C_MEAS, C_PRED, COLORS[2])):
        ax[2].plot([1, 10, 30], [cv[m][h] for h in (1, 10, 30)], "o-", color=c, label=m)
    ax[2].axhline(95, color="k", ls=":")
    style_axes(ax[2], "forecast horizon (cycles)", "coverage of '95 %' intervals (%)", "Are the intervals honest?")
    p.save(fig, "forecast", "Capacity fade of four cells, a long-range forecast with its interval, and the empirical coverage of each model's intervals.")
    bm = min(models, key=lambda m_: mase[m_][1])
    p.discuss(f"""The estimators are right on synthetic data (AR coefficients recovered, random-walk intervals covering 95 %), so what follows is about the data.
At 30 cycles the fade trend dominates and the drift model's error is {mase['drift'][30]:.2f} of the naive one; even one cycle ahead the best model ({bm}) reaches
a MASE of {mase[bm][1]:.2f} — better than the ≈ 1 I expected, because the fade per cycle is not negligible against the cycle-to-cycle noise. The
remaining-useful-life forecasts for B0005 bracket the true end of life from every origin and tighten as it approaches. The uncertainty is where the
models fail, and not in the direction I anticipated: the nominal 95 % intervals contained the future {cv['drift'][30]:.0f} % of the time at 30 cycles, and the
nominal 50 % intervals {c50['drift'][10]:.0f} % (drift) and {c50['local linear trend'][10]:.0f} % (local linear trend) at 10 cycles — the intervals are too *wide*. The one-step
residuals pass the Ljung–Box test (p = {p1:.2f}), so nothing linear is left to model; but their kurtosis is {stats.kurtosis(d, fisher=False):.0f}. Capacity 'regenerates'
after rest periods in rare large jumps, which inflate the estimated variance: a Gaussian model then spreads that variance evenly over all cycles,
over-covering on ordinary cycles and still being surprised by a jump. A forecast is a distribution; only out-of-sample coverage at several
levels shows whether its shape, and not just its mean, deserves trust.""")
# tol-convention: relative tolerances are in percent
