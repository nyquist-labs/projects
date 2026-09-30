from eelab import *

META = dict(
    id="SL-077", title="Adaptive LMS noise canceller", level="H",
    tools="NumPy LMS implementation, eigenvalue-based convergence/misadjustment/stability predictions",
    summary="Cancel broadband interference picked up through an unknown acoustic path using a reference "
            "microphone and an LMS adaptive filter; predict learning time, misadjustment and the step-size "
            "stability limit from LMS theory and measure all three.",
    problem="An adaptive filter learns the unknown path from a noise reference to the corrupted signal. How "
            "fast does it learn, what does adaptation cost, and how large may the step size be?",
    theory=r"""LMS update $\mathbf w_{n+1}=\mathbf w_n+\mu e_n\mathbf x_n$. With a white reference of variance σ² all eigenvalues of
$R=E[\mathbf x\mathbf x^T]$ equal σ², so every weight-error mode decays as $(1-\mu\sigma^2)^n$: MSE time constant
$\tau=1/(2\mu\sigma^2)$ samples and interference down 20 dB after $\tau\ln 100$. Misadjustment (excess MSE / minimum MSE)
$\mathcal M\approx\frac{\mu\,\mathrm{tr}R}{2}=\frac{\mu L\sigma^2}{2}$. Mean-square stability needs roughly
$\mu<2/\mathrm{tr}R = 2/(L\sigma^2)$ (the looser bound $2/\lambda_{max}$ only guarantees convergence of the *mean*).""",
    method="""Wanted signal s: low-pass random process (power 0.05). Reference x: white noise σ² = 1. Interference = x through an
unknown 16-tap path (‖h‖² = 0.53). Filter length L = 32. Learning curves = ensemble mean of (e − s)² over 30 runs of
6,000 samples for μ = 0.001, 0.002, 0.005. Divergence: μ swept in multiples of 2/tr R.""",
    data="Synthetic signals with a known path, so the optimum solution (e = s) is known exactly.",
)

PATH = np.array([0.6, -0.3, 0.25, 0.1, -0.05] + [0.02 * (-1) ** k for k in range(11)])


def lms(x, d, L, mu):
    w = np.zeros(L); e = np.zeros(len(x)); xb = np.zeros(L)
    for n in range(len(x)):
        xb[1:] = xb[:-1]; xb[0] = x[n]
        e[n] = d[n] - w @ xb
        w += mu * e[n] * xb
        if abs(e[n]) > 1e6:
            e[n:] = np.inf; break
    return e


def make(rng_, n):
    x = rng_.normal(size=n)
    s = np.convolve(rng_.normal(size=n), np.hanning(9) / 3, "same") * 0.3
    return x, s + np.convolve(x, PATH)[:n], s


def run(p):
    L, n = 32, 6000
    x0, _, s0 = make(p.rng, 50000)
    ms = np.mean(s0**2); trR = L * np.var(x0)
    mus = [0.001, 0.002, 0.005]
    curves = {}
    for mu in mus:
        E = []
        for r in range(30):
            x, d, s = make(np.random.default_rng(100 + r), n)
            E.append((lms(x, d, L, mu) - s) ** 2)
        curves[mu] = np.mean(E, axis=0)
    P0 = np.sum(PATH**2)
    for mu in mus:
        c = curves[mu]
        p.compare(f"μ = {mu}: misadjustment (excess MSE / min MSE)", mu * trR / 2, np.mean(c[-2000:]) / ms, "", tol=30)
        tau = 1 / (2 * mu)
        sm = np.convolve(c, np.ones(25) / 25, "valid")
        t20 = np.argmax(sm < P0 * 0.01) + 12
        p.compare(f"μ = {mu}: samples to −20 dB interference (τ·ln100)", tau * np.log(100), t20, "samples", tol=20)
    rel = np.array([0.6, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0])
    div = []
    for m_ in rel:
        runs = [not np.isfinite(lms(*make(np.random.default_rng(7 + k), 20000)[:2], L, m_ * 2 / trR)).all() for k in range(3)]
        div.append(np.mean(runs))
    first = rel[np.argmax(np.array(div) > 0.5)] if np.any(np.array(div) > 0.5) else np.nan
    p.compare("Divergence threshold (in units of 2/tr R)", 1.0, first, "×", kind="abs",
              note="exact MSE bound for white input lies between 2/(3 tr R) and 2/tr R")
    fig, ax = p.fig()
    for i, mu in enumerate(mus):
        ax.semilogy(np.convolve(curves[mu], np.ones(25) / 25, "same"), color=COLORS[i], label=f"μ = {mu} measured")
        tgrid = np.arange(n)
        ax.semilogy(P0 * np.exp(-tgrid * 2 * mu) + mu * trR / 2 * ms, "--", color=COLORS[i], lw=1)
    style_axes(ax, "sample", "residual interference (e − s)²", "LMS learning curves (dashed = theory)")
    p.save(fig, "learning_curves", "Larger μ learns faster but settles at a higher excess-error floor.")
    p.csv("learning_curves", **{f"mu_{mu}": np.convolve(curves[mu], np.ones(25) / 25, "same")[::5] for mu in mus})
    p.csv("divergence", mu_over_2_trR=rel, fraction_diverged=div)
    p.discuss("""All three LMS results appear: the learning curves follow exp(−2μσ²n) down to a floor, the floor (misadjustment)
grows in proportion to μ·tr(R)/2, and the filter diverges near 2/tr(R). That last point is the classic trap: the
often-quoted 2/λ_max only guarantees that the *average* weights converge; the mean-square error blows up at a
much smaller step for long filters. An earlier version of this project used a pure-sinusoid (mains hum) reference;
there the canceller behaves as an adaptive *notch* whose bandwidth grows with μ and removes part of the wanted
signal near 50/150/250 Hz, so the white-input misadjustment formula does not apply — a good example of checking a
theory's assumptions before using its numbers.""")
