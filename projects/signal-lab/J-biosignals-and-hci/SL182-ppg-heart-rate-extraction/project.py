from eelab import *
from eelab.data import physionet
from eelab.bio import pan_tompkins, bandpass
from scipy import signal

META = dict(
    id="SL-182", title="Heart rate from PPG, validated against ECG (BIDMC)", level="M",
    tools="PPG pulse detection (band-pass + derivative peak picking), Pan–Tompkins on the simultaneous ECG, BIDMC PPG and Respiration dataset",
    summary="Estimate beat-to-beat and 8-second-window heart rate from the finger photoplethysmogram of ICU patients and compare with the "
            "simultaneously recorded ECG; measure the pulse transit delay between R peak and pulse arrival.",
    problem="Smartwatches measure heart rate optically. How close is PPG-derived heart rate to the ECG gold standard on real patients?",
    theory=r"""Each heartbeat produces one PPG pulse, delayed by the pulse arrival time (PAT ≈ 150–300 ms at the finger). Heart rate from PPG therefore equals ECG heart rate
beat for beat, apart from detection errors and PAT variation (a few ms), so windowed-HR error should be well under 1 bpm when the signal is clean.""",
    method="""BIDMC records 1–10 (125 Hz, 8 min each, PPG 'PLETH' and ECG lead II). PPG band-passed 0.5–8 Hz, systolic peaks by find_peaks with a 0.33 s refractory period;
ECG R peaks by Pan–Tompkins. HR in 8-s windows; per-record MAE; PAT = time from R peak to next PPG peak.""",
    data="Real: BIDMC PPG and Respiration Dataset (Pimentel et al. 2016, PhysioNet), ODC-By.",
)


def run(p):
    rows = []
    for k in range(1, 11):
        rec = f"bidmc{k:02d}"
        d = physionet("bidmc", rec)
        names = [str(n).strip(" ,") for n in d["names"]]
        fs = d["fs"]
        ppg = d["signal"][:, names.index("PLETH")].astype(float)
        ecg = d["signal"][:, names.index("II")].astype(float)
        r = pan_tompkins(ecg, fs)
        pf = bandpass(ppg, fs, 0.5, 8)
        pk, _ = signal.find_peaks(pf, distance=int(0.33 * fs), prominence=np.std(pf) * 0.3)
        W = 8.0; T = len(ppg) / fs
        he, hp = [], []
        for t0 in np.arange(10, T - W, W):
            re_ = r[(r >= t0 * fs) & (r < (t0 + W) * fs)]; pp = pk[(pk >= t0 * fs) & (pk < (t0 + W) * fs)]
            if len(re_) > 2 and len(pp) > 2:
                he.append(60 * fs / np.median(np.diff(re_))); hp.append(60 * fs / np.median(np.diff(pp)))
        he, hp = np.array(he), np.array(hp)
        pat = []
        for rr in r:
            nx = pk[pk > rr]
            if len(nx) and (nx[0] - rr) / fs < 0.6:
                pat.append((nx[0] - rr) / fs)
        rows.append((rec, np.mean(np.abs(he - hp)), np.median(he), np.median(pat) * 1000 if pat else np.nan))
        if k == 1:
            show = (ecg, ppg, r, pk, fs)
    import pandas as pd
    df = pd.DataFrame(rows, columns=["record", "HR_MAE_bpm", "median_HR_bpm", "median_PAT_ms"])
    p.compare("Median per-patient HR error, PPG vs ECG (8-s windows) — expected < 1 bpm on clean PPG", 0, df.HR_MAE_bpm.median(), "bpm", kind="abs")
    p.metric("Mean per-patient HR error (pulled up by a few bad recordings)", df.HR_MAE_bpm.mean(), "bpm")
    p.metric("Median R-peak → PPG-peak delay", df.median_PAT_ms.median(), "ms", "BIDMC waveforms are not guaranteed to be time-aligned; see discussion")
    p.metric("Worst patient MAE", df.HR_MAE_bpm.max(), "bpm", df.loc[df.HR_MAE_bpm.idxmax(), "record"])
    p.csv_df("per_record", df)
    p.section("Per-patient results", df.round(2).to_markdown(index=False))
    ecg, ppg, r, pk, fs = show
    t = np.arange(len(ecg)) / fs; m = (t > 60) & (t < 66)
    fig, ax = p.fig(h=4)
    ax.plot(t[m], (ecg[m] - ecg[m].mean()) / ecg[m].std(), color=COLORS[1], lw=.8, label="ECG II")
    ax.plot(t[m], (ppg[m] - ppg[m].mean()) / ppg[m].std() - 4, color=C_MEAS, lw=.8, label="PPG (finger)")
    for rr in r[(r / fs > 60) & (r / fs < 66)]:
        ax.axvline(rr / fs, color="gray", lw=.5, ls=":")
    style_axes(ax, "time (s)", "normalised", "Each R peak is followed ~0.2 s later by a pulse at the finger")
    p.save(fig, "ppg_ecg", "ECG and PPG from BIDMC patient 1; dotted lines mark detected R peaks.")
    p.discuss("""For most patients PPG-derived heart rate agrees with the ECG closely, but a few recordings have large errors: low perfusion and motion flatten
the PPG so peaks are missed or doubled (the dicrotic notch), and the 8-s median only partly hides it — the mean error is dominated by those
patients, which is why the median is reported as the headline. The measured R-to-pulse delay (~0.08 s) is far shorter than the physiological
150–300 ms pulse arrival time; since the physiology is not in doubt, this most likely reflects a time offset between the ECG and PPG channels
in the source monitor data (or filter-group-delay differences), so PAT should not be estimated from this dataset without a timing check.""")
