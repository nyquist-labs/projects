from eelab import *
from eelab import ml

META = dict(
    id="AM-179", title="Cross-validation done wrong and done right", level="H",
    tools="k-fold, blocked and grouped cross-validation written from scratch, a 1-nearest-neighbour and an LDA classifier, leakage through overlapping windows and through shared subjects on real EMG, the 'feature selection outside the loop' trap on pure noise, nested cross-validation for a tuned hyper-parameter",
    summary="Measure how much an accuracy estimate is inflated by four common validation mistakes — overlapping windows split at random, the same "
            "person in train and test, feature selection before splitting, and reporting the score used for tuning — using real EMG data and a pure-noise control.",
    problem="The same classifier can be reported at 99 % or 80 % depending on how the data were split. Which number predicts performance on new data?",
    theory=r"""Cross-validation estimates generalisation only if test samples are independent of everything used for fitting. (1) Windows that overlap by 50 % share raw samples with their neighbours; a random split puts near-copies of test windows in
the training set (fatal for nearest-neighbour methods). (2) Windows of one person are more alike than windows of different people: random splits measure within-person accuracy, not performance on a new user. (3) Any step that saw the labels —
including feature selection — must be inside the loop; selecting the 20 best of 5000 noise features on all data yields high 'accuracy' on noise. (4) The best cross-validated score over a grid of hyper-parameters is optimistically biased;
nesting the selection removes the bias. Expected honest result on noise: 50 %.""",
    method="""EMG gestures (32 features, 36 subjects, 2 recordings each). (1) Per subject, recording 1 only: random 5-fold vs 5 contiguous blocks per gesture vs train on recording 1 / test on recording 2, with 1-NN and LDA. (2) Pooled windows: random 6-fold vs
leave-6-subjects-out. (3) 60 samples × 5000 Gaussian noise features, random labels, 200 repetitions. (4) LDA shrinkage chosen from 8 values on 12 subjects' first 60 windows: best CV score vs nested CV vs a fresh test set.""",
    data="UCI 'EMG data for gestures' (Lobov et al. 2018).",
)


def acc_lda(Xa, ya, Xb, yb, shrink=1e-3):
    A, B = ml.standardize(Xa, Xb)
    return np.mean(ml.LDA(shrink).fit(A, ya).predict(B) == yb)


def acc_1nn(Xa, ya, Xb, yb):
    A, B = ml.standardize(Xa, Xb)
    return np.mean(ml.knn_predict(A, ya, B) == yb)


