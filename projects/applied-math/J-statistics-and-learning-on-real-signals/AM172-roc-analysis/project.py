from eelab import *
from eelab import ml
from scipy import stats

META = dict(
    id="AM-172", title="ROC analysis of an arrhythmia detector", level="M",
    tools="Logistic-regression score for premature ventricular beats (train on 10 patients, test on 10 others), ROC curve by threshold sweep, AUC as a Mann–Whitney statistic, Hanley–McNeil vs bootstrap vs patient-level bootstrap standard errors, Youden operating point, precision under changing prevalence",
    summary="Evaluate a beat classifier the way a diagnostic test is evaluated: build the ROC curve, show that its area is exactly the probability "
            "that a random abnormal beat outranks a random normal one, attach honest uncertainty to it, and show why a test with AUC near 1 can still have a poor positive predictive value.",
    problem="One number — accuracy — hides the threshold, the class balance and the uncertainty. What does a complete evaluation of a detector look like?",
    theory=r"""ROC: TPR vs FPR over all thresholds; it does not depend on prevalence. $\mathrm{AUC}=P(s^+>s^-)+\tfrac12P(s^+=s^-)=U/(n_+n_-)$ with U the Mann–Whitney statistic. Standard error (Hanley–McNeil):
$\sqrt{\frac{A(1-A)+(n_+-1)(Q_1-A^2)+(n_--1)(Q_2-A^2)}{n_+n_-}}$, $Q_1=\frac{A}{2-A}$, $Q_2=\frac{2A^2}{1+A}$ — valid for independent samples. Youden's J = TPR − FPR picks the threshold farthest from chance. Predictive value depends on prevalence π:
$PPV=\frac{Se\,π}{Se\,π+(1-Sp)(1-π)}$.""",
    method="""MIT-BIH beats (7 timing and morphology features per beat): logistic regression trained on the 10 'DS1' records, scored on the 10 'DS2' records (different patients). Bootstrap: 2000 resamples of beats, and 2000 resamples of whole records.
Prevalence experiment: negatives subsampled or replicated to set π = 50 %, natural and 0.5 %.""",
    data="PhysioNet MIT-BIH Arrhythmia Database (15 min of 20 records).",
)


