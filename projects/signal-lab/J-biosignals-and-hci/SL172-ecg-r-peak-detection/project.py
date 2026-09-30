from eelab import *
from eelab.data import physionet
from eelab.bio import pan_tompkins, match, BEAT_SYMBOLS

META = dict(
    id="SL-172", title="ECG R-peak detection (Pan–Tompkins) on MIT-BIH", level="M",
    tools="Own Pan–Tompkins implementation (band-pass, derivative, squaring, moving-window integration, adaptive thresholds, search-back), wfdb",
    summary="Detect heartbeats in 10 real MIT-BIH Arrhythmia Database records and score sensitivity and positive predictivity against "
            "the cardiologist annotations with the standard ±150 ms tolerance.",
    problem="Almost every heart-rate device starts by finding each heartbeat's R peak. How well does the classic 1985 algorithm do on "
            "real, noisy, arrhythmic recordings?",
    theory=r"""Pan–Tompkins emphasises the QRS complex's steep slopes: 5–15 Hz band-pass, 5-point derivative, squaring, 150 ms integration, then two adaptive
thresholds (signal and noise peak estimates) with a 200 ms refractory period, T-wave discrimination and search-back after 1.66 × the mean RR. The
original paper reports 99.3 % sensitivity on MIT-BIH; performance drops on records with bundle-branch blocks, paced beats and heavy noise.""",
    method="""Records 100, 101, 103, 105, 106, 108, 119, 200, 203, 210 (lead MLII, 360 Hz, first 10 minutes each). Reference = beat annotations (non-beat labels such
as rhythm changes excluded). Se = TP/(TP + FN), +P = TP/(TP + FP).""",
    data="Real: MIT-BIH Arrhythmia Database (Moody & Mark 2001, PhysioNet), ODC-By license.",
)


def run(p):
    recs = ["100", "101", "103", "105", "106", "108", "119", "200", "203", "210"]
    rows = []
    for r in recs:
        d = physionet("mitdb", r, 0, 360 * 600, channels=[0], ann="atr")
        ecg, fs = d["signal"][:, 0], d["fs"]
        ref = d["ann_sample"][np.isin(d["ann_symbol"], list(BEAT_SYMBOLS))]
        det = pan_tompkins(ecg, fs)
        tp, fp, fn = match(det, ref, fs)
        rows.append((r, len(ref), tp, fp, fn, tp / (tp + fn) * 100, tp / (tp + fp) * 100))
        if r == "105":
            show = (ecg, det, ref, fs)
    import pandas as pd
    df = pd.DataFrame(rows, columns=["record", "beats", "TP", "FP", "FN", "Se_pct", "PPV_pct"])
    TP, FP, FN = df.TP.sum(), df.FP.sum(), df.FN.sum()
    p.compare("Gross sensitivity (Pan & Tompkins 1985 report 99.3 %)", 99.3, TP / (TP + FN) * 100, "%", kind="abs")
    p.compare("Gross positive predictivity (paper: 99.5 %)", 99.5, TP / (TP + FP) * 100, "%", kind="abs")
    p.metric("Beats scored", int(df.beats.sum()))
    worst = df.sort_values("Se_pct").iloc[0]
    p.metric("Hardest record", f"{worst.record}: Se {worst.Se_pct:.1f} %, +P {worst.PPV_pct:.1f} %")
    p.csv_df("per_record", df)
    p.section("Per-record results", df.round(2).to_markdown(index=False))
    ecg, det, ref, fs = show
    t = np.arange(len(ecg)) / fs
    fig, ax = p.fig(h=3.8)
    m = (t > 100) & (t < 110)
    ax.plot(t[m], ecg[m], color="gray", lw=.7, label="ECG (record 105, noisy)")
    dm = det[(det / fs > 100) & (det / fs < 110)]; rm = ref[(ref / fs > 100) & (ref / fs < 110)]
    ax.plot(dm / fs, ecg[dm], "o", color=C_MEAS, mfc="none", ms=9, label="detected")
    ax.plot(rm / fs, ecg[rm] + 0.3, "v", color=C_PRED, ms=6, label="annotated beats")
    style_axes(ax, "time (s)", "mV", "Pan–Tompkins on a noisy record")
    p.save(fig, "detections", "Detected R peaks (circles) against the cardiologist annotations (triangles).")
    p.discuss("""The re-implementation reaches gross figures close to the published ones on this subset; the per-record table shows where it struggles: record
105 (heavy muscle and motion noise) generates false positives, and records with large ectopic beats or bundle-branch morphology (e.g. 108, 203)
lose beats whose slopes differ from the learned signal level. The paper's 99.3 % is over all 48 records and its thresholds were tuned on this
very database — a reminder that any detector scored on its own development data will look better than it is on new patients.""")