def run(p):
    D = ml.emg_gesture_features(); X = D["X"].astype(float); y = D["y"]; r = p.rng
    res = {k: [] for k in ("rand_nn", "block_nn", "cross_nn", "rand_lda", "block_lda", "cross_lda")}
    for s in np.unique(D["subj"]):
        a = np.flatnonzero((D["subj"] == s) & (D["rec"] == 0)); b = np.flatnonzero((D["subj"] == s) & (D["rec"] == 1))
        if len(a) < 120 or len(b) < 60 or len(np.unique(y[a])) < 6:
            continue
        Xa, ya = X[a], y[a]
        for tr, te in ml.kfold(len(a), 5, r):
            res["rand_nn"].append(acc_1nn(Xa[tr], ya[tr], Xa[te], ya[te])); res["rand_lda"].append(acc_lda(Xa[tr], ya[tr], Xa[te], ya[te]))
        order = np.argsort(D["start"][a]); blk = np.zeros(len(a), int)
        for g in range(6):                                          # contiguous fifths of each gesture's windows, in time order
            idx = order[ya[order] == g]; blk[idx] = np.arange(len(idx)) * 5 // max(len(idx), 1)
        for f in range(5):
            tr, te = blk != f, blk == f
            res["block_nn"].append(acc_1nn(Xa[tr], ya[tr], Xa[te], ya[te])); res["block_lda"].append(acc_lda(Xa[tr], ya[tr], Xa[te], ya[te]))
        res["cross_nn"].append(acc_1nn(Xa, ya, X[b], y[b])); res["cross_lda"].append(acc_lda(Xa, ya, X[b], y[b]))
    m = {k: float(np.mean(v)) * 100 for k, v in res.items()}
    p.compare("My expectation: 1-NN on randomly split overlapping windows looks near-perfect (> 98 %; 1 = yes)", 1, int(m["rand_nn"] > 98), "", kind="abs")
    p.compare("Leakage through overlap: random split beats blocked split for 1-NN (1 = yes)", 1, int(m["rand_nn"] > m["block_nn"]), "", kind="abs")
    p.compare("… and the blocked estimate in turn beats a separate recording session (1 = yes)", 1, int(m["block_nn"] > m["cross_nn"]), "", kind="abs")
    p.metric("1-NN accuracy: random windows / blocked in time / other recording", f"{m['rand_nn']:.1f} % / {m['block_nn']:.1f} % / {m['cross_nn']:.1f} %")
    p.metric("LDA accuracy: random windows / blocked in time / other recording", f"{m['rand_lda']:.1f} % / {m['block_lda']:.1f} % / {m['cross_lda']:.1f} %", "", "a smooth model leaks less than a memorising one")
    rnd = [acc_lda(X[tr], y[tr], X[te], y[te]) for tr, te in ml.kfold(len(y), 6, r)]
    grp = [acc_lda(X[tr], y[tr], X[te], y[te]) for tr, te in ml.group_kfold(D["subj"], 6, r)]
    p.compare("Pooled data: random 6-fold overestimates accuracy on people never seen (random > leave-subjects-out; 1 = yes)", 1, int(np.mean(rnd) > np.mean(grp)), "", kind="abs")
    p.metric("Pooled LDA: random 6-fold / leave-6-subjects-out", f"{np.mean(rnd) * 100:.1f} % / {np.mean(grp) * 100:.1f} %", "", f"fold-to-fold std {np.std(rnd) * 100:.1f} / {np.std(grp) * 100:.1f} points")
    wrong, right = [], []
    for _ in range(200):
        Xn = r.normal(size=(60, 5000)); yn = r.permutation(np.r_[np.zeros(30, int), np.ones(30, int)])
        sel_all = np.argsort(-np.abs((Xn[yn == 1].mean(0) - Xn[yn == 0].mean(0)) / Xn.std(0)))[:20]
        aw = ar = 0
        for tr, te in ml.kfold(60, 5, r):
            aw += np.sum(ml.LDA(0.1).fit(Xn[tr][:, sel_all], yn[tr]).predict(Xn[te][:, sel_all]) == yn[te])
            sel = np.argsort(-np.abs((Xn[tr][yn[tr] == 1].mean(0) - Xn[tr][yn[tr] == 0].mean(0)) / Xn[tr].std(0)))[:20]
            ar += np.sum(ml.LDA(0.1).fit(Xn[tr][:, sel], yn[tr]).predict(Xn[te][:, sel]) == yn[te])
        wrong.append(aw / 60); right.append(ar / 60)
    p.compare("Pure noise, feature selection inside the CV loop: accuracy = chance", 50.0, np.mean(right) * 100, "%", kind="abs", tol=2.5)
    p.compare("Pure noise, features selected on all data first: 'accuracy' far above chance (> 85 %; 1 = yes)", 1, int(np.mean(wrong) > 0.85), "", kind="abs")
    p.metric("Accuracy on random labels: selection outside / inside the loop", f"{np.mean(wrong) * 100:.1f} % / {np.mean(right) * 100:.1f} %", "", "60 samples, best 20 of 5000 noise features")
    shr = [1e-4, 1e-3, 1e-2, 0.03, 0.1, 0.2, 0.4, 0.7]; best_cv, nested, fresh = [], [], []
    for s in np.unique(D["subj"])[:12]:
        a = np.flatnonzero((D["subj"] == s) & (D["rec"] == 0)); b = np.flatnonzero((D["subj"] == s) & (D["rec"] == 1))
        if len(a) < 120 or len(b) < 60:
            continue
        sub = r.choice(a, 60, replace=False); Xs, ys = X[sub], y[sub]
        if min(np.bincount(ys, minlength=6)) < 4:
            continue
        folds = ml.kfold(60, 5, r)
        def cv_score(idx, sh, fl):
            out = []
            for tr, te in fl:
                if len(np.unique(ys[idx][tr])) < 6:
                    continue
                out.append(acc_lda(Xs[idx][tr], ys[idx][tr], Xs[idx][te], ys[idx][te], sh))
            return np.mean(out) if out else 0.0
        allidx = np.arange(60); scores = [cv_score(allidx, sh, folds) for sh in shr]; best_cv.append(max(scores)); sh_best = shr[int(np.argmax(scores))]
        outer = []
        for tr, te in folds:
            if len(np.unique(ys[tr])) < 6:
                continue
            inner = ml.kfold(len(tr), 4, r); sc_in = [cv_score(tr, sh, inner) for sh in shr]
            outer.append(acc_lda(Xs[tr], ys[tr], Xs[te], ys[te], shr[int(np.argmax(sc_in))]))
        nested.append(np.mean(outer))
        rest = np.setdiff1d(a, sub); fresh.append(acc_lda(Xs, ys, X[rest], y[rest], sh_best))
    bc, ne, fr = np.mean(best_cv) * 100, np.mean(nested) * 100, np.mean(fresh) * 100
    p.compare("Tuning bias: the best CV score over 8 shrinkage values exceeds the nested-CV estimate (1 = yes)", 1, int(bc > ne), "", kind="abs")
    p.compare("Nested CV is closer than the best tuning score to accuracy on fresh windows of the same recording (1 = yes)", 1, int(abs(ne - fr) < abs(bc - fr)), "", kind="abs")
    p.metric("Tuned LDA, 60 training windows: best CV score / nested CV / fresh data", f"{bc:.1f} % / {ne:.1f} % / {fr:.1f} %")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    names = ["random\nwindows", "blocked\nin time", "other\nrecording"]
    ax[0].bar(np.arange(3) - 0.2, [m["rand_nn"], m["block_nn"], m["cross_nn"]], 0.4, color=C_PRED, label="1-NN"); ax[0].bar(np.arange(3) + 0.2, [m["rand_lda"], m["block_lda"], m["cross_lda"]], 0.4, color=C_MEAS, label="LDA")
    ax[0].set_xticks(range(3)); ax[0].set_xticklabels(names); ax[0].set_ylim(80, 100.5)
    style_axes(ax[0], "", "accuracy (%)", "Same subject: how the split changes the answer")
    ax[1].hist(np.array(wrong) * 100, bins=20, color=C_PRED, alpha=.8, label="selection outside CV"); ax[1].hist(np.array(right) * 100, bins=20, color=C_MEAS, alpha=.8, label="selection inside CV"); ax[1].axvline(50, color="k", ls=":")
    style_axes(ax[1], "'accuracy' on pure noise (%)", "repetitions", "Feature selection must be inside the loop")
    ax[2].bar(["random\n6-fold", "leave-subjects-\nout"], [np.mean(rnd) * 100, np.mean(grp) * 100], yerr=[np.std(rnd) * 100, np.std(grp) * 100], color=[C_PRED, C_MEAS], capsize=5)
    ax[2].set_ylim(60, 100)
    style_axes(ax[2], "", "accuracy (%)", "New windows vs new people", legend=False)
    p.save(fig, "crossval", "Accuracy estimates under different splitting schemes, the noise control for feature selection, and subject-wise validation.")
    p.discuss(f"""Four ways to fool oneself, each measured. With 50 %-overlapping windows a nearest-neighbour classifier scores {m['rand_nn']:.1f} % under a random split,
{m['block_nn']:.1f} % when test windows are contiguous in time and {m['cross_nn']:.1f} % on a separate recording — the first number is mostly a measurement of how similar
adjacent windows are. LDA, which cannot memorise, shows the same ordering with smaller gaps ({m['rand_lda']:.1f} / {m['block_lda']:.1f} / {m['cross_lda']:.1f} %). Pooling
subjects and splitting at random reports {np.mean(rnd) * 100:.1f} % where performance on unseen people is {np.mean(grp) * 100:.1f} % — a smaller gap than I expected for a
pooled model, but note the spread: random folds agree to ±{np.std(rnd) * 100:.1f} points and look reassuringly stable, whereas subject-wise folds vary by
±{np.std(grp) * 100:.1f} points, which is the real uncertainty about the next user. Selecting features before splitting turns pure
noise into {np.mean(wrong) * 100:.0f} % 'accuracy', and the same pipeline with selection inside the loop returns the correct {np.mean(right) * 100:.0f} %. The tuning bias is the
subtlest: the best of eight cross-validated scores ({bc:.1f} %) overstates the nested estimate ({ne:.1f} %). The rule behind all four: the test set must
be as different from the training set as future data will be, and nothing fitted may have seen it.""")
# tol-convention: relative tolerances are in percent
