from eelab import *
from scipy.special import gamma

META = dict(
    id="AM-087", title="Reliability: exponential and Weibull failure models, MTBF", level="M",
    tools="Constant-hazard and Weibull lifetime models, series/parallel system reliability, maximum-likelihood Weibull fitting of simulated failure data, Monte-Carlo MTBF",
    summary="Model component lifetimes, derive the MTBF of series and redundant systems, fit Weibull parameters to test data by maximum likelihood "
            "(including censored units), and check every formula by simulating thousands of systems.",
    problem="A board has 50 parts, each with a million-hour MTBF. How long will the board last — and does redundancy help as much as it seems?",
    theory=r"""Exponential: R(t) = e^{−λt}, MTBF = 1/λ. Series of n parts: λ_sys = Σλ ⇒ 50 parts at 10⁶ h → 20,000 h. Two identical units in active parallel: MTBF = 3/(2λ) (only 1.5×, not 2×). Weibull: $R(t)=e^{-(t/η)^β}$,
mean ηΓ(1+1/β); β < 1 infant mortality, β = 1 random, β > 1 wear-out. With right-censored data, the MLE maximises Σ_failures log f + Σ_censored log R.""",
    method="""Monte Carlo: 100,000 simulated systems per configuration. Weibull test: 200 units with β = 2.5, η = 5000 h, test stopped at 4000 h (censoring ~44 % of units); MLE by optimising the censored
log-likelihood; 200 repeated experiments for parameter spread.""",
)


def weibull_mle(t, failed):
    from scipy.optimize import minimize
    def nll(v):
        b, e = np.exp(v)
        z = t / e
        return -(np.sum(np.log(b / e) + (b - 1) * np.log(z[failed])) - np.sum(z ** b))
    res = minimize(nll, [0.0, np.log(np.mean(t))], method="Nelder-Mead", options=dict(xatol=1e-8, fatol=1e-10, maxiter=4000))
    return np.exp(res.x)


def run(p):
    r = p.rng; N = 100000
    lam = 1e-6
    life = r.exponential(1 / lam, (N, 50)).min(axis=1)
    p.compare("Series of 50 parts (λ = 1e-6/h each): system MTBF = 1/(50λ)", 1 / (50 * lam), life.mean(), "h", tol=1)
    par = r.exponential(1 / lam, (N, 2)).max(axis=1)
    p.compare("Two units in active parallel: MTBF = 3/(2λ)", 1.5 / lam, par.mean(), "h", tol=1)
    t1 = 1 / lam * 0.1
    p.compare("Reliability of the parallel pair at t = 0.1/λ: 1 − (1 − e^{−0.1})²", 1 - (1 - np.exp(-0.1)) ** 2, np.mean(par > t1), "", tol=0.2)
    beta, eta = 2.5, 5000.0
    w = eta * r.weibull(beta, N)
    p.compare("Weibull mean life ηΓ(1 + 1/β)", eta * gamma(1 + 1 / beta), w.mean(), "h", tol=1)
    ests = []
    for _ in range(200):
        t = eta * r.weibull(beta, 200); failed = t < 4000; tc = np.minimum(t, 4000)
        ests.append(weibull_mle(tc, failed))
    ests = np.array(ests)
    p.compare("Censored MLE: mean β̂ over 200 test campaigns", beta, ests[:, 0].mean(), "", tol=3)
    p.compare("Censored MLE: mean η̂", eta, ests[:, 1].mean(), "h", tol=2)
    p.metric("Spread of β̂ (std) with 200 units, ~44 % censored", ests[:, 0].std(), "")
    fig, ax = p.fig(1, 2, w=11)
    tt = np.linspace(0, 12000, 400)
    for b_, c in ((0.5, COLORS[0]), (1.0, COLORS[1]), (2.5, COLORS[2])):
        h = b_ / eta * (tt / eta) ** (b_ - 1)
        ax[0].plot(tt, h * 1e3, color=c, label=f"β = {b_}")
    ax[0].set_ylim(0, 1.5)
    style_axes(ax[0], "time (h)", "hazard rate (per 1000 h)", "Bathtub pieces: infant, random, wear-out")
    ax[1].hist(ests[:, 0], bins=25, color=C_MEAS); ax[1].axvline(beta, color=C_PRED, ls="--", label="true β")
    style_axes(ax[1], "β̂ (censored MLE)", "count", "Weibull shape from truncated life tests")
    p.save(fig, "reliability", "Weibull hazard shapes and the sampling distribution of the censored-data shape estimate.")
    p.discuss("""The simulations confirm the arithmetic that surprises newcomers: fifty parts each rated for a million hours make a board that lasts only 20,000 hours
on average, because failure rates add in series. Redundancy helps less than intuition says — two units in parallel give 1.5×, not 2×, the MTBF,
since once one fails the survivor is on its own — although early-life reliability improves dramatically (R(0.1/λ) from 0.905 to 0.991). The Weibull
fit shows that useful life-test conclusions do not need every unit to fail: maximum likelihood with right-censoring recovers β and η essentially
without bias from a test stopped at 4000 h, which is how wear-out (β > 1) is diagnosed in practice.""")
# tol-convention: relative tolerances are in percent
