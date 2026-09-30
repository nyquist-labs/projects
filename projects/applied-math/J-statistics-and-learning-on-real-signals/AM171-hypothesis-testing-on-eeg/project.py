from eelab import *
from eelab.bio import eegmmidb
from scipy import signal, stats

META = dict(
    id="AM-171", title="Hypothesis testing on real EEG: is alpha stronger with eyes closed?", level="M",
    tools="Own paired t-test, exact Wilcoxon signed-rank distribution (dynamic programming), exact sign-flip permutation test (all 2²⁰ relabelings), Bonferroni and Benjamini–Hochberg corrections over 64 channels, permutation-based check of false-positive rates, effect size and power by subsampling",
    summary="Test the classic Berger effect on 20 PhysioNet subjects with three different tests built from scratch, check each against SciPy, then "
            "confront the multiple-comparison problem across 64 electrodes and verify empirically that the corrections control what they claim to control.",
    problem="An effect 'is significant at p < 0.05' — by which test, corrected for how many comparisons, and how often would chance alone produce it?",
    theory=r"""Paired design: per-subject difference $d_i$ of log alpha power (eyes closed − eyes open). t-test: $t=\bar d/(s_d/\sqrt n)$, n − 1 degrees of freedom (assumes roughly normal d). Wilcoxon signed-rank: sum of ranks of positive differences; exact null
distribution by counting subsets of {1…n}. Sign-flip permutation test: under H₀ each $d_i$ is equally likely ±, so the null distribution of $\bar d$ is its distribution over all 2ⁿ sign patterns — no distributional assumption.
With m = 64 tests at α = 0.05, some false positives are expected by chance (3.2 on average if all nulls were true); Bonferroni (α/m) controls the family-wise error rate, Benjamini–Hochberg the false-discovery rate and is never less powerful.""",
    method="""EEG Motor Movement/Imagery database, subjects 1–20, runs 1 (eyes open) and 2 (eyes closed), 64 channels, 160 Hz, 1 min each. Alpha power = Welch PSD (2 s windows) integrated over 8–13 Hz, in log units. Primary test on the mean of O1, Oz, O2. Null
calibration: 2000 random sign-flip relabelings of the subjects (same flip for all channels, preserving the correlation between channels).""",
    data="PhysioNet EEG Motor Movement/Imagery Dataset (Schalk et al. 2004), fetched on first run.",
)


def alpha_power(subject, run_):
    X, fs, labels, _ = eegmmidb(subject, run_)
    f, P = signal.welch(X, fs, nperseg=int(2 * fs), axis=1)
    m = (f >= 8) & (f <= 13)
    return np.log10(np.trapezoid(P[:, m], f[m], axis=1)), [l.upper() for l in labels]


def t_paired(d):
    n = len(d); t = d.mean() / (d.std(ddof=1) / np.sqrt(n))
    return t, 2 * stats.t.sf(abs(t), n - 1)


def wilcoxon_exact(d):
    r = stats.rankdata(np.abs(d)); W = r[d > 0].sum(); n = len(d); tot = n * (n + 1) // 2
    cnt = np.zeros(tot + 1); cnt[0] = 1
    for k in range(1, n + 1):                                  # number of subsets of {1..n} with a given rank sum
        cnt[k:] = cnt[k:] + cnt[:-k].copy()
    pmf = cnt / 2 ** n; Wm = min(W, tot - W)
    return W, min(1.0, 2 * pmf[: int(np.floor(Wm)) + 1].sum())


def signflip_exact(d):
    n = len(d); obs = abs(d.sum()); count = 0
    low = d[:10]; high = d[10:]
    s_low = np.array([np.sum(low * (1 - 2 * ((k >> np.arange(len(low))) & 1))) for k in range(2 ** len(low))])
    s_high = np.array([np.sum(high * (1 - 2 * ((k >> np.arange(len(high))) & 1))) for k in range(2 ** len(high))])
    s_high.sort()
    for a in s_low:                                            # count |a + b| ≥ obs over all b
        count += len(s_high) - np.searchsorted(s_high, obs - a - 1e-12, "left") + np.searchsorted(s_high, -obs - a + 1e-12, "right")
    return count / 2 ** n


