from eelab import *
from eelab import ml
from scipy import stats

META = dict(
    id="AM-187", title="Bootstrap confidence intervals — and when they fail", level="M",
    tools="Own percentile and BCa bootstrap, coverage experiments by simulation, Wilson binomial interval, cluster (patient-level) bootstrap versus beat-level bootstrap on real ECG detections, design-effect prediction from the intraclass correlation, the known failure for the sample maximum",
    summary="Put error bars on statistics by resampling: check that bootstrap intervals cover the truth at the advertised rate where the truth is known, "
            "show that they agree with the textbook binomial interval for independent data, that they are far too narrow when resampling ignores clustering, and one statistic for which the bootstrap is simply wrong.",
    problem="A detector found 96 % of 391 abnormal beats. How uncertain is that number — and does it matter that all those beats came from only a handful of people?",
    theory=r"""The bootstrap replaces the unknown population by the sample: the spread of a statistic over resamples estimates its sampling spread. For the mean, the bootstrap SE equals $s\sqrt{(n-1)/n}/\sqrt n$. Percentile intervals are
first-order accurate; BCa corrects bias and skewness. Resampling must copy the dependence structure: with m correlated observations per cluster, the variance of a proportion is inflated by the design effect $1+(m-1)ρ_{ICC}$, so an
observation-level bootstrap is too narrow by about $\sqrt{\mathrm{deff}}$. The bootstrap fails for statistics that depend on the extreme order statistics (e.g. the maximum of a uniform), where the resampling distribution has an atom at the sample maximum.""",
    method="""Coverage: 2000 simulated samples each (n = 40 lognormal medians, n = 30 uniform maxima), 2000 resamples per interval. Real data: sensitivity of the PVC detector of AM-172 (logistic regression, train on 10 patients, test on 10 others)
— Wilson interval, beat-level bootstrap and patient-level (cluster) bootstrap; ICC of detection within patient from a one-way ANOVA estimator.""",
    data="PhysioNet MIT-BIH Arrhythmia Database.",
)


def boot(x, stat, B, rng):
    idx = rng.integers(0, len(x), (B, len(x)))
    return np.array([stat(x[i]) for i in idx])


def bca(x, stat, B, rng, alpha=0.05):
    th = stat(x); bs = boot(x, stat, B, rng)
    z0 = stats.norm.ppf(np.clip(np.mean(bs < th), 1e-6, 1 - 1e-6))
    jack = np.array([stat(np.delete(x, i)) for i in range(len(x))]); jm = jack.mean()
    a = np.sum((jm - jack) ** 3) / (6 * np.sum((jm - jack) ** 2) ** 1.5 + 1e-300)
    qs = [stats.norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z))) for z in stats.norm.ppf([alpha / 2, 1 - alpha / 2])]
    return np.quantile(bs, qs)


