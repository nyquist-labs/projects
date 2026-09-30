from eelab import *
from eelab import ml

META = dict(
    id="AM-177", title="A neural network from scratch: backpropagation verified", level="H",
    tools="Own multilayer perceptron in NumPy (ReLU, softmax, cross-entropy, Adam), analytic gradients checked against finite differences, XOR as the minimal non-linear problem, human-activity recognition from smartphone IMU features, comparison with softmax regression, over-fitting study",
    summary="Write forward and backward passes by hand, prove the gradients right to seven digits, show the network solving a problem no linear model can, "
            "then train it on a real 6-class activity-recognition benchmark, compare it fairly with a linear baseline and watch it over-fit when data are scarce.",
    problem="What does a neural network actually compute during training, and how do we know the hand-derived gradients are correct?",
    theory=r"""Layer: $a_l=\mathrm{ReLU}(a_{l-1}W_l+b_l)$, output softmax, loss = cross-entropy. Backpropagation is the chain rule applied layer by layer: $δ_L=(p-y)/n$, $\nabla W_l=a_{l-1}^Tδ_l$, $δ_{l-1}=(δ_lW_l^T)\odot[a_{l-1}>0]$.
A correct implementation matches central finite differences to ~10⁻⁷ relative error. One hidden layer suffices to represent XOR, which no linear classifier separates (best possible 75 %). On a well-engineered feature set a linear model is already
strong, so the network's gain is expected to be small; with few training samples a large network memorises (training accuracy 100 %) and generalises worse.""",
    method="""Gradient check on a 5-7-6-3 network (all parameters, step 10⁻⁵, float64). XOR: 2-8-2 network, 400 noisy points. HAR: 561 features, 21 training subjects (7352 windows) and 9 test subjects (2947); network 561-64-6, 25 epochs of Adam; softmax
regression baseline. Over-fitting: 200 training windows, 561-256-6 network without weight decay, versus the same with weight decay 0.03.""",
    data="UCI Human Activity Recognition Using Smartphones (Anguita et al. 2013), fetched on first run.",
)


