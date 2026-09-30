from eelab import *
from eelab.bio import eegmmidb
from scipy import signal, stats

META = dict(
    id="AM-185", title="Independent component analysis for removing eye blinks from EEG", level="H",
    tools="Own FastICA (PCA whitening, symmetric fixed-point iteration with tanh non-linearity), validation on synthetic mixtures with the Amari index, blink-component identification by frontal topography and kurtosis, reconstruction without the artefact, comparison with channel regression, preservation checks in the alpha band",
    summary="Separate a 64-channel EEG recording into statistically independent sources, find the one that is the eye blink, remove it and rebuild the "
            "signals — after first proving on synthetic mixtures that the algorithm recovers known sources — and measure both what was removed and what was preserved.",
    problem="An eye blink is 10 times larger than brain activity at the forehead and leaks into every electrode. How can it be subtracted without subtracting the brain?",
    theory=r"""Model $x=As$: sensors are linear mixtures of independent sources. After whitening, the unmixing is a rotation; FastICA finds it by maximising non-Gaussianity: $w\leftarrow E[z\,g(w^Tz)]-E[g'(w^Tz)]\,w$ with g = tanh, followed by symmetric
decorrelation. ICA recovers sources up to order, sign and scale; quality on known mixtures is the Amari index of $WA$ (0 = perfect). A blink is a strongly non-Gaussian (high-kurtosis), frontally dominant source, nearly independent of cortical
rhythms — an ideal ICA target. Removing it means zeroing its column before remixing. Regressing a frontal channel out of all others also removes blinks, but takes with it whatever brain activity that channel contains.""",
    method="""Synthetic: 4 sources (sine, sawtooth, Laplacian noise, amplitude-modulated tone), random 4 × 4 mixing, 20 trials. Real: EEG Motor Movement/Imagery database, subject 1, run 1 (eyes open, 64 channels, 160 Hz, 61 s), band-pass 1–40 Hz, reduced to
20 principal components, FastICA. Blinks located on Fpz (> 5 robust standard deviations of the low-passed signal). Blink component: largest |correlation| with the frontal-polar average.""",
    data="PhysioNet EEG Motor Movement/Imagery Dataset (Schalk et al. 2004).",
)


def fastica(X, ncomp, rng, iters=400, tol=1e-7):
    """X: [channels, samples]. Returns (S sources, W unmixing on centred data, A mixing, iterations)."""
    Xc = X - X.mean(1, keepdims=True)
    U, s, _ = np.linalg.svd(Xc @ Xc.T / Xc.shape[1]); K = (U[:, :ncomp] / np.sqrt(s[:ncomp])).T; Z = K @ Xc
    W = np.linalg.qr(rng.normal(size=(ncomp, ncomp)))[0]
    sym = lambda M: np.linalg.solve(np.real(__import__("scipy.linalg", fromlist=["sqrtm"]).sqrtm(M @ M.T)), M)
    for it in range(iters):
        G = np.tanh(W @ Z); Wn = sym(G @ Z.T / Z.shape[1] - np.diag((1 - G ** 2).mean(1)) @ W)
        lim = np.max(np.abs(np.abs(np.sum(Wn * W, 1)) - 1)); W = Wn
        if lim < tol:
            break
    Wf = W @ K
    return Wf @ Xc, Wf, np.linalg.pinv(Wf), it + 1


def amari(P):
    P = np.abs(P); n = len(P)
    return (np.sum(P / P.max(1, keepdims=True)) - n + np.sum(P / P.max(0, keepdims=True)) - n) / (2 * n * (n - 1))


