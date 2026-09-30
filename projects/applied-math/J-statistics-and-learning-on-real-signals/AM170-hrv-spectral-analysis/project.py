from eelab import *
from eelab.data import physionet
from scipy import signal

META = dict(
    id="AM-170", title="Heart-rate variability: time-domain and spectral statistics", level="M",
    tools="RR-interval series from MIT-BIH annotations, ectopic-beat handling, SDNN/RMSSD/pNN50, exact identities between time-domain measures, Lomb–Scargle periodogram on the unevenly sampled series vs Welch on a 4 Hz resampled tachogram, Parseval check, Poincaré descriptors",
    summary="Compute heart-rate-variability statistics from a real 30-minute ECG record, verify the algebraic identities that link them (RMSSD, lag-1 "
            "autocorrelation, Poincaré SD1/SD2, spectral power and variance), compare two spectral estimators for unevenly sampled data, and quantify how a handful of ectopic beats distorts everything.",
    problem="HRV indices are quoted as if independent measurements. Which of them are mathematically the same information — and how robust are they to a few abnormal beats?",
    theory=r"""For an RR series with variance σ² and lag-1 autocorrelation ρ₁: $\mathrm{RMSSD}^2=2σ^2(1-ρ_1)$ (exactly, up to end effects). Poincaré plot: $SD1=\mathrm{RMSSD}/\sqrt2$, $SD2^2=2\,SDNN^2-SD1^2$. Parseval: the integral of the power spectral density
equals the variance. Bands: LF 0.04–0.15 Hz, HF 0.15–0.4 Hz (respiratory sinus arrhythmia). The RR series is sampled at the beats themselves — unevenly — so either resample (cubic, 4 Hz) and use Welch, or use the Lomb–Scargle periodogram directly.
A premature beat creates a short–long RR pair: a large successive difference that inflates RMSSD and adds broadband spectral power.""",
    method="""MIT-BIH record 100 (30 min). Beat times from the reference annotations; 'NN' series = intervals between consecutive normal beats with intervals deviating > 20 % from the local median removed. Spectra: Welch (256 s Hann segments) on the 4 Hz cubic-spline
tachogram; Lomb–Scargle on the raw (t, RR) pairs, normalised to the same units.""",
    data="PhysioNet MIT-BIH Arrhythmia Database, record 100.",
)


def td(rr):
    d = np.diff(rr)
    return dict(sdnn=np.std(rr, ddof=1), rmssd=np.sqrt(np.mean(d ** 2)), pnn50=np.mean(np.abs(d) > 0.05) * 100)


