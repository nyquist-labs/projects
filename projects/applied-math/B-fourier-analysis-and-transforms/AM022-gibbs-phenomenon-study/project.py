from eelab import *
from scipy.special import sici

META = dict(
    id="AM-022", title="The Gibbs phenomenon: an overshoot that never goes away", level="M",
    tools="Partial Fourier sums of a square wave up to 2000 harmonics, the Wilbraham–Gibbs constant via the sine integral, Lanczos σ-factors",
    summary="Measure the overshoot of square-wave partial sums as the number of harmonics grows, show it converges to 8.95 % of the jump (not to "
            "zero) while moving closer to the discontinuity, and show how Lanczos σ-smoothing removes it at a cost in sharpness.",
    problem="Adding more Fourier terms reduces the error everywhere — except the peak overshoot. Why doesn't it vanish?",
    theory=r"""Near the jump the partial sum approaches $\frac2π\mathrm{Si}(Nπ x)$-shaped ringing; its first maximum is $\frac2π\mathrm{Si}(π)=1.17898$ for a ±1 wave, i.e. an overshoot of
$\frac{\mathrm{Si}(π)}{π}-\frac12 = 0.08949$ of the jump (8.95 %), independent of N. The peak sits at x ≈ 1/(2N) of a period from the jump, so it narrows but never shrinks — convergence is
pointwise but not uniform. Multiplying coefficients by $σ_k=\mathrm{sinc}(k/N)$ (Lanczos) averages the ringing away.""",
    method="""Square wave ±1, jump of 2 at t = 0; partial sums with N odd harmonics up to 2000, evaluated on a fine grid near the jump (resolution ≪ 1/N); overshoot height and position.
Same with Lanczos σ factors.""",
)


def partial(t, N, lanczos=False):
    y = np.zeros_like(t)
    for k in range(1, 2 * N, 2):
        s = np.sinc(k / (2 * N)) if lanczos else 1.0
        y += 4 / pi * np.sin(2 * pi * k * t) / k * s
    return y


def run(p):
    Si_pi = sici(pi)[0]
    gibbs = Si_pi / pi - 0.5
    Ns = np.array([5, 10, 20, 50, 100, 200, 500, 1000, 2000])
    peaks, locs, lz = [], [], []
    for N in Ns:
        t = np.linspace(0, 3 / (2 * N) / 2, 3000)          # zoom on the first lobe after the jump at t = 0
        y = partial(t, N)
        k = np.argmax(y)
        peaks.append((y[k] - 1) / 2); locs.append(t[k] * 2 * N)
        lz.append((partial(t, N, True).max() - 1) / 2)
    peaks = np.array(peaks)
    p.compare("Overshoot / jump at N = 2000 harmonics (Wilbraham–Gibbs 0.08949)", gibbs, peaks[-1], "", tol=0.2)
    p.compare("Overshoot at N = 5 vs N = 2000 (does not decrease)", peaks[-1], peaks[0], "", tol=3)
    p.compare("Peak position × 2N (odd harmonics up to 2N−1: first maximum at t ≈ 1/(4N) → 0.5)", 0.5, np.mean(locs[3:]), "", tol=1)
    p.compare("With Lanczos σ-factors: overshoot / jump", 0.012, np.array(lz)[-1], "", kind="abs", tol=0.012)
    fig, ax = p.fig(1, 2, w=11)
    for N, c in zip((10, 50, 250), COLORS):
        t = np.linspace(-0.02, 0.06, 4000)
        ax[0].plot(t, partial(t, N), color=c, label=f"N = {N}")
    ax[0].axhline(1 + 2 * gibbs, ls="--", color=C_PRED, label="1 + 2 × 0.0895")
    style_axes(ax[0], "t / T", "partial sum", "The overshoot narrows but keeps its height")
    ax[1].semilogx(Ns, peaks * 100, "o-", color=C_MEAS, label="plain partial sums")
    ax[1].semilogx(Ns, np.array(lz) * 100, "s-", color=COLORS[2], label="Lanczos σ-smoothed")
    ax[1].axhline(gibbs * 100, ls="--", color=C_PRED, label="8.95 % (Si(π)/π − ½)")
    style_axes(ax[1], "harmonics N", "overshoot (% of jump)", "Gibbs overshoot vs N")
    p.save(fig, "gibbs", "Partial sums near the discontinuity and the overshoot as a function of the number of harmonics.")
    p.discuss("""The overshoot converges to 8.95 % of the jump — the Wilbraham–Gibbs constant Si(π)/π − ½ — and stays there from 5 to 2000 harmonics,
while its position moves toward the jump in proportion to 1/N. The squeezed lobe carries less and less energy, which is why the mean-square error
still falls (AM-021) even though the maximum error does not: Fourier series converge in L², not uniformly, at a discontinuity. Lanczos σ-factors
(equivalently, smoothing the partial sum with a moving average of one ripple period) cut the overshoot to about 1 % at the price of a slower
edge — the same windowing trade-off that FIR design makes (AM-033).""")
# tol-convention: relative tolerances are in percent
