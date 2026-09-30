from eelab import *
from eelab.bio import sleep_edf, epoch_labels
from scipy import signal

META = dict(
    id="SL-186", title="Eye-movement analysis from the EOG: finding REM sleep", level="M",
    tools="Horizontal EOG, derivative-based saccade detection, per-stage rate statistics; Sleep-EDF Expanded",
    summary="Detect rapid eye movements in a whole night of horizontal EOG with a velocity-threshold detector and show that they concentrate "
            "in REM sleep and wakefulness, as the name 'REM' says — then use the rate alone to spot REM epochs.",
    problem="The electrooculogram measures the eye's corneo-retinal dipole. Can eye movements alone reveal dream sleep?",
    theory=r"""Horizontal eye rotation changes the EOG by roughly 10–20 µV per degree; saccades are fast (velocity ≫ slow drifts), so a threshold on |dV/dt| detects them.
REM sleep is defined by bursts of such movements; N2/N3 contain almost none (slow rolling movements occur mainly in N1). Expected: REM-epoch saccade
rate ≫ N2/N3 rate, making the rate a useful REM indicator (but also high during wake).""",
    method="""SC4001 night: EOG horizontal (100 Hz), 0.3–15 Hz band-pass, velocity = derivative smoothed over 30 ms, saccade = |velocity| > 6 × MAD with 200 ms refractory period. Rate per
30-s epoch grouped by the expert's stage; REM detection by rate threshold restricted to sleep epochs (ROC area).""",
    data="Real: Sleep-EDF Database Expanded (PhysioNet).",
)


def run(p):
    psg, ann = sleep_edf("SC4001E0", "SC4001EC")
    eog, fs = psg["signals"]["EOG horizontal"], psg["fs"]["EOG horizontal"]
    n = int(len(eog) / fs // 30)
    lab = epoch_labels(ann, n)
    sleep = np.flatnonzero((lab >= 1) & (lab <= 4))
    e0, e1 = max(sleep[0] - 60, 0), min(sleep[-1] + 60, n)     # sleep period ± 30 min (the file also holds ~14 h of daytime wake)
    lab = lab[e0:e1]; eog = eog[int(e0 * 30 * fs): int(e1 * 30 * fs)]; n = len(lab)
    b, a = signal.butter(2, [0.3, 15], "bandpass", fs=fs); x = signal.filtfilt(b, a, eog)
    v = np.convolve(np.gradient(x) * fs, np.ones(3) / 3, "same")
    thr = 6 * np.median(np.abs(v)) * 1.4826
    pk, _ = signal.find_peaks(np.abs(v), height=thr, distance=int(0.2 * fs))
    rate = np.bincount((pk / fs // 30).astype(int), minlength=n)[:n] * 2.0
    names = ["W", "N1", "N2", "N3", "REM"]
    med = {nm: np.mean(rate[lab == i]) for i, nm in enumerate(names) if np.any(lab == i)}
    for nm, r in med.items():
        p.metric(f"Mean saccade rate in {nm}", r, "per min", f"{int(np.sum(lab == names.index(nm)))} epochs")
    p.compare("REM / N2 mean saccade-rate ratio (≫ 1 expected)", 5, med["REM"] / max(med["N2"], 0.5), "×", kind="abs")
    sl = (lab >= 1) & (lab <= 4)
    y = (lab[sl] == 4).astype(int); sc = rate[sl]
    order = np.argsort(-sc); tpr = np.cumsum(y[order]) / y.sum(); fpr = np.cumsum(1 - y[order]) / (1 - y).sum()
    auc = np.trapezoid(np.r_[0, tpr], np.r_[0, fpr])
    p.compare("ROC area for REM vs other sleep epochs from saccade rate alone", 0.8, auc, "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].boxplot([rate[lab == i] for i in range(5)], tick_labels=names, showfliers=False)
    style_axes(ax[0], "sleep stage (expert)", "saccades per minute", "Eye movements by stage", legend=False)
    ax[1].plot(fpr, tpr, color=C_MEAS); ax[1].plot([0, 1], [0, 1], ":", color="gray")
    style_axes(ax[1], "false-positive rate", "true-positive rate", f"REM detection, AUC = {auc:.2f}", legend=False)
    p.save(fig, "eog", "Rapid eye movements are concentrated in REM (and wake), nearly absent in deep sleep.")
    p.metric("Detection threshold (6 × robust σ of velocity)", thr, "µV/s")
    p.discuss("""A first run used the whole 22-h file, whose daytime wake inflated the robust threshold so that *no* sleep saccades were detected — restricting to the
sleep period (±30 min) fixed it. The velocity detector confirms the core of the definition of REM sleep on real data: saccade rates in REM are about five
times those in N2, as predicted. But the rate alone separates REM from other sleep only modestly (AUC ≈ 0.64, below my 0.8 guess): N1 has *more*
detected movements than REM (slow rolling eye movements and wake intrusions at sleep onset), and much of REM is 'tonic' with no eye movements at
all, so many REM epochs score zero. It is not a complete REM detector — wakefulness also has many saccades (handled by excluding wake epochs here,
in practice by EMG and EEG α), and REM sleep contains tonic periods without eye movements, which limit sensitivity. Gaze-tracking HCI uses the
same signal while awake, with calibration of µV per degree.""")
