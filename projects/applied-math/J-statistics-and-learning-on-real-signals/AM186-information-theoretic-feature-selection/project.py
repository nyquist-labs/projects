from eelab import *
from eelab import ml

META = dict(
    id="AM-186", title="Feature selection with mutual information", level="H",
    tools="Plug-in mutual-information estimator on quantile-binned features with Miller–Madow bias correction, validation on distributions with known MI and on shuffled labels, Fano and Hellman–Raviv bounds checked feature by feature, max-relevance vs minimum-redundancy (mRMR) selection, LDA accuracy versus number of features",
    summary="Estimate how many bits each of 561 sensor features carries about the activity being performed, validate the estimator where the answer "
            "is known, confirm the information-theoretic bounds on classification error, and show why the 20 individually best features are a worse set than 20 chosen to avoid redundancy.",
    problem="Out of hundreds of candidate features, which few should a wearable device compute — and what does 'informative' mean quantitatively?",
    theory=r"""$I(X;Y)=\sum p(x,y)\log_2\frac{p(x,y)}{p(x)p(y)}$ bits; 0 iff independent, at most H(Y). The plug-in estimate from a table with $B_x\times B_y$ cells is biased upward by ≈ $\frac{(B_x-1)(B_y-1)}{2N\ln2}$ (Miller–Madow). Known cases: binary
symmetric channel $1-H_2(ε)$; jointly Gaussian $-\tfrac12\log_2(1-ρ^2)$. Any classifier using X obeys Fano's bound $P_e\ge\frac{H(Y|X)-1}{\log_2(K-1)}$; the Bayes classifier obeys $P_e\le\tfrac12H(Y|X)$ (Hellman–Raviv).
Selecting the top-k features by MI ignores that they may all carry the *same* bits; mRMR adds features greedily by relevance minus mean MI with those already chosen.""",
    method="""UCI HAR training set (7352 windows, 561 features, 6 classes), features binned into 10 equal-count bins. Bias check: labels shuffled. Bounds: in-sample Bayes error of each binned feature, 1 − Σₓ max_y p(x, y). Selection from the 150 most relevant
features: top-k by MI, mRMR, and random; LDA trained on the training subjects and tested on the 9 test subjects for k = 3…40.""",
    data="UCI Human Activity Recognition Using Smartphones.",
)


def binned(x, bins=10):
    e = np.quantile(x, np.linspace(0, 1, bins + 1)[1:-1])
    return np.searchsorted(e, x)


def mi_table(a, b, na, nb, correct=True):
    n = len(a); C = np.zeros((na, nb)); np.add.at(C, (a, b), 1); P = C / n
    px = P.sum(1, keepdims=True); py = P.sum(0, keepdims=True); nz = P > 0
    I = np.sum(P[nz] * np.log2(P[nz] / (px @ py)[nz]))
    if correct:
        I -= (np.sum(px > 0) - 1) * (np.sum(py > 0) - 1) / (2 * n * np.log(2))
    return I, P


