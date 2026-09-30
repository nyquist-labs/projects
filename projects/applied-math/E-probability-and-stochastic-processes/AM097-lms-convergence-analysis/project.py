from eelab import *
from scipy import signal

META = dict(
    id="AM-097", title="LMS adaptive filters: step size, stability and misadjustment", level="H",
    tools="LMS system identification, eigenvalue spread of the input correlation matrix, convergence time constants, misadjustment formula M ≈ μ·tr(R)/2, stability bound",
    summary="Identify an unknown FIR system with the LMS algorithm, predict its stability limit, learning-curve time constants and steady-state "
            "misadjustment from the input statistics, and check each prediction with ensemble-averaged learning curves for white and coloured inputs.",
    problem="The LMS step size trades speed against accuracy. Can both be predicted before running it?",
    theory=r"""With input correlation R (eigenvalues λ_i), mean weights converge with modes $(1-2μλ_i)^k$ — time constants $τ_i ≈ 1/(2μλ_i)$ samples, so eigenvalue spread slows convergence. Mean-square stability requires roughly
μ < 1/tr(R) (the textbook 2/λ_max only guarantees the mean). Excess MSE: misadjustment $M = \frac{J_{ex}}{J_{min}}≈\frac{μ\,\mathrm{tr}(R)}{1-μ\,\mathrm{tr}(R)}$ ≈ μ·tr(R) for small μ (update w ← w + 2μeu convention, e = d − wᵀu).""",
    method="""Unknown 16-tap system, measurement noise σ² = 10⁻³. Inputs: white (λ spread 1) and AR(1) with a = 0.9 (spread ≈ 360). Ensemble of 200 runs × 20,000 samples; misadjustment from the last 5000 samples; learning-curve
time constant from an exponential fit; divergence test for μ around 1/tr(R).""",
)


def lms(u, d, L, mu):
    w = np.zeros(L); e = np.empty(len(u))
    ub = np.zeros(L)
    for n in range(len(u)):
        ub = np.r_[u[n], ub[:-1]]
        e[n] = d[n] - w @ ub
        w += 2 * mu * e[n] * ub
        if not np.isfinite(w).all() or abs(e[n]) > 1e6:
            e[n:] = np.inf; break
    return e, w


