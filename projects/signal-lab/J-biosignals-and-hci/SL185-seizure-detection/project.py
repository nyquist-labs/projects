from eelab import *
from eelab.data import physionet_edf
from scipy import signal

META = dict(
    id="SL-185", title="Epileptic seizure detection in scalp EEG (CHB-MIT)", level="H",
    tools="Line-length and band-energy features in 2-s windows, patient-specific threshold, false-alarm analysis; CHB-MIT Scalp EEG Database",
    summary="Detect a clinically annotated seizure in a child's 23-channel EEG with a line-length detector, measure detection latency, and count "
            "false alarms per hour on a seizure-free hour from the same patient.",
    problem="Seizure warning devices must catch seizures quickly without crying wolf. Where is that trade-off for a simple detector?",
    theory=r"""Seizures produce rhythmic, high-amplitude activity: line length $L=\sum|x_{n+1}-x_n|$ over a window rises several-fold (Esteller 2001). A patient-specific
threshold (e.g. mean + kσ of background) trades latency against false alarms: raising k reduces false alarms roughly exponentially for Gaussian-like
background but delays detection. Clinical systems target < 1 false alarm/h with detection within ~10 s.""",
    method="""Patient chb01: file chb01_03 contains a seizure at 2996–3036 s (annotation); chb01_01 is seizure-free (1 h). 23 bipolar channels, 256 Hz, 3–30 Hz band-pass. Line
length per 2-s window summed over channels, normalised by the median of chb01_01. Detection = 3 consecutive windows above threshold k; k swept.""",
    data="Real: CHB-MIT Scalp EEG Database (Shoeb 2009, PhysioNet), ODC-By.",
)


def linelength(path):
    r = physionet_edf(path)
    X = np.array([v for k, v in r["signals"].items() if "-" in k])
    fs = list(r["fs"].values())[0]
    b, a = signal.butter(4, [3, 30], "bandpass", fs=fs); X = signal.filtfilt(b, a, X, axis=1)
    W = int(2 * fs); n = X.shape[1] // W
    return np.abs(np.diff(X[:, : n * W].reshape(X.shape[0], n, W), axis=2)).sum(2), fs


def detect(z, k, run_=3):
    above = z > k
    alarms = []
    c = 0
    for i, a in enumerate(above):
        c = c + 1 if a else 0
        if c == run_:
            alarms.append(i)
    return np.array(alarms)


