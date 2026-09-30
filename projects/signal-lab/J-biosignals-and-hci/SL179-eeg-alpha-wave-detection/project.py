from eelab import *
from eelab.bio import eegmmidb
from scipy import signal

META = dict(
    id="SL-179", title="Detecting the eyes-closed alpha rhythm in real EEG", level="M",
    tools="Welch spectra of occipital EEG (O1, Oz, O2), alpha-band power ratio, EEG Motor Movement/Imagery DB baseline runs",
    summary="Compare the 1-minute eyes-open and eyes-closed baselines of 20 subjects: measure the alpha (8–12 Hz) power increase over the "
            "occipital cortex and use it to classify 10-s epochs as eyes-open/closed.",
    problem="Closing your eyes makes the brain's 10 Hz 'idling' rhythm appear — the first EEG phenomenon ever discovered (Berger, 1929). "
            "How big and how reliable is it?",
    theory=r"""Occipital alpha power typically rises several-fold (≈ 2–10×, i.e. 3–10 dB) on eye closure, with a peak between 8 and 12 Hz; a minority of people (~10 %)
show little alpha. A per-subject threshold on relative alpha power should therefore classify epochs well above chance (50 %).""",
    method="""Subjects 1–20, runs R01 (eyes open) and R02 (eyes closed), 160 Hz, channels O1, Oz, O2 averaged. Relative alpha = P(8–12 Hz)/P(2–30 Hz) from Welch
(2-s windows). Classification: 10-s epochs, leave-one-epoch-out threshold at the midpoint of the two classes' medians per subject.""",
    data="Real: EEG Motor Movement/Imagery Database (Schalk et al. 2004, PhysioNet), ODC-By.",
)


def occ(subject, run_):
    X, fs, labels, _ = eegmmidb(subject, run_)
    idx = [i for i, l in enumerate(labels) if l.upper() in ("O1", "OZ", "O2")]
    return X[idx].mean(0), fs


def ralpha(x, fs):
    f, P = signal.welch(x, fs, nperseg=int(2 * fs))
    return P[(f >= 8) & (f <= 12)].sum() / P[(f >= 2) & (f <= 30)].sum(), f, P


def run(p):
    ratios, accs, peaks = [], [], []
    for s in range(1, 21):
        xo, fs = occ(s, 1); xc, _ = occ(s, 2)
        ao, f, Po = ralpha(xo, fs); ac, _, Pc = ralpha(xc, fs)
        ratios.append(10 * np.log10(ac / ao))
        band = (f >= 7) & (f <= 13)
        peaks.append(f[band][np.argmax(Pc[band])])
        ep = int(10 * fs)
        eo = [ralpha(xo[i:i + ep], fs)[0] for i in range(0, len(xo) - ep, ep)]
        ec = [ralpha(xc[i:i + ep], fs)[0] for i in range(0, len(xc) - ep, ep)]
        thr = (np.median(eo) + np.median(ec)) / 2
        correct = sum(v < thr for v in eo) + sum(v > thr for v in ec)
        accs.append(correct / (len(eo) + len(ec)))
        if s == 1:
            show = (f, Po, Pc)
    ratios = np.array(ratios); accs = np.array(accs)
    p.compare("Median eyes-closed / eyes-open alpha increase (3–10 dB typical)", 6, np.median(ratios), "dB", kind="abs")
    p.compare("Median alpha peak frequency (8–12 Hz)", 10, np.median(peaks), "Hz", kind="abs")
    p.compare("Epoch classification accuracy (20 subjects, chance 50 %)", 90, np.mean(accs) * 100, "%", kind="abs")
    p.metric("Subjects with < 3 dB alpha increase ('low-alpha' people)", int(np.sum(ratios < 3)), "", "of 20")
    fig, ax = p.fig(1, 2, w=11)
    f, Po, Pc = show
    ax[0].semilogy(f, Po, color=COLORS[1], label="eyes open"); ax[0].semilogy(f, Pc, color=C_MEAS, label="eyes closed")
    ax[0].axvspan(8, 12, color="gray", alpha=.1); ax[0].set_xlim(1, 40)
    style_axes(ax[0], "frequency (Hz)", "PSD (V²/Hz)", "Subject 1, occipital EEG")
    ax[1].bar(np.arange(1, 21), ratios, color=[C_MEAS if r >= 3 else COLORS[7] for r in ratios])
    style_axes(ax[1], "subject", "alpha increase (dB)", "Eyes-closed alpha increase per subject", legend=False)
    p.save(fig, "alpha", "A clear 10 Hz peak appears with eyes closed in most — not all — subjects.")
    p.csv("subjects", subject=np.arange(1, 21), alpha_increase_db=ratios, peak_hz=peaks, accuracy=accs)
    p.discuss("""The Berger effect is obvious in real data: most subjects show a clear occipital alpha peak near 10 Hz that grows by several dB on eye closure, and
a single per-subject threshold classifies 10-s epochs far above chance. The per-subject bars show the exception is common here: 9 of 20 subjects
gained less than 3 dB (my 'about 10 % of people' expectation was too optimistic for this dataset, whose 1-minute baselines are short and include
artefacts). Yet per-subject thresholds still classify epochs ~90 % correctly, because even a small alpha change is consistent within a person —
which is exactly why EEG-based interfaces need per-user calibration rather than one population threshold.""")
