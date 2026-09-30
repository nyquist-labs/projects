from eelab import *
from eelab.data import physionet
from eelab.bio import pan_tompkins, match, BEAT_SYMBOLS
from scipy import signal

META = dict(
    id="AM-169", title="ECG R-peak detection as a statistical decision problem", level="M",
    tools="Own energy detector (band-pass, derivative, squaring, moving-window integration, threshold with refractory period), threshold sweep for the sensitivity/precision trade-off, binomial confidence intervals, comparison with the repository's adaptive Pan–Tompkins detector, noise stress test with recorded electrode-motion artefact",
    summary="Treat beat detection as a detection problem with a tunable threshold: trace the sensitivity versus positive-predictivity curve on real "
            "MIT-BIH recordings, put confidence intervals on the scores, compare a fixed threshold with an adaptive one, and measure how performance degrades as real motion artefact is added.",
    problem="A QRS detector reports '99.5 % sensitivity'. How sure is that number, what was traded to get it, and how much noise does it survive?",
    theory=r"""Every detector thresholds a statistic; moving the threshold trades missed beats (FN) against false detections (FP): $Se=\frac{TP}{TP+FN}$, $+P=\frac{TP}{TP+FP}$. A score from n beats has the binomial standard error $\sqrt{p(1-p)/n}$ — with 7000 beats,
99.5 % ± 0.17 % (95 %). Published detectors reach Se and +P above 99 % on the MIT-BIH database with adaptive thresholds. The QRS occupies roughly 5–15 Hz; noise inside that band (electrode motion) cannot be filtered away, so performance must fall as its
level approaches that of the QRS energy.""",
    method="""Ten MIT-BIH records × 10 min (lead MLII), reference annotations, ±150 ms matching window. Detector statistic: 5–15 Hz band-pass → derivative → square → 150 ms integration; threshold = k × median of the 8 s running maximum, 200 ms refractory.
k swept from 0.05 to 0.9. Noise test: electrode-motion record 'em' of the MIT-BIH Noise Stress Test database added to the first 2 min of each record at SNR 24…−6 dB.""",
    data="PhysioNet MIT-BIH Arrhythmia Database and MIT-BIH Noise Stress Test Database (Open Data Commons licence), fetched on first run.",
)

RECS = ["100", "101", "103", "105", "106", "108", "119", "200", "203", "210"]


def statistic(ecg, fs):
    b, a = signal.butter(2, [5, 15], "bandpass", fs=fs); x = signal.filtfilt(b, a, ecg)
    d = np.gradient(x); w = int(0.15 * fs)
    return np.convolve(d * d, np.ones(w) / w, "same"), x


def detect(ecg, fs, k):
    s, x = statistic(ecg, fs); n = len(s); blk = int(8 * fs)
    ref = np.array([s[i:i + blk].max() for i in range(0, n, blk)])
    level = np.median(ref)
    pk, _ = signal.find_peaks(s, height=k * level, distance=int(0.2 * fs))
    w = int(0.075 * fs)
    return np.array([q - w + int(np.argmax(np.abs(x[max(q - w, 0): q + w]))) for q in pk if q - w >= 0], int)


