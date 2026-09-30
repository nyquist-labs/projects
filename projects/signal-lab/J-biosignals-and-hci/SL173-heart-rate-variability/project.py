from eelab import *
from eelab.data import physionet
from eelab.bio import pan_tompkins, match
from scipy.signal import lombscargle

META = dict(
    id="SL-173", title="Heart-rate variability: time and frequency domain", level="M",
    tools="Pan–Tompkins R peaks (eelab.bio) on MIT-BIH record 100, time-domain HRV, Lomb–Scargle spectrum (SciPy)",
    summary="Compute SDNN, RMSSD, pNN50 and LF/HF power from detected R peaks of a 30-minute real ECG, and check each metric "
            "against the same metric computed from the cardiologist's beat annotations.",
    problem="HRV is widely used as a stress/fitness marker. How sensitive are the numbers to the beat detector that produces them?",
    theory=r"""SDNN = std of NN intervals; RMSSD = √mean(ΔNN²) (short-term, vagal); LF 0.04–0.15 Hz and HF 0.15–0.4 Hz powers of the unevenly sampled RR series
(Lomb–Scargle avoids resampling). A timing error of σ_t per beat adds ≈ 2σ_t² to the successive-difference variance, so RMSSD is the most
detector-sensitive metric (e.g. a 3 ms jitter adds ~4 ms² to RMSSD²).""",
    method="""Record 100 (normal sinus rhythm with rare ectopics), full 30 min, 360 Hz. NN series = normal-to-normal intervals (ectopic beats and their neighbours
removed using the annotations for both series, so only detector timing differs). Metrics from detected vs annotated peaks.""",
    data="Real: MIT-BIH Arrhythmia Database record 100 (PhysioNet).",
)


def hrv(t_beats, normal):
    rr = np.diff(t_beats) * 1000
    ok = normal[1:] & normal[:-1]
    nn = rr[ok]; tn = t_beats[1:][ok]
    d = np.diff(nn)
    f = np.linspace(0.01, 0.5, 500)
    x = nn - nn.mean()
    P = lombscargle(tn, x, 2 * np.pi * f, normalize=False)
    lf = np.trapezoid(P[(f >= 0.04) & (f < 0.15)], f[(f >= 0.04) & (f < 0.15)])
    hf = np.trapezoid(P[(f >= 0.15) & (f < 0.4)], f[(f >= 0.15) & (f < 0.4)])
    return dict(SDNN=np.std(nn), RMSSD=np.sqrt(np.mean(d * d)), pNN50=np.mean(np.abs(d) > 50) * 100, LFHF=lf / hf, meanHR=60000 / nn.mean()), (f, P)


def run(p):
    d = physionet("mitdb", "100", channels=[0], ann="atr")
    ecg, fs = d["signal"][:, 0], d["fs"]
    sym = d["ann_symbol"]; samp = d["ann_sample"]
    beats = np.isin(sym, list("NLRBAaJSVrFejnE/fQ"))
    ref, rsym = samp[beats], sym[beats]
    det = pan_tompkins(ecg, fs)
    # align detected beats to annotations to inherit beat labels
    idx = np.searchsorted(ref, det)
    lab = []
    keep = []
    for k, dd in enumerate(det):
        j = min(max(idx[k], 0), len(ref) - 1)
        jj = j if j == 0 or abs(ref[j] - dd) < abs(ref[j - 1] - dd) else j - 1
        if abs(ref[jj] - dd) < 0.15 * fs:
            keep.append(dd); lab.append(rsym[jj] == "N")
    keep = np.array(keep); lab = np.array(lab)
    hd, spec_d = hrv(keep / fs, lab)
    hr_, spec_r = hrv(ref / fs, rsym == "N")
    for k, u in (("SDNN", "ms"), ("RMSSD", "ms"), ("pNN50", "%"), ("LFHF", ""), ("meanHR", "bpm")):
        p.compare(f"{k}: detected peaks vs annotation reference", hr_[k], hd[k], u, tol=10 if k != "pNN50" else None)
    jit = np.std([dd - ref[np.argmin(abs(ref - dd))] for dd in keep]) / fs * 1000
    p.metric("R-peak timing jitter vs annotations", jit, "ms", "the annotations themselves have ±~1 sample placement")
    p.compare("RMSSD² inflation predicted from jitter (2σ²)", hr_["RMSSD"] ** 2 + 2 * jit**2, hd["RMSSD"] ** 2, "ms²", tol=15)
    fig, ax = p.fig(1, 2, w=11)
    t = keep[1:] / fs / 60; rr = np.diff(keep) / fs * 1000
    ax[0].plot(t, rr, color=C_MEAS, lw=.6)
    style_axes(ax[0], "time (min)", "RR interval (ms)", "Tachogram, record 100", legend=False)
    ax[1].plot(spec_r[0], spec_r[1], "--", color=C_PRED, label="from annotations"); ax[1].plot(spec_d[0], spec_d[1], color=C_MEAS, label="from detected peaks")
    ax[1].axvspan(0.04, 0.15, color=COLORS[2], alpha=.1); ax[1].axvspan(0.15, 0.4, color=COLORS[3], alpha=.1)
    style_axes(ax[1], "frequency (Hz)", "Lomb–Scargle power", "HRV spectrum (LF / HF bands shaded)")
    p.save(fig, "hrv", "Detector timing jitter barely changes the slow (LF) power but inflates beat-to-beat metrics.")
    p.discuss("""Mean HR and SDNN are essentially identical whether computed from detected or annotated beats — they depend on long-term variation. RMSSD and
pNN50, which look at successive differences, are measurably inflated by the detector's few-millisecond timing jitter, and the 2σ² prediction
accounts for most of the inflation. Practical lesson: report the detector and sampling rate with any short-term HRV number, and refine peak
timing (interpolation) before computing RMSSD.""")
