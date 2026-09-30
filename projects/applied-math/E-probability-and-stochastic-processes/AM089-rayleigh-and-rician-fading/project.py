from eelab import *
from scipy.special import i0
from scipy.signal import lfilter

META = dict(
    id="AM-089", title="Rayleigh and Rician fading: distributions, level crossings, fade durations", level="H",
    tools="Sum-of-sinusoids (Jakes/Clarke) fading simulator, envelope histograms vs Rayleigh and Rice PDFs, Doppler spectrum, level-crossing rate and average fade duration vs closed forms",
    summary="Simulate a mobile radio channel as the sum of many scattered paths with Doppler shifts, confirm that the envelope is Rayleigh (Rice with "
            "a line-of-sight path), and verify the classical formulas for how often and how long the signal fades.",
    problem="A phone moving at 50 km/h sees its signal drop by 20 dB many times per second. How often, for how long — and why those distributions?",
    theory=r"""Many independent paths ⇒ complex Gaussian (CLT) ⇒ envelope Rayleigh $f(r)=\frac{r}{σ^2}e^{-r^2/2σ^2}$; with a LOS component of power ratio K: Rice $f(r)=\frac{r}{σ^2}e^{-(r^2+s^2)/2σ^2}I_0(rs/σ^2)$. For isotropic
scattering (Clarke), with ρ = R/R_rms: level-crossing rate $N_R=\sqrt{2π}f_Dρe^{-ρ^2}$ and average fade duration $\bar t=\frac{e^{ρ^2}-1}{ρf_D\sqrt{2π}}$. At ρ = −20 dB the channel fades ~0.25 f_D times per second, each fade lasting ~4 % of 1/f_D.""",
    method="""Sum of 64 sinusoids with random angles of arrival and phases; f_D = 100 Hz; 200 s at 10 kHz. Envelope histogram vs PDFs (Rayleigh; Rician K = 5); LCR and AFD at levels −30…+5 dB rel. rms vs formulas.""",
)


def fading(fd, fs, T, r, M=64, K=0.0):
    t = np.arange(int(T * fs)) / fs
    a = r.uniform(0, 2 * pi, M); ph = r.uniform(0, 2 * pi, M)
    h = np.zeros(len(t), complex)
    for k in range(M):
        h += np.exp(1j * (2 * pi * fd * np.cos(a[k]) * t + ph[k]))
    h /= np.sqrt(M)
    if K > 0:
        h = np.sqrt(1 / (K + 1)) * h + np.sqrt(K / (K + 1)) * np.exp(1j * 2 * pi * fd * 0.3 * t)
    return t, h


def run(p):
    r = p.rng; fd, fs, T = 100.0, 10000.0, 200.0
    t, h = fading(fd, fs, T, r)
    R = np.abs(h); Rrms = np.sqrt(np.mean(R ** 2))
    hist, edges = np.histogram(R / Rrms, bins=80, range=(0, 3), density=True); c = 0.5 * (edges[1:] + edges[:-1])
    ray = 2 * c * np.exp(-c * c)
    p.compare("Envelope PDF vs Rayleigh (max |difference|)", 0, np.max(np.abs(hist - ray)), "", kind="abs", tol=0.05)
    p.compare("Rayleigh: fraction of time more than 20 dB below rms = 1 − e^{−0.01}", 1 - np.exp(-0.01), np.mean(R / Rrms < 0.1), "", tol=10)
    rows = []
    for lev_db in (-30, -20, -10, -5, 0, 3):
        rho = 10 ** (lev_db / 20)
        below = R / Rrms < rho
        up = np.flatnonzero(np.diff(below.astype(int)) == -1)
        lcr = len(up) / T; afd = below.mean() / lcr if lcr else np.nan
        rows.append((lev_db, lcr, np.sqrt(2 * pi) * fd * rho * np.exp(-rho ** 2), afd, (np.exp(rho ** 2) - 1) / (rho * fd * np.sqrt(2 * pi))))
    for lev, lcr, plcr, afd, pafd in rows:
        if lev in (-20, 0):
            p.compare(f"Level {lev} dB: level-crossing rate", plcr, lcr, "1/s", tol=10)
            p.compare(f"Level {lev} dB: average fade duration", pafd, afd, "s", tol=10)
    K = 5.0
    t2, h2 = fading(fd, fs, 50.0, r, K=K)
    R2 = np.abs(h2); s = np.sqrt(K / (K + 1)); sig2 = 1 / (2 * (K + 1))
    hist2, e2 = np.histogram(R2, bins=80, range=(0, 2), density=True); c2 = 0.5 * (e2[1:] + e2[:-1])
    rice = c2 / sig2 * np.exp(-(c2 ** 2 + s * s) / (2 * sig2)) * i0(c2 * s / sig2)
    p.compare("Rician (K = 5) envelope PDF vs Rice distribution (max |difference| / peak)", 0, np.max(np.abs(hist2 - rice)) / rice.max(), "", kind="abs", tol=0.08)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    ax[0].plot(t[:int(0.2 * fs)] * 1e3, db(R[:int(0.2 * fs)] / Rrms), color=C_MEAS, lw=.8)
    style_axes(ax[0], "t (ms)", "envelope (dB rel. rms)", "f_D = 100 Hz: deep, brief fades", legend=False)
    ax[1].plot(c, hist, color=C_MEAS, label="Rayleigh sim."); ax[1].plot(c, ray, "--", color=C_PRED, label="Rayleigh PDF")
    ax[1].plot(c2 / np.sqrt(np.mean(R2 ** 2)) * 1, hist2 * np.sqrt(np.mean(R2 ** 2)), color=COLORS[2], label="Rician K = 5 sim.")
    style_axes(ax[1], "R / R_rms", "density", "Envelope distributions")
    rr = np.array(rows)
    ax[2].semilogy(rr[:, 0], rr[:, 3], "o", color=C_MEAS, label="measured AFD"); ax[2].semilogy(rr[:, 0], rr[:, 4], "--", color=C_PRED, label="formula")
    ax[2].semilogy(rr[:, 0], 1 / rr[:, 1], "s", color=COLORS[2], label="measured 1/LCR"); ax[2].semilogy(rr[:, 0], 1 / rr[:, 2], ":", color=COLORS[3], label="formula")
    style_axes(ax[2], "threshold (dB rel. rms)", "seconds", "Fade duration and spacing")
    p.save(fig, "fading", "A Rayleigh fading envelope, the envelope PDFs, and fade durations/spacings vs threshold.")
    p.discuss("""Summing 64 Doppler-shifted paths produces an envelope that is Rayleigh to within histogram noise — the central limit theorem at work — and adding a
line-of-sight component turns it into the predicted Rice distribution. The Clarke-model formulas for level-crossing rate and average fade duration
match the simulation: at 100 Hz Doppler (≈ 50 km/h at 2 GHz) the signal drops 20 dB below its rms about 25 times per second, but each fade lasts only
~0.4 ms. That combination — frequent but short fades — is why fast interleaving plus coding works so well in mobile links, and why the fraction of
time in a deep fade (1 % at −20 dB) is the number link designers budget for.""")
# tol-convention: relative tolerances are in percent
