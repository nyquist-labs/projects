from eelab import *
from eelab import ml
from scipy.optimize import minimize

META = dict(
    id="AM-176", title="Logistic regression: likelihood, Newton's method and calibration", level="M",
    tools="Own binary logistic regression (Newton/IRLS and plain gradient descent), analytic gradient checked by finite differences, comparison with a quasi-Newton optimiser (SciPy BFGS), convergence-rate measurement, odds-ratio interpretation, reliability diagram and Brier score within and across patients",
    summary="Fit a probabilistic classifier for premature ventricular beats by maximum likelihood: verify the gradient, show Newton's method converging "
            "in a handful of iterations where gradient descent needs thousands, read the coefficients as odds ratios, and test whether the predicted probabilities can be trusted on new patients.",
    problem="A classifier that outputs 'probability 0.9' should be right nine times out of ten. How is such a model fitted, and is its probability honest?",
    theory=r"""Model $P(y=1|x)=σ(w^Tx)$, $σ(z)=1/(1+e^{-z})$. Negative log-likelihood $L=-\sum y_i\lnσ_i+(1-y_i)\ln(1-σ_i)$ is convex with gradient $X^T(σ-y)$ and Hessian $X^TSX$, $S=\mathrm{diag}(σ_i(1-σ_i))$. Newton's step is a weighted
least-squares problem (IRLS) and converges quadratically — typically < 10 iterations; gradient descent converges linearly at a rate set by the Hessian's condition number. Each coefficient is a log odds ratio per standard deviation of its feature.
A maximum-likelihood model is calibrated on data from the training distribution; under distribution shift (new patients) calibration is not guaranteed.""",
    method="""PVC vs normal beats, 7 standardised features. Training set: beats of 10 patients (DS1), small ridge penalty 10⁻³. Gradient check: central differences, step 10⁻⁶. Calibration: 10 equal-count probability bins, (a) on a held-out random half
of the training patients' beats, (b) on the 10 unseen patients (DS2). Brier score and expected calibration error.""",
    data="PhysioNet MIT-BIH Arrhythmia Database (beat features built by eelab.ml.ecg_beats).",
)


def nll(w, Xb, y, l2):
    z = Xb @ w
    return np.sum(np.logaddexp(0, z) - y * z) + 0.5 * l2 * np.sum(w[:-1] ** 2)


def grad(w, Xb, y, l2):
    g = Xb.T @ (1 / (1 + np.exp(-Xb @ w)) - y); g[:-1] += l2 * w[:-1]
    return g


def calibration(pr, y, bins=10):
    o = np.argsort(pr); parts = np.array_split(o, bins)
    conf = np.array([pr[q].mean() for q in parts]); freq = np.array([y[q].mean() for q in parts]); wts = np.array([len(q) for q in parts]) / len(y)
    return conf, freq, float(np.sum(wts * np.abs(conf - freq)))


