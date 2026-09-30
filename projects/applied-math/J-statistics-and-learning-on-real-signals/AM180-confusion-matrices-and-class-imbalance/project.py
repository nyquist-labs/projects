from eelab import *
from eelab import ml
from scipy import stats

META = dict(
    id="AM-180", title="Confusion matrices and class imbalance", level="M",
    tools="Confusion-matrix metrics (accuracy, balanced accuracy, F1, Matthews correlation, Cohen's κ) coded from their definitions and cross-checked through identities, the accuracy paradox on 4 %-prevalence arrhythmia data, class weighting vs over-sampling vs threshold moving for logistic regression, micro/macro averaging on a 6-class problem",
    summary="Show on real, imbalanced ECG data why accuracy is the wrong headline number, verify the identities that tie the alternative metrics "
            "together, and test whether the usual remedies for imbalance — weighting, over-sampling, moving the threshold — are actually different things.",
    problem="A detector for a condition present in 4 % of beats is '96 % accurate' if it never fires. Which numbers should be reported instead, and how should the classifier be trained?",
    theory=r"""From the confusion matrix (TP, FP, FN, TN): accuracy of the trivial 'always negative' rule = 1 − π. Balanced accuracy = (Se + Sp)/2; F1 = 2TP/(2TP + FP + FN); Matthews correlation
$\mathrm{MCC}=\frac{TP\cdot TN-FP\cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}$ with $\mathrm{MCC}^2=χ^2/n$; Cohen's κ compares accuracy with chance agreement. Weighting the positive class by r in the likelihood is *identical* to replicating each
positive r times (over-sampling), and for a well-specified logistic model it is approximately a shift of the intercept by ln r — i.e. the same ranking with a moved threshold, $p>\frac{1}{1+r}$. For single-label multi-class problems micro-averaged F1 equals accuracy;
macro-averaging weights every class equally.""",
    method="""PVC detection, 7 features, logistic regression trained on 10 patients and tested on 10 others. Models: unweighted; positives weighted by r = (1 − π)/π; positives replicated r times (r rounded). Decision at p > 0.5, and the unweighted model
at p > 1/(1 + r). Multi-class part: softmax regression on the HAR benchmark.""",
    data="PhysioNet MIT-BIH Arrhythmia Database; UCI HAR.",
)


def metrics(y, yh):
    tp = int(np.sum((y == 1) & (yh == 1))); fp = int(np.sum((y == 0) & (yh == 1))); fn = int(np.sum((y == 1) & (yh == 0))); tn = int(np.sum((y == 0) & (yh == 0)))
    n = tp + fp + fn + tn; se = tp / max(tp + fn, 1); sp = tn / max(tn + fp, 1)
    den = np.sqrt(float(tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)); mcc = (tp * tn - fp * fn) / den if den else 0.0
    po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / n ** 2
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, acc=po, se=se, sp=sp, bal=(se + sp) / 2, f1=2 * tp / max(2 * tp + fp + fn, 1), mcc=mcc, kappa=(po - pe) / (1 - pe) if pe < 1 else 0.0,
                ppv=tp / max(tp + fp, 1))


