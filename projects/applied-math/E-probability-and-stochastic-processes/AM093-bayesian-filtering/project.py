from eelab import *

META = dict(
    id="AM-093", title="Recursive Bayesian filtering on a grid", level="H",
    tools="Histogram (grid) Bayes filter: predict by convolving with the motion model, update by multiplying with the measurement likelihood; Gaussian case compared with the Kalman filter; non-Gaussian (bimodal) likelihood",
    summary="Track a drifting quantity by propagating a full probability distribution on a grid, show that in the linear-Gaussian case the grid "
            "filter reproduces the Kalman filter exactly, and then use it where Kalman cannot: a sensor with an ambiguous (two-peaked) likelihood.",
    problem="A belief about a hidden state should be updated every time a noisy measurement arrives. What does 'recursive belief updating' actually compute?",
    theory=r"""Predict: $p(x_k|y_{1:k-1})=\int p(x_k|x_{k-1})p(x_{k-1}|y_{1:k-1})dx_{k-1}$ (a convolution for random-walk motion). Update: $p(x_k|y_{1:k})\propto p(y_k|x_k)\,p(x_k|y_{1:k-1})$. With Gaussian motion and likelihood,
every distribution stays Gaussian and the recursion is exactly the Kalman filter (mean and variance). A sensor that cannot tell x from −x (e.g. |phase|, a symmetric magnetometer) gives a bimodal
likelihood; the grid filter keeps both hypotheses until motion breaks the symmetry.""",
    method="""Random walk x_k = x_{k−1} + w, σ_w = 0.1; measurements y = x + v, σ_v = 0.5; grid of 2001 points on [−10, 10]; 200 steps. Compare posterior mean/variance with a scalar Kalman filter. Ambiguous sensor:
y = |x| + v with a drift of +0.05/step starting at x = −2; posterior mode and probability mass on x > 0 over time.""",
)


def run(p):
    r = p.rng
    x = np.linspace(-10, 10, 2001); dx = x[1] - x[0]
    sw, sv, K = 0.1, 0.5, 200
    kern = np.exp(-0.5 * (np.arange(-60, 61) * dx / sw) ** 2); kern /= kern.sum()
    xt = np.cumsum(r.normal(0, sw, K)) + 1.0; y = xt + r.normal(0, sv, K)
    belief = np.exp(-0.5 * ((x - 0) / 2.0) ** 2); belief /= belief.sum()
    m, P = 0.0, 4.0
    gm, gv, km, kv = [], [], [], []
    for k in range(K):
        belief = np.convolve(belief, kern, "same"); belief *= np.exp(-0.5 * ((y[k] - x) / sv) ** 2); belief /= belief.sum()
        mu = np.sum(x * belief); gm.append(mu); gv.append(np.sum((x - mu) ** 2 * belief))
        P += sw ** 2; Kk = P / (P + sv ** 2); m += Kk * (y[k] - m); P *= (1 - Kk); km.append(m); kv.append(P)
    gm, gv, km, kv = map(np.array, (gm, gv, km, kv))
    p.compare("Linear-Gaussian case: grid posterior mean vs Kalman filter (max difference / σ)", 0, np.max(np.abs(gm - km) / np.sqrt(kv)), "", kind="abs", tol=0.02)
    p.compare("… posterior variance vs Kalman (max relative)", 0, np.max(np.abs(gv / kv - 1)), "", kind="abs", tol=0.02)
    p.compare("Steady-state variance vs Riccati solution", 0.5 * (-sw ** 2 + np.sqrt(sw ** 4 + 4 * sw ** 2 * sv ** 2)) , kv[-1], "", tol=1)
    xt2 = -2 + 0.05 * np.arange(K) + np.cumsum(r.normal(0, 0.02, K)); y2 = np.abs(xt2) + r.normal(0, 0.3, K)
    belief = np.ones_like(x); belief /= belief.sum()
    kern2 = np.exp(-0.5 * ((np.arange(-60, 61) * dx - 0.05) / 0.05) ** 2); kern2 /= kern2.sum()
    mass_pos, modes, snaps = [], [], {}
    for k in range(K):
        belief = np.convolve(belief, kern2, "same"); belief *= np.exp(-0.5 * ((y2[k] - np.abs(x)) / 0.3) ** 2); belief /= belief.sum()
        mass_pos.append(belief[x > 0].sum()); modes.append(x[np.argmax(belief)])
        if k in (5, 60, 150):
            snaps[k] = belief.copy()
    mass_pos = np.array(mass_pos)
    p.compare("Ambiguous sensor, early (k = 5): posterior probability that x > 0 stays ≈ ½? No — the drift model already favours the true side; mass on x < 0", 1, int(mass_pos[5] < 0.5), "", kind="abs")
    cross = np.argmax(xt2 > 0)
    p.compare("After the true state crosses 0 and moves on (k = 150): posterior mass on the correct side (x > 0)", 1.0, mass_pos[150], "", kind="abs", tol=0.05)
    p.metric("Step at which the true state crosses zero", int(cross), "")
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    t = np.arange(K)
    ax[0].plot(t, xt, color="black", lw=1, label="true"); ax[0].plot(t, y, ".", ms=2, color=COLORS[7], label="measurements"); ax[0].plot(t, gm, color=C_MEAS, lw=2, label="grid Bayes mean")
    ax[0].plot(t, km, "--", color=C_PRED, label="Kalman")
    style_axes(ax[0], "step", "x", "Linear-Gaussian: identical to Kalman")
    for k, c in zip(snaps, COLORS):
        ax[1].plot(x, snaps[k] / dx, color=c, label=f"k = {k}")
    ax[1].set_xlim(-5, 7)
    style_axes(ax[1], "x", "posterior density", "|x| sensor: two hypotheses resolved by motion")
    ax[2].plot(t, xt2, color="black", label="true x"); ax[2].plot(t, modes, ".", ms=3, color=C_MEAS, label="posterior mode"); ax[2].plot(t, mass_pos * 4 - 2, color=C_PRED, label="P(x > 0), scaled")
    style_axes(ax[2], "step", None, "Tracking through the ambiguity")
    p.save(fig, "bayes_filter", "Grid Bayes filter vs Kalman in the Gaussian case, and posterior evolution with an ambiguous |x| sensor.")
    p.discuss("""With Gaussian motion and measurement models the grid filter's posterior mean and variance coincide with the Kalman filter's to within grid
resolution and converge to the Riccati steady state — confirming that the Kalman filter *is* recursive Bayes, specialised to Gaussians. The grid
filter's value shows with the |x| sensor: the likelihood has two peaks (x and −x), so the belief is genuinely bimodal; the motion model (known
positive drift) makes one branch inconsistent over time, and the posterior mass migrates to the correct side as the state crosses zero. A
Kalman or extended Kalman filter, which can carry only one Gaussian, would have committed to one branch and possibly the wrong one. The cost
is the grid: exponential in dimension, which is what particle filters (AM-095) avoid.""")
# tol-convention: relative tolerances are in percent
