from eelab import *
from eelab.data import physionet
from scipy.special import digamma
from scipy.spatial import cKDTree

META = dict(
    id="AM-206", title="Mutual information of continuous signals: estimators and a real ECG", level="H",
    tools="Plug-in histogram estimator with bias correction, Kraskov–Stögbauer–Grassberger k-nearest-neighbour estimator (own, KD-tree), Gaussian closed form, nonlinear dependence invisible to correlation, time-delayed mutual information between two ECG leads and within one lead",
    summary="Estimate how many bits one signal carries about another without assuming linearity: validate two estimators where the answer is known, "
            "show a dependence that correlation misses entirely, and apply them to two leads of a real electrocardiogram.",
    problem="Correlation measures only linear dependence. How can the total statistical dependence between two measured signals be quantified in bits?",
    theory=r"""$I(X;Y)=h(X)+h(Y)-h(X,Y)$. Jointly Gaussian: $I=-\tfrac12\log_2(1-ρ^2)$. KSG estimator: for each sample find the distance ε to its k-th neighbour in the joint (max-norm) space, count neighbours $n_x,n_y$ within ε in each marginal:
$\hat I=ψ(k)+ψ(N)-\langleψ(n_x+1)+ψ(n_y+1)\rangle$ (nats); nearly unbiased at independence. Histograms are biased and depend on the bin count. For $Y=X^2+\text{noise}$ with symmetric X, ρ = 0 but I > 0.""",
    method="""Synthetic: 5000 Gaussian pairs, ρ = 0 … 0.95; independent pairs; Y = X² + 0.1·noise. Real: MIT-BIH record 100, leads MLII and V5, 2 min at 360 Hz (subsampled 4×): I between the leads and the auto-mutual information of MLII versus lag (0–1.5 s), next to the correlations.""",
    data="PhysioNet MIT-BIH Arrhythmia Database, record 100.",
)


def ksg(x, y, k=5, rng=None):
    x = (x - x.mean()) / x.std(); y = (y - y.mean()) / y.std(); n = len(x)
    if rng is not None:                                           # quantised data (ADC codes) have exact ties; a tiny dither breaks them
        x = x + 1e-6 * rng.normal(size=n); y = y + 1e-6 * rng.normal(size=n)
    xy = np.c_[x, y]; t = cKDTree(xy); eps = t.query(xy, k + 1, p=np.inf)[0][:, -1] - 1e-12
    tx, ty = cKDTree(x[:, None]), cKDTree(y[:, None])
    nx = np.array([len(tx.query_ball_point([v], e, p=np.inf)) - 1 for v, e in zip(x, eps)])
    ny = np.array([len(ty.query_ball_point([v], e, p=np.inf)) - 1 for v, e in zip(y, eps)])
    return float((digamma(k) + digamma(n) - np.mean(digamma(nx + 1) + digamma(ny + 1))) / np.log(2))


def hist_mi(x, y, bins=16):
    C, _, _ = np.histogram2d(x, y, bins); P = C / C.sum(); px = P.sum(1, keepdims=True); py = P.sum(0, keepdims=True); nz = P > 0
    I = np.sum(P[nz] * np.log2(P[nz] / (px @ py)[nz]))
    return float(I - (np.sum(px > 0) - 1) * (np.sum(py > 0) - 1) / (2 * C.sum() * np.log(2)))


