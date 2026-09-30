from eelab import *
from eelab import ml

META = dict(
    id="AM-175", title="Support vector machines: margins, duality and kernels", level="H",
    tools="Own linear soft-margin SVM by dual coordinate descent, primal/dual objective and duality gap, KKT and support-vector checks, geometric margin on separable data, own kernel SVM (simplified SMO) with an RBF kernel, comparison with LDA and logistic regression on real ECG beats",
    summary="Implement the SVM from its optimisation problem, verify the theory that defines it — zero duality gap, KKT conditions, the 2/‖w‖ margin, "
            "only support vectors mattering — then use an RBF kernel on a problem no line can solve and compare all three linear classifiers on real arrhythmia data.",
    problem="What exactly is a 'maximum-margin' classifier, how do we know a solver has found it, and what does the kernel trick add?",
    theory=r"""Primal: $\min_w\tfrac12\|w\|^2+C\sum_i\max(0,1-y_iw^Tx_i)$. Dual: $\max_α\sum_iα_i-\tfrac12\|\sum_iα_iy_ix_i\|^2$, $0\leα_i\le C$, with $w=\sum_iα_iy_ix_i$. Strong duality: the two optima are equal (gap → 0). KKT:
$α_i=0$ ⇒ margin ≥ 1; $0<α_i<C$ ⇒ margin = 1 (on the margin); $α_i=C$ ⇒ margin ≤ 1. Removing non-support vectors leaves the solution unchanged. On separable data the margin width is 2/‖w‖. Replacing $x_i^Tx_j$ by a kernel
$k(x_i,x_j)=e^{-γ\|x_i-x_j\|^2}$ gives a non-linear boundary at the same cost in the dual.""",
    method="""(1) Separable 2-D blobs: margin vs the smallest sample distance to the boundary. (2) PVC detection (7 features, train 10 patients / test 10 others): dual coordinate descent, C = 1, class-balanced by replicating the minority; objectives, KKT violations,
retraining on support vectors only. (3) Two interleaved half-moons: linear vs RBF SVM trained by SMO on 400 points.""",
    data="PhysioNet MIT-BIH Arrhythmia Database (beat features built by eelab.ml.ecg_beats).",
)


def objectives(Xb, y, w, alpha, C):
    m = y * (Xb @ w)
    primal = 0.5 * w @ w + C * np.sum(np.maximum(0, 1 - m)); dual = alpha.sum() - 0.5 * w @ w
    return primal, dual, m


def smo_rbf(X, y, C=5.0, gamma=2.0, tol=1e-3, passes=8, rng=None):
    """Simplified SMO (Platt) for a kernel SVM."""
    n = len(y); K = np.exp(-gamma * ((X[:, None] - X[None]) ** 2).sum(-1)); a = np.zeros(n); b = 0.0; quiet = 0
    while quiet < passes:
        changed = 0
        for i in range(n):
            Ei = (a * y) @ K[i] + b - y[i]
            if (y[i] * Ei < -tol and a[i] < C) or (y[i] * Ei > tol and a[i] > 0):
                j = int(rng.integers(n - 1)); j += j >= i
                Ej = (a * y) @ K[j] + b - y[j]; ai, aj = a[i], a[j]
                Lo, Hi = (max(0, aj - ai), min(C, C + aj - ai)) if y[i] != y[j] else (max(0, ai + aj - C), min(C, ai + aj))
                eta = 2 * K[i, j] - K[i, i] - K[j, j]
                if Lo == Hi or eta >= 0:
                    continue
                a[j] = np.clip(aj - y[j] * (Ei - Ej) / eta, Lo, Hi)
                if abs(a[j] - aj) < 1e-6:
                    continue
                a[i] = ai + y[i] * y[j] * (aj - a[j])
                b1 = b - Ei - y[i] * (a[i] - ai) * K[i, i] - y[j] * (a[j] - aj) * K[i, j]
                b2 = b - Ej - y[i] * (a[i] - ai) * K[i, j] - y[j] * (a[j] - aj) * K[j, j]
                b = b1 if 0 < a[i] < C else b2 if 0 < a[j] < C else (b1 + b2) / 2; changed += 1
        quiet = quiet + 1 if changed == 0 else 0
    return a, b, K