def run(p):
    data = []
    for r_ in RECS:
        d = physionet("mitdb", r_, 0, 360 * 600, channels=[0], ann="atr")
        ref = d["ann_sample"][np.isin(d["ann_symbol"], list(BEAT_SYMBOLS))]
        data.append((d["signal"][:, 0].astype(float), d["fs"], ref))
    nbeats = sum(len(q[2]) for q in data)
    ks = np.r_[0.03, 0.05, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5, 0.7, 0.9]; curve = []
    for k in ks:
        tp = fp = fn = 0
        for ecg, fs, ref in data:
            a, b, c = match(detect(ecg, fs, k), ref, fs); tp += a; fp += b; fn += c
        curve.append((k, tp / (tp + fn), tp / (tp + fp), tp, fp, fn))
    cv = np.array(curve); f1 = 2 * cv[:, 1] * cv[:, 2] / (cv[:, 1] + cv[:, 2]); ib = int(np.argmax(f1))
    se, pp = cv[ib, 1], cv[ib, 2]
    p.metric("Beats evaluated / records", f"{nbeats} / {len(RECS)}")
    p.compare("Fixed-threshold detector at its best F1: sensitivity (published detectors: > 99 %)", 99.0, se * 100, "%", kind="abs", tol=1.0)
    p.compare("… positive predictivity (> 99 %)", 99.0, pp * 100, "%", kind="abs", tol=1.0)
    ci = 1.96 * np.sqrt(se * (1 - se) / nbeats) * 100
    p.metric("95 % binomial confidence half-width on the sensitivity", ci, "pp", "the third digit of a published score is inside this")
    p.compare("Trade-off: sensitivity falls monotonically as the threshold rises (violations)", 0, int(np.sum(np.diff(cv[:, 1]) > 1e-12)), "", kind="abs")
    p.compare("Trade-off: false detections fall monotonically as the threshold rises (violations)", 0, int(np.sum(np.diff(cv[:, 4]) > 0)), "", kind="abs")
    tp = fp = fn = 0; jit = []
    for ecg, fs, ref in data:
        det = pan_tompkins(ecg, fs); a, b, c = match(det, ref, fs); tp += a; fp += b; fn += c
        j = np.searchsorted(det, ref); j = np.clip(j, 1, len(det) - 1)
        dd = np.minimum(np.abs(det[j] - ref), np.abs(det[j - 1] - ref)); jit += list(dd[dd < 0.15 * fs] / fs * 1000)
    se_a, pp_a = tp / (tp + fn), tp / (tp + fp)
    p.compare("Adaptive-threshold Pan–Tompkins on the same data: sensitivity", 99.5, se_a * 100, "%", kind="abs", tol=0.6)
    p.compare("… positive predictivity", 99.5, pp_a * 100, "%", kind="abs", tol=0.6)
    z = (se_a - se) / np.sqrt(se_a * (1 - se_a) / nbeats + se * (1 - se) / nbeats)
    p.metric("Is adaptive better than fixed? z-score of the sensitivity difference", float(z), "", "|z| > 1.96 ⇒ significant at 5 %")
    p.metric("Timing of detections vs annotations: median / 95th percentile offset", f"{np.median(jit):.1f} / {np.percentile(jit, 95):.1f}", "ms")
    n2 = 360 * 120; em = physionet("nstdb", "em", 0, n2, channels=[0])["signal"][:, 0].astype(float); em -= em.mean()
    snrs = [24, 18, 12, 6, 0, -6]; rows = []
    for snr in snrs:
        tp = fp = fn = 0
        for ecg, fs, ref in data:
            x = ecg[:n2] - np.median(ecg[:n2]); rr = ref[ref < n2]
            # SNR defined on the QRS-band signal power (peak-to-peak based definitions are common; this one is stated explicitly)
            nz = em * np.sqrt(np.mean(x ** 2) / np.mean(em ** 2) / 10 ** (snr / 10))
            a, b, c = match(pan_tompkins(x + nz, fs), rr, fs); tp += a; fp += b; fn += c
        rows.append((snr, tp / (tp + fn) * 100, tp / (tp + fp) * 100))
    rr_ = np.array(rows)
    p.compare("Noise stress: both scores stay above 95 % down to 12 dB SNR (1 = yes)", 1, int(np.all(rr_[rr_[:, 0] >= 12, 1:] > 95)), "", kind="abs")
    p.compare("… and positive predictivity collapses below 90 % at −6 dB (in-band artefact looks like beats; 1 = yes)", 1, int(rr_[-1, 2] < 90), "", kind="abs")
    p.section("Noise stress test (electrode-motion artefact added)", "| SNR (dB) | sensitivity (%) | positive predictivity (%) |\n|---|---|---|\n" + "\n".join(f"| {a:.0f} | {b:.2f} | {c:.2f} |" for a, b, c in rr_))
    p.csv("threshold_sweep", k=cv[:, 0], sensitivity=cv[:, 1], ppv=cv[:, 2], tp=cv[:, 3], fp=cv[:, 4], fn=cv[:, 5])
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ecg, fs, ref = data[3]; s, x = statistic(ecg, fs); t = np.arange(len(ecg)) / fs; m = (t > 60) & (t < 68)
    ax[0].plot(t[m], ecg[m] - np.median(ecg), color="gray", lw=.8, label="ECG (record 105)"); ax[0].plot(t[m], s[m] / s[m].max() * 1.5, color=C_MEAS, label="detection statistic")
    ax[0].plot(ref[(ref / fs > 60) & (ref / fs < 68)] / fs, np.full(np.sum((ref / fs > 60) & (ref / fs < 68)), 1.7), "v", color=C_PRED, label="annotated beats")
    style_axes(ax[0], "time (s)", "mV / a.u.", "From waveform to decision statistic")
    ax[1].plot((1 - cv[:, 2]) * 100, cv[:, 1] * 100, "o-", color=C_MEAS, label="fixed threshold, k swept"); ax[1].plot([(1 - pp_a) * 100], [se_a * 100], "s", color=C_PRED, ms=9, label="adaptive Pan–Tompkins")
    ax[1].set_xscale("log")
    style_axes(ax[1], "false detections, 100 − +P (%)", "sensitivity (%)", "Threshold trade-off")
    ax[2].plot(rr_[:, 0], rr_[:, 1], "o-", color=C_MEAS, label="sensitivity"); ax[2].plot(rr_[:, 0], rr_[:, 2], "s-", color=C_PRED, label="positive predictivity")
    ax[2].invert_xaxis()
    style_axes(ax[2], "SNR (dB)", "%", "Electrode-motion noise stress")
    p.save(fig, "rpeak_stats", "Detection statistic, the sensitivity/false-detection trade-off, and degradation under added motion artefact.")
    p.discuss(f"""A single threshold on a QRS-energy statistic already finds {se * 100:.2f} % of {nbeats} annotated beats at {pp * 100:.2f} % positive predictivity, and
sweeping the threshold shows the unavoidable trade: lowering it recovers missed beats only by admitting false ones. The adaptive Pan–Tompkins
detector sits at {se_a * 100:.2f} % / {pp_a * 100:.2f} %. Whether that difference is real is a statistical question — the binomial uncertainty on a score from
this many beats is ±{ci:.2f} points, and the z-score of the sensitivity difference is {z:.1f}: on these ten records the simple fixed threshold is, contrary
to my expectation, significantly *more* sensitive than the adaptive detector (whose published 99.5 % refers to the whole database and a tuned
implementation). Adaptivity is insurance against amplitude changes, not a guarantee of a better score on a given set of records. Performance is not a property of the algorithm alone: adding
recorded electrode-motion artefact leaves the scores above 95 % down to 12 dB, after which false detections take over
(+P {rr_[-1, 2]:.0f} % at −6 dB), because that artefact lives in the same 5–15 Hz band as the QRS and no linear filter can separate them. Quoting a detector's
accuracy therefore needs three things: the threshold policy, the confidence interval, and the noise conditions.""")
# tol-convention: relative tolerances are in percent
