from eelab import *
from eelab.data import har

META = dict(
    id="SL-191", title="Human-activity recognition from smartphone IMU data", level="M",
    tools="Multinomial logistic regression (softmax, gradient descent) from scratch on the 561 UCI-HAR features; subject-independent test split",
    summary="Classify walking, stairs up/down, sitting, standing and lying from a waist-worn phone's accelerometer and gyroscope for "
            "9 unseen test subjects, and compare with the dataset authors' published accuracy.",
    problem="Phones know whether you are walking or sitting. How accurately, and which activities get confused?",
    theory=r"""Dynamic activities differ strongly in acceleration variance and periodicity; static postures differ mainly in the gravity vector's orientation, except
sitting vs standing, which look almost identical at the waist. Anguita et al. (2013) reported 96 % with a multiclass SVM on these features; a linear
softmax model should come close, with most errors between sitting and standing.""",
    method="""Official split: 21 training subjects (7,352 windows) and 9 test subjects (2,947 windows), 2.56-s windows at 50 Hz. Standardised features, softmax
regression with L2 (λ = 1e-3), 800 full-batch gradient steps.""",
    data="Real: UCI Human Activity Recognition Using Smartphones (Anguita et al. 2013), CC BY 4.0.",
)

ACT = ["walking", "upstairs", "downstairs", "sitting", "standing", "lying"]


def run(p):
    Xtr, ytr, _ = har("train"); Xte, yte, _ = har("test")
    ytr -= 1; yte -= 1
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    W = np.zeros((A.shape[1] + 1, 6)); Ab = np.c_[A, np.ones(len(A))]; Y = np.eye(6)[ytr]
    for it in range(800):
        Z = Ab @ W; Z -= Z.max(1, keepdims=True); P = np.exp(Z); P /= P.sum(1, keepdims=True)
        W -= 0.5 * (Ab.T @ (P - Y) / len(A) + 1e-3 * W)
    pred = np.argmax(np.c_[B, np.ones(len(B))] @ W, 1)
    acc = np.mean(pred == yte) * 100
    p.compare("Test accuracy on 9 unseen subjects (published SVM: 96 %)", 96, acc, "%", kind="abs")
    C = np.zeros((6, 6))
    for a, b in zip(yte, pred):
        C[a, b] += 1
    off = C.copy(); np.fill_diagonal(off, 0)
    i, j = np.unravel_index(np.argmax(off), off.shape)
    p.metric("Most common confusion", f"{ACT[i]} → {ACT[j]} ({int(off[i, j])} windows)", "", "predicted: sitting ↔ standing")
    p.compare("Share of all errors that are sitting↔standing", 70, (off[3, 4] + off[4, 3]) / off.sum() * 100, "%", kind="abs")
    fig, ax = p.fig(w=6.5, h=5.5)
    cn = C / C.sum(1, keepdims=True)
    ax.imshow(cn, cmap="Blues", vmin=0, vmax=1)
    for a in range(6):
        for b in range(6):
            ax.text(b, a, f"{cn[a, b]*100:.0f}", ha="center", va="center", fontsize=8, color="white" if cn[a, b] > .5 else "black")
    ax.set_xticks(range(6)); ax.set_xticklabels(ACT, rotation=45, ha="right"); ax.set_yticks(range(6)); ax.set_yticklabels(ACT); ax.grid(False)
    ax.set_title("Confusion matrix (%), unseen subjects", loc="left", fontsize=10)
    p.save(fig, "har", "Dynamic activities are separated cleanly; sitting and standing are the hard pair.")
    p.discuss("""A plain linear softmax model reaches accuracy close to the published SVM on subjects it has never seen — the 561 hand-engineered features already do
most of the work. As predicted, the errors concentrate in sitting vs standing: at the waist both are static with gravity pointing down the
phone's same axis, differing only in subtle tilt. Distinguishing them reliably needs a second sensor location (thigh) or context such as the
transition that preceded the posture.""")