def run(p):
    ch_bg, fs = linelength("chbmit/1.0.0/chb01/chb01_01.edf")
    ch_sz, _ = linelength("chbmit/1.0.0/chb01/chb01_03.edf")
    ll_bg, ll_sz = ch_bg.sum(0), ch_sz.sum(0)
    base = np.median(ll_bg); spread = np.median(np.abs(ll_bg - base)) * 1.4826
    zb = (ll_bg - base) / spread; zs = (ll_sz - base) / spread
    onset, offset = 2996 / 2, 3036 / 2
    t = np.arange(len(zs)) * 2
    peak_ratio = ll_sz[int(onset): int(offset)].mean() / base
    p.compare("Line-length increase during the seizure (several-fold expected)", 3, peak_ratio, "×", kind="abs")
    rows = []
    for k in (3, 4, 5, 6, 8, 10, 12, 15):
        fa = len(detect(zb, k)) / (len(zb) * 2 / 3600)
        al = detect(zs, k)
        hit = al[(al >= onset) & (al <= offset + 5)]
        lat = (hit[0] - onset) * 2 if len(hit) else np.nan
        false_sz = np.sum((al < onset - 30) | (al > offset + 60))
        rows.append((k, fa, lat, false_sz))
    k_, fa_, lat_, _ = map(np.array, zip(*rows))
    ok = np.flatnonzero((fa_ < 1) & ~np.isnan(lat_))
    if len(ok):
        j = ok[0]
        p.compare(f"At the first threshold with < 1 false alarm/h (k = {k_[j]:g}): detection latency (target < 10 s)", 10, lat_[j], "s", kind="abs")
    else:
        p.metric("No threshold gives < 1 false alarm/h AND detects the seizure with the raw 2-s feature", 0, "", "see trade-off plot")
    # improved detector: per-channel robust z-scores averaged over channels, then 20-s moving average (seizures are sustained, artefacts brief)
    med = np.median(ch_bg, 1, keepdims=True); mad = np.median(np.abs(ch_bg - med), 1, keepdims=True) * 1.4826
    L = 10; ker = np.ones(L) / L
    sb = np.convolve(((ch_bg - med) / mad).mean(0), ker, "valid"); ss = np.convolve(((ch_sz - med) / mad).mean(0), ker, "valid")
    thr = 1.05 * sb.max()          # set from the seizure-free training hour only: zero false alarms there by construction
    above = np.flatnonzero(ss > thr)
    ts = (np.arange(len(ss)) + L - 1) * 2       # time of the end of each smoothing window (causal)
    hit = above[(ts[above] >= 2996) & (ts[above] <= 3036 + 20)]
    fa_other = np.sum(np.diff(np.r_[-5, above[(ts[above] < 2996 - 60) | (ts[above] > 3036 + 60)]]) > 1) if len(above) else 0
    p.metric("Smoothed detector threshold (from seizure-free hour)", thr, "σ")
    p.compare("Smoothed detector: latency after electrographic onset (target < 10 s + 20-s averaging)", 20, (ts[hit[0]] - 2996) if len(hit) else np.nan, "s", kind="abs")
    p.metric("Smoothed detector: false alarms in the ~59 non-seizure minutes of chb01_03 (held out)", fa_other, "")
    p.metric("Seizure detected by raw feature at every threshold up to", float(k_[~np.isnan(lat_)].max()) if np.any(~np.isnan(lat_)) else np.nan, "σ")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t / 60, zs, color=C_MEAS, lw=.6); ax[0].axvspan(2996 / 60, 3036 / 60, color=COLORS[7], alpha=.2, label="annotated seizure")
    style_axes(ax[0], "time (min)", "normalised line length (σ)", "chb01_03")
    ax[1].plot(fa_, lat_, "o-", color=C_MEAS)
    for k, f, l in zip(k_, fa_, lat_):
        ax[1].annotate(f"k={k:g}", (f, l), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax[1].set_xscale("symlog", linthresh=0.5)
    style_axes(ax[1], "false alarms per hour (seizure-free hour)", "detection latency (s)", "Threshold trade-off", legend=False)
    p.save(fig, "seizure", "The seizure raises line length, but brief artefacts in the background hour reach similar values.")
    fig2, a2 = p.fig(1, 1, w=9, h=3.6)
    a2.plot(ts / 60, ss, color=C_MEAS, lw=.8, label="chb01_03 (with seizure)"); a2.axhline(thr, ls="--", color=C_PRED, label="threshold from seizure-free hour")
    a2.axvspan(2996 / 60, 3036 / 60, color=COLORS[7], alpha=.2, label="annotated seizure")
    style_axes(a2, "time (min)", "20-s mean channel z-score", "Averaging over channels and time separates the sustained seizure from brief artefacts")
    p.save(fig2, "smoothed_detector", "Channel-averaged, time-smoothed line length with a threshold set only on the training hour.")
    import pandas as pd
    p.csv_df("tradeoff", pd.DataFrame(rows, columns=["k_sigma", "false_alarms_per_h", "latency_s", "false_alarms_in_seizure_file"]))
    p.discuss("""My prediction of a several-fold line-length jump was too optimistic: summed over all 23 channels the increase is under 2× because chb01's seizure is
strongest on a subset of channels, and brief movement/chewing artefacts in the seizure-free hour reach similar 2-s values. With the raw feature,
thresholds low enough to catch the seizure cost several false alarms per hour. Using the fact that seizures are *sustained* — averaging robust
per-channel z-scores over channels and over 20 s — and setting the threshold only from the seizure-free hour, the detector catches the seizure
with no false alarms in the rest of the held-out file, at the price of latency from the averaging window. The margin is thin — the seizure's smoothed peak is only slightly above the threshold — so\nthis is a demonstration on one seizure, not evidence of a reliable detector. This is one seizure in one patient — the easy case: patient-specific detectors
tuned on each child's own data are exactly how the CHB-MIT benchmark is usually attacked, and performance across patients (or on patients with
subtle, low-amplitude seizures and more artefact) is far lower. Reporting false alarms per hour next to sensitivity is essential — a detector
with 'perfect sensitivity' and 20 false alarms/h is useless to a family.""")
