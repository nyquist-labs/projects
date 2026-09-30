from eelab import *
from eelab import ml
from scipy import stats

META = dict(
    id="AM-174", title="Linear discriminant analysis from scratch", level="M",
    tools="Own multi-class LDA (pooled covariance, shrinkage, priors), Bayes error for Gaussian classes in closed form, equivalence with least-squares regression for two classes, Fisher-criterion check against random directions, small-sample shrinkage study, real EMG gesture data",
    summary="Derive LDA as the Bayes classifier for Gaussian classes with a common covariance, verify its error rate against the closed form, confirm "
            "it maximises the Fisher criterion and coincides with least squares for two classes, and study how shrinkage rescues it when training data are scarce — on synthetic data and on real EMG.",
    problem="LDA is the default classifier for EMG and EEG interfaces. What does it assume, when is it optimal, and what breaks when there are few training windows?",
    theory=r"""For classes $\mathcal N(μ_k,Σ)$ the Bayes rule is linear: choose k maximising $x^TΣ^{-1}μ_k-\tfrac12μ_k^TΣ^{-1}μ_k+\ln π_k$. Two classes with equal priors: error $=Φ(-Δ/2)$, $Δ^2=(μ_1-μ_0)^TΣ^{-1}(μ_1-μ_0)$ (Mahalanobis distance).
The direction $w=Σ^{-1}(μ_1-μ_0)$ maximises the Fisher ratio $\frac{(w^T(μ_1-μ_0))^2}{w^TΣw}$ and is proportional to the least-squares regression of the class label on x. With n training samples in d dimensions the estimated covariance
is poorly conditioned when n ≈ d; shrinking it toward a scaled identity trades bias for variance.""",
    method="""Synthetic: d = 10, Δ = 1, 2, 3; 2000 training and 200 000 test samples. Fisher check: 2000 random directions. Small-sample study: d = 32 (the EMG feature dimension), 40 to 640 training windows per subject drawn from real data, shrinkage 0,
0.01, 0.1, 0.3. Real data: six gestures, 36 subjects, train on one recording, test on the other.""",
    data="UCI 'EMG data for gestures' (Lobov et al. 2018).",
)


