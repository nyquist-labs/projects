from eelab import *
from eelab.bio import eegmmidb
from scipy import signal

META = dict(
    id="SL-180", title="Removing eye-blink artefacts from EEG with ICA", level="H",
    tools="Own FastICA (symmetric, tanh non-linearity, whitening), blink-component identification by frontal topography, EEG Motor Movement/Imagery DB",
    summary="Decompose 64-channel real EEG into independent components, identify the eye-blink component from its frontal dominance and "
            "spike shape, remove it, and measure how much blink energy disappears from Fp1/Fp2 while occipital EEG is left untouched.",
    problem="Every blink produces a potential 10× larger than the brain signals near the forehead. Can it be subtracted without damaging "
            "the EEG underneath?",
    theory=r"""Blinks are a spatially fixed source mixed linearly into all electrodes (strongest frontally), statistically independent of cortical sources and highly
non-Gaussian (spiky) — exactly the assumptions of ICA. Projecting out that one component should remove most of the blink variance at Fp1/Fp2
(> 80 %) while changing posterior channels by only a few percent.""",
    method="""Subject 1, eyes-open baseline R01 (61 s, 160 Hz, 64 channels), 1 Hz high-pass. Whitening via PCA to 30 components, FastICA (symmetric, tanh, 200 iterations).
Blink component = largest |kurtosis| × frontal/posterior weight ratio. Blink epochs detected on Fp1+Fp2 (threshold 5 × MAD); metrics inside ±0.3 s of blinks.""",
    data="Real: EEG Motor Movement/Imagery Database (PhysioNet).",
)


def fastica(Z, n_iter=200, seed=0):
    rng_ = np.random.default_rng(seed)
    n = Z.shape[0]
    W = np.linalg.qr(rng_.normal(size=(n, n)))[0]
    for _ in range(n_iter):
        Y = W @ Z
        g = np.tanh(Y); gp = 1 - g * g
        Wn = (g @ Z.T) / Z.shape[1] - np.diag(gp.mean(1)) @ W
        u, s_, vt = np.linalg.svd(Wn); W = u @ vt
    return W


def run(p):
    from scipy.stats import kurtosis
    X, fs, labels, _ = eegmmidb(1, 1)
    b, a = signal.butter(2, 1, "highpass", fs=fs); X = signal.filtfilt(b, a, X, axis=1)
    mu = X.mean(1, keepdims=True); Xc = X - mu
    C = np.cov(Xc); ev, E = np.linalg.eigh(C); order = np.argsort(ev)[::-1][:30]
    D = np.diag(1 / np.sqrt(ev[order])); V = D @ E[:, order].T
    Z = V @ Xc
    W = fastica(Z)
    S = W @ Z
    A = np.linalg.pinv(W @ V)            # mixing: channels × components
    front = [labels.index(c) for c in ("Fp1", "Fpz", "Fp2") if c in labels]
    post = [labels.index(c) for c in ("O1", "Oz", "O2", "Pz") if c in labels]
    score = np.abs(kurtosis(S, axis=1)) * (np.abs(A[front]).mean(0) / (np.abs(A[post]).mean(0) + 1e-12))
    k = int(np.argmax(score))
    Xclean = Xc - np.outer(A[:, k], S[k])
    fp = Xc[front].mean(0)
    mad = np.median(np.abs(fp - np.median(fp)))
    pk, _ = signal.find_peaks(np.abs(fp), height=5 * mad * 1.4826, distance=int(0.5 * fs))
    mask = np.zeros(X.shape[1], bool)
    for q in pk:
        mask[max(q - int(0.3 * fs), 0): q + int(0.3 * fs)] = True
    red_f = 1 - np.var(Xclean[front][:, mask]) / np.var(Xc[front][:, mask])
    red_p = 1 - np.var(Xclean[post][:, ~mask]) / np.var(Xc[post][:, ~mask])
    p.compare("Blink variance removed at Fp1/Fpz/Fp2 (inside blink windows)", 80, red_f * 100, "%", kind="abs", note="> 80 % expected")
    p.compare("Occipital variance changed outside blinks", 0, red_p * 100, "%", kind="abs")
    p.metric("Blinks detected in 61 s", len(pk)); p.metric("Blink component kurtosis", kurtosis(S[k]))
    t = np.arange(X.shape[1]) / fs
    fig, ax = p.fig(2, 1, h=6, sharex=True)
    m = (t > 5) & (t < 25)
    ax[0].plot(t[m], Xc[front[0], m] * 1e6 if np.abs(Xc).max() < 1 else Xc[front[0], m], color="gray", lw=.7, label="Fp1 original")
    ax[0].plot(t[m], Xclean[front[0], m] * 1e6 if np.abs(Xc).max() < 1 else Xclean[front[0], m], color=C_MEAS, lw=.7, label="Fp1 after ICA")
    style_axes(ax[0], None, "µV", "Frontal channel: blinks removed")
    ax[1].plot(t[m], S[k, m], color=COLORS[1], lw=.7, label=f"independent component {k}")
    style_axes(ax[1], "time (s)", "a.u.", "The blink component")
    p.save(fig, "ica", "ICA isolates the blinks into one component; subtracting it cleans the frontal EEG.")
    p.discuss("""One independent component captures the blinks: it is extremely spiky (high kurtosis) and loads almost only on the frontal electrodes. Removing it
cancels most of the blink energy at Fp1/Fp2 while leaving occipital channels essentially unchanged outside blinks — the linear-mixing and
independence assumptions hold well for ocular artefacts. The residue inside blink windows is frontal brain activity plus the part of the blink
not captured by a single fixed topography (eye movements add a second, horizontal component).""")