def run(p):
    D = ml.ecg_beats(); tr = D["rec"] < 10; te = ~tr
    Xtr, Xte = ml.standardize(D["F"][tr], D["F"][te]); ytr, yte = D["y"][tr], D["y"][te]; rec_te = D["rec"][te]
    w, _ = ml.logistic_irls(Xtr, ytr, l2=1e-3)
    s = np.c_[Xte, np.ones(len(Xte))] @ w
    fpr, tpr, thr, auc = ml.roc_curve(s, yte)
    npos, nneg = int(yte.sum()), int((1 - yte).sum())
    rk = stats.rankdata(s); U = rk[yte == 1].sum() - npos * (npos + 1) / 2
    p.compare("AUC by the trapezoid rule vs Mann–Whitney U/(n₊n₋) from ranks", U / (npos * nneg), auc, "", tol=1e-8)
    ref = stats.mannwhitneyu(s[yte == 1], s[yte == 0]).statistic / (npos * nneg)
    p.compare("… and vs scipy.stats.mannwhitneyu", ref, auc, "", tol=1e-8)
    r = p.rng; pairs = r.integers(0, npos, 200000), r.integers(0, nneg, 200000)
    sp_, sn_ = s[yte == 1], s[yte == 0]
    p.compare("AUC = probability that a random PVC scores higher than a random normal beat (200 000 random pairs)", auc, float(np.mean(sp_[pairs[0]] > sn_[pairs[1]])), "", tol=0.3)
    Q1, Q2 = auc / (2 - auc), 2 * auc ** 2 / (1 + auc)
    se_hm = np.sqrt((auc * (1 - auc) + (npos - 1) * (Q1 - auc ** 2) + (nneg - 1) * (Q2 - auc ** 2)) / (npos * nneg))
    boot = []
    for _ in range(2000):
        i = r.integers(0, len(yte), len(yte)); boot.append(ml.roc_curve(s[i], yte[i])[3])
    se_b = np.std(boot)
    recs = np.unique(rec_te); bootc = []
    for _ in range(2000):
        pick = r.choice(recs, len(recs)); idx = np.concatenate([np.flatnonzero(rec_te == q) for q in pick])
        if yte[idx].sum() > 0:
            bootc.append(ml.roc_curve(s[idx], yte[idx])[3])
    se_c = np.std(bootc)
    p.compare("Standard error of the AUC: Hanley–McNeil formula vs beat-level bootstrap", se_hm, se_b, "", tol=40)
    p.compare("Patient-level bootstrap gives a larger standard error than the beat-level one (beats of one patient are not independent; 1 = yes)", 1, int(se_c > se_b), "", kind="abs")
    p.metric("AUC and its standard error: Hanley–McNeil / beat bootstrap / patient bootstrap", f"{auc:.4f} ± {se_hm:.4f} / {se_b:.4f} / {se_c:.4f}", "", f"{npos} PVCs, {nneg} normal beats, {len(recs)} patients")
    j = np.argmax(tpr - fpr); se_y, sp_y = tpr[j], 1 - fpr[j]
    p.metric("Youden operating point: sensitivity / specificity", f"{se_y * 100:.1f} % / {sp_y * 100:.1f} %")
    pred = s >= thr[j]; ppv_nat = np.sum(pred & (yte == 1)) / pred.sum(); pi_nat = npos / len(yte)
    p.compare(f"PPV at the natural prevalence ({pi_nat * 100:.1f} %) from Se, Sp and Bayes' rule", se_y * pi_nat / (se_y * pi_nat + (1 - sp_y) * (1 - pi_nat)), ppv_nat, "", tol=0.01)
    for pi_t in (0.5, 0.005):
        k = int(round(npos * (1 - pi_t) / pi_t)); neg_idx = r.choice(np.flatnonzero(yte == 0), k, replace=k > nneg)
        idx = np.r_[np.flatnonzero(yte == 1), neg_idx]; pr = s[idx] >= thr[j]; yy = yte[idx]
        p.compare(f"PPV when prevalence is {pi_t * 100:g} % (same detector, same threshold)", se_y * pi_t / (se_y * pi_t + (1 - sp_y) * (1 - pi_t)), np.sum(pr & (yy == 1)) / pr.sum(), "", tol=6)
    o = np.argsort(-s); prec = np.cumsum(yte[o]) / np.arange(1, len(o) + 1); rec = np.cumsum(yte[o]) / npos
    ap = float(np.sum(np.diff(np.r_[0, rec]) * prec))
    p.metric("Area under the precision–recall curve (average precision)", ap, "", f"chance level = prevalence = {pi_nat:.3f}; chance AUC-ROC = 0.5")
    p.csv("roc", fpr=fpr, tpr=tpr)
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].hist(sn_, bins=60, density=True, color=C_MEAS, alpha=.6, label="normal beats"); ax[0].hist(sp_, bins=60, density=True, color=C_PRED, alpha=.6, label="PVC")
    ax[0].axvline(thr[j], color="k", ls="--", lw=1, label="Youden threshold")
    style_axes(ax[0], "classifier score", "density", "Score distributions (unseen patients)")
    ax[1].plot(fpr, tpr, color=C_MEAS, label=f"AUC = {auc:.3f}"); ax[1].plot([0, 1], [0, 1], ":", color="gray"); ax[1].plot([fpr[j]], [tpr[j]], "o", color=C_PRED, label="Youden point")
    ax[1].set_xscale("symlog", linthresh=0.01)
    style_axes(ax[1], "false-positive rate", "true-positive rate", "ROC (log-scaled FPR axis)")
    ax[2].plot(rec, prec, color=C_MEAS, label=f"AP = {ap:.3f}"); ax[2].axhline(pi_nat, color="gray", ls=":", label="prevalence")
    style_axes(ax[2], "recall (sensitivity)", "precision (PPV)", "Precision–recall at 4 % prevalence")
    p.save(fig, "roc", "Score distributions, ROC curve and precision–recall curve of the PVC detector on unseen patients.")
    p.discuss(f"""The area under the ROC curve is not just a geometric summary: computed by the trapezoid rule it equals the Mann–Whitney statistic to machine
precision, and sampling random (PVC, normal) pairs confirms its meaning — the detector ranks the abnormal beat higher {auc * 100:.1f} % of the time.
Its uncertainty depends on what is treated as independent. The Hanley–McNeil formula and a beat-level bootstrap give ±{se_b:.4f}, but beats from one
patient resemble each other; resampling whole patients gives ±{se_c:.4f}, {se_c / se_b:.0f}× larger, and that is the honest figure for 'how would this do on new
patients'. Finally, the ROC is blind to prevalence and the user is not: at the Youden point the detector has Se {se_y * 100:.0f} % and Sp {sp_y * 100:.0f} %, yet with
PVCs at {pi_nat * 100:.0f} % of beats its positive predictive value is only {ppv_nat * 100:.0f} %, and at 0.5 % prevalence most alarms would be false — Bayes' rule,
confirmed by resampling. For rare events the precision–recall curve tells the story the ROC hides.""")
# tol-convention: relative tolerances are in percent