def run(p):
    r = p.rng; L = 16; h = r.normal(size=L) * np.exp(-np.arange(L) / 4); Jmin = 1e-3
    res = {}
    for name, a in (("white", 0.0), ("AR(1), a = 0.9", 0.9)):
        R = a ** np.abs(np.subtract.outer(np.arange(L), np.arange(L))) * 1.0
        ev = np.linalg.eigvalsh(R); trR = np.trace(R)
        mu = 0.05 / trR
        J = np.zeros(20000)
        for run_ in range(200):
            u = signal.lfilter([np.sqrt(1 - a * a)], [1, -a], r.normal(size=20000))
            d = signal.lfilter(h, [1], u) + r.normal(0, np.sqrt(Jmin), 20000)
            e, _ = lms(u, d, L, mu); J += e ** 2
        J /= 200
        Mm = (J[-5000:].mean() - Jmin) / Jmin
        res[name] = (J, Mm, mu * trR / (1 - mu * trR), ev, mu)
    for name, (J, Mm, Mp, ev, mu) in res.items():
        p.compare(f"{name}: misadjustment ≈ μ·tr(R)/(1 − μ·tr(R))", Mp, Mm, "", tol=15)
    Jw, _, _, evw, muw = res["white"]
    k = np.arange(20000); win = (k >= 30) & (k <= 400)              # clean exponential part: after the tap line fills, before the noise floor
    tau = -1 / np.polyfit(k[win], np.log(Jw[win] - Jmin * (1 + res["white"][1])), 1)[0]
    p.compare("White input: learning-curve time constant ≈ 1/(4μλ) (MSE decays twice as fast as weights)", 1 / (4 * muw * 1.0), tau, "samples", tol=15)
    Jc = res["AR(1), a = 0.9"][0]
    t_w = np.argmax(Jw < 2 * Jmin * (1 + res["white"][1])); t_c = np.argmax(Jc < 2 * Jmin * (1 + res["AR(1), a = 0.9"][1])) if np.any(Jc < 2 * Jmin * (1 + res["AR(1), a = 0.9"][1])) else len(Jc)
    p.metric("Eigenvalue spread λmax/λmin: white / AR(1)", f"1 / {res['AR(1), a = 0.9'][3].max() / res['AR(1), a = 0.9'][3].min():.0f}")
    p.metric("Samples to reach 2× final MSE: white / coloured", f"{t_w} / {t_c}")
    stab = []
    fw = lambda m_: np.sum(m_ * 1.0 / (1 - 2 * m_ * 1.0)) * L / L        # Feuer–Weinstein: Σ μλ_i/(1−2μλ_i) < 1 for Gaussian input (white: λ_i = 1)
    mu_max = 1 / (L + 2)
    p.metric("Exact mean-square stability limit for white Gaussian input (Feuer–Weinstein), μ·tr(R)", mu_max * L, "")
    for frac in (0.3, 0.6, 0.7, 0.8, 0.85, 0.9, 1.0, 1.1):
        ok = 0
        for _ in range(10):
            u = r.normal(size=20000); d = signal.lfilter(h, [1], u) + r.normal(0, np.sqrt(Jmin), 20000)
            e, _ = lms(u, d, L, frac / L); ok += bool(np.isfinite(e[-1]) and np.mean(e[-1000:] ** 2) < 1)
        stab.append((frac, ok / 10))
    sd = dict(stab)
    edge = next(f_ for f_, s_ in stab if s_ < 0.5)
    p.compare("Empirical stability edge (first μ·tr(R) where < 50 % of 10 runs stay bounded) vs Feuer–Weinstein 0.889", mu_max * L, edge, "", kind="abs", tol=0.1)
    p.metric("Fraction of 10 runs that stay bounded, by μ·tr(R)", ", ".join(f"{f_}: {s_ * 100:.0f} %" for f_, s_ in stab))
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    for (name, (J, *_)), c in zip(res.items(), (C_MEAS, C_PRED)):
        ax.semilogy(J, color=c, lw=.8, label=name)
    ax.axhline(Jmin, color="black", ls=":", label="J_min (noise floor)")
    style_axes(ax, "iteration", "ensemble MSE (200 runs)", "Learning curves at equal μ·tr(R) = 0.05")
    p.save(fig, "lms", "Ensemble-averaged learning curves for white and strongly coloured inputs.")
    p.discuss("""The steady-state misadjustment matches μ·tr(R)/(1 − μ·tr(R)) for both inputs — it depends only on the total input power, not on its colour — and the
white-input learning curve decays with the predicted time constant 1/(4μλ). Colour changes the *speed*: with AR(1) input the correlation matrix's
eigenvalue spread is several hundred, so the slow modes (small λ) take hundreds of times longer to converge at the same μ, which is exactly the
long tail of the coloured learning curve. The stability sweep located the limit sharply: my first guess (stable up to μ·tr(R) ≈ 1) was slightly
too generous — the exact mean-square condition for Gaussian input, Σ μλᵢ/(1 − 2μλᵢ) < 1, puts the edge at 0.889 for this 16-tap white case, and
over 10 runs per step size the fraction that stays bounded falls from 90 % at 0.8 to 60 % at 0.85 and 10 % at 0.9 (near the edge the error
has huge excursions, and the tapped delay line violates the theory's independence assumption) — far inside the mean-convergence bound 2/λ_max that textbooks often quote. Normalised LMS (μ ∝ 1/‖u‖²) and RLS/lattice filters exist to remove these two dependencies.""")
# tol-convention: relative tolerances are in percent