def run(p):
    r = p.rng; t = np.arange(8000) / 1000; am = []; cors = []
    for _ in range(20):
        S = np.array([np.sin(2 * pi * 7 * t + r.uniform(0, 6)), signal.sawtooth(2 * pi * 3.1 * t + r.uniform(0, 6)), r.laplace(size=len(t)), np.sin(2 * pi * 23 * t) * (1 + 0.8 * np.sin(2 * pi * 0.7 * t))])
        S = (S - S.mean(1, keepdims=True)) / S.std(1, keepdims=True); A = r.normal(size=(4, 4))
        Sh, W, _, _ = fastica(A @ S, 4, r); am.append(amari(W @ A))
        C = np.abs(np.corrcoef(np.vstack([S, Sh]))[:4, 4:]); cors.append(C.max(1).min())
    p.compare("Synthetic mixtures: Amari index of W·A (0 = perfect separation; mean of 20 trials)", 0.0, float(np.mean(am)), "", kind="abs", tol=0.03)
    p.compare("Synthetic mixtures: worst |correlation| between a true source and its estimate", 1.0, float(np.min(cors)), "", tol=2)
    X, fs, labels, _ = eegmmidb(1, 1); lab = [l.upper() for l in labels]
    b, a = signal.butter(4, [1, 40], "bandpass", fs=fs); X = signal.filtfilt(b, a, X, axis=1) * 1e6 if np.abs(X).max() < 1e-2 else signal.filtfilt(b, a, X, axis=1)
    fp = [lab.index(c) for c in ("FP1", "FPZ", "FP2")]; occ = [lab.index(c) for c in ("O1", "OZ", "O2")]
    bl, al = signal.butter(2, 5, "low", fs=fs); ref = signal.filtfilt(bl, al, X[fp].mean(0))
    mad = np.median(np.abs(ref - np.median(ref))) * 1.4826; pk, _ = signal.find_peaks(np.abs(ref), height=5 * mad, distance=int(0.4 * fs))
    blink = np.zeros(X.shape[1], bool)
    for q in pk:
        blink[max(0, q - int(0.25 * fs)): q + int(0.25 * fs)] = True
    p.metric("Blinks found on the frontal-polar channels", len(pk), "", f"in {X.shape[1] / fs:.0f} s; {blink.mean() * 100:.0f} % of samples within ±0.25 s of a blink")
    S, W, A, its = fastica(X, 20, r)
    cc = np.array([np.corrcoef(S[k], X[fp].mean(0))[0, 1] for k in range(20)]); kb = int(np.argmax(np.abs(cc)))
    kurt = stats.kurtosis(S, axis=1, fisher=False)
    p.compare("The blink component is the most kurtotic one (rank of its kurtosis among 20; 1 = highest)", 1, int(np.sum(kurt > kurt[kb])) + 1, "", kind="abs", tol=1)
    topo = np.abs(A[:, kb]); front_share = topo[fp].mean() / topo.mean()
    p.compare("Its scalp map is frontal: weight at Fp1/Fpz/Fp2 relative to the average electrode (> 3; 1 = yes)", 1, int(front_share > 3), "", kind="abs")
    p.metric("Blink component: correlation with frontal average / kurtosis / frontal weight ratio", f"{abs(cc[kb]):.2f} / {kurt[kb]:.0f} / {front_share:.1f}", "", f"FastICA converged in {its} iterations")
    Xc = X - X.mean(1, keepdims=True); Xclean = Xc - np.outer(A[:, kb], S[kb])
    amp = lambda Y: np.median([np.ptp(Y[fp[1], max(0, q - int(0.25 * fs)): q + int(0.25 * fs)]) for q in pk])
    a0, a1 = amp(Xc), amp(Xclean); base = np.median([np.ptp(Xc[fp[1], s: s + int(0.5 * fs)]) for s in range(0, Xc.shape[1] - int(0.5 * fs), int(0.5 * fs)) if not blink[s: s + int(0.5 * fs)].any()])
    p.compare("Blink amplitude at Fpz after removal, relative to the blink-free background (≈ 1 if the blink is gone)", 1.0, a1 / base, "", tol=60)
    p.metric("Median blink peak-to-peak at Fpz: before / after / blink-free background", f"{a0:.0f} / {a1:.0f} / {base:.0f}", "µV", f"reduction {100 * (1 - (a1 - base) / (a0 - base)):.0f} % of the excess")

    def alpha(Y, ch):
        f, P = signal.welch(Y[ch][:, ~blink], fs, nperseg=int(2 * fs), axis=1); m = (f >= 8) & (f <= 13)
        return np.trapezoid(P[:, m], f[m], axis=1).mean()
    ch_al = (alpha(Xclean, occ) / alpha(Xc, occ) - 1) * 100
    p.compare("Occipital alpha power outside blinks: change caused by the removal", 0.0, ch_al, "%", kind="abs", tol=5)
    beta_ = Xc @ Xc[fp].mean(0) / np.sum(Xc[fp].mean(0) ** 2); Xreg = Xc - np.outer(beta_, Xc[fp].mean(0))
    front2 = [lab.index(c) for c in ("AF3", "AFZ", "AF4", "F3", "FZ", "F4")]
    keep_ica = np.mean(np.var(Xclean[front2][:, ~blink], axis=1) / np.var(Xc[front2][:, ~blink], axis=1))
    keep_reg = np.mean(np.var(Xreg[front2][:, ~blink], axis=1) / np.var(Xc[front2][:, ~blink], axis=1))
    p.compare("Blink-free frontal EEG retained (variance ratio): ICA keeps more than regression on the frontal-polar channel (1 = yes)", 1, int(keep_ica > keep_reg), "", kind="abs")
    p.metric("Variance of blink-free frontal EEG (AF/F electrodes) retained: ICA / regression", f"{keep_ica * 100:.0f} % / {keep_reg * 100:.0f} %", "", "regression subtracts the brain activity seen by the reference channel too")
    tt = np.arange(X.shape[1]) / fs; q0 = pk[min(2, len(pk) - 1)] / fs; m = (tt > q0 - 3) & (tt < q0 + 3)
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    ax[0].plot(tt[m], Xc[fp[1], m], color=C_PRED, lw=.8, label="Fpz raw"); ax[0].plot(tt[m], Xclean[fp[1], m], color=C_MEAS, lw=.8, label="Fpz after ICA")
    style_axes(ax[0], "time (s)", "µV", "Blinks removed, background kept")
    ax[1].plot(tt[m], S[kb, m], color="k", lw=.8)
    style_axes(ax[1], "time (s)", "a.u.", f"The blink component (kurtosis {kurt[kb]:.0f})", legend=False)
    order = np.argsort(-np.abs(A[:, kb]))[:12]
    ax[2].barh([labels[i] for i in order][::-1], np.abs(A[order, kb])[::-1] / np.abs(A[:, kb]).max(), color=C_MEAS)
    style_axes(ax[2], "relative weight in the component's scalp map", "", "Where the component projects", legend=False)
    p.save(fig, "ica", "A frontal channel before and after removing the blink component, the component's time course, and its strongest electrodes.")
    p.discuss(f"""On mixtures with known sources FastICA recovers them essentially exactly (Amari index {np.mean(am):.3f}, source correlations above {np.min(cors):.2f}), which is the
licence to use it on data where the truth is unknown. On the real recording one component stands out on every criterion at once: it correlates
{abs(cc[kb]):.2f} with the frontal-polar channels, has a kurtosis of {kurt[kb]:.0f} against ≈ 3 for ongoing EEG, and projects {front_share:.0f} times more strongly to Fp1/Fpz/Fp2 than
to the average electrode. Removing it brings the blink at Fpz from {a0:.0f} µV to {a1:.0f} µV peak-to-peak, against a blink-free background of {base:.0f} µV, while
occipital alpha power changes by {ch_al:+.1f} %. The comparison with regression shows why a source model is preferable: subtracting a scaled copy of the
frontal-polar signal keeps only {keep_reg * 100:.0f} % of the blink-free activity at neighbouring frontal electrodes, ICA {keep_ica * 100:.0f} %. The usual caveats apply — the blink is
identified here by a rule, the number of components is a choice, and ICA assumes the mixing does not change over the recording.""")
# tol-convention: relative tolerances are in percent
