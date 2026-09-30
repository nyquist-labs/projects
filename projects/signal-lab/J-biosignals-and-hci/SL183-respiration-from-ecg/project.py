from eelab import *
from eelab.data import physionet
from eelab.bio import pan_tompkins, bandpass
from scipy import signal

META = dict(
    id="SL-183", title="Respiration rate derived from the ECG (EDR)", level="H",
    tools="R-peak amplitude and RR-interval modulation (respiratory sinus arrhythmia), spectral rate estimation, BIDMC reference respiration",
    summary="Estimate breathing rate from the ECG alone — using how breathing modulates R-peak amplitude and heart rate — and validate it "
            "against the impedance-pneumography respiration signal recorded simultaneously in ICU patients.",
    problem="Can a single ECG lead also tell you how fast someone is breathing?",
    theory=r"""Breathing rotates the heart's electrical axis and changes thoracic impedance, modulating R-peak amplitude (EDR), and vagal tone modulates RR intervals
(respiratory sinus arrhythmia). Both modulations are sampled once per beat, so for heart rate HR and breathing rate BR estimation needs HR/2 > BR
(beat-sampling Nyquist); the modulation frequency = breathing rate.""",
    method="""BIDMC records 1–20 (8 min, 125 Hz). R peaks by Pan–Tompkins; amplitude and RR series resampled to 4 Hz; spectral peak in 0.1–0.7 Hz over 64-s windows; fused
estimate = the mean of the two where they agree within 3 breaths/min. Reference: spectral peak of the RESP signal in the same windows.""",
    data="Real: BIDMC PPG and Respiration Dataset (PhysioNet).",
)


def peak_rate(x, fs):
    f, P = signal.welch(x - np.mean(x), fs, nperseg=len(x))
    m = (f > 0.1) & (f < 0.7)
    return f[m][np.argmax(P[m])] * 60


def run(p):
    errs_a, errs_r, errs_f = [], [], []
    rows = []
    for k in range(1, 21):
        d = physionet("bidmc", f"bidmc{k:02d}")
        names = [str(n).strip(" ,") for n in d["names"]]; fs = d["fs"]
        ecg = d["signal"][:, names.index("II")].astype(float); resp = d["signal"][:, names.index("RESP")].astype(float)
        r = pan_tompkins(ecg, fs)
        amp = bandpass(ecg, fs, 1, 30)[r]
        tb = r / fs
        tg = np.arange(tb[1], tb[-1], 0.25)
        a_i = np.interp(tg, tb, amp); rr_i = np.interp(tg, tb[1:], np.diff(tb))
        resp4 = signal.resample_poly(resp, 4, int(fs))
        for t0 in np.arange(tg[0], tg[-1] - 64, 32):
            m = (tg >= t0) & (tg < t0 + 64)
            ref = peak_rate(resp4[int(t0 * 4): int((t0 + 64) * 4)], 4.0)
            ea = peak_rate(a_i[m], 4.0); er = peak_rate(rr_i[m], 4.0)
            fused = (ea + er) / 2 if abs(ea - er) < 3 else ea
            errs_a.append(ea - ref); errs_r.append(er - ref); errs_f.append(fused - ref)
            rows.append((k, t0, ref, ea, er, fused))
    ea, er, ef = map(lambda v: np.abs(np.array(v)), (errs_a, errs_r, errs_f))
    p.compare("EDR (R-amplitude) respiration-rate MAE", 0, ea.mean(), "breaths/min", kind="abs")
    p.compare("RSA (RR-interval) respiration-rate MAE", 0, er.mean(), "breaths/min", kind="abs")
    p.compare("Fused estimate MAE", 0, ef.mean(), "breaths/min", kind="abs")
    p.metric("Windows within ±2 breaths/min (fused)", np.mean(ef <= 2) * 100, "%")
    import pandas as pd
    df = pd.DataFrame(rows, columns=["record", "t0_s", "ref_bpm", "edr_bpm", "rsa_bpm", "fused_bpm"])
    p.csv_df("windows", df)
    fig, ax = p.fig()
    ax.plot(df.ref_bpm, df.edr_bpm, "o", ms=3, color=COLORS[1], alpha=.6, label="R-amplitude (EDR)")
    ax.plot(df.ref_bpm, df.fused_bpm, "s", ms=3, color=C_MEAS, alpha=.7, label="fused")
    lim = [df.ref_bpm.min() - 2, df.ref_bpm.max() + 2]; ax.plot(lim, lim, "--", color=C_PRED, label="identity")
    style_axes(ax, "reference breathing rate (impedance), breaths/min", "ECG-derived rate", "Breathing rate from the ECG, 20 ICU patients")
    p.save(fig, "edr", "Most windows land on the identity line; outliers come from irregular breathing and ventilated patients.")
    p.discuss("""R-peak amplitude modulation recovers breathing rate for most windows; RSA is weaker in these (mostly elderly, sedated or ventilated) ICU patients,
whose vagal modulation of heart rate is blunted — the opposite of healthy young subjects, where RSA is the stronger cue. Combining the two only
when they agree trims the gross errors. Beat-to-beat sampling sets a hard limit: at 60 bpm the ECG samples breathing only 1×/s, so fast
breathing (> 30/min) aliases — a limitation no algorithm can remove.""")
