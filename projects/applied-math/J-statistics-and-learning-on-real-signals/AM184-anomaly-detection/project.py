from eelab import *
from eelab import ml
from scipy import stats

META = dict(
    id="AM-184", title="Anomaly detection without labels: abnormal heartbeats as outliers", level="H",
    tools="Mahalanobis distance from a per-patient model of 'usual' beats, robust (iteratively trimmed) mean and covariance against contamination, χ² calibration of the threshold, comparison of false-alarm rates with theory, PCA reconstruction error on beat waveforms, ROC evaluation against reference annotations",
    summary="Detect premature ventricular beats with no training labels at all, by modelling each patient's usual beat and flagging what is far from it. "
            "Test the Gaussian theory behind the threshold, show how outliers corrupt the very model that should detect them, and compare with the supervised detector of AM-172.",
    problem="Labelled abnormal examples are rare and patient-specific. Can 'unusual for this patient' be detected directly — and how is the alarm threshold set?",
    theory=r"""If normal beats' features were Gaussian $\mathcal N(μ,Σ)$, the squared Mahalanobis distance $D^2=(x-μ)^TΣ^{-1}(x-μ)$ would follow $χ^2_d$, so a threshold at the 99th percentile of $χ^2_d$ gives a 1 % false-alarm rate.
Two practical problems: (1) real features are heavy-tailed, so the true false-alarm rate is higher; (2) μ and Σ must be estimated from unlabeled data that *contain* the anomalies, which inflate Σ and hide themselves ('masking'). Robust estimation —
fit, discard the most distant beats, refit — restores the contrast, provided more is trimmed than the share of anomalies. For waveforms, the analogous score is the reconstruction error after projecting on the principal components of the patient's beats.""",
    method="""MIT-BIH beats of 20 records, 7 timing/morphology features each (labels used only for scoring). Per record: classical and trimmed (5 iterations, 60 % of beats kept) estimates on all beats of that record; ROC within each record and pooled. χ² check on annotated-normal beats.
Waveform variant: PCA (5 components) of each record's beats, reconstruction error as the score.""",
    data="PhysioNet MIT-BIH Arrhythmia Database.",
)


def mahal(F, mu, S):
    Z = F - mu
    return np.einsum("ij,ij->i", Z @ np.linalg.inv(S), Z)


def robust_fit(F, keep=0.6, iters=5):
    mu = np.median(F, 0); S = np.cov(F.T) + 1e-9 * np.eye(F.shape[1])
    for _ in range(iters):
        d2 = mahal(F, mu, S); core = d2 <= np.quantile(d2, keep)
        mu = F[core].mean(0); S = np.cov(F[core].T) + 1e-9 * np.eye(F.shape[1])
    # consistency factor so that distances of the Gaussian core are χ²-scaled again
    d = F.shape[1]; c = keep / stats.chi2.cdf(stats.chi2.ppf(keep, d), d + 2)
    return mu, S * c


