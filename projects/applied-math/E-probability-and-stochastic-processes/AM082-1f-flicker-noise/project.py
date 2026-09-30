from eelab import *
from scipy import signal

META = dict(
    id="AM-082", title="1/f flicker noise: synthesis, spectrum and Allan deviation", level="H",
    tools="Two synthesis methods — FFT spectral shaping and a sum of Lorentzians (McWhorter model, log-uniform time constants) — spectral-slope fits, overlapping Allan deviation",
    summary="Generate 1/f noise two ways, confirm the −10 dB/decade spectrum and its extent, show that the McWhorter superposition of simple "
            "trapping processes produces it, and measure the Allan deviation's characteristic flat floor (white noise: slope −½).",
    problem="Flicker noise dominates every amplifier at low frequency, yet no single physical time constant has a 1/f spectrum. Where does it come from?",
    theory=r"""A single trap gives a Lorentzian $\frac{τ}{1+(ωτ)^2}$. With time constants distributed uniformly in log τ between τ₁ and τ₂ the sum is ∝ 1/f for $1/(2πτ_2) ≪ f ≪ 1/(2πτ_1)$ (McWhorter). For 1/f noise the
Allan deviation σ_A(τ) is constant (flicker floor), for white noise it falls as τ^{−1/2}, for random walk it rises as τ^{+1/2} — the standard way oscillator and sensor noise is classified.""",
    method="""N = 2²⁰ samples at 1 kHz. (i) FFT method: white Gaussian noise shaped by 1/√f. (ii) 60 Ornstein–Uhlenbeck processes with τ log-uniform over 1 ms…100 s. Spectral slope by log-log fit over 0.1–100 Hz;
Allan deviation for τ = 0.01…100 s, plus white and random-walk references.""",
)


def fft_pink(n, r):
    X = np.fft.rfft(r.normal(size=n)); f = np.fft.rfftfreq(n)
    X[1:] /= np.sqrt(f[1:]); X[0] = 0
    return np.fft.irfft(X, n)


def mcwhorter(n, fs, r, m=60, t1=1e-3, t2=100.0):
    x = np.zeros(n); dt = 1 / fs
    for tau in np.logspace(np.log10(t1), np.log10(t2), m):
        a = np.exp(-dt / tau)
        x += signal.lfilter([1.0], [1.0, -a], r.normal(size=n) * np.sqrt(1 - a * a))
    return x


def adev(x, fs, taus):
    out = []
    for t in taus:
        m = int(t * fs)
        y = np.cumsum(x) / fs
        d = y[2 * m:] - 2 * y[m:-m] + y[:-2 * m]
        out.append(np.sqrt(np.mean(d ** 2) / (2 * t * t)))
    return np.array(out)


def slope(x, fs, lo=0.1, hi=100):
    f, P = signal.welch(x, fs, nperseg=2 ** 17)
    b = (f > lo) & (f < hi)
    return np.polyfit(np.log10(f[b]), np.log10(P[b]), 1)[0], f, P


def run(p):
    r = p.rng; fs = 1000.0; n = 2 ** 20
    x1 = fft_pink(n, r); x2 = mcwhorter(n, fs, r)
    s1, f1, P1 = slope(x1, fs); s2, f2, P2 = slope(x2, fs, 0.1, 10)
    p.compare("FFT-shaped noise: PSD slope (1/f → −1)", -1.0, s1, "", kind="abs", tol=0.05)
    p.compare("Sum of 60 Lorentzians (τ log-uniform 1 ms–100 s): slope over 0.1–10 Hz", -1.0, s2, "", kind="abs", tol=0.1)
    _, fb, Pb = slope(x2, fs, 100, 400)
    p.metric("McWhorter spectrum slope above 1/(2πτ_min) = 160 Hz (Lorentzian tail → −2)", np.polyfit(np.log10(fb[(fb > 200) & (fb < 450)]), np.log10(Pb[(fb > 200) & (fb < 450)]), 1)[0], "")
    taus = np.logspace(-2, 1.5, 12)
    a_pink = adev(x1, fs, taus); a_white = adev(r.normal(size=n), fs, taus); a_rw = adev(np.cumsum(r.normal(size=n)) / np.sqrt(fs), fs, taus)
    k = lambda a: np.polyfit(np.log10(taus[2:-2]), np.log10(a[2:-2]), 1)[0]
    p.compare("Allan deviation slope: white noise (−½)", -0.5, k(a_white), "", kind="abs", tol=0.05)
    p.compare("Allan deviation slope: 1/f noise (0, flicker floor)", 0.0, k(a_pink), "", kind="abs", tol=0.08)
    p.compare("Allan deviation slope: random walk (+½)", 0.5, k(a_rw), "", kind="abs", tol=0.08)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(f1[1:], P1[1:], color=C_MEAS, lw=.6, label="FFT-shaped"); ax[0].loglog(f2[1:], P2[1:] * P1[10] / P2[10], color=C_PRED, lw=.6, label="McWhorter sum (scaled)")
    ax[0].loglog(f1[1:], P1[10] * f1[10] / f1[1:], ":", color="black", label="1/f")
    style_axes(ax[0], "frequency (Hz)", "PSD", "Two routes to 1/f")
    for a_, lab, c in ((a_white, "white", COLORS[0]), (a_pink, "1/f", COLORS[1]), (a_rw, "random walk", COLORS[2])):
        ax[1].loglog(taus, a_ / a_[4], "o-", color=c, label=lab)
    style_axes(ax[1], "averaging time τ (s)", "Allan deviation (norm.)", "Noise types by Allan slope")
    p.save(fig, "flicker", "Spectra of two 1/f synthesis methods and Allan-deviation signatures of three noise types.")
    p.discuss("""Both constructions give a −10 dB/decade spectrum: spectral shaping by construction, and the McWhorter superposition because Lorentzians with
log-uniformly distributed time constants each contribute equal power per decade — no individual process is 1/f, their ensemble is. Outside the
range of time constants the sum reverts to the Lorentzian shapes (flat below, 1/f² above), which is why real 1/f noise always has corner
frequencies. The Allan deviation cleanly separates the noise types: slope −½ for white, a flat floor for flicker (averaging longer stops helping),
+½ for random walk — the reason averaging a sensor beyond its flicker corner is pointless and why chopper and auto-zero amplifiers exist.""")
# tol-convention: relative tolerances are in percent