def run(p):
    r = p.rng
    Xs = np.r_[r.normal([-2, -2], 0.6, (100, 2)), r.normal([2, 2], 0.6, (100, 2))]; ys = np.r_[-np.ones(100), np.ones(100)]
    w, al = ml.svm_dcd(Xs, ys, C=1e4, epochs=4000, rng=r, tol=1e-8)
    dist = np.abs(np.c_[Xs, np.ones(200)] @ w) / np.linalg.norm(w[:2])
    # the bias is regularised in this formulation (constant feature), so the margin is measured geometrically
    p.compare("Separable data: distance of the closest points to the boundary on both sides are equal (ratio)", 1.0, dist[ys > 0].min() / dist[ys < 0].min(), "", tol=1)
    p.compare("… and equal 1/‖w‖ in the augmented space projected to the plane: margin width vs 2·(closest distance)", 2 * dist.min(), 2 / np.linalg.norm(w[:2]), "", tol=1)
    p.metric("Support vectors on the separable problem", int(np.sum(al > 1e-8)), "", "of 200 points")
    w_s, al_s = w.copy(), al.copy()
    D = ml.ecg_beats(); tr = D["rec"] < 10; te = ~tr
    Xtr, Xte = ml.standardize(D["F"][tr], D["F"][te]); ytr, yte = D["y"][tr], D["y"][te]
    pos = np.flatnonzero(ytr == 1); neg = r.choice(np.flatnonzero(ytr == 0), 4 * len(pos), replace=False)
    idx = np.r_[np.repeat(pos, 4), neg]; Xa, ya = Xtr[idx], 2.0 * ytr[idx] - 1; C = 1.0
    w, al = ml.svm_dcd(Xa, ya, C=C, epochs=1500, rng=r, tol=1e-6)
    Xab = np.c_[Xa, np.ones(len(Xa))]; pr, du, m = objectives(Xab, ya, w, al, C)
    p.compare("Duality gap (primal − dual) relative to the primal objective", 0.0, (pr - du) / pr, "", kind="abs", tol=2e-3)
    p.compare("w reconstructed from the dual variables Σαᵢyᵢxᵢ (max difference)", 0.0, float(np.max(np.abs(w - (al * ya) @ Xab))), "", kind="abs", tol=1e-8)
    eps = 2e-2
    viol = np.sum((al < 1e-9) & (m < 1 - eps)) + np.sum((al > C - 1e-9) & (m > 1 + eps)) + np.sum((al > 1e-9) & (al < C - 1e-9) & (np.abs(m - 1) > eps))
    p.compare("KKT violations among the training samples (tolerance 0.02 on the margin)", 0, int(viol), "", kind="abs", tol=len(ya) * 0.002)
    sv = al > 1e-9
    w2, _ = ml.svm_dcd(Xa[sv], ya[sv], C=C, epochs=1500, rng=r, tol=1e-6)
    p.compare("Retraining on the support vectors alone gives the same classifier (relative change of w)", 0.0, float(np.linalg.norm(w2 - w) / np.linalg.norm(w)), "", kind="abs", tol=0.02)
    p.metric("Support vectors: on the margin / inside or wrong (α = C) / total samples", f"{int(np.sum(sv & (al < C - 1e-9)))} / {int(np.sum(al > C - 1e-9))} / {len(ya)}")
    sc = np.c_[Xte, np.ones(len(Xte))] @ w; auc_svm = ml.roc_curve(sc, yte)[3]; pred = sc > 0
    se = np.sum(pred & (yte == 1)) / yte.sum(); ppv = np.sum(pred & (yte == 1)) / pred.sum()
    wl, _ = ml.logistic_irls(Xa, (ya + 1) / 2, l2=1e-3); auc_lr = ml.roc_curve(np.c_[Xte, np.ones(len(Xte))] @ wl, yte)[3]
    lda = ml.LDA().fit(Xa, ((ya + 1) / 2).astype(int)); sl = lda.scores(Xte); auc_lda = ml.roc_curve(sl[:, 1] - sl[:, 0], yte)[3]
    p.compare("Linear SVM vs logistic regression on unseen patients: AUC difference (three linear models should be close)", 0.0, auc_svm - auc_lr, "", kind="abs", tol=0.01)
    p.metric("Test AUC: linear SVM / logistic regression / LDA", f"{auc_svm:.4f} / {auc_lr:.4f} / {auc_lda:.4f}")
    p.metric("Linear SVM at its natural threshold: sensitivity / positive predictivity", f"{se * 100:.1f} % / {ppv * 100:.1f} %")
    n = 200; th = r.uniform(0, pi, n)
    Xm = np.r_[np.c_[np.cos(th), np.sin(th)], np.c_[1 - np.cos(th), 0.5 - np.sin(th)]] + r.normal(0, 0.12, (2 * n, 2)); ym = np.r_[-np.ones(n), np.ones(n)]
    wlin, _ = ml.svm_dcd(Xm, ym, C=1.0, epochs=200, rng=r); acc_lin = np.mean(np.sign(np.c_[Xm, np.ones(2 * n)] @ wlin) == ym)
    a, b, K = smo_rbf(Xm, ym, rng=r); acc_rbf = np.mean(np.sign((a * ym) @ K + b) == ym)
    tht = r.uniform(0, pi, 1000); Xt = np.r_[np.c_[np.cos(tht), np.sin(tht)], np.c_[1 - np.cos(tht), 0.5 - np.sin(tht)]] + r.normal(0, 0.12, (2000, 2)); yt = np.r_[-np.ones(1000), np.ones(1000)]
    Kt = np.exp(-2.0 * ((Xt[:, None] - Xm[None]) ** 2).sum(-1)); acc_rbf_t = np.mean(np.sign(Kt @ (a * ym) + b) == yt)
    acc_lin_t = np.mean(np.sign(np.c_[Xt, np.ones(2000)] @ wlin) == yt)
    p.compare("Two half-moons: RBF-kernel SVM test accuracy (a line cannot exceed ≈ 88 %)", 99.0, acc_rbf_t * 100, "%", kind="abs", tol=1.5)
    p.metric("Half-moons test accuracy: linear / RBF", f"{acc_lin_t * 100:.1f} % / {acc_rbf_t * 100:.1f} %", "", f"{int(np.sum(a > 1e-6))} support vectors of 400")
    fig, ax = p.fig(1, 3, w=13, h=4)
    ax[0].scatter(Xs[:, 0], Xs[:, 1], c=np.where(ys > 0, C_PRED, C_MEAS), s=8)
    xx = np.linspace(-4, 4, 50)
    for off, ls in ((0, "-"), (1, "--"), (-1, "--")):
        ax[0].plot(xx, (off - w_s[2] - w_s[0] * xx) / w_s[1], ls, color="k", lw=1)
    svs = al_s > 1e-8; ax[0].scatter(Xs[svs, 0], Xs[svs, 1], s=90, facecolors="none", edgecolors="k")
    ax[0].set_xlim(-4, 4); ax[0].set_ylim(-4, 4)
    style_axes(ax[0], "x₁", "x₂", "Maximum margin: only the circled points matter", legend=False)
    ax[1].hist(m[ya > 0], bins=60, range=(-3, 6), color=C_PRED, alpha=.6, label="PVC"); ax[1].hist(m[ya < 0], bins=60, range=(-3, 6), color=C_MEAS, alpha=.6, label="normal"); ax[1].axvline(1, color="k", ls="--", lw=1)
    style_axes(ax[1], "functional margin yᵢ·wᵀxᵢ", "training beats", "Hinge loss acts only left of 1")
    g = np.linspace(-1.6, 2.6, 160); GX, GY = np.meshgrid(g, np.linspace(-1.2, 1.7, 120)); Gp = np.c_[GX.ravel(), GY.ravel()]
    Z = (np.exp(-2.0 * ((Gp[:, None] - Xm[None]) ** 2).sum(-1)) @ (a * ym) + b).reshape(GX.shape)
    ax[2].contourf(GX, GY, Z, levels=[-10, 0, 10], colors=[C_MEAS, C_PRED], alpha=.18); ax[2].contour(GX, GY, Z, levels=[0], colors="k", linewidths=1)
    ax[2].scatter(Xm[:, 0], Xm[:, 1], c=np.where(ym > 0, C_PRED, C_MEAS), s=6); ax[2].grid(False)
    ax[2].set_title("RBF kernel: a curved boundary from the same dual", loc="left", fontsize=10)
    p.save(fig, "svm", "Maximum-margin separator with its support vectors, margin distribution on real beats, and an RBF-kernel boundary.")
    p.discuss(f"""The solver demonstrably finds the SVM solution: primal and dual objectives meet (relative gap {(pr - du) / pr:.1e}), w equals Σαᵢyᵢxᵢ, the KKT conditions
hold sample by sample, and retraining on the {int(sv.sum())} support vectors alone — {sv.mean() * 100:.0f} % of the training beats — reproduces the classifier. On
separable data the boundary sits exactly midway between the closest points of the two classes. On the real arrhythmia problem the three linear
classifiers are practically indistinguishable (AUC {auc_svm:.3f}, {auc_lr:.3f}, {auc_lda:.3f}): with seven informative features the choice of loss function matters
far less than the features and the train/test protocol. What the SVM adds is the kernel: on the half-moons no line exceeds {acc_lin_t * 100:.0f} %, while the
same dual problem with an RBF kernel reaches {acc_rbf_t * 100:.0f} % using {int(np.sum(a > 1e-6))} support vectors.""")
# tol-convention: relative tolerances are in percent