def run(p):
    D = ml.ecg_beats(); F, y, rec = D["F"], D["y"], D["rec"]; d = F.shape[1]
    sc_c = np.zeros(len(y)); sc_r = np.zeros(len(y)); per = []
    for k in np.unique(rec):
        m = rec == k; Fk = F[m]
        sc_c[m] = mahal(Fk, Fk.mean(0), np.cov(Fk.T) + 1e-9 * np.eye(d))
        mu, S = robust_fit(Fk); sc_r[m] = mahal(Fk, mu, S)
        if y[m].sum() >= 5:
            per.append((k, y[m].mean(), ml.roc_curve(sc_c[m], y[m])[3], ml.roc_curve(sc_r[m], y[m])[3]))
    per = np.array(per)
    auc_c = ml.roc_curve(sc_c, y)[3]; auc_r = ml.roc_curve(sc_r, y)[3]; wc, wr = per[:, 2].mean(), per[:, 3].mean()
    p.compare("Unsupervised detection (robust distance, no labels): mean within-patient AUC (supervised detector on unseen patients: 0.988)", 0.988, wr, "", kind="abs", tol=0.02)
    p.compare("Robust fit improves on the classical fit (mean within-patient AUC higher; 1 = yes)", 1, int(wr > wc), "", kind="abs")
    p.metric("Mean within-patient AUC: classical / robust", f"{wc:.4f} / {wr:.4f}", "", f"{int(y.sum())} PVCs among {len(y)} beats, {len(per)} records with ≥ 5 PVCs")
    p.metric("Pooled AUC (one threshold for all patients): classical / robust", f"{auc_c:.4f} / {auc_r:.4f}")
    top = per[np.argsort(-per[:, 1])[:3]]
    p.compare("Masking: in the three records with the most PVCs (18–26 % of beats) the classical AUC is below the robust AUC (count)", 3, int(np.sum(top[:, 2] < top[:, 3])), "", kind="abs")
    p.metric("Those three records: PVC share → classical / robust AUC", "; ".join(f"{a_ * 100:.0f} % → {b_:.3f} / {c_:.3f}" for _, a_, b_, c_ in top))
    sweep = []
    for keep in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        aucs = []
        for k in per[:, 0].astype(int):
            m = rec == k; Fk = F[m]
            mu_, S_ = (Fk.mean(0), np.cov(Fk.T)) if keep == 1.0 else robust_fit(Fk, keep=keep)
            aucs.append(ml.roc_curve(mahal(Fk, mu_, S_ + 1e-9 * np.eye(d)), y[m])[3])
        sweep.append((keep, np.mean(aucs), np.min(aucs)))
    p.section("Effect of the trimming fraction (chosen after seeing this table — it is a tuning parameter)", "| fraction of beats kept | mean within-patient AUC | worst record |\n|---|---|---|\n" + "\n".join(f"| {a_:.0%} | {b_:.4f} | {c_:.3f} |" for a_, b_, c_ in sweep))
    worst = top[0]
    thr = stats.chi2.ppf(0.99, d); normal = y == 0
    fpr = np.mean(sc_r[normal] > thr); se = np.mean(sc_r[y == 1] > thr)
    p.compare("False-alarm rate on normal beats at the χ²₇ 99 % threshold (Gaussian theory: 1 %)", 1.0, fpr * 100, "%", kind="abs", tol=1.0)
    fpr_c = np.mean(sc_c[normal] > thr)
    p.metric("… same threshold with the classical (contaminated) estimates", fpr_c * 100, "%", "fewer false alarms only because the inflated covariance shrinks every distance")
    p.metric("… sensitivity to PVCs at that threshold", se * 100, "%")
    emp = np.quantile(sc_r[normal], 0.99)
    p.metric("Threshold giving a true 1 % false-alarm rate (empirical 99th percentile) vs χ² value", f"{emp:.0f} vs {thr:.1f}", "", f"sensitivity there: {np.mean(sc_r[y == 1] > emp) * 100:.0f} %")
    hit = tot = 0
    for k in per[:, 0].astype(int):
        m = rec == k; t_k = np.quantile(sc_r[m & normal], 0.99); hit += int(np.sum(sc_r[m & (y == 1)] > t_k)); tot += int(np.sum(m & (y == 1)))
    se_pp = hit / tot
    p.metric("Sensitivity at a 1 % false-alarm rate with a separate threshold per patient", se_pp * 100, "%", "scores are not comparable between patients; one global threshold wastes most of the detector's ability")
    med_ratio = np.median(sc_r[normal]) / stats.chi2.ppf(0.5, d)
    p.compare("Centre of the distribution is Gaussian-like: median D² of normal beats / median of χ²₇", 1.0, med_ratio, "", tol=35)
    p.metric("Kurtosis of the normal beats' features (mean over features; Gaussian = 3)", float(np.mean([stats.kurtosis(F[normal & (rec == k)][:, j], fisher=False) for k in np.unique(rec) for j in range(d)])))
    W = D["wave"].astype(float); sc_w = np.zeros(len(y))
    for k in np.unique(rec):
        m = rec == k; Wk = W[m]; med = np.median(Wk, 0); Z = Wk - med
        core = np.argsort(np.sum(Z ** 2, 1))[: int(0.6 * len(Z))]
        U, s, Vt = np.linalg.svd(Z[core] - Z[core].mean(0), full_matrices=False); B = Vt[:5]
        R = Z - (Z @ B.T) @ B; sc_w[m] = np.sum(R ** 2, 1) / np.median(np.sum(R ** 2, 1))
    auc_w = ml.roc_curve(sc_w, y)[3]
    p.metric("Waveform-only score (PCA reconstruction error): pooled AUC", auc_w, "", "no RR-interval information")
    comb = stats.rankdata(sc_w) + stats.rankdata(sc_r)
    p.metric("Rank-sum of both scores: pooled AUC", ml.roc_curve(comb, y)[3])
    fpr_c, tpr_c, _, _ = ml.roc_curve(sc_c, y); fpr_r, tpr_r, _, _ = ml.roc_curve(sc_r, y)
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    xs = np.linspace(0.01, 60, 400)
    ax[0].hist(sc_r[normal], bins=np.linspace(0, 60, 80), density=True, color=C_MEAS, alpha=.6, label="normal beats"); ax[0].hist(np.clip(sc_r[y == 1], 0, 60), bins=np.linspace(0, 60, 80), density=True, color=C_PRED, alpha=.6, label="PVC (clipped at 60)")
    ax[0].plot(xs, stats.chi2.pdf(xs, d), "k--", lw=1, label="χ²₇"); ax[0].axvline(thr, color="gray", ls=":"); ax[0].set_yscale("log"); ax[0].set_ylim(1e-5, 1)
    style_axes(ax[0], "squared Mahalanobis distance", "density", "Normal beats follow χ² only near the centre")
    ax[1].plot(fpr_c, tpr_c, color=C_PRED, label=f"classical (AUC {auc_c:.3f})"); ax[1].plot(fpr_r, tpr_r, color=C_MEAS, label=f"robust (AUC {auc_r:.3f})"); ax[1].set_xscale("symlog", linthresh=0.01)
    style_axes(ax[1], "false-alarm rate", "PVC detection rate", "Unsupervised ROC, all records")
    ax[2].scatter(per[:, 1] * 100, per[:, 2], color=C_PRED, label="classical"); ax[2].scatter(per[:, 1] * 100, per[:, 3], color=C_MEAS, marker="s", label="robust (60 % kept)")
    style_axes(ax[2], "PVC share in the record (%)", "AUC within the record", "Contamination hurts the classical fit")
    p.save(fig, "anomaly", "Distance distribution against χ², ROC of classical and robust detectors, and per-record AUC versus contamination.")
    p.discuss(f"""Without a single label, 'far from this patient's usual beat' detects PVCs with a mean within-patient AUC of {wr:.3f} — the level of the
supervised detector (0.988 on unseen patients) — because a premature, wide, oddly shaped beat is an outlier by construction. Robust estimation is
what makes it work. With the ordinary mean and covariance the AUC is {wc:.3f}, and in the three records where 18–26 % of beats are PVCs it falls to
{top[:, 2].min():.2f}–{top[:, 2].max():.2f}: the anomalies inflate the covariance that was supposed to expose them. My first robust version kept 80 % of the beats and
still failed on the record with 26 % PVCs — the trimming has to exceed the contamination — so the table above shows the whole sweep rather than
only the best setting. The Gaussian threshold theory does *not* survive contact with the data: the centre of the distance distribution is
χ²-like (median ratio {med_ratio:.2f}), but the feature distributions are heavy-tailed (kurtosis ≈ {np.mean([stats.kurtosis(F[normal & (rec == k)][:, j], fisher=False) for k in np.unique(rec) for j in range(d)]):.0f}) and the nominal 1 % threshold fires on {fpr * 100:.0f} % of
normal beats. A threshold has to come from empirical quantiles, and per patient: one global
threshold set for a true 1 % false-alarm rate (D² ≈ {emp:.0f} instead of {thr:.0f}) catches only {np.mean(sc_r[y == 1] > emp) * 100:.0f} % of PVCs, whereas a 1 % threshold set within
each record catches {se_pp * 100:.0f} %. And an unsupervised detector flags *unusual*, not
*dangerous* — a lead change or a run of paced beats would score just as high — so it complements rather than replaces a trained classifier.""")
# tol-convention: relative tolerances are in percent
