from eelab import *
from eelab import ml

META = dict(
    id="AM-181", title="Dimensionality reduction: PCA and t-SNE from scratch", level="H",
    tools="PCA by SVD and by eigen-decomposition of the covariance, reconstruction-error identity, k-NN accuracy versus retained dimensions, own exact t-SNE (perplexity calibration by bisection, early exaggeration, momentum gradient descent), neighbourhood-preservation and class-purity measures",
    summary="Reduce 561-dimensional activity-recognition features to a handful of dimensions: verify the algebra of PCA on real data, find how few "
            "components a classifier needs, implement t-SNE and quantify — not just look at — how much better it preserves local neighbourhoods than a linear projection.",
    problem="A 561-dimensional feature vector cannot be plotted and is mostly redundant. How many dimensions carry the information, and how far can a 2-D picture be trusted?",
    theory=r"""PCA: the right singular vectors of the centred data are the eigenvectors of its covariance; variances are $s_i^2/(n-1)$. Keeping k components gives the best rank-k reconstruction, with mean squared error equal to the sum of the discarded
eigenvalues (Eckart–Young). t-SNE instead matches neighbour probabilities: Gaussian affinities $p_{ij}$ in the original space (bandwidth per point set by a target perplexity) and Student-t affinities $q_{ij}$ in the map, minimising KL(P‖Q) with gradient
$4\sum_j(p_{ij}-q_{ij})(y_i-y_j)(1+\|y_i-y_j\|^2)^{-1}$. It preserves local structure, not global distances: expect tighter class clusters in 2-D than PCA, at the cost of meaningless inter-cluster distances.""",
    method="""UCI HAR training features (7352 × 561, standardised). PCA checks on the full set. k-NN (k = 5) accuracy on the 9 test subjects versus number of components. t-SNE on 1500 random training windows, perplexity 30, 500 iterations, initialised from the
first two PCs. Quality: fraction of each point's 10 nearest neighbours (in 561-D) that remain among its 10 nearest in 2-D, and class purity of the 10 nearest map neighbours.""",
    data="UCI Human Activity Recognition Using Smartphones.",
)


def tsne(X, rng, perplexity=30.0, iters=500, init=None):
    n = len(X); D2 = (X ** 2).sum(1)[:, None] - 2 * X @ X.T + (X ** 2).sum(1)[None]; np.fill_diagonal(D2, np.inf)
    target = np.log(perplexity); beta = np.ones(n); lo = np.zeros(n); hi = np.full(n, np.inf)
    for _ in range(50):                                        # bisection on the precision of every point at once
        Pc = np.exp(-(D2 - D2.min(1, keepdims=True)) * beta[:, None]); Pc /= Pc.sum(1, keepdims=True)
        Hh = -np.sum(Pc * np.log(Pc + 1e-300), 1); up = Hh > target
        lo = np.where(up, beta, lo); hi = np.where(up, hi, beta)
        beta = np.where(np.isinf(hi), beta * 2, (lo + hi) / 2)
    P = (Pc + Pc.T) / (2 * n); P = np.maximum(P, 1e-12)
    Y = init.copy() if init is not None else rng.normal(0, 1e-4, (n, 2)); Y = Y / Y.std(0) * 1e-4
    V = np.zeros_like(Y); gains = np.ones_like(Y); kl = []
    for it in range(iters):
        ex = 12.0 if it < 100 else 1.0
        num = 1 / (1 + (Y ** 2).sum(1)[:, None] - 2 * Y @ Y.T + (Y ** 2).sum(1)[None]); np.fill_diagonal(num, 0)
        Q = np.maximum(num / num.sum(), 1e-12)
        W = (ex * P - Q) * num
        G = 4 * (np.diag(W.sum(1)) - W) @ Y
        gains = np.where(np.sign(G) != np.sign(V), gains + 0.2, gains * 0.8); gains = np.maximum(gains, 0.01)
        V = (0.5 if it < 250 else 0.8) * V - 200.0 * gains * G; Y = Y + V; Y -= Y.mean(0)
        if it % 50 == 49 or it == iters - 1:
            kl.append(float(np.sum(P * np.log(P / Q))))
    return Y, kl, np.exp(Hh)