def run(p):
    D = ml.ecg_beats(); tr = D["rec"] < 10; te = ~tr
    Xtr, Xte = ml.standardize(D["F"][tr], D["F"][te]); ytr, yte = D["y"][tr], D["y"][te]; pi_tr = ytr.mean(); pi_te = yte.mean()
    triv = metrics(yte, np.zeros_like(yte))
    p.compare("Accuracy of a detector that never fires = 1 − prevalence", (1 - pi_te) * 100, triv["acc"] * 100, "%", tol=1e-6)
    p.compare("… while its balanced accuracy is 50 % and its MCC, κ and F1 are 0 (sum of the three)", 0.0, triv["mcc"] + triv["kappa"] + triv["f1"], "", kind="abs", tol=1e-12)
    Xb = np.c_[Xte, np.ones(len(Xte))]
    w0, _ = ml.logistic_irls(Xtr, ytr.astype(float), l2=1e-3); s0 = Xb @ w0; m0 = metrics(yte, (s0 > 0).astype(int))
    chi2 = stats.chi2_contingency([[m0["tp"], m0["fn"]], [m0["fp"], m0["tn"]]], correction=False)[0]
    p.compare("Identity: MCC² = χ²/n for the 2 × 2 table", chi2 / len(yte), m0["mcc"] ** 2, "", tol=1e-8)
    p.compare("Identity: F1 is the harmonic mean of sensitivity and positive predictive value", 2 * m0["se"] * m0["ppv"] / (m0["se"] + m0["ppv"]), m0["f1"], "", tol=1e-8)
    rr = int(round((1 - pi_tr) / pi_tr))
    ww, _ = ml.logistic_irls(Xtr, ytr.astype(float), l2=1e-3, sample_weight=np.where(ytr == 1, float(rr), 1.0))
    idx = np.r_[np.flatnonzero(ytr == 0), np.repeat(np.flatnonzero(ytr == 1), rr)]
    wo, _ = ml.logistic_irls(Xtr[idx], ytr[idx].astype(float), l2=1e-3)
    p.compare(f"Weighting positives by r = {rr} vs replicating them r times: max coefficient difference", 0.0, float(np.max(np.abs(ww - wo))), "", kind="abs", tol=1e-6)
    mw = metrics(yte, (Xb @ ww > 0).astype(int)); mt = metrics(yte, (s0 > -np.log(rr)).astype(int))
    p.compare("Weighted model at p > 0.5 vs unweighted model at p > 1/(1 + r): sensitivity", mw["se"] * 100, mt["se"] * 100, "%", kind="abs", tol=2.5)
    p.compare("… specificity", mw["sp"] * 100, mt["sp"] * 100, "%", kind="abs", tol=1.5)
    p.compare("Intercept shift caused by weighting ≈ ln r", np.log(rr), ww[-1] - w0[-1], "", tol=40)
    auc0 = ml.roc_curve(s0, yte)[3]; aucw = ml.roc_curve(Xb @ ww, yte)[3]
    p.compare("Weighting barely changes the ranking: AUC weighted − AUC unweighted", 0.0, aucw - auc0, "", kind="abs", tol=0.005)
    rows = [("never fires", triv), ("logistic, p > 0.5", m0), (f"weighted ×{rr}, p > 0.5", mw), (f"unweighted, p > 1/{rr + 1}", mt)]
    p.section("Four detectors, six metrics (unseen patients)", "| detector | accuracy | sensitivity | specificity | PPV | balanced acc. | F1 | MCC | κ |\n|---|---|---|---|---|---|---|---|---|\n" + "\n".join(
        f"| {nm} | {m['acc'] * 100:.2f} % | {m['se'] * 100:.1f} % | {m['sp'] * 100:.1f} % | {m['ppv'] * 100:.1f} % | {m['bal'] * 100:.1f} % | {m['f1']:.3f} | {m['mcc']:.3f} | {m['kappa']:.3f} |" for nm, m in rows))
    p.compare("Re-balancing trades precision for sensitivity: weighted model has higher Se and lower PPV than the unweighted one (1 = yes)", 1, int(mw["se"] > m0["se"] and mw["ppv"] < m0["ppv"]), "", kind="abs")
    H = ml.har_features(); A, B = ml.standardize(H["Xtr"].astype(float), H["Xte"].astype(float))
    sm = ml.Softmax(l2=1e-3, lr=0.3, iters=400).fit(A, H["ytr"]); C = ml.confusion(H["yte"], sm.predict(B), 6)
    tp = np.diag(C); fp = C.sum(0) - tp; fn = C.sum(1) - tp
    micro = 2 * tp.sum() / (2 * tp.sum() + fp.sum() + fn.sum()); f1c = 2 * tp / (2 * tp + fp + fn)
    p.compare("Multi-class: micro-averaged F1 = accuracy", tp.sum() / C.sum(), micro, "", tol=1e-8)
    p.metric("HAR: accuracy / macro-F1 / worst class F1", f"{tp.sum() / C.sum() * 100:.1f} % / {f1c.mean():.3f} / {f1c.min():.3f} ({ml.HAR_NAMES[int(np.argmin(f1c))]})")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    for k, (nm, m) in enumerate(rows[1:3]):
        M = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]]); ax[k].imshow(M / M.sum(1, keepdims=True), cmap="Blues", vmin=0, vmax=1); ax[k].grid(False)
        for i in range(2):
            for j in range(2):
                ax[k].text(j, i, f"{M[i, j]}", ha="center", va="center", fontsize=12, color="white" if M[i, j] / M[i].sum() > 0.5 else "black")
        ax[k].set_xticks([0, 1]); ax[k].set_yticks([0, 1]); ax[k].set_xticklabels(["pred. normal", "pred. PVC"]); ax[k].set_yticklabels(["normal", "PVC"])
        ax[k].set_title(nm, loc="left", fontsize=10)
    names = ["accuracy", "balanced", "F1", "MCC", "κ"]; keys = ["acc", "bal", "f1", "mcc", "kappa"]; xk = np.arange(5)
    for k, (nm, m) in enumerate(rows[:3]):
        ax[2].bar(xk + (k - 1) * 0.27, [m[q] for q in keys], 0.27, color=["gray", C_MEAS, C_PRED][k], label=nm)
    ax[2].set_xticks(xk); ax[2].set_xticklabels(names)
    style_axes(ax[2], "", "score", "Only accuracy is fooled by the trivial detector")
    p.save(fig, "imbalance", "Confusion matrices of the unweighted and weighted detectors, and five metrics for three detectors.")
    p.discuss(f"""With PVCs at {pi_te * 100:.1f} % of beats, a detector that never fires is {triv['acc'] * 100:.1f} % accurate — and scores zero on F1, MCC and κ and 50 % balanced
accuracy, which is why those are the numbers to report. The metrics are not independent inventions: MCC² is the χ² statistic of the table divided
by n, and F1 is the harmonic mean of sensitivity and precision, both verified to round-off. The remedies for imbalance are less different than
their names suggest. Weighting the positive class by {rr} and replicating every positive {rr} times give the *same* coefficients; and the weighted
model behaves almost exactly like the unweighted one with its threshold moved from 0.5 to 1/{rr + 1} (sensitivity {mw['se'] * 100:.1f} vs {mt['se'] * 100:.1f} %, specificity
{mw['sp'] * 100:.1f} vs {mt['sp'] * 100:.1f} %), with an unchanged AUC. Re-balancing does not make the classifier better; it moves the operating point —
more PVCs caught ({m0['se'] * 100:.0f} → {mw['se'] * 100:.0f} %), more false alarms (PPV {m0['ppv'] * 100:.0f} → {mw['ppv'] * 100:.0f} %). Whether that trade is right depends on the costs,
not on the class ratio.""")
# tol-convention: relative tolerances are in percent
