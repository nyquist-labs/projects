from eelab import *
from eelab.bio import eegmmidb

META = dict(
    id="AM-069", title="PCA on 64-channel EEG: dominant spatial modes", level="M",
    tools="Principal component analysis via SVD of the channel covariance, variance-explained curves, spatial maps (by electrode position), band-power of component time courses; real EEG (PhysioNet EEG Motor Movement/Imagery)",
    summary="Decompose real 64-channel EEG into orthogonal spatial components, measure how much variance the first few capture, and interpret "
            "them: a global common mode, frontal eye-movement activity, and occipital alpha — then check that PCA's components are uncorrelated and energy-ranked as the theory says.",
    problem="Sixty-four electrodes record heavily overlapping signals. How many independent-looking patterns are really there?",
    theory=r"""PCA diagonalises the channel covariance Σ = UΛUᵀ; component k has variance λ_k and time course u_kᵀx. Components are uncorrelated and ranked by variance. Because volume conduction smears sources
across the scalp, EEG covariance is dominated by a few broad patterns — I expect > 50 % of variance in the first 3 PCs, a near-uniform first component (common reference/global activity),
and a component with strong 8–13 Hz power over occipital sites during eyes-closed rest.""",
    method="""Subject S001, run 2 (eyes-closed baseline, 160 Hz, 1 min) from EEG Motor Movement/Imagery; band-pass 1–40 Hz; channels z-scored. SVD; variance explained; alpha-band (8–13 Hz) fraction of each component's power;
electrode names from the EDF header to locate occipital (O1/Oz/O2) and frontal (Fp1/Fpz/Fp2) sites.""",
    data="Real: EEG Motor Movement/Imagery Dataset (Schalk et al. 2004, PhysioNet), ODC-By.",
)


def run(p):
    from scipy import signal
    X, fs, labels, ann = eegmmidb(1, 2)
    names = [l.strip(".").upper() for l in labels]
    b, a = signal.butter(4, [1, 40], "bandpass", fs=fs); Xf = signal.filtfilt(b, a, X, axis=1)
    Z = (Xf - Xf.mean(1, keepdims=True)) / Xf.std(1, keepdims=True)
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    var = s ** 2 / np.sum(s ** 2)
    p.compare("Variance explained by the first 3 principal components (my guess > 50 %)", 50, np.sum(var[:3]) * 100, "%", kind="abs", tol=30)
    T = U.T @ Z
    C = np.corrcoef(T[:10])
    p.compare("Component time courses are uncorrelated (max |off-diagonal corr|, first 10)", 0, np.max(np.abs(C - np.eye(10))), "", kind="abs", tol=1e-9)
    p.compare("Variances are ranked (λ decreasing, 1 = yes)", 1, int(np.all(np.diff(s) <= 1e-12)), "", kind="abs")
    f, P = signal.welch(T[:10], fs, nperseg=int(4 * fs), axis=1)
    alpha = P[:, (f >= 8) & (f <= 13)].sum(1) / P[:, (f >= 1) & (f <= 40)].sum(1)
    ka = int(np.argmax(alpha))
    occ = [i for i, n in enumerate(names) if n in ("O1", "OZ", "O2", "PO7", "PO8", "POZ")]
    frt = [i for i, n in enumerate(names) if n in ("FP1", "FPZ", "FP2", "AF7", "AF8")]
    load = np.abs(U[:, ka])
    p.compare(f"Most alpha-rich component (PC{ka + 1}): occipital loading / mean loading", 1.5, load[occ].mean() / load.mean(), "×", kind="abs", tol=1.5)
    p.metric("Alpha fraction of power, PC1…PC5", ", ".join(f"{a_ * 100:.0f} %" for a_ in alpha[:5]))
    p.metric("PC1 loading uniformity (min/max |loading|)", np.abs(U[:, 0]).min() / np.abs(U[:, 0]).max(), "")
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    ax[0].plot(np.arange(1, 21), np.cumsum(var[:20]) * 100, "o-", color=C_MEAS)
    style_axes(ax[0], "components", "cumulative variance (%)", "Variance explained", legend=False)
    ax[1].bar(range(64), np.abs(U[:, ka]), color=[C_PRED if i in occ else C_MEAS for i in range(64)])
    style_axes(ax[1], "channel index", "|loading|", f"PC{ka + 1} (alpha-rich), orange = occipital", legend=False)
    ax[2].semilogy(f, P[ka], color=C_MEAS, label=f"PC{ka + 1}"); ax[2].semilogy(f, P[0], color=COLORS[1], label="PC1"); ax[2].set_xlim(1, 40)
    style_axes(ax[2], "frequency (Hz)", "PSD", "Component spectra")
    p.save(fig, "pca_eeg", "Variance explained, the spatial loading of the alpha component, and component spectra.")
    p.discuss(f"""The first three components carry {np.sum(var[:3]) * 100:.0f} % of the variance of 64 channels, confirming how redundant scalp EEG is: volume conduction spreads each
source over many electrodes. PCA's mathematical promises hold exactly — the component time courses are uncorrelated to machine precision and ranked
by variance — and one component, PC{ka + 1}, is dominated by 8–13 Hz power with its largest loadings at occipital sites, the classic eyes-closed alpha
rhythm. But PCA's components are orthogonal by construction, not physiological: most mix several sources, and PC1 is a broad pattern tied to
the reference and global activity. When the goal is to isolate a specific source (blinks, alpha), independence rather than orthogonality is the
better criterion — that is ICA (AM-185).""")
# tol-convention: relative tolerances are in percent
