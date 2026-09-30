from eelab import *
from eelab import ml

META = dict(
    id="AM-188", title="EMG cursor control: from classifier accuracy to task performance", level="H",
    tools="Per-user LDA on real EMG streamed window by window, Wolpaw information-transfer rate vs mutual information of the confusion matrix, random-walk (Wald) prediction of time-to-target, majority-vote smoothing vs the binomial independence prediction, lag-correlation of classifier errors, closed-loop cursor simulation",
    summary="Turn recorded forearm EMG into a four-direction cursor, and predict how long reaching a target takes from nothing but the classifier's confusion "
            "statistics. Test the independence assumption behind error-smoothing and information-rate formulas against the real decision stream, where errors come in bursts.",
    problem="A gesture classifier is '95 % accurate'. How fast can someone actually move a cursor with it, and do smoothing tricks deliver the gains that textbook formulas promise?",
    theory=r"""Decisions every 100 ms; gestures flexion/extension → left/right, radial/ulnar deviation → up/down. If a step goes toward the target with probability p and away with probability q, the expected time to cover D steps is $D/(p-q)$ decisions
(Wald's identity). Information: Wolpaw's ITR $\log_2N+P\log_2P+(1-P)\log_2\frac{1-P}{N-1}$ bits per decision assumes errors spread evenly; the mutual information of the actual confusion matrix is the exact figure for a memoryless channel. A majority vote over m
decisions with independent errors would succeed with probability $\sum_{k>m/2}\binom mk p^k(1-p)^{m-k}$ (lower bound for more classes). Classifier errors on consecutive, overlapping EMG windows are correlated, so the real gain should be smaller.""",
    method="""36 subjects; LDA trained on recording 1, the decision stream of recording 2 replayed in time order. Cursor: targets 12 steps away along one axis; each decision moves the cursor one step (rest and fist do nothing); 400 simulated reaches per subject by
sampling contiguous stretches of the real decision stream. Majority vote over 5 consecutive decisions.""",
    data="UCI 'EMG data for gestures' (Lobov et al. 2018).",
)

MOVE = {2: (-1, 0), 3: (1, 0), 4: (0, 1), 5: (0, -1)}
OPP = {2: 3, 3: 2, 4: 5, 5: 4}


def mi_bits(C):
    P = C / C.sum(); px = P.sum(1, keepdims=True); py = P.sum(0, keepdims=True); nz = P > 0
    return float(np.sum(P[nz] * np.log2(P[nz] / (px @ py)[nz])))


