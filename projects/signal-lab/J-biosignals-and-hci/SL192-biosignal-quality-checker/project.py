from eelab import *
from eelab.data import physionet
from eelab.bio import bandpass
from scipy import signal
from scipy.stats import kurtosis

META = dict(
    id="SL-192", title="Automatic ECG signal-quality checker", level="M",
    tools="Signal-quality indices (kurtosis, band-power ratio, template agreement) on MIT-BIH + NSTDB noise with known noisy segments",
    summary="Flag unusable 5-second ECG segments automatically using three signal-quality indices, and measure sensitivity and specificity "
            "against segments where real electrode-motion noise was deliberately added at known times.",
    problem="Wearables record hours of ECG, much of it corrupted by movement. Can software recognise which parts to trust?",
    theory=r"""Clean ECG is spiky (kurtosis ≫ 3), has most power in 5–15 Hz relative to 5–40 Hz (QRS band ratio ≈ 0.5–0.8), and consecutive beats look alike. Noise
lowers kurtosis toward 3 (Gaussian) and shifts power outside the QRS band. A segment is flagged if 2 of 3 indices fail; expected detection is
good at ≤ 0 dB SNR and poor at ≥ 12 dB, where the noise barely changes the waveform.""",
    method="""Record 100 (30 min) with NSTDB 'em' noise added in alternating 2-minute blocks at SNR −6, 0, 6, 12 dB; 5-s segments labelled noisy if inside a noise block. Thresholds
chosen on record 101 (same procedure), tested on record 100.""",
    data="Real: MIT-BIH records 100/101 + MIT-BIH Noise Stress Test Database electrode-motion noise (PhysioNet).",
)


def sqi(seg, fs):
    k = kurtosis(seg, fisher=False)
    f, P = signal.welch(seg, fs, nperseg=len(seg))
    ratio = P[(f >= 5) & (f <= 15)].sum() / P[(f >= 5) & (f <= 40)].sum()
    x = bandpass(seg, fs, 5, 15)
    pk, _ = signal.find_peaks(x, distance=int(0.3 * fs), height=np.percentile(x, 95) * 0.5)
    w = int(0.1 * fs)
    beats = np.array([seg[q - w: q + w] for q in pk if q - w >= 0 and q + w < len(seg)])
    if len(beats) >= 3:
        tm = beats.mean(0); corr = np.mean([np.corrcoef(b, tm)[0, 1] for b in beats])
    else:
        corr = 0.0
    return k, ratio, corr


def build(rec, snr_list, fs=360.0, n=360 * 1800):
    ecg = physionet("mitdb", rec, 0, n, channels=[0])["signal"][:, 0].astype(float)
    nz = physionet("nstdb", "em", 0, n, channels=[0])["signal"][:, 0].astype(float)
    nz -= nz.mean()
    x = ecg.copy(); lab = np.zeros(n, bool); snr_at = np.full(n, np.inf)
    blk = int(120 * fs)
    for i, start in enumerate(range(blk, n - blk, 2 * blk)):
        s = snr_list[i % len(snr_list)]
        seg = slice(start, start + blk)
        g = np.sqrt(np.mean(ecg[seg] ** 2) / np.mean(nz[seg] ** 2) / 10 ** (s / 10))
        x[seg] += g * nz[seg]; lab[seg] = True; snr_at[seg] = s
    return x, lab, snr_at


def segment_features(x, lab, snr_at, fs=360.0):
    L = int(5 * fs); F, y, sn = [], [], []
    for i in range(0, len(x) - L, L):
        F.append(sqi(x[i:i + L], fs)); y.append(lab[i + L // 2]); sn.append(snr_at[i + L // 2])
    return np.array(F), np.array(y), np.array(sn)


def run(p):
    snrs = [-6, 0, 6, 12]
    Ftr, ytr, _ = segment_features(*build("101", snrs))
    thr = [(np.median(Ftr[~ytr, j]) + np.median(Ftr[ytr, j])) / 2 for j in range(3)]
    flag = lambda F: ((F[:, 0] < thr[0]).astype(int) + (F[:, 1] < thr[1]) + (F[:, 2] < thr[2])) >= 2
    Fte, yte, sn = segment_features(*build("100", snrs))
    fl = flag(Fte)
    spec = np.mean(~fl[~yte]) * 100
    p.compare("Specificity on clean segments", 95, spec, "%", kind="abs")
    for s in snrs:
        m = yte & (sn == s)
        sens = np.mean(fl[m]) * 100
        p.compare(f"Noisy-segment detection at {s:+d} dB SNR", 100 if s <= 0 else (50 if s == 6 else 10), sens, "%", kind="abs",
                  note="expected: near-complete at ≤ 0 dB, poor at ≥ 12 dB")
    p.metric("Thresholds (kurtosis, QRS band ratio, template corr) — trained on record 101", ", ".join(f"{t:.2f}" for t in thr))
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    for j, nm in enumerate(("kurtosis", "QRS band ratio", "template correlation")):
        ax[j].hist(Fte[~yte, j], 25, color=C_MEAS, alpha=.7, label="clean"); ax[j].hist(Fte[yte, j], 25, color=COLORS[7], alpha=.6, label="noise added")
        ax[j].axvline(thr[j], color=C_PRED, ls="--")
        style_axes(ax[j], nm, "segments", None)
    p.save(fig, "sqi", "Each index separates clean from heavily corrupted segments; majority voting combines them.")
    p.discuss(f"""Trained on one patient and tested on another, the 2-of-3 vote catches almost every corrupted segment — including most at 6–12 dB, more than I
expected — but at the cost of specificity ({spec:.0f} % of clean segments kept, below the 95 % I aimed for). The thresholds, set halfway between the
training record's class medians, sit too close to the clean distribution for the test patient, whose own ECG morphology gives lower kurtosis. A
per-patient baseline (thresholds relative to the first clean minute) would trade some sensitivity back for specificity. Labelling by *where noise was added* rather than by *usability* is the main limitation of this evaluation;
clinical SQI work uses expert usability labels instead.""")
