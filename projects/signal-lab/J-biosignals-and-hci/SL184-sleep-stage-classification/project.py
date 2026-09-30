from eelab import *
from eelab.bio import sleep_edf, epoch_labels
from scipy import signal

META = dict(
    id="SL-184", title="Sleep-stage scoring from EEG (Sleep-EDF)", level="H",
    tools="30-s epoch spectral features (δ, θ, α, σ, β band powers, EOG & EMG power) + softmax classifier; Sleep-EDF Expanded cassette recordings",
    summary="Score Wake, N1, N2, N3 and REM on whole-night recordings using band powers of the Fpz-Cz and Pz-Oz EEG, EOG and chin EMG; train on "
            "one night, test on a different subject's night, and compare with human inter-scorer agreement.",
    problem="Sleep technicians label every 30 s of a night by eye. How far does a simple spectral classifier get toward that?",
    theory=r"""N3 = slow waves (δ 0.5–4 Hz) dominate; N2 = spindles (σ 12–15 Hz) and K-complexes; REM = mixed-frequency EEG with rapid eye movements and low chin EMG;
Wake = α/β with high EMG; N1 = transitional (hardest). Human scorers agree on ~80 % of epochs (κ ≈ 0.75); simple feature-based classifiers typically
reach 70–80 % on unseen subjects, with N1 the worst class.""",
    method="""Train: SC4001 night 1; test: SC4011 night 1 (different subject). Epochs from 30 min before sleep onset to 30 min after the last sleep epoch. Features: log relative
band powers of both EEG channels (Welch, 4-s segments), EOG power 0.5–5 Hz, EMG (1 Hz envelope channel) mean; standardised; softmax regression with
class weighting. Accuracy, per-class recall and Cohen's κ.""",
    data="Real: Sleep-EDF Database Expanded (Kemp et al. 2000, PhysioNet), ODC-By.",
)

BANDS = [(0.5, 2), (2, 4), (4, 8), (8, 12), (12, 15), (15, 30)]
NAMES = ["W", "N1", "N2", "N3", "REM"]


def feats(psg, ann):
    sig, fs = psg["signals"], psg["fs"]
    e1, e2 = sig["EEG Fpz-Cz"], sig["EEG Pz-Oz"]; eog = sig["EOG horizontal"]; emg = sig["EMG submental"]
    f0 = fs["EEG Fpz-Cz"]; n = int(len(e1) / f0 // 30)
    lab = epoch_labels(ann, n)
    sleep = np.flatnonzero((lab >= 1) & (lab <= 4))
    a, b = max(sleep[0] - 60, 0), min(sleep[-1] + 60, n)
    F, Y = [], []
    for k in range(a, b):
        if lab[k] < 0:
            continue
        row = []
        for x in (e1, e2):
            seg = x[int(k * 30 * f0): int((k + 1) * 30 * f0)]
            f, P = signal.welch(seg, f0, nperseg=int(4 * f0))
            tot = P[(f >= 0.5) & (f <= 30)].sum()
            row += [np.log(P[(f >= lo) & (f < hi)].sum() / tot) for lo, hi in BANDS]
        seg = eog[int(k * 30 * f0): int((k + 1) * 30 * f0)]
        f, P = signal.welch(seg, f0, nperseg=int(4 * f0)); row.append(np.log(P[(f >= 0.5) & (f <= 5)].sum() + 1e-12))
        row.append(np.log(np.mean(emg[k * 30: (k + 1) * 30]) - emg.min() + 1e-6))
        F.append(row); Y.append(lab[k])
    return np.array(F), np.array(Y)


def softmax_fit(X, y, k=5, iters=1500):
    W = np.zeros((X.shape[1] + 1, k)); Xb = np.c_[X, np.ones(len(X))]; Y = np.eye(k)[y]
    cw = 1 / np.maximum(np.bincount(y, minlength=k), 1); cw = cw[y] / cw.mean()
    for _ in range(iters):
        Z = Xb @ W; Z -= Z.max(1, keepdims=True); P = np.exp(Z); P /= P.sum(1, keepdims=True)
        W -= 0.3 * (Xb.T @ ((P - Y) * cw[:, None]) / len(y) + 1e-3 * W)
    return W


def run(p):
    Ftr, ytr = feats(*sleep_edf("SC4001E0", "SC4001EC"))
    Fte, yte = feats(*sleep_edf("SC4011E0", "SC4011EH"))
    mu, sd = Ftr.mean(0), Ftr.std(0) + 1e-9
    W = softmax_fit((Ftr - mu) / sd, ytr)
    pred = np.argmax(np.c_[(Fte - mu) / sd, np.ones(len(Fte))] @ W, 1)
    acc = np.mean(pred == yte) * 100
    C = np.zeros((5, 5))
    for a, b in zip(yte, pred):
        C[a, b] += 1
    po = np.trace(C) / C.sum(); pe = (C.sum(0) @ C.sum(1)) / C.sum() ** 2
    kappa = (po - pe) / (1 - pe)
    p.compare("Accuracy on an unseen subject's night (simple classifiers: 70–80 %)", 75, acc, "%", kind="abs")
    p.compare("Cohen's κ (human inter-scorer ≈ 0.75)", 0.75, kappa, "", kind="abs")
    rec = np.diag(C) / np.maximum(C.sum(1), 1) * 100
    for i, n in enumerate(NAMES):
        p.metric(f"Recall {n}", rec[i], "%", f"{int(C.sum(1)[i])} epochs")
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    t = np.arange(len(yte)) * 0.5 / 60
    order = {0: 4, 4: 3, 1: 2, 2: 1, 3: 0}
    ax[0].step(t, [order[v] for v in yte], color="black", lw=1, where="post"); ax[0].set_yticks(range(5)); ax[0].set_yticklabels(["N3", "N2", "N1", "REM", "W"])
    style_axes(ax[0], None, None, "Hypnogram — human expert (SC4011)", legend=False)
    ax[1].step(t, [order[v] for v in pred], color=C_MEAS, lw=1, where="post"); ax[1].set_yticks(range(5)); ax[1].set_yticklabels(["N3", "N2", "N1", "REM", "W"])
    style_axes(ax[1], "time (h)", None, f"Hypnogram — classifier ({acc:.0f} % agreement, κ = {kappa:.2f})", legend=False)
    p.save(fig, "hypnogram", "The classifier reproduces the night's architecture; errors cluster in N1 and at stage transitions.")
    p.csv("confusion", **{f"true_{n}": C[i] for i, n in enumerate(NAMES)})
    p.discuss(f"""Trained on one night and tested on another person, band powers alone recover the sleep architecture — sleep onset, cycles of N2/N3 and REM — with
{acc:.0f} % agreement (κ = {kappa:.2f}) — at the low end of my 70–80 % guess and well below human κ ≈ 0.75. Wake and N3 are recognised well; the worst
class is REM (recall ≈ {rec[4]:.0f} %), not N1 as I expected: REM EEG looks spectrally like N1/light N2, and the features that define REM — bursts of
rapid eye movements and chin-muscle atonia — are poorly captured by a 30-s EOG power and a single EMG level that varies between subjects (training on
one person's EMG scale and testing on another's hurts). N1 (≈ {rec[1]:.0f} %) is also weak, as for human scorers. Deep-learning sleep scorers gain mostly by using context from
neighbouring epochs, since stage transitions follow strong sequential rules the per-epoch classifier ignores.""")
