from eelab import *
from eelab import ml
from scipy.special import logsumexp

META = dict(
    id="AM-182", title="Clustering without labels: k-means and Gaussian mixtures", level="M",
    tools="Own k-means (k-means++ seeding) and Gaussian-mixture EM (diagonal covariances, log-domain), monotonicity checks of both objectives, adjusted Rand index and purity against held-back labels, elbow and BIC model selection, restarts and initialisation sensitivity",
    summary="Cluster smartphone-sensor windows without using the activity labels, verify the defining properties of the algorithms (inertia and "
            "likelihood can only improve), and then use the labels to judge what unsupervised structure actually corresponds to: movement versus rest is found perfectly, the six activities are not.",
    problem="Without labels, what structure does a clustering algorithm find in real sensor data — and how do we know whether to believe it?",
    theory=r"""k-means alternates assignment and mean update; each step cannot increase the inertia $\sum_i\|x_i-μ_{c(i)}\|^2$, so it converges (to a local optimum that depends on the start; k-means++ seeding gives an O(log k) guarantee in expectation).
EM for a Gaussian mixture alternates responsibilities (E) and weighted moments (M); the log-likelihood never decreases. BIC = −2 ln L + (parameters)·ln n penalises complexity. Agreement with reference labels: adjusted Rand index (0 = chance,
1 = identical). Clusters reflect the geometry of the features — dominant variance first — which need not match the labels a human would choose.""",
    method="""UCI HAR training set, 561 features standardised and reduced to 20 principal components (k-means and the GMM are distance-based; PCA removes redundant directions). k-means for k = 2…10, 10 restarts each; GMM for the same k. Reference labels: 6
activities, and the coarse split moving (3 activities) vs static (3).""",
    data="UCI Human Activity Recognition Using Smartphones.",
)


def gmm_em(X, k, rng, iters=80):
    n, d = X.shape; lab, C, _ = ml.kmeans(X, k, rng, iters=10)
    mu = C.copy(); var = np.array([X[lab == j].var(0) + 1e-3 if np.any(lab == j) else X.var(0) for j in range(k)]); w = np.bincount(lab, minlength=k) / n + 1e-9
    ll = []
    for _ in range(iters):
        logp = -0.5 * (((X[:, None, :] - mu[None]) ** 2) / var[None]).sum(2) - 0.5 * np.log(2 * pi * var).sum(1)[None] + np.log(w)[None]
        tot = logsumexp(logp, axis=1); ll.append(float(tot.sum())); R = np.exp(logp - tot[:, None])
        Nk = R.sum(0) + 1e-9; w = Nk / n; mu = (R.T @ X) / Nk[:, None]
        var = (R.T @ (X ** 2)) / Nk[:, None] - mu ** 2 + 1e-4
        if len(ll) > 1 and abs(ll[-1] - ll[-2]) < 1e-6 * abs(ll[-1]):
            break
    return R.argmax(1), ll, k * (2 * d) + k - 1


def purity(lab, y):
    return sum(np.bincount(y[lab == c]).max() for c in np.unique(lab)) / len(y)