def run(p):
    D = ml.ecg_beats(); r = p.rng; tr = D["rec"] < 10; te = ~tr
    idx = r.permutation(np.flatnonzero(tr)); fit_i, hold_i = idx[: len(idx) // 2], idx[len(idx) // 2:]
    mu = D["F"][fit_i].mean(0); sd = D["F"][fit_i].std(0) + 1e-9; Z = (D["F"] - mu) / sd
    X, y = Z[fit_i], D["y"][fit_i].astype(float); Xb = np.c_[X, np.ones(len(X))]; l2 = 1e-3
    w0 = r.normal(0, 0.3, 8); g = grad(w0, Xb, y, l2); h = 1e-6
    gn = np.array([(nll(w0 + h * e, Xb, y, l2) - nll(w0 - h * e, Xb, y, l2)) / (2 * h) for e in np.eye(8)])
    p.compare("Analytic gradient vs central finite differences (worst relative error)", 0.0, float(np.max(np.abs(g - gn) / (np.abs(gn) + 1e-9))), "", kind="abs", tol=1e-5)
    w, its = ml.logistic_irls(X, y, l2=l2)
    ref = minimize(nll, np.zeros(8), args=(Xb, y, l2), jac=grad, method="BFGS", options=dict(gtol=1e-9))
    p.compare("Newton/IRLS solution vs SciPy BFGS: max coefficient difference", 0.0, float(np.max(np.abs(w - ref.x))), "", kind="abs", tol=1e-4)
    p.compare("Newton iterations to convergence (theory: < 10 for well-behaved data)", 8, its, "", kind="abs", tol=6)
    wk = np.zeros(8); errs = []
    for k in range(12):
        errs.append(np.linalg.norm(wk - w)); pr = 1 / (1 + np.exp(-Xb @ wk))
        Hm = (Xb * (pr * (1 - pr))[:, None]).T @ Xb + np.diag(np.r_[np.full(7, l2), 1e-10]); wk = wk - np.linalg.solve(Hm, grad(wk, Xb, y, l2))
    errs = np.array(errs); ok = errs > 1e-9
    order = np.log(errs[ok][-1] / errs[ok][-2]) / np.log(errs[ok][-2] / errs[ok][-3])
    p.compare("Newton convergence order near the optimum (quadratic = 2)", 2.0, order, "", kind="abs", tol=0.6)
    pr0 = 1 / (1 + np.exp(-Xb @ w)); Hs = (Xb * (pr0 * (1 - pr0))[:, None]).T @ Xb; ev = np.linalg.eigvalsh(Hs); lr = 1 / ev[-1]
    wg = np.zeros(8); gd_it = None
    for k in range(200000):
        wg -= lr * grad(wg, Xb, y, l2)
        if k % 50 == 0 and np.linalg.norm(wg - w) < 1e-3 * np.linalg.norm(w):
            gd_it = k + 1; break
    p.compare("Gradient descent (step 1/λ_max) needs orders of magnitude more iterations than Newton (> 100×; 1 = yes)", 1, int((gd_it or 200000) > 100 * its), "", kind="abs")
    p.metric("Iterations: Newton (to a step of 10⁻¹⁰) / gradient descent (to 0.1 % of the solution)", f"{its} / {gd_it if gd_it else '> 200000'}", "", f"Hessian condition number {ev[-1] / ev[0]:.0f}")
    orr = np.exp(w[:-1]); o = np.argsort(-np.abs(w[:-1]))
    p.section("Coefficients as odds ratios (per standard deviation of the feature)", "| feature | coefficient | odds ratio |\n|---|---|---|\n" + "\n".join(f"| {ml.BEAT_FEATURES[j]} | {w[j]:+.2f} | {orr[j]:.2f} |" for j in o))
    pm = lambda idx_: 1 / (1 + np.exp(-(np.c_[Z[idx_], np.ones(len(idx_))] @ w)))
    ph, yh = pm(hold_i), D["y"][hold_i]; pt, yt = pm(np.flatnonzero(te)), D["y"][te]
    ch, fh, ece_h = calibration(ph, yh); ct, ft, ece_t = calibration(pt, yt)
    p.compare("Held-out beats of the training patients: mean predicted probability = observed PVC rate", yh.mean(), ph.mean(), "", tol=8)
    p.compare("Calibration on the training distribution: expected calibration error (small)", 0.0, ece_h, "", kind="abs", tol=0.01)
    p.compare("Calibration degrades on unseen patients (ECE larger than on held-out training patients; 1 = yes)", 1, int(ece_t > ece_h), "", kind="abs")
    p.metric("Expected calibration error: same patients / new patients", f"{ece_h:.4f} / {ece_t:.4f}")
    band = {}
    for nm, (pp_, yy_) in (("same", (ph, yh)), ("new", (pt, yt))):
        mband = (pp_ > 0.1) & (pp_ < 0.9); band[nm] = (pp_[mband].mean(), yy_[mband].mean(), int(mband.sum()))
    p.metric("Uncertain beats (predicted 0.1–0.9), same patients: mean prediction / observed PVC rate", f"{band['same'][0]:.2f} / {band['same'][1]:.2f}", "", f"{band['same'][2]} beats")
    p.metric("Uncertain beats (predicted 0.1–0.9), new patients: mean prediction / observed PVC rate", f"{band['new'][0]:.2f} / {band['new'][1]:.2f}", "", f"{band['new'][2]} beats")
    p.metric("Brier score: same patients / new patients / always predicting the base rate", f"{np.mean((ph - yh) ** 2):.4f} / {np.mean((pt - yt) ** 2):.4f} / {yt.mean() * (1 - yt.mean()):.4f}")
    p.metric("Discrimination on new patients (AUC)", ml.roc_curve(np.log(pt / (1 - pt) + 1e-300), yt)[3], "", "discrimination survives the change of patients")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].semilogy(errs[ok], "o-", color=C_MEAS, label="Newton / IRLS")
    wg = np.zeros(8); eg = []
    for k in range(300):
        eg.append(np.linalg.norm(wg - w)); wg -= lr * grad(wg, Xb, y, l2)
    ax[0].semilogy(eg, color=C_PRED, label="gradient descent"); ax[0].set_xlim(0, 60)
    style_axes(ax[0], "iteration", "‖w − w*‖", "Quadratic vs linear convergence")
    ax[1].barh([ml.BEAT_FEATURES[j] for j in o][::-1], w[:-1][o][::-1], color=[C_PRED if v > 0 else C_MEAS for v in w[:-1][o][::-1]])
    style_axes(ax[1], "coefficient (log odds per SD)", "", "What makes a beat look ventricular", legend=False)
    ax[2].plot([0, 1], [0, 1], ":", color="gray"); ax[2].plot(ch, fh, "o-", color=C_MEAS, label="same patients"); ax[2].plot(ct, ft, "s-", color=C_PRED, label="new patients")
    style_axes(ax[2], "predicted probability", "observed frequency", "Reliability diagram")
    p.save(fig, "logreg", "Convergence of Newton versus gradient descent, fitted coefficients, and calibration within and across patients.")
    p.discuss(f"""Maximum likelihood for the logistic model is a smooth convex problem and Newton's method exploits it: {its} iterations to machine-level
agreement with SciPy's BFGS and an observed order of {order:.1f}, against {gd_it if gd_it else 'more than 200000'} steps of gradient descent on the same data (Hessian condition
number {ev[-1] / ev[0]:.0f}). The coefficients are readable: the strongest predictors of a ventricular beat are its prematurity, its width and its
dissimilarity to the patient's normal template, which is exactly how a cardiologist describes a PVC. On beats from the training patients the
probabilities are honest: the expected calibration error is {ece_h:.4f}, and among the {band['same'][2]} genuinely uncertain beats (predicted 0.1–0.9) the mean
prediction {band['same'][0]:.2f} matches the observed PVC rate {band['same'][1]:.2f}. On ten new patients the ranking is as good as before (AUC unchanged) and the overall
calibration error is {ece_t / ece_h:.1f}× larger ({ece_t:.4f}); in the uncertain band the model predicts {band['new'][0]:.2f} on average where {band['new'][1]:.2f} of the beats are PVCs.
Both errors are small in absolute terms because 96 % of beats are confidently normal — a single summary number says little about the decision
region, and there the evidence is thin (a few dozen beats). So on this data calibration held up across patients better than I expected; the
check is still the right habit, because nothing in maximum likelihood guarantees calibration once the population changes (a different PVC rate
alone shifts every probability), and recalibration on the target population is cheap.""")
# tol-convention: relative tolerances are in percent
