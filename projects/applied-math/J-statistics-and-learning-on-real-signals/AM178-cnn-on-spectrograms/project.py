from eelab import *
from eelab import ml
from numpy.lib.stride_tricks import sliding_window_view

META = dict(
    id="AM-178", title="A convolutional network on spectrograms, written in NumPy", level="H",
    tools="Own CNN (3×3 convolutions via sliding windows and einsum, ReLU, 2×2 max-pooling, dense layers, Adam) with hand-derived backward pass, finite-difference gradient check, log-mel spectrograms of spoken digits, comparisons with a dense network and a nearest-centroid baseline, random-recording versus unseen-speaker evaluation",
    summary="Turn one-second audio clips into 32 × 32 log-mel images and classify spoken digits with a small convolutional network implemented from scratch — "
            "gradients verified numerically — then ask the question that matters: does it recognise digits, or the six speakers it was trained on?",
    problem="Why do convolutions suit spectrograms, how is a CNN trained without a deep-learning library, and what does its test accuracy really measure?",
    theory=r"""A convolution layer applies the same small filter at every time–frequency position (weight sharing): far fewer parameters than a dense layer and built-in tolerance to shifts, which pooling reinforces. Backward pass: the gradient w.r.t. the
filters is the correlation of the layer input with the output gradient; the gradient w.r.t. the input is the 'full' correlation with the flipped filters; max-pooling routes the gradient to the winning position.
Expected: CNN > dense network > template matching on unseen recordings of known speakers (published small-CNN results on FSDD: 95–99 %), with a clear drop on a speaker never heard in training.""",
    method="""Free Spoken Digit Dataset: 3000 recordings, 6 speakers, 8 kHz. Features: 32-band log-mel spectrogram, 32 frames centred on the energy centroid. Network: conv 8@3×3 → pool → conv 16@3×3 → pool → dense 64 → 10 (≈ 67 000 parameters), 14 epochs.
Split A (standard): takes 0–4 of every speaker and digit for testing (300), the rest for training. Split B: one speaker held out completely.""",
    data="Free Spoken Digit Dataset (Jakobovski et al., CC BY-SA 4.0), fetched on first run.",
)