def run(p):
    r = p.rng; n = 5000; rows = []
    for rho in (0.0, 0.3, 0.6, 0.8, 0.95):
        z = r.normal(size=(n, 2)); x = z[:, 0]; y = rho * x + np.sqrt(1 - rho ** 2) * z[:, 1]
        rows.append((rho, -0.5 * np.log2(1 - rho ** 2), ksg(x, y), hist_mi(x, y)))
    rr = np.array(rows)
    p.compare("KSG estimator vs Gaussian closed form −½log₂(1 − ρ²), worst absolute error for ρ = 0…0.95", 0.0, float(np.max(np.abs(rr[:, 2] - rr[:, 1]))), "bit", kind="abs", tol=0.05)
    p.compare("Histogram estimator (16 bins, bias-corrected), worst absolute error — larger at strong dependence", 0.0, float(np.max(np.abs(rr[:, 3] - rr[:, 1]))), "bit", kind="abs", tol=0.2)
    x = r.normal(size=n); y = x ** 2 + 0.1 * r.normal(size=n)
    p.compare("Y = X² + noise: correlation coefficient (≈ 0)", 0.0, float(np.corrcoef(x, y)[0, 1]), "", kind="abs", tol=0.05)
    p.compare("… yet the mutual information is large (KSG > 1 bit; 1 = yes)", 1, int(ksg(x, y) > 1.0), "", kind="abs")
    p.metric("Y = X² + noise: KSG / histogram estimate", f"{ksg(x, y):.2f} / {hist_mi(x, y):.2f} bit")
    d = physionet("mitdb", "100", 0, 360 * 120); s = d["signal"][::4].astype(float); fs = d["fs"] / 4
    a, b = s[:, 0] - s[:, 0].mean(), s[:, 1] - s[:, 1].mean()
    rho = np.corrcoef(a, b)[0, 1]; I_ab = ksg(a, b, rng=r)
    p.compare("Two ECG leads: measured MI exceeds what their correlation alone implies (nonlinear/non-Gaussian dependence; 1 = yes)", 1, int(I_ab > -0.5 * np.log2(1 - rho ** 2)), "", kind="abs")
    p.metric("Leads MLII vs V5: correlation / Gaussian-implied MI / KSG MI", f"{rho:.2f} / {-0.5 * np.log2(1 - rho ** 2):.2f} / {I_ab:.2f} bit")
    lags = np.arange(0, int(1.5 * fs), 3); ami = []; acf = []
    for L_ in lags:
        u, v = a[: len(a) - L_], a[L_:]; ami.append(ksg(u[::2], v[::2], k=4, rng=r)); acf.append(np.corrcoef(u, v)[0, 1])
    ami, acf = np.array(ami), np.array(acf)
    t_beat = lags[np.argmax(ami[lags / fs > 0.4])] / fs if np.any(lags / fs > 0.4) else np.nan
    k0 = lags / fs > 0.4; t_beat = (lags[k0][np.argmax(ami[k0])]) / fs
    from eelab.bio import BEAT_SYMBOLS
    dd = physionet("mitdb", "100", 0, 360 * 120, channels=[0], ann="atr"); bs = dd["ann_sample"][np.isin(dd["ann_symbol"], list(BEAT_SYMBOLS))]
    rr_mean = np.mean(np.diff(bs)) / 360
    p.compare("Auto-mutual information of MLII peaks again one heartbeat later (lag vs mean RR interval)", rr_mean, t_beat, "s", tol=8)
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].plot(rr[:, 0], rr[:, 1], "k-", label="Gaussian formula"); ax[0].plot(rr[:, 0], rr[:, 2], "o", color=C_MEAS, label="KSG"); ax[0].plot(rr[:, 0], rr[:, 3], "s", color=C_PRED, label="histogram")
    style_axes(ax[0], "correlation ρ", "I (bits)", "Estimators on Gaussian pairs")
    ax[1].plot(x[:1500], y[:1500], ".", ms=2, color=C_MEAS)
    style_axes(ax[1], "X", "Y = X² + noise", f"ρ ≈ {np.corrcoef(x, y)[0, 1]:.2f}, yet I ≈ {ksg(x, y):.1f} bit", legend=False)
    ax[2].plot(lags / fs, ami, color=C_MEAS, label="auto-mutual information"); ax[2].plot(lags / fs, acf, color=C_PRED, label="autocorrelation"); ax[2].axvline(rr_mean, color="gray", ls=":", label="mean RR")
    style_axes(ax[2], "lag (s)", "bits / correlation", "ECG lead MLII")
    p.save(fig, "mutual_information", "Estimator validation, a dependence invisible to correlation, and time-lagged mutual information of a real ECG.")
    p.discuss(f"""The k-nearest-neighbour (KSG) estimator recovers the Gaussian closed form within {np.max(np.abs(rr[:, 2] - rr[:, 1])):.3f} bit from ρ = 0 to 0.95, while a 16-bin histogram,
even bias-corrected, errs by up to {np.max(np.abs(rr[:, 3] - rr[:, 1])):.2f} bit at strong dependence, where the joint distribution is concentrated in too few bins. The
case for mutual information is the parabola: correlation {np.corrcoef(x, y)[0, 1]:.2f}, dependence {ksg(x, y):.1f} bits. On a real ECG (after one practical fix: the recorder's integer codes produce exact ties, and the
first run returned an infinite estimate until a 10⁻⁶ dither broke them) the two leads share {I_ab:.2f} bits per
sample — more than their correlation of {rho:.2f} would imply for Gaussian signals, because the QRS complex couples them nonlinearly — and the signal's
auto-mutual information peaks again at {t_beat:.2f} s, one heartbeat (mean RR {rr_mean:.2f} s): each beat is informative about the next.""")
# tol-convention: relative tolerances are in percent
