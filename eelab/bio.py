"""Biosignal helpers: Pan–Tompkins QRS detector, beat matching, band-pass utilities."""
import numpy as np
from scipy import signal


def bandpass(x, fs, lo, hi, order=2):
    b, a = signal.butter(order, [lo, hi], "bandpass", fs=fs)
    return signal.filtfilt(b, a, x)


def pan_tompkins(ecg, fs):
    """Pan & Tompkins (1985) with adaptive thresholds and search-back. Returns R-peak sample indices."""
    x = bandpass(ecg, fs, 5, 15)
    d = np.convolve(x, np.array([1, 2, 0, -2, -1]) * fs / 8.0, "same")
    sq = d * d
    win = int(0.150 * fs)
    mwi = np.convolve(sq, np.ones(win) / win, "same")
    refractory = int(0.2 * fs)
    peaks, _ = signal.find_peaks(mwi, distance=refractory)
    spki = npki = 0.0
    init = mwi[: 2 * int(fs)]
    spki, npki = init.max() * 0.25, init.mean() * 0.5
    thr = npki + 0.25 * (spki - npki)
    qrs, rr = [], []
    for pk in peaks:
        if mwi[pk] > thr:
            if qrs and pk - qrs[-1] < int(0.36 * fs):   # T-wave check
                seg_prev = np.max(np.abs(d[max(qrs[-1] - win, 0): qrs[-1]]))
                seg_cur = np.max(np.abs(d[max(pk - win, 0): pk]))
                if seg_cur < 0.5 * seg_prev:
                    npki = 0.125 * mwi[pk] + 0.875 * npki; thr = npki + 0.25 * (spki - npki); continue
            spki = 0.125 * mwi[pk] + 0.875 * spki
            if qrs:
                rr.append(pk - qrs[-1])
                rr_avg = np.mean(rr[-8:])
                if pk - qrs[-1] > 1.66 * rr_avg:           # search back with half threshold
                    cand = [c for c in peaks if qrs[-1] + refractory < c < pk - refractory and mwi[c] > 0.5 * thr]
                    if cand:
                        c = max(cand, key=lambda c: mwi[c]); qrs.append(c)
            qrs.append(pk)
        else:
            npki = 0.125 * mwi[pk] + 0.875 * npki
        thr = npki + 0.25 * (spki - npki)
    qrs = np.array(sorted(set(qrs)))
    # refine to the local maximum of |band-passed ECG| (R peak) within ±75 ms
    w = int(0.075 * fs)
    ref = [q - w + int(np.argmax(np.abs(x[max(q - w, 0): q + w]))) for q in qrs]
    return np.array(ref)


def match(det, ref, fs, tol=0.15):
    """Greedy matching of detected vs reference beats within ±tol s → (TP, FP, FN)."""
    ref = np.asarray(ref); det = np.asarray(det)
    used = np.zeros(len(det), bool); tp = 0
    t = int(tol * fs)
    for r in ref:
        i = np.searchsorted(det, r)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(det) and not used[j] and abs(det[j] - r) <= t:
                if best is None or abs(det[j] - r) < abs(det[best] - r):
                    best = j
        if best is not None:
            used[best] = True; tp += 1
    return tp, int((~used).sum()), len(ref) - tp


BEAT_SYMBOLS = set("NLRBAaJSVrFejnE/fQ")


def eegmmidb(subject, run):
    """EEG Motor Movement/Imagery DB (Schalk et al. 2004): 64 ch, 160 Hz. Returns (data[ch, n], fs, labels, annotations)."""
    from .data import physionet_edf
    r = physionet_edf(f"eegmmidb/1.0.0/S{subject:03d}/S{subject:03d}R{run:02d}.edf")
    labels = list(r["signals"].keys())
    X = np.array([r["signals"][k] for k in labels])
    return X, r["fs"][labels[0]], [l.strip(".") for l in labels], r["annotations"]


def lda_fit(X, y):
    m0, m1 = X[y == 0].mean(0), X[y == 1].mean(0)
    S = np.cov(X[y == 0].T) + np.cov(X[y == 1].T) + 1e-6 * np.eye(X.shape[1])
    w = np.linalg.solve(S, m1 - m0)
    b = -w @ (m0 + m1) / 2
    return w, b


def sleep_edf(rec="SC4001E0", hyp="SC4001EC"):
    from .data import physionet_file, read_edf
    psg = read_edf(physionet_file(f"sleep-edfx/1.0.0/sleep-cassette/{rec}-PSG.edf"))
    h = read_edf(physionet_file(f"sleep-edfx/1.0.0/sleep-cassette/{hyp}-Hypnogram.edf"))["annotations"]
    return psg, h


STAGE = {"Sleep stage W": 0, "Sleep stage 1": 1, "Sleep stage 2": 2, "Sleep stage 3": 3, "Sleep stage 4": 3, "Sleep stage R": 4}


def epoch_labels(ann, n_epochs, ep=30.0):
    lab = np.full(n_epochs, -1)
    for on, dur, txt in ann:
        if txt in STAGE:
            a, b = int(on // ep), int((on + dur) // ep)
            lab[a:min(b, n_epochs)] = STAGE[txt]
    return lab
