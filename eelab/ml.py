"""Machine-learning building blocks written from scratch in NumPy (no scikit-learn), plus cached feature sets built
from the public datasets used by the 'statistics and learning on real signals' projects.

Everything here is deliberately small and readable: the projects verify these implementations against theory
(closed-form error rates, duality gaps, finite-difference gradients) or against SciPy where an independent
reference exists."""
import numpy as np
from .data import CACHE

DERIVED = CACHE / "derived"


# ------------------------------------------------------------------ datasets (cached)
def _cached(name, build):
    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / (name + ".npz")
    if path.exists():
        z = np.load(path, allow_pickle=False)
        return {k: z[k] for k in z}
    out = build()
    np.savez_compressed(path, **out)
    return out


EMG_NAMES = ["rest", "fist", "flexion", "extension", "radial dev.", "ulnar dev."]


def emg_gesture_features(W=200, H=100):
    """UCI 'EMG data for gestures' (36 subjects, 8-channel Myo, 1 kHz, two recordings each).
    Hudgins time-domain features per window: log MAV, log WL, ZC, SSC for each channel (32 features).
    Returns dict X, y (0..5), subj, rec (0/1), start (sample index of the window)."""
    def build():
        from .data import emg_gestures
        X, y, s_, r_, st = [], [], [], [], []
        for s in range(1, 37):
            for ri, arr in enumerate(emg_gestures(s)[:2]):
                sig, c = arr[:, 1:9], arr[:, 9].astype(int)
                for i in range(0, len(sig) - W, H):
                    lab = c[i:i + W]
                    if lab.min() == lab.max() and 1 <= lab[0] <= 6:
                        w = sig[i:i + W]; d = np.diff(w, axis=0); thr = 1e-5
                        mav = np.abs(w).mean(0); wl = np.abs(d).sum(0)
                        zc = ((w[:-1] * w[1:] < 0) & (np.abs(d) > thr)).sum(0)
                        ssc = ((d[:-1] * d[1:] < 0) & ((np.abs(d[:-1]) > thr) | (np.abs(d[1:]) > thr))).sum(0)
                        X.append(np.r_[np.log(mav + 1e-7), np.log(wl + 1e-7), zc, ssc]); y.append(lab[0] - 1)
                        s_.append(s); r_.append(ri); st.append(i)
        return dict(X=np.array(X, np.float32), y=np.array(y), subj=np.array(s_), rec=np.array(r_), start=np.array(st))
    return _cached(f"emg_gesture_features_{W}_{H}", build)


DS1 = ["101", "106", "108", "109", "112", "114", "115", "116", "118", "119"]
DS2 = ["100", "103", "105", "111", "113", "117", "121", "123", "200", "202"]
BEAT_FEATURES = ["RR before", "RR after", "RR before / local mean", "RR after / RR before", "QRS width", "template correlation", "R amplitude"]


def ecg_beats():
    """MIT-BIH Arrhythmia DB, first 15 min of 20 records (10 'DS1' training patients, 10 'DS2' test patients).
    Returns dict F (7 timing/morphology features), y (1 = premature ventricular contraction), rec (index into DS1+DS2),
    wave (beat waveforms, ±0.25 s around the annotated beat, band-passed 0.5–40 Hz)."""
    def build():
        from .data import physionet
        from .bio import bandpass
        Fs, ys, rs, ws = [], [], [], []
        for ri, rec in enumerate(DS1 + DS2):
            d = physionet("mitdb", rec, 0, 360 * 900, channels=[0], ann="atr")
            x, fs = d["signal"][:, 0].astype(float), d["fs"]
            xf = bandpass(x, fs, 0.5, 40)
            s, sym = d["ann_sample"], d["ann_symbol"]
            keep = np.isin(sym, list("NLRejV")); s, sym = s[keep], sym[keep]
            w = int(0.25 * fs)
            idx = np.array([i for i in range(1, len(s) - 1) if s[i] - w >= 0 and s[i] + w < len(xf)])
            beats = np.array([xf[s[i] - w: s[i] + w] for i in idx])
            lab = (sym[idx] == "V").astype(int)
            pre = (s[idx] - s[idx - 1]) / fs; post = (s[idx + 1] - s[idx]) / fs
            loc = np.convolve(pre, np.ones(21) / 21, "same")
            tmpl = np.median(beats, axis=0)
            corr = np.array([np.corrcoef(b, tmpl)[0, 1] for b in beats])
            e = beats ** 2; c = np.cumsum(e, axis=1) / e.sum(1, keepdims=True)
            width = (np.argmax(c > 0.9, axis=1) - np.argmax(c > 0.1, axis=1)) / fs
            amp = beats[:, w] / np.median(np.abs(beats[:, w]))
            Fs.append(np.c_[pre, post, pre / loc, post / pre, width, corr, amp]); ys.append(lab)
            rs.append(np.full(len(lab), ri)); ws.append(beats[:, ::2].astype(np.float32))
        return dict(F=np.vstack(Fs), y=np.concatenate(ys), rec=np.concatenate(rs), wave=np.vstack(ws))
    return _cached("mitdb_beats_v1", build)