def run(p):
    r = p.rng; d = 10
    A = r.normal(size=(d, d)); S = A @ A.T / d + 0.5 * np.eye(d); Lc = np.linalg.cholesky(S)
    for delta in (1.0, 2.0, 3.0):
        u = r.normal(size=d); u = u / np.sqrt(u @ np.linalg.solve(S, u)) * delta          # μ1 − μ0 with Mahalanobis length Δ
        def draw(n):
            y = r.integers(0, 2, n); return r.normal(size=(n, d)) @ Lc.T + np.outer(y, u), y
        Xtr, ytr = draw(2000); Xte, yte = draw(200000)
        clf = ml.LDA(shrink=0.0).fit(Xtr, ytr); err = np.mean(clf.predict(Xte) != yte)
        p.compare(f"Synthetic Gaussians, Δ = {delta:g}: test error vs Bayes error Φ(−Δ/2)", stats.norm.cdf(-delta / 2) * 100, err * 100, "%", tol=4)
        if delta == 2.0:
            w = clf.W[1] - clf.W[0]
            Xb = np.c_[Xtr, np.ones(len(Xtr))]; wl = np.linalg.lstsq(Xb, ytr * 2.0 - 1, rcond=None)[0][:d]
            p.compare("Two classes: cosine between the LDA direction and the least-squares regression direction", 1.0, float(w @ wl / np.linalg.norm(w) / np.linalg.norm(wl)), "", tol=1e-6)
            Sw = clf.S; dm = clf.mu[1] - clf.mu[0]; Jf = lambda v: (v @ dm) ** 2 / (v @ Sw @ v)
            best_rand = max(Jf(r.normal(size=d)) for _ in range(2000))
            p.compare("Fisher criterion: random directions (2000) that beat the LDA direction", 0, int(best_rand > Jf(w) * (1 + 1e-12)), "", kind="abs")
            p.compare("Fisher ratio at the LDA direction = estimated Δ²", float(dm @ np.linalg.solve(Sw, dm)), float(Jf(w)), "", tol=1e-8)
    D = ml.emg_gesture_features(); X = D["X"].astype(float); accs = []; conf = np.zeros((6, 6), int)
    for s in np.unique(D["subj"]):
        a = (D["subj"] == s) & (D["rec"] == 0); b = (D["subj"] == s) & (D["rec"] == 1)
        if a.sum() < 60 or b.sum() < 60 or len(np.unique(D["y"][a])) < 6:
            continue
        Xa, Xb = ml.standardize(X[a], X[b]); pr = ml.LDA(1e-3).fit(Xa, D["y"][a]).predict(Xb)
        accs.append(np.mean(pr == D["y"][b])); conf += ml.confusion(D["y"][b], pr, 6)
    accs = np.array(accs)
    p.compare("Real EMG, six gestures, per-user LDA: mean accuracy (literature for this feature set: 90–95 %)", 92.0, accs.mean() * 100, "%", kind="abs", tol=5)
    p.metric("Subjects / accuracy range", f"{len(accs)} / {accs.min() * 100:.0f}–{accs.max() * 100:.0f} %", "", "chance 16.7 %")
    off = conf - np.diag(np.diag(conf)); i, j = np.unravel_index(off.argmax(), off.shape)
    p.metric("Most frequent confusion", f"{ml.EMG_NAMES[i]} → {ml.EMG_NAMES[j]}", "", f"{off[i, j]} windows")
    ns = [40, 80, 160, 320, 640]; shr = [0.0, 0.01, 0.1, 0.3]; res = np.zeros((len(shr), len(ns))); cnt = 0
    for s in np.unique(D["subj"])[:24]:
        a = np.flatnonzero((D["subj"] == s) & (D["rec"] == 0)); b = (D["subj"] == s) & (D["rec"] == 1)
        if len(a) < 150 or b.sum() < 60 or len(np.unique(D["y"][a])) < 6:
            continue
        pool = np.flatnonzero(D["subj"] == s); test = np.flatnonzero(b)
        cnt += 1
        for jn, n in enumerate(ns):
            for rep in range(3):
                tr = r.choice(a, min(n, len(a)), replace=False)
                if len(np.unique(D["y"][tr])) < 6 or min(np.bincount(D["y"][tr], minlength=6)) < 2:
                    continue
                Xa, Xb = ml.standardize(X[tr], X[test])
                for js, sh in enumerate(shr):
                    try:
                        res[js, jn] += np.mean(ml.LDA(max(sh, 1e-9)).fit(Xa, D["y"][tr]).predict(Xb) == D["y"][test]) / 3
                    except np.linalg.LinAlgError:
                        pass
    res /= max(cnt, 1)
    p.compare("Few training windows (40, about the feature dimension): shrinkage 0.1 beats no shrinkage (1 = yes)", 1, int(res[2, 0] > res[0, 0]), "", kind="abs")
    p.compare("Plenty of training windows: the unshrunk estimate is as good or better than heavy shrinkage 0.3 (1 = yes)", 1, int(res[0, -1] >= res[3, -1] - 0.002), "", kind="abs")
    p.metric("Accuracy with 40 training windows: shrinkage 0 / 0.01 / 0.1 / 0.3", " / ".join(f"{v * 100:.1f} %" for v in res[:, 0]))
    p.metric("Accuracy with the largest training set: shrinkage 0 / 0.01 / 0.1 / 0.3", " / ".join(f"{v * 100:.1f} %" for v in res[:, -1]))
    fig, ax = p.fig(1, 2, w=11)
    for js, sh in enumerate(shr):
        ax[0].semilogx(ns, res[js] * 100, "o-", color=COLORS[js], label=f"shrinkage {sh:g}")
    style_axes(ax[0], "training windows", "test accuracy (%)", "Shrinkage matters when data are scarce (d = 32)")
    Cn = conf / conf.sum(1, keepdims=True); im = ax[1].imshow(Cn, cmap="Blues", vmin=0, vmax=1)
    ax[1].set_xticks(range(6)); ax[1].set_yticks(range(6)); ax[1].set_xticklabels(ml.EMG_NAMES, rotation=40, ha="right", fontsize=8); ax[1].set_yticklabels(ml.EMG_NAMES, fontsize=8); ax[1].grid(False)
    for a_ in range(6):
        for b_ in range(6):
            ax[1].text(b_, a_, f"{Cn[a_, b_] * 100:.0f}", ha="center", va="center", fontsize=8, color="white" if Cn[a_, b_] > 0.5 else "black")
    ax[1].set_title("Confusion matrix (%), per-user LDA", loc="left", fontsize=10)
    p.save(fig, "lda", "Accuracy of LDA versus training-set size for several shrinkage levels, and the confusion matrix on real EMG.")
    p.discuss(f"""On data that satisfy its assumptions LDA is simply the best possible classifier: the test error lands on the Bayes error Φ(−Δ/2) for every
separation tried, its direction is the one that maximises the Fisher ratio (no random direction did better), and for two classes it coincides with
ordinary least squares on the labels. On real EMG the assumptions hold only roughly, yet per-user accuracy is {accs.mean() * 100:.1f} % over {len(accs)} subjects,
which is why LDA remains the baseline in myoelectric control. Its weak point is the covariance estimate: with 40 training windows for 32 features
the unshrunk classifier scores {res[0, 0] * 100:.0f} %, and blending the covariance with 10 % of a scaled identity lifts it to {res[2, 0] * 100:.0f} %; with hundreds of
windows the shrinkage no longer matters ({res[0, -1] * 100:.1f} vs {res[2, -1] * 100:.1f} %). Shrinkage is the cheap insurance that makes LDA usable after a short calibration.""")
# tol-convention: relative tolerances are in percent