def run(p):
    r = p.rng; N = 200000
    x = r.integers(0, 2, N); y = x ^ (r.random(N) < 0.1); h2 = lambda e: -e * np.log2(e) - (1 - e) * np.log2(1 - e)
    p.compare("Estimator check, binary symmetric channel ε = 0.1: I = 1 − H₂(ε)", 1 - h2(0.1), mi_table(x, y.astype(int), 2, 2)[0], "bit", tol=1)
    rho = 0.8; g = r.normal(size=(N, 2)); g[:, 1] = rho * g[:, 0] + np.sqrt(1 - rho ** 2) * g[:, 1]
    p.compare("Estimator check, Gaussian pair ρ = 0.8, 30 × 30 bins: I = −½ log₂(1 − ρ²) (binning loses a little)", -0.5 * np.log2(1 - rho ** 2), mi_table(binned(g[:, 0], 30), binned(g[:, 1], 30), 30, 30)[0], "bit", tol=5)
    H = ml.har_features(); X = H["Xtr"].astype(float); y = H["ytr"]; n, d = X.shape
    B = np.array([binned(X[:, j]) for j in range(d)]).T
    hy = -np.sum(np.bincount(y) / n * np.log2(np.bincount(y) / n))
    mi = np.zeros(d); pe = np.zeros(d); hyx = np.zeros(d)
    for j in range(d):
        I_raw, P = mi_table(B[:, j], y, 10, 6, correct=False); mi[j] = mi_table(B[:, j], y, 10, 6)[0]; hyx[j] = hy - I_raw; pe[j] = 1 - P.max(1).sum()
    ys = r.permutation(y); null_raw = np.mean([mi_table(B[:, j], ys, 10, 6, correct=False)[0] for j in range(0, d, 5)]); null_cor = np.mean([mi_table(B[:, j], ys, 10, 6)[0] for j in range(0, d, 5)])
    p.compare("Shuffled labels: raw plug-in MI equals the Miller–Madow bias (B_x−1)(B_y−1)/(2N ln 2)", 9 * 5 / (2 * n * np.log(2)), null_raw, "bit", tol=12)
    p.compare("Shuffled labels: bias-corrected MI", 0.0, null_cor, "bit", kind="abs", tol=5e-4)
    fano = (hyx - 1) / np.log2(5); hr = 0.5 * hyx
    p.compare("Fano lower bound violated by a feature's Bayes error (of 561)", 0, int(np.sum(pe < fano - 1e-12)), "", kind="abs")
    p.compare("Hellman–Raviv upper bound Pₑ ≤ ½H(Y|X) violated (of 561)", 0, int(np.sum(pe > hr + 1e-12)), "", kind="abs")
    p.metric("Class entropy H(Y) / most informative single feature", f"{hy:.2f} bit / {mi.max():.2f} bit", "", f"its single-feature Bayes error: {pe[np.argmax(mi)] * 100:.0f} %")
    pool = np.argsort(-mi)[:150]
    ff = np.zeros((150, 150))
    for a in range(150):
        for b in range(a + 1, 150):
            ff[a, b] = ff[b, a] = mi_table(B[:, pool[a]], B[:, pool[b]], 10, 10)[0]
    sel = [0]
    while len(sel) < 40:
        cand = [c for c in range(150) if c not in sel]
        score = [mi[pool[c]] - ff[c, sel].mean() for c in cand]; sel.append(cand[int(np.argmax(score))])
    mrmr = pool[sel]; top = pool[:40]
    red_top = ff[:20, :20][np.triu_indices(20, 1)].mean(); red_m = ff[np.ix_(sel[:20], sel[:20])][np.triu_indices(20, 1)].mean()
    p.compare("Redundancy (mean pairwise MI) among the first 20 mRMR features is lower than among the top-20 by relevance (1 = yes)", 1, int(red_m < red_top), "", kind="abs")
    p.metric("Mean pairwise MI among 20 selected features: top-MI / mRMR", f"{red_top:.2f} / {red_m:.2f}", "bit", "the top-ranked features are near-copies of one another")
    Xte = H["Xte"].astype(float); yte = H["yte"]; ks = [3, 5, 10, 20, 40]; acc = {"top-MI": [], "mRMR": [], "random": []}
    for k in ks:
        for name, idx in (("top-MI", top[:k]), ("mRMR", mrmr[:k])):
            A_, B_ = ml.standardize(X[:, idx], Xte[:, idx]); acc[name].append(np.mean(ml.LDA(1e-2).fit(A_, y).predict(B_) == yte))
        rr = []
        for _ in range(10):
            idx = r.choice(d, k, replace=False); A_, B_ = ml.standardize(X[:, idx], Xte[:, idx]); rr.append(np.mean(ml.LDA(1e-2).fit(A_, y).predict(B_) == yte))
        acc["random"].append(np.mean(rr))
    p.compare("With 10 features, mRMR beats top-MI selection on unseen subjects (1 = yes)", 1, int(acc["mRMR"][2] > acc["top-MI"][2]), "", kind="abs")
    p.compare("My expectation: the 10 most informative features beat 10 random ones (1 = yes)", 1, int(acc["top-MI"][2] > acc["random"][2]), "", kind="abs")
    p.section("LDA test accuracy (%) vs number of features", "| k | top-k by MI | mRMR | random (mean of 10) |\n|---|---|---|---|\n" + "\n".join(f"| {k} | {acc['top-MI'][i] * 100:.1f} | {acc['mRMR'][i] * 100:.1f} | {acc['random'][i] * 100:.1f} |" for i, k in enumerate(ks)))
    A_, B_ = ml.standardize(X, Xte); full = np.mean(ml.LDA(1e-2).fit(A_, y).predict(B_) == yte)
    p.metric("LDA on all 561 features", full * 100, "%", f"mRMR with 40 features: {acc['mRMR'][-1] * 100:.1f} %")
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    ax[0].plot(np.sort(mi)[::-1], color=C_MEAS); ax[0].axhline(hy, color=C_PRED, ls="--", label=f"H(Y) = {hy:.2f} bit")
    style_axes(ax[0], "feature rank", "I(feature; activity) (bit)", "Information per feature")
    o = np.argsort(hyx); ax[1].plot(hyx[o], pe[o], ".", ms=3, color=C_MEAS, label="features"); xx = np.linspace(hyx.min(), hy, 50)
    ax[1].plot(xx, np.maximum((xx - 1) / np.log2(5), 0), "--", color=C_PRED, label="Fano lower bound"); ax[1].plot(xx, xx / 2, ":", color=COLORS[2], label="Hellman–Raviv upper bound")
    style_axes(ax[1], "H(Y | feature) (bit)", "Bayes error of the binned feature", "Error is boxed in by conditional entropy")
    for name, c in (("top-MI", C_PRED), ("mRMR", C_MEAS), ("random", "gray")):
        ax[2].plot(ks, np.array(acc[name]) * 100, "o-", color=c, label=name)
    ax[2].axhline(full * 100, color="k", ls=":", label="all 561")
    style_axes(ax[2], "number of features", "test accuracy (%)", "Relevance is not enough")
    p.save(fig, "mi_selection", "Mutual information per feature, the Fano and Hellman–Raviv bounds, and accuracy for three selection strategies.")
    p.discuss(f"""The estimator reproduces the known mutual information of a binary symmetric channel and of a Gaussian pair, and on shuffled labels its raw value
equals the Miller–Madow bias — so the numbers on real features can be read as bits. The best single feature carries {mi.max():.2f} of the {hy:.2f} bits needed to
name the activity, and every one of the 561 features respects both bounds that tie conditional entropy to error. The selection experiment shows
the classic trap. The 20 most informative features share {red_top:.2f} bit with each other on average — they are variations of the same measurement —
so ten of them give {acc['top-MI'][2] * 100:.0f} % accuracy, {'no better than' if acc['top-MI'][2] <= acc['random'][2] else 'against'} {acc['random'][2] * 100:.0f} % for ten *random* features. mRMR, which penalises redundancy, reaches
{acc['mRMR'][2] * 100:.0f} % with ten and {acc['mRMR'][-1] * 100:.0f} % with forty (all 561: {full * 100:.0f} %). A feature's value depends on what is already in the set; ranking features one at a
time cannot see that.""")
# tol-convention: relative tolerances are in percent