HAR_NAMES = ["walking", "upstairs", "downstairs", "sitting", "standing", "laying"]


def har_features():
    """UCI HAR (smartphone IMU): the 561 published features. Returns Xtr, ytr (0..5), str (subject), Xte, yte, ste."""
    def build():
        from .data import har
        Xtr, ytr, st = har("train"); Xte, yte, se = har("test")
        return dict(Xtr=Xtr.astype(np.float32), ytr=ytr - 1, str=st, Xte=Xte.astype(np.float32), yte=yte - 1, ste=se)
    return _cached("har_features", build)


# ------------------------------------------------------------------ utilities
def standardize(Xtr, *others):
    mu = Xtr.mean(0); sd = Xtr.std(0) + 1e-9
    return [(Xtr - mu) / sd] + [(X - mu) / sd for X in others]


def confusion(y, yhat, k=None):
    k = k or int(max(y.max(), yhat.max())) + 1
    C = np.zeros((k, k), int); np.add.at(C, (y, yhat), 1)
    return C


def kfold(n, k, rng):
    idx = rng.permutation(n)
    folds = np.array_split(idx, k)
    return [(np.concatenate([folds[j] for j in range(k) if j != i]), folds[i]) for i in range(k)]


def group_kfold(groups, k, rng):
    ug = rng.permutation(np.unique(groups)); parts = np.array_split(ug, k)
    return [(np.flatnonzero(~np.isin(groups, part)), np.flatnonzero(np.isin(groups, part))) for part in parts]


def roc_curve(score, y):
    """ROC by sweeping the threshold over the sorted scores. Returns fpr, tpr, thresholds, auc (trapezoid)."""
    o = np.argsort(-score, kind="stable"); s = score[o]; yy = y[o]
    tp = np.cumsum(yy); fp = np.cumsum(1 - yy)
    last = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]          # one point per distinct score
    tpr = np.r_[0, tp[last] / max(tp[-1], 1)]; fpr = np.r_[0, fp[last] / max(fp[-1], 1)]
    return fpr, tpr, np.r_[np.inf, s[last]], float(np.trapezoid(tpr, fpr))


# ------------------------------------------------------------------ classifiers
class LDA:
    """Multi-class linear discriminant analysis with optional shrinkage of the pooled covariance."""
    def __init__(self, shrink=1e-3):
        self.shrink = shrink

    def fit(self, X, y):
        self.classes = np.unique(y); k = len(self.classes)
        self.mu = np.array([X[y == c].mean(0) for c in self.classes])
        R = X - self.mu[np.searchsorted(self.classes, y)]            # residuals about each class mean
        S = np.atleast_2d(R.T @ R / max(len(y) - k, 1))              # pooled within-class covariance
        S = (1 - self.shrink) * S + self.shrink * np.trace(S) / S.shape[0] * np.eye(S.shape[0])
        self.S = S; Si = np.linalg.inv(S)
        self.W = self.mu @ Si; self.b = -0.5 * np.sum(self.W * self.mu, 1) + np.log(np.array([np.mean(y == c) for c in self.classes]))
        return self

    def scores(self, X):
        return X @ self.W.T + self.b

    def predict(self, X):
        return self.classes[np.argmax(self.scores(X), 1)]


def softmax(Z):
    Z = Z - Z.max(1, keepdims=True); E = np.exp(Z)
    return E / E.sum(1, keepdims=True)


class Softmax:
    """Multinomial logistic regression, L2-regularised, full-batch gradient descent with momentum."""
    def __init__(self, l2=1e-3, lr=0.5, iters=400):
        self.l2, self.lr, self.iters = l2, lr, iters

    def fit(self, X, y):
        n, d = X.shape; k = int(y.max()) + 1
        Y = np.eye(k)[y]; W = np.zeros((d, k)); b = np.zeros(k); vW = np.zeros_like(W); vb = np.zeros_like(b)
        for _ in range(self.iters):
            P = softmax(X @ W + b); G = X.T @ (P - Y) / n + self.l2 * W; g = (P - Y).mean(0)
            vW = 0.9 * vW - self.lr * G; vb = 0.9 * vb - self.lr * g; W += vW; b += vb
        self.W, self.b = W, b
        return self

    def proba(self, X):
        return softmax(X @ self.W + self.b)

    def predict(self, X):
        return np.argmax(X @ self.W + self.b, 1)


