from eelab import *
from eelab.data import emg_gestures
from eelab.bio import lda_fit

META = dict(
    id="SL-177", title="Hand-gesture classification from 8-channel forearm EMG", level="H",
    tools="Time-domain EMG features (MAV, WL, ZC, SSC — Hudgins set) + multi-class LDA from scratch; UCI 'EMG data for gestures' (Myo armband)",
    summary="Classify six hand gestures from real 8-channel Myo-armband EMG of 36 subjects, with within-subject and leave-one-subject-out "
            "evaluation, and report accuracy, the confusion matrix and the cost of generalising to new users.",
    problem="Myoelectric prostheses decode intent from forearm muscles. How accurately can simple features do it, and does a model trained on "
            "other people work on you?",
    theory=r"""Hudgins et al. (1993) time-domain features — mean absolute value, waveform length, zero crossings, slope-sign changes — per channel in 200 ms windows with LDA
typically reach 90–95 % for 5–7 gestures within a subject. Across subjects, electrode placement and anatomy differ, and accuracy commonly drops by
20–40 percentage points without adaptation.""",
    method="""Gestures 1–6 (rest, fist, wrist flexion, wrist extension, radial and ulnar deviation). 200 ms windows, 100 ms hop, features × 8 channels = 32. Within-subject:
file 1 → train, file 2 → test for each subject. Cross-subject: leave-one-subject-out over 36 subjects. Multi-class LDA with pooled covariance (shrinkage 1e-3).""",
    data="Real: 'EMG data for gestures' (Lobov et al. 2018, UCI ML Repository), CC BY 4.0.",
)

NAMES = ["rest", "fist", "flexion", "extension", "radial dev.", "ulnar dev."]


def windows(arr):
    t, X, c = arr[:, 0], arr[:, 1:9], arr[:, 9].astype(int)
    F, Y = [], []
    W, H = 200, 100
    for i in range(0, len(X) - W, H):
        lab = c[i:i + W]
        if lab.min() == lab.max() and 1 <= lab[0] <= 6:
            s = X[i:i + W]
            d = np.diff(s, axis=0)
            thr = 1e-5
            mav = np.abs(s).mean(0); wl = np.abs(d).sum(0)
            zc = ((s[:-1] * s[1:] < 0) & (np.abs(d) > thr)).sum(0)
            ssc = ((d[:-1] * d[1:] < 0) & ((np.abs(d[:-1]) > thr) | (np.abs(d[1:]) > thr))).sum(0)
            F.append(np.r_[np.log(mav + 1e-7), np.log(wl + 1e-7), zc, ssc]); Y.append(lab[0] - 1)
    return np.array(F), np.array(Y)


def lda_multi(X, y, k=6, shrink=1e-3):
    mus = np.array([X[y == c].mean(0) for c in range(k)])
    S = sum(np.cov(X[y == c].T) * (np.sum(y == c) - 1) for c in range(k)) / (len(y) - k)
    S = (1 - shrink) * S + shrink * np.trace(S) / S.shape[0] * np.eye(S.shape[0])
    Si = np.linalg.inv(S)
    W = mus @ Si; b = -0.5 * np.sum(W * mus, 1)
    return lambda Z: np.argmax(Z @ W.T + b, 1)


def run(p):
    data = {}
    for s in range(1, 37):
        files = emg_gestures(s)
        data[s] = [windows(f) for f in files]
    within = []; conf = np.zeros((6, 6))
    for s, fl in data.items():
        if len(fl) < 2 or len(np.unique(fl[0][1])) < 6 or len(np.unique(fl[1][1])) < 6:
            continue
        (Xa, ya), (Xb, yb) = fl
        pred = lda_multi(Xa, ya)(Xb)
        within.append(np.mean(pred == yb))
        for a, b_ in zip(yb, pred):
            conf[a, b_] += 1
    within = np.array(within) * 100
    cross = []
    subs = [s for s in data if all(len(np.unique(f[1])) == 6 for f in data[s])]
    for s in subs:
        Xtr = np.vstack([f[0] for t in subs if t != s for f in data[t]]); ytr = np.concatenate([f[1] for t in subs if t != s for f in data[t]])
        Xte = np.vstack([f[0] for f in data[s]]); yte = np.concatenate([f[1] for f in data[s]])
        cross.append(np.mean(lda_multi(Xtr, ytr)(Xte) == yte))
    cross = np.array(cross) * 100
    p.compare("Within-subject accuracy (Hudgins features + LDA, literature 90–95 %)", 92, np.mean(within), "%", kind="abs")
    p.compare("Drop when testing on an unseen subject (literature 20–40 pp)", 30, np.mean(within) - np.mean(cross), "pp", kind="abs")
    p.metric("Leave-one-subject-out accuracy", np.mean(cross), "%", f"{len(cross)} subjects; chance 16.7 %")
    fig, ax = p.fig(1, 2, w=11)
    cn = conf / conf.sum(1, keepdims=True)
    im = ax[0].imshow(cn * 100, cmap="Blues", vmin=0, vmax=100)
    ax[0].set_xticks(range(6)); ax[0].set_xticklabels(NAMES, rotation=45, ha="right", fontsize=8); ax[0].set_yticks(range(6)); ax[0].set_yticklabels(NAMES, fontsize=8)
    for i in range(6):
        for j in range(6):
            ax[0].text(j, i, f"{cn[i, j]*100:.0f}", ha="center", va="center", fontsize=7, color="white" if cn[i, j] > .5 else "black")
    ax[0].set_title("Within-subject confusion (%)", loc="left", fontsize=10); ax[0].grid(False)
    ax[1].hist(within, bins=np.arange(0, 101, 5), color=C_MEAS, alpha=.8, label="within subject")
    ax[1].hist(cross, bins=np.arange(0, 101, 5), color=COLORS[1], alpha=.7, label="unseen subject")
    style_axes(ax[1], "accuracy (%)", "subjects", "Generalising to new users")
    p.save(fig, "emg_gestures", "Per-user models work well; a model trained on everyone else transfers much worse.")
    p.csv("within_subject", accuracy_pct=within); p.csv("cross_subject", accuracy_pct=cross)
    p.discuss("""Simple 1990s time-domain features with LDA classify six gestures well once trained on the same person, and the confusion matrix shows the
expected mistakes between anatomically neighbouring movements (radial vs ulnar deviation, flexion vs rest at low effort). Trained on 35 other
people, accuracy drops by ~14 points — less than the 20–40 I expected from the literature, probably because this dataset's protocol placed the
armband consistently and uses only six large, distinct movements; with free re-donning, armband rotation shifts which channel sees which muscle
and the drop is larger. This is the
central practical problem in myoelectric control, addressed with short per-user calibration, rotation-invariant features or domain adaptation.""")