def wilson(k, n, z=1.96):
    ph = k / n; c = (ph + z * z / (2 * n)) / (1 + z * z / n); h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def run(p):
    r = p.rng
    x = r.normal(10, 3, 50); bs = boot(x, np.mean, 20000, r)
    p.compare("Bootstrap SE of the mean vs s·√((n−1)/n)/√n", x.std(ddof=1) * np.sqrt(49 / 50) / np.sqrt(50), bs.std(), "", tol=3)
    truth = np.exp(0.0); hp = hb = 0; T = 600
    for _ in range(T):
        s = r.lognormal(0, 1, 40); b = boot(s, np.median, 1000, r)
        lo, hi = np.quantile(b, [0.025, 0.975]); hp += lo <= truth <= hi
        lo2, hi2 = bca(s, np.median, 1000, r); hb += lo2 <= truth <= hi2
    p.compare("Coverage of the 95 % percentile interval for the median of a lognormal sample (n = 40)", 95.0, hp / T * 100, "%", kind="abs", tol=3)
    p.compare("… BCa interval", 95.0, hb / T * 100, "%", kind="abs", tol=3)
    hm = 0
    for _ in range(T):
        s = r.uniform(0, 1, 30); b = boot(s, np.max, 1000, r); lo, hi = np.quantile(b, [0.025, 0.975]); hm += lo <= 1.0 <= hi
    p.compare("Known failure: percentile interval for the maximum of Uniform(0, 1) — coverage is far below 95 % (< 20 %; 1 = yes)", 1, int(hm / T < 0.2), "", kind="abs")
    p.metric("Coverage for the uniform maximum", hm / T * 100, "%", "the bootstrap never produces a value above the sample maximum, the truth is always above it")
    D = ml.ecg_beats(); tr = D["rec"] < 10; te = ~tr
    Xtr, Xte = ml.standardize(D["F"][tr], D["F"][te]); w, _ = ml.logistic_irls(Xtr, D["y"][tr].astype(float), l2=1e-3)
    det = (np.c_[Xte, np.ones(len(Xte))] @ w > 0).astype(int); yte = D["y"][te]; rec = D["rec"][te]
    pos = yte == 1; hit = det[pos]; rp = rec[pos]; k, n = int(hit.sum()), int(pos.sum())
    wl = wilson(k, n); bb = boot(hit.astype(float), np.mean, 5000, r); bl = np.quantile(bb, [0.025, 0.975])
    p.compare("Sensitivity: beat-level bootstrap interval width vs Wilson interval width (independent-beats assumption)", wl[1] - wl[0], bl[1] - bl[0], "", tol=15)
    recs = np.unique(rp); groups = {q: hit[rp == q] for q in recs}; bc = []
    for _ in range(5000):
        pick = r.choice(recs, len(recs)); v = np.concatenate([groups[q] for q in pick]); bc.append(v.mean())
    cl = np.quantile(bc, [0.025, 0.975])
    msz = np.array([len(groups[q]) for q in recs]); means = np.array([groups[q].mean() for q in recs]); pbar = hit.mean()
    msb = np.sum(msz * (means - pbar) ** 2) / (len(recs) - 1); msw = np.sum([np.sum((groups[q] - groups[q].mean()) ** 2) for q in recs]) / (n - len(recs))
    m0 = (n - np.sum(msz ** 2) / n) / (len(recs) - 1); icc = max(0.0, (msb - msw) / (msb + (m0 - 1) * msw))
    deff = 1 + (np.sum(msz ** 2) / n - 1) * icc
    p.compare("Resampling patients instead of beats widens the interval (1 = yes)", 1, int((cl[1] - cl[0]) > (bl[1] - bl[0])), "", kind="abs")
    p.metric("Width ratio patient-level / beat-level interval vs √(design effect) from the ANOVA ICC", f"{(cl[1] - cl[0]) / (bl[1] - bl[0]):.2f} vs {np.sqrt(deff):.2f}", "", "the ICC estimate from so few clusters is unreliable (it truncates at 0 here)")
    p.metric("Sensitivity with 95 % intervals: Wilson / beat bootstrap / patient bootstrap", f"{k / n * 100:.1f} % [{wl[0] * 100:.1f}, {wl[1] * 100:.1f}] / [{bl[0] * 100:.1f}, {bl[1] * 100:.1f}] / [{cl[0] * 100:.1f}, {cl[1] * 100:.1f}]", "", f"{n} PVCs from {len(recs)} patients")
    p.metric("Intraclass correlation of detections within a patient / design effect", f"{icc:.3f} / {deff:.1f}", "", "effective number of independent PVCs ≈ " + f"{n / deff:.0f}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].hist(bb * 100, bins=40, color=C_PRED, alpha=.6, density=True, label="resampling beats"); ax[0].hist(np.array(bc) * 100, bins=40, color=C_MEAS, alpha=.6, density=True, label="resampling patients")
    style_axes(ax[0], "sensitivity (%)", "density", "Two bootstraps of the same number")
    ax[1].bar(np.arange(len(recs)), means * 100, color=C_MEAS); ax[1].set_xticks(np.arange(len(recs))); ax[1].set_xticklabels([ml.DS2[q - 10] for q in recs], rotation=45)
    style_axes(ax[1], "record", "sensitivity (%)", "Detection rate differs between patients", legend=False)
    p.save(fig, "bootstrap", "Bootstrap distributions of the detector's sensitivity under beat-level and patient-level resampling, and per-patient sensitivity.")
    p.discuss(f"""Where the answer is known the bootstrap earns its reputation: its standard error of a mean matches the formula, and its 95 % intervals for a
skewed sample median cover the truth {hp / T * 100:.0f} % (percentile) and {hb / T * 100:.0f} % (BCa) of the time. Two cautions follow from the same experiments. For the maximum
of a uniform sample the coverage is {hm / T * 100:.0f} % — the bootstrap cannot produce values beyond the sample, so statistics set by the extremes are out
of its reach. And the resampling unit matters. For the detector's {k / n * 100:.1f} % sensitivity, resampling individual beats reproduces the Wilson interval
([{wl[0] * 100:.1f}, {wl[1] * 100:.1f}] %), both implicitly assuming {n} independent PVCs. Resampling patients gives [{cl[0] * 100:.1f}, {cl[1] * 100:.1f}] %, {(cl[1] - cl[0]) / (bl[1] - bl[0]):.1f}× wider. The formula route
failed here: with only {len(recs)} test patients contributing PVCs, the ANOVA estimate of the intraclass correlation comes out at its floor of zero
(design effect {deff:.1f}), yet the per-patient sensitivities in the right-hand plot clearly differ — five clusters are too few to estimate an ICC, but
enough for the cluster bootstrap to show that most of the uncertainty is *which patients* were tested. The honest interval for 'a new patient' is
the wide one, and a study with more patients, not more beats, is what would narrow it.""")
# tol-convention: relative tolerances are in percent