def logistic_irls(X, y, l2=0.0, iters=50, tol=1e-10, sample_weight=None):
    """Binary logistic regression by Newton / IRLS. Returns (w including bias as last element, number of iterations)."""
    Xb = np.c_[X, np.ones(len(X))]; w = np.zeros(Xb.shape[1]); sw = np.ones(len(y)) if sample_weight is None else sample_weight
    reg = l2 * np.r_[np.ones(X.shape[1]), 0]
    for it in range(iters):
        pr = 1 / (1 + np.exp(-np.clip(Xb @ w, -35, 35)))
        g = Xb.T @ (sw * (pr - y)) + reg * w
        Hm = (Xb * (sw * pr * (1 - pr))[:, None]).T @ Xb + np.diag(reg) + 1e-10 * np.eye(len(w))
        step = np.linalg.solve(Hm, g); w = w - step
        if np.max(np.abs(step)) < tol:
            break
    return w, it + 1


def svm_dcd(X, y, C=1.0, epochs=50, rng=None, tol=1e-4):
    """Linear soft-margin SVM (L1 hinge loss) by dual coordinate descent (Hsieh et al. 2008). y ∈ {−1, +1}.
    The bias is handled by an appended constant feature. Returns w (with bias last), alpha."""
    rng = rng or np.random.default_rng(0)
    Xb = np.c_[X, np.ones(len(X))]; n = len(y); alpha = np.zeros(n); w = np.zeros(Xb.shape[1]); Qd = np.sum(Xb * Xb, 1)
    for ep in range(epochs):
        worst = 0.0
        for i in rng.permutation(n):
            G = y[i] * (Xb[i] @ w) - 1
            PG = min(G, 0) if alpha[i] == 0 else max(G, 0) if alpha[i] == C else G
            worst = max(worst, abs(PG))
            if PG != 0:
                a_old = alpha[i]; alpha[i] = min(max(a_old - G / Qd[i], 0), C)
                w += (alpha[i] - a_old) * y[i] * Xb[i]
        if worst < tol:
            break
    return w, alpha


class MLP:
    """Fully connected network with ReLU hidden layers and a softmax output, trained by mini-batch Adam."""
    def __init__(self, sizes, rng, l2=1e-4):
        self.W = [rng.normal(0, np.sqrt(2 / a), (a, b)) for a, b in zip(sizes[:-1], sizes[1:])]
        self.b = [np.zeros(b) for b in sizes[1:]]; self.l2 = l2

    def forward(self, X):
        acts = [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            Z = acts[-1] @ W + b
            acts.append(np.maximum(Z, 0) if i < len(self.W) - 1 else softmax(Z))
        return acts

    def loss_grad(self, X, y):
        acts = self.forward(X); n = len(y); P = acts[-1]
        loss = -np.mean(np.log(P[np.arange(n), y] + 1e-300)) + 0.5 * self.l2 * sum(np.sum(W * W) for W in self.W)
        D = P.copy(); D[np.arange(n), y] -= 1; D /= n; gW, gb = [], []
        for i in range(len(self.W) - 1, -1, -1):
            gW.insert(0, acts[i].T @ D + self.l2 * self.W[i]); gb.insert(0, D.sum(0))
            if i:
                D = (D @ self.W[i].T) * (acts[i] > 0)
        return loss, gW, gb

    def fit(self, X, y, epochs=30, batch=64, lr=1e-3, rng=None, callback=None):
        rng = rng or np.random.default_rng(0)
        m = [np.zeros_like(a) for a in self.W + self.b]; v = [np.zeros_like(a) for a in self.W + self.b]; t = 0
        for ep in range(epochs):
            idx = rng.permutation(len(y))
            for s in range(0, len(y), batch):
                j = idx[s:s + batch]; _, gW, gb = self.loss_grad(X[j], y[j]); t += 1
                for k, (par, g) in enumerate(zip(self.W + self.b, gW + gb)):
                    m[k] = 0.9 * m[k] + 0.1 * g; v[k] = 0.999 * v[k] + 0.001 * g * g
                    par -= lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v[k] / (1 - 0.999 ** t)) + 1e-8)
            if callback:
                callback(ep, self)
        return self

    def predict(self, X):
        return np.argmax(self.forward(X)[-1], 1)


# ------------------------------------------------------------------ unsupervised
def pca(X, k=None):
    """PCA by SVD of the centred data. Returns (components [k, d], explained variance [k], mean)."""
    mu = X.mean(0); U, s, Vt = np.linalg.svd(X - mu, full_matrices=False)
    var = s ** 2 / (len(X) - 1)
    return Vt[:k], var[:k], mu


