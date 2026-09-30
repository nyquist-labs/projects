from eelab import *
from eelab import ml
from eelab.data import emg_gestures
from scipy import stats

META = dict(
    id="AM-173", title="EMG features: what they measure and how much they overlap", level="M",
    tools="Amplitude statistics of surface EMG (MAV/RMS ratio, kurtosis) against Gaussian and Laplacian models, estimator variance versus window length, correlation structure of the Hudgins feature set, Fisher separability, per-feature-family classification with LDA",
    summary="Examine the classic time-domain EMG features on real 8-channel armband recordings: test the Gaussian model of the EMG amplitude, measure how "
            "feature noise falls with window length, show which features carry the same information, and rank them by how well they separate six gestures.",
    problem="Dozens of EMG features exist. Which are genuinely different measurements, how noisy are they, and how long a window do they need?",
    theory=r"""Model: EMG = zero-mean noise whose standard deviation follows muscle activation. For a Gaussian amplitude distribution MAV/RMS = $\sqrt{2/π}$ ≈ 0.798 and kurtosis 3; for a Laplacian 1/√2 ≈ 0.707 and kurtosis 6 (surface EMG at low force is
closer to Laplacian). With N independent Gaussian samples the MAV estimate has coefficient of variation $\sqrt{π/2-1}/\sqrt N$ = 0.756/√N — correlated samples reduce the effective N. Waveform length (Σ|Δx|) is MAV of the differenced signal, so log WL
and log MAV should be highly correlated; zero crossings and slope-sign changes measure frequency content instead.""",
    method="""UCI 'EMG data for gestures' (Myo armband, 8 channels, 36 subjects). Amplitude statistics on gesture segments of subjects 1–10. Estimator noise: features recomputed for 50, 100, 200 and 400-sample windows; within-gesture scatter of log MAV
(per subject, channel and gesture). Separability: Fisher ratio per feature and within-subject LDA accuracy (train on recording 1, test on recording 2) for each feature family and for all 32.""",
    data="UCI Machine Learning Repository, 'EMG data for gestures' (Lobov et al. 2018), fetched on first run.",
)


def within_subject(D, cols):
    acc = []
    for s in np.unique(D["subj"]):
        a = (D["subj"] == s) & (D["rec"] == 0); b = (D["subj"] == s) & (D["rec"] == 1)
        if a.sum() < 60 or b.sum() < 60 or len(np.unique(D["y"][a])) < 6:
            continue
        Xa, Xb = ml.standardize(D["X"][a][:, cols].astype(float), D["X"][b][:, cols].astype(float))
        acc.append(np.mean(ml.LDA().fit(Xa, D["y"][a]).predict(Xb) == D["y"][b]))
    return np.array(acc)


