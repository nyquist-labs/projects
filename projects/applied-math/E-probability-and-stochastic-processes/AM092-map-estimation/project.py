from eelab import *
from scipy.stats import norm

META = dict(
    id="AM-092", title="MAP vs ML: when prior knowledge helps", level="H",
    tools="Gaussian conjugate estimation of a sensor offset, MSE formulas for ML and MAP estimators, Monte-Carlo over the prior, MAP detection with unequal priors",
    summary="Estimate a DC offset from a few noisy samples with and without a prior, derive the mean-squared error of both estimators, confirm by "
            "Monte Carlo that MAP wins when data are scarce and the prior is informative, and show the MAP threshold shift in detection.",
    problem="A calibration has only five noisy readings, but you know roughly what the answer should be. How much should that knowledge count?",
    theory=r"""x ~ N(μ_p, σ_p²), y_i = x + n_i, n ~ N(0, σ²). ML: sample mean, MSE σ²/N. MAP (= posterior mean here): $\hat x=\frac{σ_p^2\bar y+ (σ^2/N)μ_p}{σ_p^2+σ^2/N}$, MSE $=\left(\frac{N}{σ^2}+\frac1{σ_p^2}\right)^{-1}$ — always ≤ ML, and much smaller
when N is small or σ_p small. If the prior is wrong (mean off by b), MAP gains a bias and can lose. Detection with P(1) = 0.9: MAP threshold moves by $\frac{σ^2}{Δ}\ln\frac{P_0}{P_1}$.""",
    method="""σ = 1, σ_p = 0.5, N = 1…100; 20,000 Monte-Carlo trials per N with x drawn from the prior. Misspecified prior (mean off by 1σ_p). Binary detection of ±1 in σ = 1 noise with P(+1) = 0.9: error rate vs threshold.""",
)


def run(p):
    r = p.rng; sig, sp, mp = 1.0, 0.5, 2.0
    rows = []
    for N in (1, 2, 5, 10, 20, 50, 100):
        x = r.normal(mp, sp, 20000); y = x[:, None] + r.normal(0, sig, (20000, N)); yb = y.mean(1)
        ml = yb; map_ = (sp ** 2 * yb + sig ** 2 / N * mp) / (sp ** 2 + sig ** 2 / N)
        wrong = (sp ** 2 * yb + sig ** 2 / N * (mp + sp)) / (sp ** 2 + sig ** 2 / N)
        rows.append((N, np.mean((ml - x) ** 2), sig ** 2 / N, np.mean((map_ - x) ** 2), 1 / (N / sig ** 2 + 1 / sp ** 2), np.mean((wrong - x) ** 2)))
    rr = np.array(rows)
    for N_, mlm, mlp, mpm, mpp, wr in rr[[0, 2, 6]]:
        p.compare(f"N = {int(N_)}: ML MSE = σ²/N", mlp, mlm, "", tol=5)
        p.compare(f"N = {int(N_)}: MAP MSE = (N/σ² + 1/σ_p²)⁻¹", mpp, mpm, "", tol=5)
    p.metric("MSE gain of MAP over ML at N = 1 / 100", f"{rr[0, 1] / rr[0, 3]:.1f}× / {rr[-1, 1] / rr[-1, 3]:.2f}×")
    p.compare("Prior off by 1σ_p: MAP MSE at N = 5 (= MSE + bias²; still below ML here)", 1 / (5 + 4) + (sig ** 2 / 5 / (sp ** 2 + sig ** 2 / 5) * sp) ** 2, rr[2, 5], "", tol=5)
    P1 = 0.9; th_map = sig ** 2 / 2 * np.log((1 - P1) / P1)
    ths = np.linspace(-1.5, 1, 101)
    b = r.random(400000) < P1; s = np.where(b, 1.0, -1.0); y = s + r.normal(0, sig, len(s))
    err = [np.mean((y > t) != b) for t in ths]
    p.compare("MAP detection threshold with P(+1) = 0.9: (σ²/2)·ln(P0/P1)", th_map, ths[int(np.argmin(err))], "", kind="abs", tol=0.05)
    pe = lambda t: P1 * norm.cdf((t - 1) / sig) + (1 - P1) * norm.sf((t + 1) / sig)
    p.metric("Error rate: ML threshold 0 vs MAP threshold", f"{pe(0) * 100:.2f} % vs {pe(th_map) * 100:.2f} %")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(rr[:, 0], rr[:, 1], "o", color=COLORS[1], label="ML (sim)"); ax[0].loglog(rr[:, 0], rr[:, 2], "--", color=COLORS[1])
    ax[0].loglog(rr[:, 0], rr[:, 3], "s", color=C_MEAS, label="MAP (sim)"); ax[0].loglog(rr[:, 0], rr[:, 4], "--", color=C_MEAS)
    ax[0].loglog(rr[:, 0], rr[:, 5], "^", color=COLORS[2], label="MAP with wrong prior")
    style_axes(ax[0], "number of samples N", "mean-squared error", "Prior matters most when data are scarce")
    ax[1].plot(ths, np.array(err) * 100, color=C_MEAS); ax[1].axvline(th_map, color=C_PRED, ls="--", label="MAP threshold"); ax[1].axvline(0, color="gray", ls=":", label="ML threshold")
    style_axes(ax[1], "decision threshold", "error rate (%)", "Detection with unequal priors")
    p.save(fig, "map", "MSE of ML and MAP estimators vs number of samples, and the error rate of binary detection vs threshold.")
    p.discuss("""The simulations land on both closed-form MSEs. With one sample, the prior (σ_p = 0.5) is worth more than the measurement (σ = 1), and MAP's error is
five times smaller; by N = 100 the data dominate and the two estimators converge — the prior's weight falls as σ²/N shrinks. A prior that is
wrong by one standard deviation adds bias², which is still a net win at N = 5 here but would lose with more data or a more confident wrong prior —
the Bayesian bet is only as good as the prior. In detection, prior probabilities simply shift the threshold toward the rarer symbol, by
(σ²/2)ln(P₀/P₁), cutting the error rate.""")
# tol-convention: relative tolerances are in percent