def kmeans(X, k, rng, iters=100):
    """Lloyd's algorithm with k-means++ seeding. Returns (labels, centres, inertia history)."""
    C = [X[rng.integers(len(X))]]
    for _ in range(k - 1):
        d2 = np.min([np.sum((X - c) ** 2, 1) for c in C], 0)
        C.append(X[rng.choice(len(X), p=d2 / d2.sum())])
    C = np.array(C); hist = []
    for _ in range(iters):
        D = ((X ** 2).sum(1)[:, None] - 2 * X @ C.T + (C ** 2).sum(1)[None]); lab = D.argmin(1)
        hist.append(float(D[np.arange(len(X)), lab].sum()))
        Cn = np.array([X[lab == j].mean(0) if np.any(lab == j) else C[j] for j in range(k)])
        if np.allclose(Cn, C):
            break
        C = Cn
    return lab, C, hist


def adjusted_rand(a, b):
    """Adjusted Rand index between two labelings (1 = identical partitions, ≈ 0 = chance agreement)."""
    from math import comb
    ia = np.unique(a, return_inverse=True)[1]; ib = np.unique(b, return_inverse=True)[1]
    C = np.zeros((ia.max() + 1, ib.max() + 1), int); np.add.at(C, (ia, ib), 1)
    s = sum(comb(int(v), 2) for v in C.ravel()); sa = sum(comb(int(v), 2) for v in C.sum(1)); sb = sum(comb(int(v), 2) for v in C.sum(0))
    exp = sa * sb / comb(len(a), 2)
    return (s - exp) / (0.5 * (sa + sb) - exp)


# ------------------------------------------------------------------ spoken digits as images
def fsdd_melspec(n_mels=32, frames=32):
    """Free Spoken Digit Dataset → fixed-size log-mel spectrograms (n_mels × frames), one per recording.
    Returns dict S [N, n_mels, frames] (float32, per-clip standardised), digit, speaker (index), idx (take number), speakers."""
    def build():
        from .data import fsdd
        from scipy import signal as sg
        fs = 8000; nfft = 256; hop = 100
        mel = lambda f: 2595 * np.log10(1 + f / 700); imel = lambda m: 700 * (10 ** (m / 2595) - 1)
        edges = imel(np.linspace(mel(100), mel(3800), n_mels + 2)); fbin = np.fft.rfftfreq(nfft, 1 / fs)
        FB = np.maximum(0, np.minimum((fbin[None] - edges[:-2, None]) / (edges[1:-1, None] - edges[:-2, None]),
                                      (edges[2:, None] - fbin[None]) / (edges[2:, None] - edges[1:-1, None])))
        S, dg, sp, ix = [], [], [], []; names = []
        for d, spk, i, x, f_ in fsdd():
            x = x.astype(float); x = x / (np.max(np.abs(x)) + 1e-9)
            _, _, Z = sg.stft(x, fs, nperseg=nfft, noverlap=nfft - hop, window="hann", padded=True)
            M = np.log(FB @ (np.abs(Z) ** 2) + 1e-6)
            e = M.mean(0); c = int(np.round(np.sum(np.arange(len(e)) * (e - e.min())) / max(np.sum(e - e.min()), 1e-9)))   # energy centroid
            lo = max(0, min(c - frames // 2, M.shape[1] - frames)); seg = M[:, lo: lo + frames]
            if seg.shape[1] < frames:
                seg = np.pad(seg, ((0, 0), (0, frames - seg.shape[1])), constant_values=M.min())
            seg = (seg - seg.mean()) / (seg.std() + 1e-9)
            if spk not in names:
                names.append(spk)
            S.append(seg.astype(np.float32)); dg.append(d); sp.append(names.index(spk)); ix.append(i)
        return dict(S=np.array(S), digit=np.array(dg), speaker=np.array(sp), idx=np.array(ix), speakers=np.array(names))
    return _cached(f"fsdd_mel_{n_mels}_{frames}", build)


def knn_predict(Xtr, ytr, Xte, k=1):
    """k-nearest-neighbour classification (Euclidean), brute force in blocks."""
    out = np.zeros(len(Xte), int); n2 = (Xtr ** 2).sum(1)
    for s in range(0, len(Xte), 512):
        B = Xte[s:s + 512]; D2 = (B ** 2).sum(1)[:, None] - 2 * B @ Xtr.T + n2[None]
        if k == 1:
            out[s:s + 512] = ytr[np.argmin(D2, 1)]
        else:
            nn = np.argpartition(D2, k, axis=1)[:, :k]; votes = ytr[nn]
            out[s:s + 512] = np.array([np.bincount(v).argmax() for v in votes])
    return out
