from eelab import *
from eelab.bio import eegmmidb, lda_fit
from scipy import signal
from scipy.linalg import eigh

META = dict(
    id="SL-181", title="Motor-imagery brain–computer interface (CSP + LDA)", level="H",
    tools="Mu/beta band-pass, Common Spatial Patterns (generalised eigenproblem), LDA from scratch, cross-validation; EEG Motor Movement/Imagery DB",
    summary="Classify imagined left- vs right-fist movements from real 64-channel EEG of 10 subjects with the classic CSP + LDA pipeline, "
            "using properly separated cross-validation, and compare accuracy with chance and with the published range.",
    problem="Imagining a hand movement suppresses the 8–30 Hz rhythm over the opposite motor cortex. Can that be read out reliably enough "
            "to control something?",
    theory=r"""Event-related desynchronisation: imagining the left hand lowers mu/beta power over the right motor cortex (C4) and vice versa. CSP finds spatial filters w
maximising $\frac{w^TC_1w}{w^TC_2w}$ (generalised eigenvectors); log-variance of the first/last filters are near-optimal features. Published
single-session accuracies on this dataset with CSP+LDA are typically 60–80 %, with large inter-subject spread (BCI 'illiteracy').""",
    method="""Subjects 1–10, imagery runs R04, R08, R12 (T1 = left fist, T2 = right fist; ~45 trials/subject). 8–30 Hz band-pass, epochs 0.5–2.5 s after cue, CSP (3 filter
pairs) fitted inside each training fold, LDA on log-variance, 5-fold cross-validation. Binomial 95 % chance level for the trial count.""",
    data="Real: EEG Motor Movement/Imagery Database (PhysioNet).",
)


def epochs(subject):
    Xs, ys = [], []
    for run_ in (4, 8, 12):
        X, fs, labels, ann = eegmmidb(subject, run_)
        b, a = signal.butter(4, [8, 30], "bandpass", fs=fs)
        Xf = signal.filtfilt(b, a, X, axis=1)
        for onset, dur, txt in ann:
            if txt in ("T1", "T2"):
                i0 = int((onset + 0.5) * fs); i1 = int((onset + 2.5) * fs)
                if i1 <= Xf.shape[1]:
                    Xs.append(Xf[:, i0:i1]); ys.append(0 if txt == "T1" else 1)
    return np.array(Xs), np.array(ys)


def csp(X, y, m=3):
    cov = lambda E: np.mean([e @ e.T / np.trace(e @ e.T) for e in E], axis=0)
    C1, C2 = cov(X[y == 0]), cov(X[y == 1])
    ev, W = eigh(C1, C1 + C2)
    idx = np.r_[np.arange(m), np.arange(len(ev) - m, len(ev))]
    return W[:, idx]


def feats(X, W):
    Z = np.einsum("ck,tcn->tkn", W, X)
    v = Z.var(axis=2)
    return np.log(v / v.sum(1, keepdims=True))


def run(p):
    from scipy.stats import binom
    accs = []
    for s in range(1, 11):
        X, y = epochs(s)
        idx = p.rng.permutation(len(y)); folds = np.array_split(idx, 5)
        correct = 0
        for k in range(5):
            te = folds[k]; tr = np.setdiff1d(idx, te)
            W = csp(X[tr], y[tr])
            Ftr, Fte = feats(X[tr], W), feats(X[te], W)
            w, b = lda_fit(Ftr, y[tr])
            correct += np.sum(((Fte @ w + b) > 0).astype(int) == y[te])
        accs.append(correct / len(y))
        ntr = len(y)
    accs = np.array(accs) * 100
    chance95 = binom.ppf(0.95, ntr, 0.5) / ntr * 100
    p.compare("Mean CV accuracy over 10 subjects (published CSP+LDA ≈ 60–80 %)", 70, accs.mean(), "%", kind="abs")
    p.metric("Chance level (95 % binomial bound for ~45 trials)", chance95, "%")
    p.metric("Subjects significantly above chance", int(np.sum(accs > chance95)), "", "of 10")
    p.metric("Best / worst subject", f"{accs.max():.0f} % / {accs.min():.0f} %")
    X, y = epochs(1)
    W = csp(X, y)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].bar(np.arange(1, 11), accs, color=[C_MEAS if a > chance95 else COLORS[7] for a in accs])
    ax[0].axhline(chance95, color=C_PRED, ls="--", label="95 % chance bound"); ax[0].axhline(50, color="gray", ls=":")
    style_axes(ax[0], "subject", "CV accuracy (%)", "Left vs right imagined fist")
    F = feats(X, W)
    ax[1].scatter(F[y == 0, 0], F[y == 0, -1], color=COLORS[0], s=18, label="left (T1)"); ax[1].scatter(F[y == 1, 0], F[y == 1, -1], color=COLORS[1], s=18, label="right (T2)")
    style_axes(ax[1], "log-var CSP filter 1", "log-var CSP filter 6", "Subject 1 feature space")
    p.save(fig, "bci", "Some subjects are decoded well, others barely above chance — the familiar BCI spread.")
    p.csv("accuracy", subject=np.arange(1, 11), cv_accuracy_pct=accs)
    p.discuss("""With CSP fitted only on training folds (fitting it on all trials first is a common, inflating mistake) the mean accuracy falls in the published range,
and the per-subject bars show the characteristic spread: a few subjects are decoded well, others barely beat chance with only ~45 trials. A real
brain–computer interface is therefore closer to a skill both the user and the classifier learn together than to a plug-in sensor — and 45 trials
per class is far fewer than practical BCIs use for calibration.""")
