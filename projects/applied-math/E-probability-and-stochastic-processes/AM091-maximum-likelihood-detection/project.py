from eelab import *
from scipy.stats import norm
from scipy.optimize import brentq

META = dict(
    id="AM-091", title="Maximum-likelihood detection when the noise depends on the symbol", level="H",
    tools="Likelihood-ratio derivation for on-off keying with signal-dependent Gaussian noise (optical receiver), closed-form ML threshold (roots of a quadratic), BER vs threshold by Monte Carlo",
    summary="Derive the maximum-likelihood decision threshold for an optical on-off-keyed link where a '1' carries more noise than a '0' (shot noise), "
            "show it is *not* the midpoint, and verify by Monte Carlo that it minimises the error rate and by how much it beats the naive midpoint threshold.",
    problem="The textbook detector puts the threshold halfway between the symbols. When is that wrong?",
    theory=r"""Received level y ~ N(μ₀, σ₀²) for '0' and N(μ₁, σ₁²) for '1' with σ₁ > σ₀. ML (equal priors) decides '1' when $\frac{f_1(y)}{f_0(y)}>1$, i.e. where the two Gaussians cross:
$\frac{(y-μ_0)^2}{2σ_0^2}-\frac{(y-μ_1)^2}{2σ_1^2}=\ln\frac{σ_1}{σ_0}$ — a quadratic. For moderate σ-ratios the root is close to $y^*≈\frac{σ_1μ_0+σ_0μ_1}{σ_0+σ_1}$ (where the two Q-arguments are equal), pulled toward the quieter
symbol. The resulting BER ≈ Q((μ₁−μ₀)/(σ₀+σ₁)) — the optical 'Q-factor' formula.""",
    method="""μ₀ = 0, μ₁ = 1, σ₀ = 0.08, σ₁ = 0.16 (shot-noise-dominated '1'). 4×10⁶ bits; BER swept over thresholds 0.2–0.7; ML root, Q-factor approximation and midpoint compared.""",
)


def run(p):
    m0, m1, s0, s1 = 0.0, 1.0, 0.08, 0.16
    g = lambda y: (y - m0) ** 2 / (2 * s0 ** 2) - (y - m1) ** 2 / (2 * s1 ** 2) - np.log(s1 / s0)
    y_ml = brentq(g, m0, m1)
    y_q = (s1 * m0 + s0 * m1) / (s0 + s1)
    ber = lambda th: 0.5 * (norm.sf((th - m0) / s0) + norm.cdf((th - m1) / s1))
    p.metric("ML threshold (exact root) / Q-factor approximation / midpoint", f"{y_ml:.4f} / {y_q:.4f} / 0.5")
    r = p.rng; N = 4_000_000
    b = r.integers(0, 2, N); y = np.where(b == 1, r.normal(m1, s1, N), r.normal(m0, s0, N))
    ths = np.linspace(0.2, 0.7, 101)
    emp = np.array([np.mean((y > t) != (b == 1)) for t in ths])
    p.compare("Threshold minimising the simulated BER vs ML threshold", y_ml, ths[np.argmin(emp)], "", kind="abs", tol=0.015)
    p.compare("BER at the ML threshold: simulated vs exact (≈ 60 errors counted → ±13 % statistical)", ber(y_ml), np.mean((y > y_ml) != (b == 1)), "", tol=30)
    p.compare("Q-factor formula BER ≈ Q((μ₁−μ₀)/(σ₀+σ₁))", norm.sf((m1 - m0) / (s0 + s1)), ber(y_ml), "", tol=30)
    p.compare("Penalty of the midpoint threshold (BER ratio midpoint / ML)", ber(0.5) / ber(y_ml), np.mean((y > 0.5) != (b == 1)) / np.mean((y > y_ml) != (b == 1)), "×", tol=30)
    fig, ax = p.fig(1, 2, w=11)
    yy = np.linspace(-0.4, 1.6, 600)
    ax[0].plot(yy, norm.pdf(yy, m0, s0), color=C_MEAS, label="p(y | 0)"); ax[0].plot(yy, norm.pdf(yy, m1, s1), color=C_PRED, label="p(y | 1)")
    ax[0].axvline(y_ml, color="black", label=f"ML threshold {y_ml:.3f}"); ax[0].axvline(0.5, color="gray", ls=":", label="midpoint")
    style_axes(ax[0], "received level", "density", "Unequal noise pulls the threshold toward '0'")
    ax[1].semilogy(ths, emp, "o", ms=3, color=C_MEAS, label="simulated BER"); ax[1].semilogy(ths, ber(ths), "--", color=C_PRED, label="exact")
    ax[1].axvline(y_ml, color="black")
    style_axes(ax[1], "threshold", "BER", "BER vs threshold (4 million bits)")
    p.save(fig, "ml_detection", "Class-conditional densities with the ML threshold, and measured BER as a function of threshold.")
    p.discuss(f"""Because the '1' level carries twice the noise, the two likelihoods cross at {y_ml:.3f}, not 0.5, and the simulated BER-vs-threshold curve has its minimum
exactly there. Using the naive midpoint costs a factor of ~{ber(0.5) / ber(y_ml):.0f} in error rate — for free, since only the decision level changes. The optical
Q-factor formula Q(Δμ/(σ₀+σ₁)) captures the result to within a few tens of percent (it equalises the two conditional error probabilities rather than
solving the likelihood equation). This is why optical receivers adjust their decision threshold adaptively, and it generalises: ML detection means
comparing likelihoods, not distances, whenever the noise is not identical for every symbol.""")
# tol-convention: relative tolerances are in percent