def run(p):
    ratios, kurt, ac1 = [], [], []
    for s in range(1, 11):
        for arr in emg_gestures(s)[:1]:
            sig, c = arr[:, 1:9], arr[:, 9].astype(int)
            for g in range(2, 7):
                seg = sig[c == g]
                if len(seg) < 500:
                    continue
                seg = seg - seg.mean(0); act = seg[:, np.argsort(seg.std(0))[-3:]]              # the three most active channels
                ratios += list(np.abs(act).mean(0) / np.sqrt((act ** 2).mean(0))); kurt += list(stats.kurtosis(act, axis=0, fisher=False))
                ac1 += [np.corrcoef(act[:-1, k], act[1:, k])[0, 1] for k in range(3)]
    mr = float(np.median(ratios))
    p.compare("MAV/RMS of active surface EMG: Gaussian model √(2/π)", np.sqrt(2 / pi), mr, "", tol=4)
    p.metric("… Laplacian model would give", 1 / np.sqrt(2), "", f"measured median {mr:.3f}; median kurtosis {np.median(kurt):.2f} (Gaussian 3, Laplacian 6)")
    p.metric("Lag-1 autocorrelation of the raw EMG samples (median)", float(np.median(ac1)), "", "samples are not independent ⇒ fewer effective samples per window")
    Ws = [50, 100, 200, 400]; sc = []; acc_w = []
    for W in Ws:
        D = ml.emg_gesture_features(W, W // 2)
        sd = []
        for s in range(1, 11):
            for g in range(1, 6):
                m = (D["subj"] == s) & (D["y"] == g) & (D["rec"] == 0)
                if m.sum() > 8:
                    sd.append(D["X"][m][:, :8].astype(float).std(0).mean())
        sc.append(np.mean(sd)); acc_w.append(within_subject(D, np.arange(32)).mean())
    slope = np.polyfit(np.log(Ws), np.log(sc), 1)[0]
    p.compare("Scatter of log MAV within a gesture vs window length: slope −½ if only estimation noise mattered", -0.5, slope, "", kind="abs", tol=0.15)
    pred_cv = np.sqrt(pi / 2 - 1) / np.sqrt(200)
    p.metric("Scatter of log MAV with 200-sample windows: measured vs white-Gaussian prediction 0.756/√N", f"{sc[2]:.3f} vs {pred_cv:.3f}", "", f"ratio {sc[2] / pred_cv:.1f} — real contractions are not stationary")
    p.metric("Within-subject accuracy (all 32 features) at window 50 / 100 / 200 / 400 ms", " / ".join(f"{a * 100:.1f} %" for a in acc_w))
    p.compare("Longer windows help: accuracy at 400 ms > accuracy at 50 ms (1 = yes)", 1, int(acc_w[-1] > acc_w[0]), "", kind="abs")
    D = ml.emg_gesture_features(); X = D["X"].astype(float); fam = {"MAV": np.arange(0, 8), "WL": np.arange(8, 16), "ZC": np.arange(16, 24), "SSC": np.arange(24, 32)}
    cc = []
    for s in np.unique(D["subj"]):
        m = (D["subj"] == s) & (D["y"] > 0)
        cc.append([np.mean([np.corrcoef(X[m][:, fam[a][k]], X[m][:, fam[b][k]])[0, 1] for k in range(8)]) for a in fam for b in fam])
    Cm = np.mean(cc, 0).reshape(4, 4)
    p.compare("Correlation between log MAV and log WL on the same channel (predicted: > 0.9)", 0.95, Cm[0, 1], "", kind="abs", tol=0.06)
    p.compare("ZC and SSC are much less correlated with amplitude than WL is (|r| < 0.6; 1 = yes)", 1, int(abs(Cm[0, 2]) < 0.6 and abs(Cm[0, 3]) < 0.6), "", kind="abs")
    accs = {k: within_subject(D, v) for k, v in fam.items()}; accs["MAV+ZC"] = within_subject(D, np.r_[fam["MAV"], fam["ZC"]]); accs["all 32"] = within_subject(D, np.arange(32))
    for k in ("MAV", "WL", "ZC", "SSC", "MAV+ZC", "all 32"):
        p.metric(f"Within-subject accuracy, {k}", accs[k].mean() * 100, "%", f"{len(accs[k])} subjects, chance 16.7 %")
    accs["MAV+WL"] = within_subject(D, np.r_[fam["MAV"], fam["WL"]])
    p.metric("Within-subject accuracy, MAV+WL", accs["MAV+WL"].mean() * 100, "%")
    p.compare("My expectation: adding ZC to MAV helps more than adding the redundant WL (1 = yes)", 1, int(accs["MAV+WL"].mean() < accs["MAV+ZC"].mean()), "", kind="abs")
    fisher = []
    for j in range(32):
        vals = []
        for s in np.unique(D["subj"])[:20]:
            m = D["subj"] == s; mu = np.array([X[m & (D["y"] == g), j].mean() for g in range(6)]); var = np.mean([X[m & (D["y"] == g), j].var() for g in range(6)])
            vals.append(mu.var() / var)
        fisher.append(np.mean(vals))
    fisher = np.array(fisher)
    p.metric("Mean Fisher ratio (between/within variance) per family: MAV / WL / ZC / SSC", " / ".join(f"{fisher[v].mean():.1f}" for v in fam.values()))
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].hist(ratios, bins=30, color=C_MEAS); ax[0].axvline(np.sqrt(2 / pi), color=C_PRED, ls="--", label="Gaussian 0.798"); ax[0].axvline(1 / np.sqrt(2), color=COLORS[2], ls=":", label="Laplacian 0.707")
    style_axes(ax[0], "MAV / RMS", "segments", "Amplitude distribution of active EMG")
    ax[1].loglog(Ws, sc, "o-", color=C_MEAS, label="measured scatter of log MAV"); ax[1].loglog(Ws, np.sqrt(pi / 2 - 1) / np.sqrt(np.array(Ws)), "--", color=C_PRED, label="0.756/√N (white Gaussian)")
    style_axes(ax[1], "window length (samples)", "within-gesture std of log MAV", "Feature noise vs window length")
    im = ax[2].imshow(Cm, vmin=-1, vmax=1, cmap="RdBu_r"); ax[2].set_xticks(range(4)); ax[2].set_yticks(range(4)); ax[2].set_xticklabels(list(fam)); ax[2].set_yticklabels(list(fam)); ax[2].grid(False)
    for i in range(4):
        for j in range(4):
            ax[2].text(j, i, f"{Cm[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax[2].set_title("Correlation between feature families", loc="left", fontsize=10)
    p.save(fig, "emg_features", "MAV/RMS ratio of real EMG, feature scatter versus window length, and correlation between feature families.")
    p.discuss(f"""The Gaussian model is a fair first description of active surface EMG: the median MAV/RMS ratio is {mr:.3f} against 0.798 (a Laplacian would give
0.707), with a kurtosis of {np.median(kurt):.1f}. It is not a description of a *contraction*, though: the scatter of log MAV between windows of the same gesture is
{sc[2] / pred_cv:.0f}× what estimation noise of a stationary Gaussian signal would give and falls with window length with slope {slope:.2f} rather than −½ —
most of the feature noise is the muscle's force actually wandering, which longer windows cannot average away. The correlation matrix shows why
feature lists overstate their diversity: log WL and log MAV correlate at {Cm[0, 1]:.2f} (waveform length is essentially amplitude), whereas zero crossings
and slope-sign changes measure frequency content. I expected that complementary information to pay off; on this dataset it does not. Amplitude
alone classifies six gestures at {accs['MAV'].mean() * 100:.1f} %, ZC or SSC alone at only {accs['ZC'].mean() * 100:.0f} % and {accs['SSC'].mean() * 100:.0f} %, and adding ZC to MAV gives {accs['MAV+ZC'].mean() * 100:.1f} % —
no better than adding the 'redundant' WL ({accs['MAV+WL'].mean() * 100:.1f} %). The whole 32-feature set reaches {accs['all 32'].mean() * 100:.1f} %, half a point above eight amplitude
values. With this armband (200 Hz sampling, heavily filtered) the gesture information is in *which channels are active*, i.e. the spatial
amplitude pattern; the frequency features matter in recordings with wider bandwidth and for fatigue, not here.""")
# tol-convention: relative tolerances are in percent