class CNN:
    def __init__(self, rng, c1=8, c2=16, hidden=64, size=32, classes=10):
        he = lambda shape, fan: rng.normal(0, np.sqrt(2 / fan), shape)
        self.P = dict(K1=he((c1, 1, 3, 3), 9), b1=np.zeros(c1), K2=he((c2, c1, 3, 3), 9 * c1), b2=np.zeros(c2),
                      W3=he((c2 * (size // 4) ** 2, hidden), c2 * (size // 4) ** 2), b3=np.zeros(hidden), W4=he((hidden, classes), hidden), b4=np.zeros(classes))

    @staticmethod
    def conv(X, K, b):
        Xp = np.pad(X, ((0, 0), (0, 0), (1, 1), (1, 1))); Wn = sliding_window_view(Xp, (3, 3), axis=(2, 3))
        return np.einsum("nchwij,kcij->nkhw", Wn, K, optimize=True) + b[None, :, None, None], Wn

    @staticmethod
    def pool(X):
        n, c, h, w = X.shape; R = X.reshape(n, c, h // 2, 2, w // 2, 2); out = R.max(axis=(3, 5))
        mask = (R == out[:, :, :, None, :, None])
        return out, mask

    def forward(self, X):
        P = self.P; c = {}
        z1, c["w1"] = self.conv(X, P["K1"], P["b1"]); a1 = np.maximum(z1, 0); p1, c["m1"] = self.pool(a1)
        z2, c["w2"] = self.conv(p1, P["K2"], P["b2"]); a2 = np.maximum(z2, 0); p2, c["m2"] = self.pool(a2)
        f = p2.reshape(len(X), -1); h = np.maximum(f @ P["W3"] + P["b3"], 0); pr = ml.softmax(h @ P["W4"] + P["b4"])
        c.update(z1=z1, z2=z2, p1=p1, p2=p2, f=f, h=h)
        return pr, c

    def loss_grad(self, X, y):
        P = self.P; pr, c = self.forward(X); n = len(y)
        loss = -np.mean(np.log(pr[np.arange(n), y] + 1e-300)); G = {}
        d = pr.copy(); d[np.arange(n), y] -= 1; d /= n
        G["W4"] = c["h"].T @ d; G["b4"] = d.sum(0); d = (d @ P["W4"].T) * (c["h"] > 0)
        G["W3"] = c["f"].T @ d; G["b3"] = d.sum(0); d = (d @ P["W3"].T).reshape(c["p2"].shape)
        d = self.unpool(d, c["m2"]) * (c["z2"] > 0)
        G["K2"] = np.einsum("nchwij,nkhw->kcij", c["w2"], d, optimize=True); G["b2"] = d.sum((0, 2, 3))
        dp = np.pad(d, ((0, 0), (0, 0), (1, 1), (1, 1))); Wd = sliding_window_view(dp, (3, 3), axis=(2, 3))
        d = np.einsum("nkhwij,kcij->nchw", Wd, P["K2"][:, :, ::-1, ::-1], optimize=True)
        d = self.unpool(d, c["m1"]) * (c["z1"] > 0)
        G["K1"] = np.einsum("nchwij,nkhw->kcij", c["w1"], d, optimize=True); G["b1"] = d.sum((0, 2, 3))
        return loss, G

    @staticmethod
    def unpool(d, mask):
        n, c, h, _, w, _ = mask.shape
        cnt = mask.sum(axis=(3, 5), keepdims=True)                 # ties share the gradient
        return (mask * (d[:, :, :, None, :, None] / cnt)).reshape(n, c, h * 2, w * 2)

    def fit(self, X, y, epochs, rng, lr=2e-3, batch=50, callback=None):
        m = {k: np.zeros_like(v) for k, v in self.P.items()}; v = {k: np.zeros_like(v_) for k, v_ in self.P.items()}; t = 0
        for ep in range(epochs):
            idx = rng.permutation(len(y))
            for s in range(0, len(y), batch):
                j = idx[s:s + batch]; _, G = self.loss_grad(X[j], y[j]); t += 1
                for k in self.P:
                    m[k] = 0.9 * m[k] + 0.1 * G[k]; v[k] = 0.999 * v[k] + 0.001 * G[k] ** 2
                    self.P[k] -= lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v[k] / (1 - 0.999 ** t)) + 1e-8)
            if callback:
                callback(ep, self)
        return self

    def predict(self, X):
        return np.concatenate([np.argmax(self.forward(X[s:s + 200])[0], 1) for s in range(0, len(X), 200)])


def run(p):
    r = p.rng
    tiny = CNN(r, c1=2, c2=3, hidden=5, size=8, classes=4); X = r.normal(size=(6, 1, 8, 8)); y = r.integers(0, 4, 6)
    _, G = tiny.loss_grad(X, y); worst = 0; h = 1e-5
    for k, par in tiny.P.items():
        flat = par.reshape(-1); gi = G[k].reshape(-1)
        for i in r.choice(len(flat), min(len(flat), 25), replace=False):
            old = flat[i]; flat[i] = old + h; lp = tiny.loss_grad(X, y)[0]; flat[i] = old - h; lm = tiny.loss_grad(X, y)[0]; flat[i] = old
            num = (lp - lm) / (2 * h); worst = max(worst, abs(num - gi[i]) / max(1e-8, abs(num) + abs(gi[i])))
    p.compare("CNN backward pass vs finite differences (sampled parameters of every layer): worst relative error", 0.0, worst, "", kind="abs", tol=1e-5)
    D = ml.fsdd_melspec(); S = D["S"][:, None].astype(np.float64); dg = D["digit"]
    te = D["idx"] < 5; tr = ~te
    curve = []
    net = CNN(r).fit(S[tr], dg[tr], 14, r, callback=lambda ep, n_: curve.append(np.mean(n_.predict(S[te]) == dg[te])))
    acc_cnn = curve[-1]; npar = sum(v.size for v in net.P.values())
    F = S.reshape(len(S), -1); Ftr, Fte = ml.standardize(F[tr], F[te])
    mlp = ml.MLP([1024, 64, 10], r, l2=1e-3).fit(Ftr, dg[tr], epochs=30, batch=50, lr=1e-3, rng=r); acc_mlp = np.mean(mlp.predict(Fte) == dg[te])
    cent = np.array([F[tr][dg[tr] == k].mean(0) for k in range(10)]); acc_cen = np.mean(np.argmin(((F[te][:, None] - cent[None]) ** 2).sum(-1), 1) == dg[te])
    p.compare("Standard split (new takes of known speakers): CNN test accuracy (published small CNNs: 95–99 %)", 97.0, acc_cnn * 100, "%", kind="abs", tol=3)
    p.compare("CNN at least as accurate as the dense network on the same input (1 = yes)", 1, int(acc_cnn >= acc_mlp), "", kind="abs")
    p.metric("Test accuracy: nearest class-mean template / dense 1024-64-10 / CNN", f"{acc_cen * 100:.1f} % / {acc_mlp * 100:.1f} % / {acc_cnn * 100:.1f} %", "", f"300 test clips; CNN has {npar} parameters, the dense net {1024 * 64 + 64 + 64 * 10 + 10}")
    shift = np.roll(S[te], 3, axis=3); acc_cnn_s = np.mean(net.predict(shift) == dg[te]); acc_mlp_s = np.mean(mlp.predict(ml.standardize(F[tr], shift.reshape(len(shift), -1))[1]) == dg[te])
    p.compare("Shift tolerance: accuracy lost when test clips are delayed by 3 frames (37 ms) is smaller for the CNN than for the dense net (1 = yes)", 1, int((acc_cnn - acc_cnn_s) < (acc_mlp - acc_mlp_s)), "", kind="abs")
    p.metric("Accuracy after a 3-frame shift: dense / CNN", f"{acc_mlp_s * 100:.1f} % / {acc_cnn_s * 100:.1f} %")
    accs_lo = []
    for held in (0, len(D["speakers"]) - 1):
        trb = D["speaker"] != held; teb = ~trb
        nb = CNN(r).fit(S[trb], dg[trb], 10, r); accs_lo.append(np.mean(nb.predict(S[teb]) == dg[teb]))
    p.compare("Unseen speaker: accuracy is lower than on new takes of known speakers (1 = yes)", 1, int(np.mean(accs_lo) < acc_cnn), "", kind="abs")
    p.metric("CNN accuracy on a completely held-out speaker (two different speakers tried)", " / ".join(f"{a * 100:.1f} %" for a in accs_lo), "", f"speakers: {D['speakers'][0]}, {D['speakers'][-1]}")
    C = ml.confusion(dg[te], net.predict(S[te]), 10)
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    ex = [int(np.flatnonzero((dg == d_) & te)[0]) for d_ in (0, 3, 7)]
    mos = np.hstack([D["S"][i] for i in ex]); ax[0].imshow(mos, origin="lower", aspect="auto", cmap="magma"); ax[0].grid(False)
    ax[0].set_title("Log-mel 'images' of the digits 0, 3, 7", loc="left", fontsize=10); ax[0].set_xlabel("frame"); ax[0].set_ylabel("mel band")
    ax[1].plot(np.arange(1, len(curve) + 1), np.array(curve) * 100, "o-", color=C_MEAS, label="CNN"); ax[1].axhline(acc_mlp * 100, color=C_PRED, ls="--", label="dense network"); ax[1].axhline(acc_cen * 100, color="gray", ls=":", label="class-mean template")
    style_axes(ax[1], "epoch", "test accuracy (%)", "Known speakers, new takes")
    ax[2].imshow(C, cmap="Blues"); ax[2].grid(False); ax[2].set_xticks(range(10)); ax[2].set_yticks(range(10))
    for a_ in range(10):
        for b_ in range(10):
            if C[a_, b_]:
                ax[2].text(b_, a_, str(C[a_, b_]), ha="center", va="center", fontsize=8, color="white" if C[a_, b_] > 15 else "black")
    ax[2].set_title("CNN confusion matrix (30 clips per digit)", loc="left", fontsize=10)
    p.save(fig, "cnn", "Example spectrograms, test accuracy during training, and the CNN's confusion matrix.")
    p.discuss(f"""A CNN needs no library — sliding windows, two einsum calls per layer and a carefully derived backward pass, which matches finite differences
to {worst:.0e}. On the standard split it recognises {acc_cnn * 100:.1f} % of 300 unseen recordings, against {acc_mlp * 100:.1f} % for a dense network with a similar number of
parameters ({npar} vs {1024 * 64 + 64 + 64 * 10 + 10}) and {acc_cen * 100:.1f} % for class-mean templates. The CNN's lead over the dense network is {round((acc_cnn - acc_mlp) * 300)} clip(s) out of 300 — not a
significant difference (standard error ≈ 0.6 points); on centred, equal-length clips a dense layer has little to lose. The benefit of weight
sharing shows when the input moves: delaying the test clips by three frames costs the dense network {(acc_mlp - acc_mlp_s) * 100:.1f} points and the CNN {(acc_cnn - acc_cnn_s) * 100:.1f}. The standard split, however, tests new takes by speakers the network has
already heard. Holding a speaker out entirely gives {accs_lo[0] * 100:.0f} % and {accs_lo[1] * 100:.0f} % — the honest estimate of performance on a new voice, and a
reminder that with six speakers a model can lean on who is speaking as much as on what is said.""")
# tol-convention: relative tolerances are in percent
