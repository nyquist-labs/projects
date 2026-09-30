from eelab import *
from scipy.special import erfc
from scipy.integrate import quad

META = dict(
    id="AM-085", title="The Q-function: derivation, bounds and rare-event estimation", level="M",
    tools="Gaussian tail integral by quadrature, erfc identity, Chernoff and asymptotic bounds, Craig's finite-range formula, naive vs importance-sampling Monte Carlo for probabilities down to 10⁻¹²",
    summary="Derive the Q-function and its erfc form, test the classic bounds and approximations against exact values, verify Craig's formula, "
            "and show why brute-force Monte Carlo cannot measure a 10⁻¹² error rate while importance sampling can.",
    problem="Error probabilities in communications all reduce to Gaussian tails. How accurate are the shortcuts — and how do you simulate an event that happens once in a trillion trials?",
    theory=r"""$Q(x)=\frac1{\sqrt{2π}}\int_x^∞e^{-t^2/2}dt=\tfrac12\mathrm{erfc}(x/\sqrt2)$. Bounds: $\frac{x}{1+x^2}\frac{e^{-x^2/2}}{\sqrt{2π}} < Q(x) < \frac{e^{-x^2/2}}{x\sqrt{2π}}$; Chernoff $Q(x)\le\frac12e^{-x^2/2}$. Craig: $Q(x)=\frac1π\int_0^{π/2}e^{-x^2/(2\sin^2θ)}dθ$ (finite limits).
Naive Monte Carlo needs ~100/p samples for 10 % accuracy; importance sampling from N(x, 1) with weights e^{−xz + x²/2} has relative error that stays O(1/√n) at any depth.""",
    method="""x from 0.5 to 7: quad integral vs erfc; bounds; Craig by quad. Estimation of Q(7) ≈ 1.28×10⁻¹²: naive (10⁷ samples) vs importance sampling (10⁵ samples), 50 repetitions each.""",
)


def Q(x):
    return 0.5 * erfc(x / np.sqrt(2))


def run(p):
    xs = np.linspace(0.5, 7, 27)
    quadv = np.array([quad(lambda t: np.exp(-t * t / 2), x, np.inf)[0] / np.sqrt(2 * pi) for x in xs])
    p.compare("Direct integral vs ½·erfc(x/√2) (worst relative, x = 0.5…7)", 0, np.max(np.abs(quadv / Q(xs) - 1)), "", kind="abs", tol=1e-8)
    craig = np.array([quad(lambda th: np.exp(-x * x / (2 * np.sin(th) ** 2)), 0, pi / 2)[0] / pi for x in xs])
    p.compare("Craig's formula vs erfc (worst relative)", 0, np.max(np.abs(craig / Q(xs) - 1)), "", kind="abs", tol=1e-8)
    ub = np.exp(-xs ** 2 / 2) / (xs * np.sqrt(2 * pi)); lb = xs / (1 + xs ** 2) * np.exp(-xs ** 2 / 2) / np.sqrt(2 * pi); ch = 0.5 * np.exp(-xs ** 2 / 2)
    p.compare("Upper/lower bounds bracket Q(x) everywhere (1 = yes)", 1, int(np.all((lb < Q(xs)) & (Q(xs) < ub) & (Q(xs) <= ch))), "", kind="abs")
    p.compare("Asymptotic bound e^{−x²/2}/(x√2π): relative error at x = 5 (≈ 1/x²)", 1 / 25, ub[np.argmin(abs(xs - 5))] / Q(5) - 1, "", kind="abs", tol=0.01)
    p.metric("Chernoff bound ½e^{−x²/2} overestimates Q(7) by", ch[-1] / Q(7), "×")
    r = p.rng; x = 7.0; true = Q(x)
    naive = [np.mean(r.normal(size=10 ** 7) > x) for _ in range(5)]
    isamp = []
    for _ in range(50):
        z = r.normal(loc=x, size=10 ** 5)
        w = np.exp(-x * z + x * x / 2)
        isamp.append(np.mean((z > x) * w))
    isamp = np.array(isamp)
    p.compare("Importance sampling (10⁵ samples) estimate of Q(7) = 1.28e-12", true, isamp.mean(), "", tol=2)
    p.metric("Importance-sampling relative std per 10⁵-sample run", isamp.std() / true, "")
    p.metric("Naive Monte Carlo with 10⁷ samples: estimates", ", ".join(f"{v:.1e}" for v in naive), "all zero — would need ~10¹⁴ samples")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(xs, Q(xs), color="black", lw=2, label="Q(x)"); ax[0].semilogy(xs, ub, "--", color=C_PRED, label="upper e^{−x²/2}/(x√2π)")
    ax[0].semilogy(xs, lb, ":", color=C_MEAS, label="lower bound"); ax[0].semilogy(xs, ch, "-.", color=COLORS[2], label="Chernoff ½e^{−x²/2}")
    style_axes(ax[0], "x", "tail probability", "Q-function and bounds")
    ax[1].hist(isamp / true, bins=15, color=C_MEAS)
    style_axes(ax[1], "IS estimate / true Q(7)", "count", "50 importance-sampling runs", legend=False)
    p.save(fig, "qfunction", "The Q-function with its bounds, and the spread of importance-sampling estimates of a 10⁻¹² tail.")
    p.discuss("""Three independent routes — direct quadrature, the erfc identity and Craig's finite-range integral — agree to 10⁻⁹ relative, and the textbook bounds
bracket Q(x) everywhere, with the simple asymptotic form accurate to ~1/x² (4 % at x = 5, i.e. good enough for high-SNR BER work). The Chernoff bound
has the right exponent but a wrong prefactor (tens of times too large at x = 7). The simulation half is the practical lesson: ten million
Gaussian samples produced zero events beyond 7σ, so a naive BER simulation of a 10⁻¹² link is hopeless; shifting the sampling distribution to the
tail and re-weighting estimates the same probability to about 1 % with only 10⁵ samples.""")
# tol-convention: relative tolerances are in percent