def run(p):
    D = ml.emg_gesture_features(); X = D["X"].astype(float); r = p.rng
    rows = []; C4 = np.zeros((4, 4)); streams = {}
    for s in np.unique(D["subj"]):
        a = (D["subj"] == s) & (D["rec"] == 0); b = np.flatnonzero((D["subj"] == s) & (D["rec"] == 1))
        if a.sum() < 60 or len(b) < 60 or len(np.unique(D["y"][a])) < 6:
            continue
        b = b[np.argsort(D["start"][b])]; A_, B_ = ml.standardize(X[a], X[b]); pr = ml.LDA(1e-3).fit(A_, D["y"][a]).predict(B_)
        streams[s] = (D["y"][b], pr)
        for g in MOVE:
            for q in MOVE:
                C4[g - 2, q - 2] += np.sum((D["y"][b] == g) & (pr == q))
    Pacc = np.trace(C4) / C4.sum(); N = 4
    wolpaw = np.log2(N) + Pacc * np.log2(Pacc) + (1 - Pacc) * np.log2((1 - Pacc) / (N - 1))
    mi = mi_bits(C4)
    p.compare("Four direction gestures: Wolpaw ITR vs mutual information of the pooled confusion matrix (bits per decision)", mi, wolpaw, "bit", tol=10)
    p.metric("Direction accuracy / bits per decision / bits per minute at 10 decisions/s", f"{Pacc * 100:.1f} % / {mi:.2f} / {mi * 600:.0f}")
    pred_t, meas_t = [], []; Dist = 12
    for s, (yt, pr) in streams.items():
        for g in MOVE:
            idx = np.flatnonzero(yt == g)
            if len(idx) < 30:
                continue
            seq = pr[idx]; pp = np.mean(seq == g); qq = np.mean(seq == OPP[g])
            if pp - qq <= 0.05:
                continue
            pred_t.append(Dist / (pp - qq)); tt = []
            for _ in range(100):
                pos = 0; k = 0; st = int(r.integers(len(seq)))
                while pos < Dist and k < 5000:
                    d_ = seq[(st + k) % len(seq)]; pos += 1 if d_ == g else -1 if d_ == OPP[g] else 0; k += 1
                tt.append(k)
            meas_t.append(np.mean(tt))
    pred_t, meas_t = np.array(pred_t), np.array(meas_t)
    noisy = pred_t > Dist / 0.95
    p.compare("Time to reach a target 12 steps away, error-prone pairs (p − q < 0.95): Wald prediction D/(p − q) vs replayed streams (median ratio)", 1.0, float(np.median(meas_t[noisy] / pred_t[noisy])), "", tol=10)
    p.metric("Reach time on those pairs: predicted / simulated (median)", f"{np.median(pred_t[noisy]) / 10:.2f} s / {np.median(meas_t[noisy]) / 10:.2f} s", "", f"{int(noisy.sum())} of {len(pred_t)} (subject, direction) pairs; the others are almost error-free (minimum possible 1.2 s)")
    p.metric("Worst (subject, direction) pair: predicted / simulated reach time", f"{pred_t.max() / 10:.1f} s / {meas_t[np.argmax(pred_t)] / 10:.1f} s")
    m = 5; acc1 = []; accv = []; predv = []; lagc = []
    for s, (yt, pr) in streams.items():
        ok = (pr == yt).astype(float); acc1.append(ok.mean())
        vote = np.array([np.bincount(pr[i:i + m], minlength=6).argmax() for i in range(len(pr) - m + 1)])
        same = np.array([len(set(yt[i:i + m])) == 1 for i in range(len(pr) - m + 1)])
        accv.append(np.mean(vote[same] == yt[:len(vote)][same])); pa = ok.mean()
        predv.append(sum(__import__("math").comb(m, k) * pa ** k * (1 - pa) ** (m - k) for k in range(m // 2 + 1, m + 1)))
        e = 1 - ok; e = e - e.mean()
        if e.std() > 0:
            lagc.append(np.mean(e[:-1] * e[1:]) / e.var())
    gain_pred = np.mean(predv) - np.mean(acc1); gain_meas = np.mean(accv) - np.mean(acc1)
    p.compare("Majority vote of 5: accuracy gain predicted assuming independent errors vs measured on the real stream (ratio)", 1.0, gain_meas / gain_pred, "", tol=30)
    p.metric("Accuracy: single decision / 5-vote measured / 5-vote if errors were independent", f"{np.mean(acc1) * 100:.1f} % / {np.mean(accv) * 100:.1f} % / {np.mean(predv) * 100:.1f} %")
    p.compare("Classifier errors on consecutive windows are positively correlated (median lag-1 correlation > 0.2; 1 = yes)", 1, int(np.median(lagc) > 0.2), "", kind="abs")
    p.metric("Median lag-1 autocorrelation of the error indicator", float(np.median(lagc)), "", "errors arrive in bursts, during gesture onsets and weak contractions")
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    s0 = list(streams)[0]; yt, pr = streams[s0]; g = 3; seq = pr[yt == g]
    for k_ in range(6):
        pos = [0]; st = int(r.integers(len(seq)))
        for j in range(80):
            d_ = seq[(st + j) % len(seq)]; pos.append(pos[-1] + (1 if d_ == g else -1 if d_ == OPP[g] else 0))
        ax[0].plot(np.arange(81) / 10, pos, lw=1)
    ax[0].axhline(Dist, color="k", ls="--")
    style_axes(ax[0], "time (s)", "cursor position (steps)", "Replayed reaches (one subject, 'extension')", legend=False)
    ax[1].loglog(pred_t / 10, meas_t / 10, "o", ms=4, color=C_MEAS); lim = [min(pred_t.min(), meas_t.min()) / 10, max(pred_t.max(), meas_t.max()) / 10]; ax[1].plot(lim, lim, "--", color=C_PRED, label="prediction = simulation")
    style_axes(ax[1], "predicted D/(p − q) (s)", "simulated reach time (s)", "Wald's identity on real decision streams")
    ax[2].bar(["single", "5-vote\n(measured)", "5-vote\n(independent)"], [np.mean(acc1) * 100, np.mean(accv) * 100, np.mean(predv) * 100], color=[COLORS[7], C_MEAS, C_PRED])
    ax[2].set_ylim(80, 100)
    style_axes(ax[2], "", "accuracy (%)", "Smoothing gains less than independence promises", legend=False)
    p.save(fig, "cursor", "Simulated cursor reaches driven by recorded EMG, predicted vs simulated reach times, and the effect of majority voting.")
    p.discuss(f"""Classifier statistics predict task performance remarkably well when the prediction uses the right quantity. The time to reach a target is set by
the drift p − q (toward minus away from the target), and Wald's identity D/(p − q) matches the replayed real decision streams (median ratio
{np.median(meas_t[noisy] / pred_t[noisy]):.2f} on the pairs where errors matter) — errors that stop the cursor cost time, errors that reverse it cost twice. Wolpaw's information-rate formula and the exact mutual
information of the confusion matrix agree within {abs(wolpaw - mi) / mi * 100:.0f} % at {mi:.2f} bits per decision. The independence assumption is where the formulas
overpromise: consecutive errors are correlated (lag-1 correlation {np.median(lagc):.2f}), so a 5-decision majority vote lifts accuracy from {np.mean(acc1) * 100:.1f} % to
{np.mean(accv) * 100:.1f} %, not to the {np.mean(predv) * 100:.1f} % the binomial formula predicts, and it adds 200 ms of latency. For a real interface the useful targets are the
drift and the burstiness of errors, not the headline accuracy.""")
# tol-convention: relative tolerances are in percent
