from eelab import *
from eelab.data import physionet

META = dict(
    id="SL-174", title="Premature ventricular contraction detection (inter-patient)", level="H",
    tools="Beat features (RR intervals, QRS width, template correlation) + own logistic regression; MIT-BIH DS1/DS2 inter-patient split",
    summary="Classify beats as normal vs premature ventricular contraction (PVC) using timing and morphology features, trained on one set of "
            "patients and tested on different patients, reporting sensitivity, precision and the gap to an (unrealistic) intra-patient split.",
    problem="An automatic arrhythmia detector must work on patients it has never seen. How much worse is it than the optimistic results "
            "obtained by mixing patients between training and test sets?",
    theory=r"""PVCs arrive early (short pre-RR, long post-RR) and have wide, bizarre QRS complexes. De Chazal et al. (2004) established the inter-patient DS1/DS2 split
because random beat-level splits leak patient-specific morphology into training: published intra-patient accuracies of ~99 % drop to roughly
80–90 % PVC sensitivity inter-patient. Expect the same gap here.""",
    method="""DS1 records 101, 106, 108, 109, 112, 114, 115, 116, 118, 119 (train) and DS2 records 100, 103, 105, 111, 113, 117, 121, 123, 200, 202 (test), first 15 min each,
lead MLII, annotated beat positions. Features: pre-RR, post-RR, local-average-normalised RR, QRS width (energy-based), correlation with the record's median
beat, R amplitude. Logistic regression (gradient descent) with class weighting. Intra-patient comparison: random 50/50 beat split of the same records.""",
    data="Real: MIT-BIH Arrhythmia Database (PhysioNet).",
)

DS1 = ["101", "106", "108", "109", "112", "114", "115", "116", "118", "119"]
DS2 = ["100", "103", "105", "111", "113", "117", "121", "123", "200", "202"]


def features(rec):
    d = physionet("mitdb", rec, 0, 360 * 900, channels=[0], ann="atr")
    x, fs = d["signal"][:, 0].astype(float), d["fs"]
    from eelab.bio import bandpass
    xf = bandpass(x, fs, 0.5, 40)
    s, sym = d["ann_sample"], d["ann_symbol"]
    keep = np.isin(sym, list("NLRejV"))
    s, sym = s[keep], sym[keep]
    w = int(0.25 * fs)
    beats = np.array([xf[k - w: k + w] for k in s[1:-1] if k - w >= 0 and k + w < len(xf)])
    ss = np.array([k for k in s[1:-1] if k - w >= 0 and k + w < len(xf)])
    lab = np.array([sym[i] == "V" for i in range(1, len(s) - 1) if s[i] - w >= 0 and s[i] + w < len(xf)], int)
    idx = np.searchsorted(s, ss)
    pre = (s[idx] - s[idx - 1]) / fs; post = (s[idx + 1] - s[idx]) / fs
    loc = np.convolve(pre, np.ones(21) / 21, "same")
    tmpl = np.median(beats, axis=0)
    corr = np.array([np.corrcoef(b, tmpl)[0, 1] for b in beats])
    e = beats ** 2; c = np.cumsum(e, axis=1) / e.sum(1, keepdims=True)
    width = (np.argmax(c > 0.9, axis=1) - np.argmax(c > 0.1, axis=1)) / fs
    amp = beats[:, w] / np.median(np.abs(beats[:, w]))
    F = np.c_[pre, post, pre / loc, post / pre, width, corr, amp]
    return F, lab


def logreg(X, y, iters=3000, lr=0.1):
    Xb = np.c_[X, np.ones(len(X))]; w = np.zeros(Xb.shape[1])
    cw = np.where(y == 1, 0.5 / y.mean(), 0.5 / (1 - y.mean()))
    for _ in range(iters):
        pr = 1 / (1 + np.exp(-Xb @ w))
        w -= lr * Xb.T @ ((pr - y) * cw) / len(y)
    return w


def scores(y, yh):
    tp = np.sum((y == 1) & (yh == 1)); fp = np.sum((y == 0) & (yh == 1)); fn = np.sum((y == 1) & (yh == 0))
    return tp / max(tp + fn, 1) * 100, tp / max(tp + fp, 1) * 100


def run(p):
    tr = [features(r) for r in DS1]; te = [features(r) for r in DS2]
    Xtr = np.vstack([f for f, _ in tr]); ytr = np.concatenate([l for _, l in tr])
    Xte = np.vstack([f for f, _ in te]); yte = np.concatenate([l for _, l in te])
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    w = logreg((Xtr - mu) / sd, ytr)
    yh = (np.c_[(Xte - mu) / sd, np.ones(len(Xte))] @ w > 0).astype(int)
    se, ppv = scores(yte, yh)
    p.compare("Inter-patient PVC sensitivity (literature ≈ 80–90 %)", 85, se, "%", kind="abs")
    p.compare("Inter-patient PVC positive predictivity (literature ≈ 70–90 %)", 80, ppv, "%", kind="abs")
    Xall = np.vstack([Xtr, Xte]); yall = np.concatenate([ytr, yte])
    perm = p.rng.permutation(len(yall)); h = len(yall) // 2
    a, b = perm[:h], perm[h:]
    mu2, sd2 = Xall[a].mean(0), Xall[a].std(0) + 1e-9
    w2 = logreg((Xall[a] - mu2) / sd2, yall[a])
    yh2 = (np.c_[(Xall[b] - mu2) / sd2, np.ones(len(b))] @ w2 > 0).astype(int)
    se2, ppv2 = scores(yall[b], yh2)
    p.metric("Intra-patient (random beat split) sensitivity / +P", f"{se2:.1f} % / {ppv2:.1f} %", "", "optimistic: same patients in train and test")
    p.metric("Beats", f"train {len(ytr)} ({ytr.sum()} PVC), test {len(yte)} ({yte.sum()} PVC)")
    names = ["pre-RR", "post-RR", "pre/local RR", "post/pre", "QRS width", "template corr", "R amplitude"]
    fig, ax = p.fig(1, 2, w=11)
    ax[0].scatter(Xte[yte == 0, 5], Xte[yte == 0, 4] * 1000, s=2, color=C_MEAS, alpha=.3, label="normal")
    ax[0].scatter(Xte[yte == 1, 5], Xte[yte == 1, 4] * 1000, s=4, color=COLORS[7], alpha=.6, label="PVC")
    style_axes(ax[0], "correlation with median beat", "QRS width (ms)", "Test patients: morphology features")
    ax[1].barh(names, w[:-1], color=C_MEAS)
    style_axes(ax[1], "logistic weight (standardised features)", None, "What the classifier relies on", legend=False)
    p.save(fig, "pvc", "PVCs are wide and unlike the patient's normal beat; timing adds the rest.")
    p.discuss(f"""On these test patients the classifier did *better* than the 80–90 % inter-patient range I predicted from the literature ({se:.0f} % sensitivity,
{ppv:.0f} % precision), and — unusually — no worse than the random beat split. Three reasons, all of which make this an easier test than published
DS2 benchmarks: (1) beat positions come from the reference annotations, so there are no detection errors; (2) only the first 15 minutes of 10 of
the 22 DS2 records are used, and they happen to contain clear, high-amplitude PVCs; (3) the strongest features (template correlation, QRS
width relative to the record's own median beat) are normalised per patient, which is precisely what lets them transfer between people.
Before claiming a real-world number this should be rerun on all of DS2 with detected beats and supraventricular classes included.""")
