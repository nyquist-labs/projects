from eelab import *
from scipy.integrate import solve_ivp

META = dict(
    id="AM-054", title="Van der Pol oscillator: limit cycles from weak to relaxation", level="H",
    tools="Adaptive RK45 integration (SciPy), phase portraits, amplitude from averaging theory, relaxation period from singular perturbation, Poincaré-section convergence",
    summary="Integrate ẍ − μ(1 − x²)ẋ + x = 0 for μ from 0.1 to 20, show that every start converges to one limit cycle, and compare its amplitude "
            "and period with the small-μ averaging result and the large-μ relaxation formula.",
    problem="Why does an oscillator with negative resistance settle at a definite amplitude — regardless of how it starts?",
    theory=r"""The term −μ(1−x²)ẋ is negative damping for |x| < 1 and positive damping outside, so energy is pumped in at small amplitude and removed at large. Averaging (μ ≪ 1): amplitude → 2,
period → 2π(1 + μ²/16). Relaxation (μ ≫ 1): period → (3 − 2 ln 2)μ ≈ 1.614μ, amplitude → 2. Every non-zero initial condition converges to the same closed orbit (a stable limit cycle).""",
    method="""RK45 with rtol 1e-10. μ ∈ {0.1, 0.5, 1, 2, 5, 10, 20}; period from successive upward zero crossings after transients; amplitude = max x. Convergence from 5 initial conditions for μ = 1.""",
)


def vdp(mu):
    return lambda t, y: [y[1], mu * (1 - y[0] ** 2) * y[1] - y[0]]


def period_amp(mu, T=None):
    T = T or max(200, 40 * mu)
    s = solve_ivp(vdp(mu), (0, T), [0.5, 0], rtol=1e-10, atol=1e-12, dense_output=True, max_step=0.05)
    t = np.linspace(T / 2, T, 400000); x = s.sol(t)[0]
    up = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    tz = t[up] - x[up] * (t[up + 1] - t[up]) / (x[up + 1] - x[up])
    return np.mean(np.diff(tz)), x.max()


def run(p):
    rows = []
    for mu in (0.1, 0.5, 1, 2, 5, 10, 20):
        P, A = period_amp(mu); rows.append((mu, P, A))
    for mu, P, A in rows:
        if mu <= 0.5:
            p.compare(f"μ = {mu}: period ≈ 2π(1 + μ²/16)", 2 * pi * (1 + mu ** 2 / 16), P, "", tol=0.2)
            p.compare(f"μ = {mu}: amplitude ≈ 2", 2.0, A, "", tol=1)
        if mu >= 10:
            p.compare(f"μ = {mu}: relaxation period, leading term (3 − 2 ln 2)μ", (3 - 2 * np.log(2)) * mu, P, "", tol=10)
            p.compare(f"μ = {mu}: with the first correction (3 − 2 ln 2)μ + 3α·μ^(−1/3), α = 2.338", (3 - 2 * np.log(2)) * mu + 3 * 2.338 * mu ** (-1 / 3), P, "", tol=3)
    ends = []
    for x0, v0 in ((0.01, 0), (3, 0), (0, 4), (-2, -2), (0.5, 0.5)):
        s = solve_ivp(vdp(1.0), (0, 100), [x0, v0], rtol=1e-10, atol=1e-12, dense_output=True)
        tt = np.linspace(80, 100, 20000); ends.append(s.sol(tt)[0].max())
    p.compare("μ = 1: spread of final amplitude over 5 very different initial conditions", 0, np.ptp(ends), "", kind="abs", tol=1e-4)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    for x0, v0, c in ((0.01, 0, C_MEAS), (3, 3, C_PRED)):
        s = solve_ivp(vdp(1.0), (0, 40), [x0, v0], rtol=1e-9, dense_output=True); tt = np.linspace(0, 40, 8000); y = s.sol(tt)
        ax[0].plot(y[0], y[1], color=c, lw=.8)
    style_axes(ax[0], "x", "ẋ", "μ = 1: inside and outside converge", legend=False)
    for mu, c in ((0.1, COLORS[0]), (2, COLORS[1]), (10, COLORS[2])):
        s = solve_ivp(vdp(mu), (0, 60), [0.5, 0], rtol=1e-9, dense_output=True, max_step=0.05); tt = np.linspace(0, 60, 12000)
        ax[1].plot(tt, s.sol(tt)[0], color=c, lw=.8, label=f"μ = {mu}")
    style_axes(ax[1], "t", "x", "From sinusoid to relaxation")
    r = np.array(rows)
    mm = np.logspace(-1, 1.4, 100)
    ax[2].loglog(r[:, 0], r[:, 1], "o", color=C_MEAS, label="measured period")
    ax[2].loglog(mm, 2 * pi * (1 + mm ** 2 / 16), "--", color=C_PRED, label="2π(1+μ²/16)"); ax[2].loglog(mm, (3 - 2 * np.log(2)) * mm, ":", color=COLORS[2], label="1.614 μ")
    ax[2].set_ylim(4, 60)
    style_axes(ax[2], "μ", "period", "Two asymptotic regimes")
    p.save(fig, "vanderpol", "Phase portrait, waveforms and period of the Van der Pol oscillator across μ.")
    p.discuss("""Trajectories starting inside and outside the cycle land on the same closed orbit — the final amplitudes of five very different starts agree to
1e-4 — which is what makes a real oscillator's amplitude reproducible: it is set by the nonlinearity, not by the start-up. For weak nonlinearity
the orbit is nearly a circle of radius 2 with period 2π(1 + μ²/16), exactly the averaging-theory prediction; for strong nonlinearity it becomes
a relaxation oscillation (slow drift, fast jump) whose period approaches (3 − 2 ln 2)μ. The leading relaxation formula is only asymptotic and under-predicts by 18 % at μ = 10;
adding the first matched-asymptotics correction 3α·μ^{−1/3} (α = 2.338, the first zero of the Airy function) brings it within ~2 % — the
correction decays so slowly that 'large μ' has to be very large indeed.""")
# tol-convention: relative tolerances are in percent