def bh(pv, q=0.05):
    m = len(pv); o = np.argsort(pv); thr = q * np.arange(1, m + 1) / m
    ok = np.flatnonzero(pv[o] <= thr)
    rej = np.zeros(m, bool)
    if len(ok):
        rej[o[: ok[-1] + 1]] = True
    return rej


def run(p):
    D = []; labels = None
    for s in range(1, 21):
        a_open, labels = alpha_power(s, 1); a_closed, _ = alpha_power(s, 2); D.append(a_closed - a_open)
    D = np.array(D); occ = [labels.index(c) for c in ("O1", "OZ", "O2")]
    d = D[:, occ].mean(1); n = len(d)
    t, pt = t_paired(d); ref = stats.ttest_rel(d, np.zeros(n))
    p.compare("Own paired t statistic vs scipy.stats", ref.statistic, t, "", tol=1e-8)
    p.compare("Own t-test p-value vs scipy.stats (ratio)", 1.0, pt / ref.pvalue, "", tol=1e-6)
    W, pw = wilcoxon_exact(d); refw = stats.wilcoxon(d, mode="exact")
    p.compare("Exact Wilcoxon signed-rank p-value vs scipy.stats (ratio)", 1.0, pw / refw.pvalue, "", tol=1e-6)
    pp = signflip_exact(d)
    p.metric("Occipital alpha, eyes closed vs open: mean change", f"×{10 ** d.mean():.2f} in power ({d.mean() * 10:.1f} dB), {int(np.sum(d > 0))}/{n} subjects increase")
    p.metric("p-values: t-test / Wilcoxon / exact sign-flip permutation", f"{pt:.1e} / {pw:.1e} / {pp:.1e}")
    p.compare("The three tests agree on the conclusion at α = 0.001 (1 = yes)", 1, int(max(pt, pw, pp) < 1e-3), "", kind="abs")
    p.compare("Smallest p the permutation test can give with n = 20 is 2/2²⁰; it cannot go below that (1 = holds)", 1, int(pp >= 2 / 2 ** 20 - 1e-15), "", kind="abs")
    dz = d.mean() / d.std(ddof=1)
    p.metric("Effect size (Cohen's d_z)", dz)
    pv = np.array([t_paired(D[:, c])[1] for c in range(D.shape[1])])
    n_unc = int(np.sum(pv < 0.05)); n_bonf = int(np.sum(pv < 0.05 / len(pv))); n_bh = int(bh(pv).sum())
    p.metric("Channels significant: uncorrected / Benjamini–Hochberg / Bonferroni", f"{n_unc} / {n_bh} / {n_bonf}", "of 64")
    p.compare("Ordering: Bonferroni ≤ BH ≤ uncorrected discoveries (1 = yes)", 1, int(n_bonf <= n_bh <= n_unc), "", kind="abs")
    r = p.rng; B = 2000; any_unc = any_bonf = 0; fp_rate = []; bh_any = 0
    for _ in range(B):
        sg = r.choice([-1.0, 1.0], n)[:, None]; Dn = D * sg
        tt = Dn.mean(0) / (Dn.std(0, ddof=1) / np.sqrt(n)); pn = 2 * stats.t.sf(np.abs(tt), n - 1)
        fp_rate.append(np.mean(pn < 0.05)); any_unc += np.any(pn < 0.05); any_bonf += np.any(pn < 0.05 / 64); bh_any += bh(pn).any()
    p.compare("Null calibration: per-channel false-positive rate at α = 0.05", 5.0, np.mean(fp_rate) * 100, "%", kind="abs", tol=1.0)
    p.compare("Null: without correction, 'at least one significant channel' happens far more often than 5 % (> 10 %; 1 = yes)", 1, int(any_unc / B > 0.10), "", kind="abs")
    p.metric("… measured family-wise error without correction (64 independent tests would give 96 %)", any_unc / B * 100, "%")
    p.compare("Null: family-wise error rate with Bonferroni ≤ 5 % (1 = yes)", 1, int(any_bonf / B <= 0.05 + 2 * np.sqrt(0.05 * 0.95 / B)), "", kind="abs")
    p.metric("Null: family-wise error — uncorrected / Bonferroni / BH", f"{any_unc / B * 100:.1f} % / {any_bonf / B * 100:.1f} % / {bh_any / B * 100:.1f} %", "", "channels are strongly correlated, so far fewer than 64 independent tests")
    pow_meas = {}; pow_pred = {}
    for k in (4, 6, 8, 12):
        hits = 0
        for _ in range(3000):
            sub = r.choice(n, k, replace=False); hits += t_paired(d[sub])[1] < 0.05
        pow_meas[k] = hits / 3000
        nc = dz * np.sqrt(k); tc = stats.t.ppf(0.975, k - 1)
        pow_pred[k] = stats.nct.sf(tc, k - 1, nc) + stats.nct.cdf(-tc, k - 1, nc)
    p.compare("Power with only 6 subjects: non-central t prediction vs subsampling the real data", pow_pred[6] * 100, pow_meas[6] * 100, "%", kind="abs", tol=12)
    p.metric("Power at n = 4 / 6 / 8 / 12 subjects (subsampled)", " / ".join(f"{pow_meas[k] * 100:.0f} %" for k in (4, 6, 8, 12)))
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].bar(np.arange(n) + 1, np.sort(d) * 10, color=C_MEAS); ax[0].axhline(0, color="gray", lw=.6)
    style_axes(ax[0], "subject (sorted)", "alpha change (dB)", "Eyes closed − eyes open, occipital", legend=False)
    o = np.argsort(pv)
    ax[1].semilogy(np.arange(1, 65), pv[o], "o", ms=3, color=C_MEAS, label="channel p-values (sorted)")
    ax[1].semilogy(np.arange(1, 65), 0.05 * np.arange(1, 65) / 64, "--", color=C_PRED, label="BH line"); ax[1].axhline(0.05 / 64, color=COLORS[2], ls=":", label="Bonferroni"); ax[1].axhline(0.05, color="gray", lw=.6)
    style_axes(ax[1], "rank", "p-value", "64 tests: which survive correction?")
    ks = sorted(pow_meas); ax[2].plot(ks, [pow_meas[k] * 100 for k in ks], "o-", color=C_MEAS, label="subsampled data"); ax[2].plot(ks, [pow_pred[k] * 100 for k in ks], "--", color=C_PRED, label="non-central t")
    style_axes(ax[2], "number of subjects", "power (%)", "How many subjects would have been enough?")
    p.save(fig, "hypothesis", "Per-subject effect, sorted channel p-values with correction thresholds, and power versus sample size.")
    p.discuss(f"""The Berger effect is unmistakable in these 20 subjects — occipital alpha power rises {10 ** d.mean():.1f}-fold with eyes closed — and the three tests,
built from scratch and matching SciPy, agree (p from {min(pt, pw, pp):.0e} to {max(pt, pw, pp):.0e}). They differ in what they assume: the t-test needs roughly normal
differences, the Wilcoxon test only symmetry, and the sign-flip test enumerates all 2²⁰ relabelings and assumes nothing else. Across 64 electrodes
the multiple-comparison problem is real: relabeling the data at random makes 'at least one significant channel' appear in {any_unc / B * 100:.0f} % of null
experiments without correction, versus {any_bonf / B * 100:.1f} % with Bonferroni. (Independent tests would give 96 %; EEG channels are highly correlated, so
the effective number of tests is much smaller — and Bonferroni is correspondingly conservative.) Finally, a power analysis on the real effect size
(d_z = {dz:.1f}) shows that about {min(k for k in ks if pow_meas[k] > 0.8) if any(pow_meas[k] > 0.8 for k in ks) else 12} subjects already give 80 % power — knowing that before recording is the point of power analysis.""")
# tol-convention: relative tolerances are in percent