def run(p):
    H = ml.har_features(); X = ml.standardize(H["Xtr"].astype(float))[0]; y = H["ytr"]; r = p.rng
    comps, var, mu = ml.pca(X, 20); Z = (X - mu) @ comps.T
    lab2, C2, h2 = ml.kmeans(Z, 2, r)
    p.compare("k-means inertia never increases from one iteration to the next (violations, k = 2…10, all restarts)", 0,
              int(sum(np.sum(np.diff(ml.kmeans(Z, k, r)[2]) > 1e-6) for k in range(2, 11) for _ in range(3))), "", kind="abs")
    coarse = (y >= 3).astype(int)
    p.compare("k = 2 recovers 'moving vs static' without labels: purity", 100.0, purity(lab2, coarse) * 100, "%", kind="abs", tol=1.0)
    p.compare("… adjusted Rand index against that split", 1.0, ml.adjusted_rand(lab2, coarse), "", kind="abs", tol=0.03)
    res = {}; inert = []
    for k in range(2, 11):
        best = None
        for _ in range(10):
            lab, C, hist = ml.kmeans(Z, k, r)
            if best is None or hist[-1] < best[1]:
                best = (lab, hist[-1])
        res[k] = best; inert.append(best[1])
    ari6 = ml.adjusted_rand(res[6][0], y)
    p.compare("k = 6 vs the six activity labels: adjusted Rand index (literature for k-means on these features: ≈ 0.45)", 0.45, ari6, "", kind="abs", tol=0.12)
    p.metric("k = 6: purity", purity(res[6][0], y) * 100, "%", "chance for 6 balanced classes ≈ 19 %")
    C = ml.confusion(y, res[6][0], 6)
    p.section("Activities (rows) vs k-means clusters (columns), k = 6", "| | " + " | ".join(f"c{j}" for j in range(6)) + " |\n|---|" + "---|" * 6 + "\n" + "\n".join(f"| {ml.HAR_NAMES[i]} | " + " | ".join(str(v) for v in C[i]) + " |" for i in range(6)))
    inits = [ml.kmeans(Z, 6, r)[2][-1] for _ in range(30)]
    p.metric("k = 6, 30 random restarts: spread of the final inertia (max/min − 1)", (max(inits) / min(inits) - 1) * 100, "%", "different local optima — always restart")
    ll_viol = 0; bic = []; gl = {}
    for k in range(2, 11):
        lab, ll, npar = gmm_em(Z, k, r); ll_viol += int(np.sum(np.diff(ll) < -1e-6 * abs(ll[-1]))); bic.append(-2 * ll[-1] + npar * np.log(len(Z))); gl[k] = lab
    p.compare("EM log-likelihood never decreases (violations, k = 2…10)", 0, ll_viol, "", kind="abs")
    ari_g = ml.adjusted_rand(gl[6], y)
    p.metric("Gaussian mixture, k = 6: adjusted Rand index vs activities", ari_g, "", f"k-means: {ari6:.2f}")
    p.compare("BIC keeps falling up to k = 10 — the data are not six Gaussian blobs (BIC-optimal k > 6; 1 = yes)", 1, int(int(np.argmin(bic)) + 2 > 6), "", kind="abs")
    drop = -np.diff(inert) / np.array(inert[:-1])
    p.metric("Relative inertia drop when adding a cluster, k = 2→3, 3→4, …", ", ".join(f"{v * 100:.0f} %" for v in drop[:6]), "", "no sharp elbow after k = 2")
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    sub = r.choice(len(Z), 2000, replace=False)
    for c in range(6):
        m = res[6][0][sub] == c; ax[0].plot(Z[sub][m, 0], Z[sub][m, 1], ".", ms=3, color=COLORS[c])
    style_axes(ax[0], "PC 1", "PC 2", "k-means clusters (k = 6)", legend=False)
    for c in range(6):
        m = y[sub] == c; ax[1].plot(Z[sub][m, 0], Z[sub][m, 1], ".", ms=3, color=COLORS[c], label=ml.HAR_NAMES[c])
    style_axes(ax[1], "PC 1", "PC 2", "True activities"); ax[1].legend(fontsize=7, markerscale=3)
    ks = np.arange(2, 11); ax[2].plot(ks, np.array(inert) / inert[0], "o-", color=C_MEAS, label="k-means inertia (rel.)"); ax[2].plot(ks, (np.array(bic) - min(bic)) / (max(bic) - min(bic)), "s-", color=C_PRED, label="GMM BIC (scaled)")
    style_axes(ax[2], "number of clusters k", "relative value", "No clear 'right' k")
    p.save(fig, "clustering", "k-means clusters and true activities in the plane of the first two principal components; model-selection curves.")
    p.discuss(f"""Both algorithms behave as their derivations promise — inertia and log-likelihood never moved the wrong way — and both depend on where they start
(the final inertia of 30 k-means runs differs by {(max(inits) / min(inits) - 1) * 100:.0f} %). What they find is instructive. Asked for two clusters, k-means separates moving
from static activities with {purity(lab2, coarse) * 100:.1f} % purity, without ever seeing a label: that split is the dominant structure of the data. Asked for six, it
does not return the six activities (adjusted Rand {ari6:.2f}; the Gaussian mixture gives {ari_g:.2f}): the table shows sitting and standing sharing clusters
while walking styles are split. Neither the elbow nor BIC points to k = 6. The labels humans care about are one of many possible partitions, and
an unsupervised method has no way to know which; cluster-validity numbers measure compactness, not meaning.""")
# tol-convention: relative tolerances are in percent