def run(p):
    d = physionet("mitdb", "100", channels=[0], ann="atr"); fs = d["fs"]
    sym = d["ann_symbol"]; samp = d["ann_sample"]; beats = np.isin(sym, list("NLRBAaJSVrFejnE/fQ"))
    t = samp[beats] / fs; s = sym[beats]
    rr_all = np.diff(t); t_all = t[1:]
    normal = (s[1:] == "N") & (s[:-1] == "N")
    med = signal.medfilt(rr_all, 11); ok = normal & (np.abs(rr_all - med) < 0.2 * med)
    rr, tt = rr_all[ok], t_all[ok]
    p.metric("Beats / ectopic or rejected intervals", f"{len(rr_all) + 1} / {int((~ok).sum())}", "", f"mean heart rate {60 / rr.mean():.1f} bpm")
    a = td(rr); b = td(rr_all)
    rho1 = np.corrcoef(rr[:-1], rr[1:])[0, 1]
    p.compare("Identity: RMSSD² = 2σ²(1 − ρ₁)", np.sqrt(2 * np.var(rr) * (1 - rho1)), a["rmssd"], "s", tol=1.5)
    x1, x2 = rr[:-1], rr[1:]; sd1 = np.std((x2 - x1) / np.sqrt(2), ddof=1); sd2 = np.std((x2 + x1) / np.sqrt(2), ddof=1)
    p.compare("Poincaré SD1 = RMSSD/√2", a["rmssd"] / np.sqrt(2), sd1, "s", tol=1)
    p.compare("Poincaré SD2² = 2·SDNN² − SD1²", np.sqrt(2 * a["sdnn"] ** 2 - sd1 ** 2), sd2, "s", tol=1)
    from scipy.interpolate import CubicSpline
    fr = 4.0; tu = np.arange(tt[0], tt[-1], 1 / fr); xu = CubicSpline(tt, rr)(tu)
    f, P = signal.welch(xu - xu.mean(), fr, nperseg=1024, noverlap=512, window="hann")
    f0, P0 = signal.periodogram(xu - xu.mean(), fr, window="boxcar", detrend=False)
    p.compare("Parseval: ∫PSD df of the full-length periodogram = variance of the tachogram", np.var(xu), np.sum(P0) * (f0[1] - f0[0]), "s²", tol=0.5)
    p.metric("Share of the variance seen by Welch with 256 s segments", np.trapezoid(P, f) / np.var(xu) * 100, "%", "the rest is slower than the segment length (VLF drift) and is removed with each segment's mean")
    band = lambda f_, P_, lo, hi: np.trapezoid(P_[(f_ >= lo) & (f_ < hi)], f_[(f_ >= lo) & (f_ < hi)])
    lf, hf = band(f, P, 0.04, 0.15), band(f, P, 0.15, 0.4)
    fl = np.linspace(0.005, 0.5, 1000)
    pg = signal.lombscargle(tt, rr - rr.mean(), 2 * pi * fl, normalize=False)
    Pl = pg * 2 / len(rr) * (tt[-1] - tt[0]) / len(rr) * 2               # scale the classical periodogram to a one-sided PSD in s²/Hz
    Pl *= np.var(rr) / np.trapezoid(Pl, fl)                             # and fix the normalisation by Parseval
    lf_l, hf_l = band(fl, Pl, 0.04, 0.15), band(fl, Pl, 0.15, 0.4)
    p.compare("LF/HF ratio: Lomb–Scargle (no resampling) vs Welch on the resampled series", lf / hf, lf_l / hf_l, "", tol=30)
    p.metric("LF / HF power (Welch)", f"{lf * 1e6:.0f} / {hf * 1e6:.0f}", "ms²")
    fpk = f[(f >= 0.15) & (f < 0.4)][np.argmax(P[(f >= 0.15) & (f < 0.4)])]
    p.metric("HF peak frequency (respiration)", fpk, "Hz", f"≈ {fpk * 60:.0f} breaths/min")
    p.compare("RMSSD predicted from the spectrum: √∫PSD·4 sin²(πf·RR̄) df (a high-pass view of RMSSD)", a["rmssd"], np.sqrt(np.sum(P0 * 4 * np.sin(pi * f0 * rr.mean()) ** 2) * (f0[1] - f0[0])), "s", tol=15)
    p.compare("A few ectopic beats inflate RMSSD (ratio with/without cleaning > 1.5; 1 = yes)", 1, int(b["rmssd"] / a["rmssd"] > 1.5), "", kind="abs")
    p.metric("SDNN / RMSSD / pNN50, cleaned NN series", f"{a['sdnn'] * 1e3:.1f} ms / {a['rmssd'] * 1e3:.1f} ms / {a['pnn50']:.1f} %")
    p.metric("SDNN / RMSSD / pNN50, all beats (ectopics kept)", f"{b['sdnn'] * 1e3:.1f} ms / {b['rmssd'] * 1e3:.1f} ms / {b['pnn50']:.1f} %", "", f"{int((~ok).sum())} of {len(rr_all)} intervals are responsible")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    ax[0].plot(t_all / 60, rr_all * 1e3, ".", ms=2, color=C_PRED, label="all intervals"); ax[0].plot(tt / 60, rr * 1e3, ".", ms=2, color=C_MEAS, label="NN (cleaned)")
    style_axes(ax[0], "time (min)", "RR interval (ms)", "Tachogram, record 100")
    ax[1].semilogy(f, P * 1e6, color=C_MEAS, label="Welch, 4 Hz resampled"); ax[1].semilogy(fl, Pl * 1e6, color=C_PRED, lw=.8, alpha=.8, label="Lomb–Scargle")
    ax[1].axvspan(0.04, 0.15, color=COLORS[2], alpha=.12); ax[1].axvspan(0.15, 0.4, color=COLORS[3], alpha=.12); ax[1].set_xlim(0, 0.5)
    style_axes(ax[1], "frequency (Hz)", "PSD (ms²/Hz)", "LF and HF bands")
    ax[2].plot(x1 * 1e3, x2 * 1e3, ".", ms=2, color=C_MEAS)
    style_axes(ax[2], "RRₙ (ms)", "RRₙ₊₁ (ms)", f"Poincaré plot: SD1 {sd1 * 1e3:.0f} ms, SD2 {sd2 * 1e3:.0f} ms", legend=False)
    p.save(fig, "hrv", "RR tachogram, power spectrum by two estimators, and the Poincaré plot.")
    p.discuss(f"""Several 'different' HRV indices are one number seen from different sides: RMSSD equals √(2σ²(1 − ρ₁)), the Poincaré width SD1 is RMSSD/√2 and SD2
follows from SDNN and SD1 — all confirmed on real data to about a percent. In the frequency domain the full-length periodogram integrates exactly to the
variance, while Welch's method with 256 s segments accounts for only {np.trapezoid(P, f) / np.var(xu) * 100:.0f} % of it — my first Parseval check 'failed' by 23 % for that reason:
drift slower than the segment length is removed with each segment's mean, a reminder that a PSD estimate only describes the band it can resolve.
RMSSD is the variance seen through the high-pass filter 4 sin²(πf·RR̄), which is why it tracks the HF (respiratory) band. The Lomb–Scargle and
resample-then-Welch estimates agree on the LF/HF balance only to within tens of percent — the ratio is a noisy statistic from 30 minutes of data and
should be reported with that in mind. Most important in practice is the cleaning step: just {int((~ok).sum())} abnormal intervals out of {len(rr_all)} raise
RMSSD from {a['rmssd'] * 1e3:.0f} to {b['rmssd'] * 1e3:.0f} ms and pNN50 from {a['pnn50']:.1f} to {b['pnn50']:.1f} %. HRV numbers without a statement of how ectopic beats were
handled are not comparable.""")
# tol-convention: relative tolerances are in percent