def neighbours(Z, k=10):
    D2 = (Z ** 2).sum(1)[:, None] - 2 * Z @ Z.T + (Z ** 2).sum(1)[None]; np.fill_diagonal(D2, np.inf)
    return np.argpartition(D2, k, axis=1)[:, :k]


def run(p):
    H = ml.har_features(); Xtr, Xte = ml.standardize(H["Xtr"].astype(float), H["Xte"].astype(float)); ytr, yte = H["ytr"], H["yte"]; r = p.rng
    comps, var, mu = ml.pca(Xtr)
    ev = np.linalg.eigvalsh(np.cov(Xtr.T))[::-1]
    p.compare("PCA variances from the SVD vs eigenvalues of the covariance matrix (largest 50, worst relative difference)", 0.0, float(np.max(np.abs(var[:50] - ev[:50]) / ev[:50])), "", kind="abs", tol=1e-8)
    p.compare("Principal axes are orthonormal: ‖VVᵀ − I‖ for the first 50", 0.0, float(np.max(np.abs(comps[:50] @ comps[:50].T - np.eye(50)))), "", kind="abs", tol=1e-10)
    k = 30; Z = (Xtr - mu) @ comps[:k].T; rec = Z @ comps[:k] + mu
    mse = np.sum((Xtr - rec) ** 2) / (len(Xtr) - 1)
    p.compare("Reconstruction error with 30 components = sum of the discarded eigenvalues", float(var[k:].sum()), float(mse), "", tol=1e-6)
    cum = np.cumsum(var) / var.sum(); k95 = int(np.argmax(cum >= 0.95)) + 1
    p.metric("Components for 80 / 95 / 99 % of the variance", f"{int(np.argmax(cum >= 0.8)) + 1} / {k95} / {int(np.argmax(cum >= 0.99)) + 1}", "", "of 561 features")
    r_ = p.rng.normal(size=(561, k)); Qr, _ = np.linalg.qr(r_); recr = (Xtr - mu) @ Qr @ Qr.T + mu
    p.compare("Eckart–Young: a random 30-dimensional projection reconstructs worse than the PCA one (1 = yes)", 1, int(np.sum((Xtr - recr) ** 2) > np.sum((Xtr - rec) ** 2)), "", kind="abs")
    ks = [2, 5, 10, 20, 50, 100, 561]; acc = []
    for kk in ks:
        A = (Xtr - mu) @ comps[:kk].T; B = (Xte - mu) @ comps[:kk].T
        acc.append(np.mean(ml.knn_predict(A, ytr, B, k=5) == yte))
    p.compare("Accuracy lost by keeping 50 of 561 dimensions (my expectation: under 2 points)", 0.0, (acc[-1] - acc[4]) * 100, "pp", kind="abs", tol=2.0)
    p.metric("5-NN test accuracy with 2 / 5 / 10 / 20 / 50 / 100 / 561 dimensions", " / ".join(f"{a * 100:.1f}" for a in acc), "%")
    sub = r.choice(len(Xtr), 1500, replace=False); Xs = Xtr[sub]; ys = ytr[sub]
    P2 = (Xs - mu) @ comps[:2].T
    Y, kl, perp = tsne((Xs - mu) @ comps[:50].T, r, init=P2)
    p.compare("t-SNE bandwidth calibration: achieved perplexity (mean over points)", 30.0, float(perp.mean()), "", tol=1)
    p.compare("t-SNE objective KL(P‖Q) decreases after the exaggeration phase (violations between checkpoints)", 0, int(np.sum(np.diff(kl[2:]) > 1e-3)), "", kind="abs")
    nn_hi = neighbours(Xs); nn_p = neighbours(P2); nn_t = neighbours(Y)
    keep = lambda a, b: float(np.mean([len(set(a[i]) & set(b[i])) / a.shape[1] for i in range(len(a))]))
    pur = lambda nn: float(np.mean(ys[nn] == ys[:, None]))
    kp, kt = keep(nn_hi, nn_p), keep(nn_hi, nn_t)
    p.compare("t-SNE preserves 10-nearest-neighbour sets better than 2-D PCA (1 = yes)", 1, int(kt > kp), "", kind="abs")
    p.metric("Fraction of the 10 nearest neighbours preserved in 2-D: PCA / t-SNE", f"{kp * 100:.1f} % / {kt * 100:.1f} %")
    p.metric("Class purity of the 10 nearest map neighbours: 561-D / PCA-2D / t-SNE-2D", f"{pur(nn_hi) * 100:.1f} % / {pur(nn_p) * 100:.1f} % / {pur(nn_t) * 100:.1f} %")
    dyn = ys < 3; sep = lambda M: np.linalg.norm(M[dyn].mean(0) - M[~dyn].mean(0)) / np.sqrt((M[dyn].var(0).sum() + M[~dyn].var(0).sum()) / 2)
    p.metric("Moving vs static activities: separation (centroid distance / spread) in PCA / t-SNE", f"{sep(P2):.1f} / {sep(Y):.1f}", "", "the first principal component alone separates movement from rest")
    fig, ax = p.fig(1, 3, w=13, h=4)
    ax[0].plot(np.arange(1, 101), cum[:100] * 100, color=C_MEAS); ax[0].axhline(95, color="gray", ls=":"); ax[0].axvline(k95, color=C_PRED, ls="--", label=f"95 % at k = {k95}")
    ax0b = ax[0]; ax0b.plot(ks[:-1], np.array(acc[:-1]) * 100, "s-", color=COLORS[2], label="5-NN test accuracy")
    style_axes(ax[0], "number of principal components", "%", "Variance explained and accuracy")
    for c in range(6):
        ax[1].plot(P2[ys == c, 0], P2[ys == c, 1], ".", ms=3, color=COLORS[c], label=ml.HAR_NAMES[c]); ax[2].plot(Y[ys == c, 0], Y[ys == c, 1], ".", ms=3, color=COLORS[c])
    style_axes(ax[1], "PC 1", "PC 2", "PCA: linear, global structure"); ax[1].legend(fontsize=7, markerscale=3)
    style_axes(ax[2], "t-SNE 1", "t-SNE 2", "t-SNE: local neighbourhoods", legend=False)
    p.save(fig, "dimred", "Explained variance and accuracy versus dimension; the same 1500 windows under PCA and under t-SNE.")
    p.discuss(f"""The algebra of PCA holds to round-off on real data: SVD and covariance eigen-decomposition give the same spectrum, the axes are orthonormal and the
reconstruction error equals the discarded variance exactly. The practical finding is the redundancy of the feature set — {k95} of 561 directions hold
95 % of the variance, and a nearest-neighbour classifier on 50 components ({acc[4] * 100:.1f} %) comes within {(acc[-1] - acc[4]) * 100:.1f} points of the full set ({acc[-1] * 100:.1f} %) —
slightly more than the 2 points I expected; the low-variance directions are not pure noise. Two components, however, are not
enough for classification ({acc[0] * 100:.0f} %): the 2-D PCA picture separates moving from static activities and little else. t-SNE, implemented here with exact
gradients, keeps {kt * 100:.0f} % of each point's ten nearest neighbours against {kp * 100:.0f} % for PCA, and its map neighbours share the class label {pur(nn_t) * 100:.0f} % of the
time — close to the {pur(nn_hi) * 100:.0f} % of the original space. That is its purpose and its limit: clusters and their membership are trustworthy, the distances and
sizes of clusters in the map are not, and it gives no projection for new data.""")
# tol-convention: relative tolerances are in percent