def run(p):
    r = p.rng
    net = ml.MLP([5, 7, 6, 3], r, l2=1e-3); X = r.normal(size=(20, 5)); y = r.integers(0, 3, 20)
    _, gW, gb = net.loss_grad(X, y); worst = 0; h = 1e-5
    for par, g in zip(net.W + net.b, gW + gb):
        it = np.nditer(par, flags=["multi_index"])
        for _ in it:
            i = it.multi_index; old = par[i]
            par[i] = old + h; lp = net.loss_grad(X, y)[0]; par[i] = old - h; lm = net.loss_grad(X, y)[0]; par[i] = old
            num = (lp - lm) / (2 * h); worst = max(worst, abs(num - g[i]) / max(1e-8, abs(num) + abs(g[i])))
    p.compare("Backpropagation vs central finite differences: worst relative error over all 119 parameters", 0.0, worst, "", kind="abs", tol=1e-6)
    Xx = r.uniform(-1, 1, (400, 2)); yx = ((Xx[:, 0] > 0) ^ (Xx[:, 1] > 0)).astype(int); Xx += r.normal(0, 0.05, Xx.shape)
    lin = ml.Softmax(l2=1e-4, iters=500).fit(Xx, yx); acc_lin = np.mean(lin.predict(Xx) == yx)
    nx = ml.MLP([2, 8, 2], r, l2=0.0).fit(Xx, yx, epochs=200, batch=32, lr=0.01, rng=r); acc_x = np.mean(nx.predict(Xx) == yx)
    p.compare("XOR: best linear classifier cannot beat 75 % (measured accuracy of the linear model ≤ 75 %; 1 = yes)", 1, int(acc_lin <= 0.76), "", kind="abs")
    p.compare("XOR: one hidden layer of 8 units", 100.0, acc_x * 100, "%", kind="abs", tol=3)
    H = ml.har_features(); Xtr, Xte = ml.standardize(H["Xtr"].astype(float), H["Xte"].astype(float)); ytr, yte = H["ytr"], H["yte"]
    hist = []
    net = ml.MLP([561, 64, 6], r, l2=1e-3)
    net.fit(Xtr, ytr, epochs=25, batch=64, lr=1e-3, rng=r, callback=lambda ep, n_: hist.append((np.mean(n_.predict(Xtr) == ytr), np.mean(n_.predict(Xte) == yte))))
    acc_nn = hist[-1][1]
    sm = ml.Softmax(l2=1e-3, lr=0.3, iters=600).fit(Xtr, ytr); acc_sm = np.mean(sm.predict(Xte) == yte)
    p.compare("HAR, 9 unseen subjects: MLP test accuracy (published results on these features: ≈ 95–96 %)", 95.5, acc_nn * 100, "%", kind="abs", tol=2.0)
    p.compare("HAR: linear softmax regression on the same features (expected within ~2 points of the network)", acc_nn * 100, acc_sm * 100, "%", kind="abs", tol=2.5)
    nte = len(yte); se = np.sqrt(acc_nn * (1 - acc_nn) / nte) * 100
    p.metric("Binomial standard error of a test accuracy on 2947 windows", se, "pp", "differences smaller than ~1 point are not meaningful (and windows of one subject are correlated)")
    C = ml.confusion(yte, net.predict(Xte), 6); off = C - np.diag(np.diag(C))
    p.metric("Share of the network's errors that are sitting ↔ standing", (C[3, 4] + C[4, 3]) / off.sum() * 100, "%", "the two static postures differ only in the gravity direction at the waist")
    sub = r.choice(len(ytr), 200, replace=False)
    big = ml.MLP([561, 256, 6], r, l2=0.0).fit(Xtr[sub], ytr[sub], epochs=150, batch=32, lr=1e-3, rng=r)
    reg = ml.MLP([561, 256, 6], r, l2=0.03).fit(Xtr[sub], ytr[sub], epochs=150, batch=32, lr=1e-3, rng=r)
    a_tr, a_te = np.mean(big.predict(Xtr[sub]) == ytr[sub]), np.mean(big.predict(Xte) == yte); r_te = np.mean(reg.predict(Xte) == yte)
    p.compare("200 training windows, 145 000 parameters, no regularisation: training accuracy (memorisation)", 100.0, a_tr * 100, "%", kind="abs", tol=0.5)
    p.compare("… generalisation gap (train − test) is large (> 5 points; 1 = yes)", 1, int(a_tr - a_te > 0.05), "", kind="abs")
    p.metric("Test accuracy with 200 training windows: no weight decay / weight decay 0.03 / full training set", f"{a_te * 100:.1f} % / {r_te * 100:.1f} % / {acc_nn * 100:.1f} %")
    hist = np.array(hist)
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    g = np.linspace(-1.2, 1.2, 150); GX, GY = np.meshgrid(g, g); Z = nx.forward(np.c_[GX.ravel(), GY.ravel()])[-1][:, 1].reshape(GX.shape)
    ax[0].contourf(GX, GY, Z, levels=[0, 0.5, 1], colors=[C_MEAS, C_PRED], alpha=.2); ax[0].scatter(Xx[:, 0], Xx[:, 1], c=np.where(yx > 0, C_PRED, C_MEAS), s=6); ax[0].grid(False)
    ax[0].set_title("XOR: decision regions of a 2-8-2 network", loc="left", fontsize=10)
    ax[1].plot(np.arange(1, 26), hist[:, 0] * 100, color=C_PRED, label="training subjects"); ax[1].plot(np.arange(1, 26), hist[:, 1] * 100, color=C_MEAS, label="unseen subjects"); ax[1].axhline(acc_sm * 100, color="gray", ls=":", label="softmax regression")
    ax[1].set_ylim(88, 100.5)
    style_axes(ax[1], "epoch", "accuracy (%)", "Activity recognition: learning curves")
    Cn = C / C.sum(1, keepdims=True); ax[2].imshow(Cn, cmap="Blues", vmin=0, vmax=1); ax[2].grid(False)
    ax[2].set_xticks(range(6)); ax[2].set_yticks(range(6)); ax[2].set_xticklabels(ml.HAR_NAMES, rotation=40, ha="right", fontsize=8); ax[2].set_yticklabels(ml.HAR_NAMES, fontsize=8)
    for a_ in range(6):
        for b_ in range(6):
            ax[2].text(b_, a_, f"{Cn[a_, b_] * 100:.0f}", ha="center", va="center", fontsize=8, color="white" if Cn[a_, b_] > 0.5 else "black")
    ax[2].set_title("Confusion matrix (%), unseen subjects", loc="left", fontsize=10)
    p.save(fig, "mlp", "A network solving XOR, learning curves on the activity-recognition task, and the test confusion matrix.")
    p.discuss(f"""The hand-written backward pass agrees with finite differences to {worst:.0e} on every parameter — the check that should precede any training run.
With it the network does what linear models cannot (XOR: {acc_x * 100:.0f} % against {acc_lin * 100:.0f} %) and reaches {acc_nn * 100:.1f} % on nine unseen subjects of the
activity benchmark. The instructive comparison is the baseline: plain softmax regression on the same 561 engineered features scores
{acc_sm * 100:.1f} %, a difference of {abs(acc_nn - acc_sm) * 100:.1f} points against a standard error of {se:.1f}. When the features already linearise the problem, a
hidden layer buys little; the largest single group of remaining errors ({(C[3, 4] + C[4, 3]) / off.sum() * 100:.0f} %) is sitting-versus-standing, a limit of the sensor
placement rather than of the classifier. And capacity cuts both ways: given only 200 windows, a 145 000-parameter network fits them perfectly and
scores {a_te * 100:.1f} % on new subjects; weight decay barely changes that ({r_te * 100:.1f} %) — what the small training set lacks is other people's movement,
which no regulariser can supply.""")
# tol-convention: relative tolerances are in percent
