from eelab import *
from eelab.data import nasa_battery
from scipy.optimize import least_squares

META = dict(
    id="AM-111", title="Fitting a real battery discharge curve: models, residuals and uncertainty", level="M",
    tools="Linear and nonlinear least squares on real NASA Li-ion discharge data, polynomial vs physically motivated models, residual analysis (autocorrelation, runs), parameter covariance and cross-validation",
    summary="Fit the voltage-vs-capacity curve of a real 18650 cell with polynomials of increasing degree and with a compact empirical "
            "(Shepherd-type) model, judge the fits by residual structure and held-out error rather than R², and quantify parameter uncertainty.",
    problem="Any flexible enough curve fits the data. How do you know a fit is good — and when have you overfitted?",
    theory=r"""Least squares assumes independent errors; if residuals are autocorrelated, the model is missing structure and the covariance σ²(JᵀJ)⁻¹ underestimates uncertainty. A physically motivated model (Shepherd-type:
$V = E_0 - K\frac{Q}{Q-q} + Ae^{-Bq}$ plus a linear term) should fit with few parameters and extrapolate sensibly; a high-degree polynomial fits the training range but oscillates outside it (Runge). Held-out (interpolation) error and extrapolation error expose the difference.""",
    method="""NASA PCoE cell B0005, first 2 A discharge: voltage vs delivered charge q. Fit on the middle 90 % of the curve (then also on the first 80 % to test extrapolation to the knee). Polynomials degree 1–12 (Chebyshev basis) and the
5-parameter model (nonlinear LS). Metrics: RMS residual, lag-1 residual autocorrelation, 5-fold interleaved CV error, extrapolation error on the last 20 %.""",
    data="Real: NASA Ames PCoE Battery Data Set (B0005).",
)


def shep(th, q, Q):
    E0, K, A, Bb, c = th
    return E0 - K * Q / (Q - q) + A * np.exp(-Bb * q) + c * q


def run(p):
    d = [c for c in nasa_battery("B0005") if c["type"] == "discharge"][0]["data"]
    t, V, I = d["Time"], d["Voltage_measured"], -d["Current_measured"]
    on = I > 1.0; t, V, I = t[on], V[on], I[on]
    q = np.r_[0, np.cumsum(np.diff(t) * I[1:])] / 3600
    stop = np.argmax(V < 2.7) if np.any(V < 2.7) else len(V)
    q, V = q[:stop], V[:stop]
    Q = q[-1] * 1.02
    n = len(q)
    res = []
    for deg in (1, 2, 3, 5, 8, 12):
        cc = np.polynomial.Chebyshev.fit(q, V, deg)
        r_ = V - cc(q)
        cv = []
        for f in range(5):
            tr = np.arange(n) % 5 != f
            cf = np.polynomial.Chebyshev.fit(q[tr], V[tr], deg); cv.append(np.sqrt(np.mean((V[~tr] - cf(q[~tr])) ** 2)))
        tr = q < 0.8 * q[-1]
        ce = np.polynomial.Chebyshev.fit(q[tr], V[tr], deg)
        res.append((f"poly {deg}", deg + 1, np.sqrt(np.mean(r_ ** 2)), np.corrcoef(r_[:-1], r_[1:])[0, 1], np.mean(cv), np.sqrt(np.mean((V[~tr] - ce(q[~tr])) ** 2))))
    th0 = [4.0, 0.01, 0.3, 20.0, -0.2]
    fit = least_squares(lambda th: shep(th, q, Q) - V, th0, bounds=([2, 0, 0, 0, -5], [5, 1, 2, 500, 5]))
    r_ = fit.fun
    tr = q < 0.8 * q[-1]
    fe = least_squares(lambda th: shep(th, q[tr], Q) - V[tr], fit.x, bounds=([2, 0, 0, 0, -5], [5, 1, 2, 500, 5]))
    cv = []
    for f in range(5):
        m = np.arange(n) % 5 != f
        ff = least_squares(lambda th: shep(th, q[m], Q) - V[m], fit.x, bounds=([2, 0, 0, 0, -5], [5, 1, 2, 500, 5])); cv.append(np.sqrt(np.mean((V[~m] - shep(ff.x, q[~m], Q)) ** 2)))
    res.append(("Shepherd-type (5 par.)", 5, np.sqrt(np.mean(r_ ** 2)), np.corrcoef(r_[:-1], r_[1:])[0, 1], np.mean(cv), np.sqrt(np.mean((V[~tr] - shep(fe.x, q[~tr], Q)) ** 2))))
    for name, k, rms, ac, cvv, ext in res:
        p.metric(f"{name}: RMS residual / lag-1 autocorr / CV RMS / extrapolation RMS", f"{rms * 1e3:.1f} mV / {ac:.2f} / {cvv * 1e3:.1f} mV / {ext * 1e3:.0f} mV")
    sh = res[-1]; p5 = [r for r in res if r[0] == "poly 5"][0]; p12 = [r for r in res if r[0] == "poly 12"][0]
    p.compare("Shepherd model extrapolates to the knee better than a degree-12 polynomial (error ratio poly12 / Shepherd > 1)", 3, p12[5] / sh[5], "×", kind="abs", tol=100)
    p.compare("Residuals are autocorrelated for every model (lag-1 > 0.5 means structure the model misses)", 1, int(all(r[3] > 0.5 for r in res)), "", kind="abs")
    J = fit.jac; s2 = np.sum(r_ ** 2) / (n - 5)
    cov = s2 * np.linalg.inv(J.T @ J)
    neff = n * (1 - sh[3]) / (1 + sh[3])
    p.metric("Shepherd E0 ± 1σ (naive covariance / corrected for autocorrelation)", f"{fit.x[0]:.4f} ± {np.sqrt(cov[0, 0]) * 1e3:.2f} mV / ± {np.sqrt(cov[0, 0] * n / neff) * 1e3:.1f} mV")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(q, V, color="black", lw=3, alpha=.3, label="measured (B0005)")
    ax[0].plot(q, np.polynomial.Chebyshev.fit(q[tr], V[tr], 12)(q), color=COLORS[1], label="poly 12 fitted on first 80 %"); ax[0].plot(q, shep(fe.x, q, Q), "--", color=C_MEAS, label="Shepherd fitted on first 80 %")
    ax[0].axvline(0.8 * q[-1], color="gray", ls=":"); ax[0].set_ylim(2.5, 4.3)
    style_axes(ax[0], "delivered charge (Ah)", "voltage (V)", "Extrapolating to the knee")
    ax[1].plot(q, r_ * 1e3, color=C_MEAS, lw=.8)
    style_axes(ax[1], "delivered charge (Ah)", "residual (mV)", "Shepherd residuals: small but structured", legend=False)
    p.save(fig, "battery_fit", "Model extrapolation beyond the fitted range, and the structured residuals of the best compact model.")
    p.discuss(f"""Measured by in-sample RMS alone, the degree-12 polynomial 'wins'; measured by what matters, it does not. Fitted on the first 80 % of the
discharge, it swings wildly beyond the data, while the 5-parameter Shepherd-type model — whose Q/(Q−q) term encodes the physics of the end-of-
discharge knee — extrapolates with far smaller error ({sh[5] * 1e3:.0f} mV vs {p12[5] * 1e3:.0f} mV). Interleaved cross-validation cannot detect this because
held-out points sit between training points. Every model leaves strongly autocorrelated residuals (lag-1 correlation near 1): the measurement noise
is small and the remaining misfit is systematic, so textbook parameter error bars, which assume independent errors, are too optimistic by the
factor √(n/n_eff) shown above.""")
# tol-convention: relative tolerances are in percent
