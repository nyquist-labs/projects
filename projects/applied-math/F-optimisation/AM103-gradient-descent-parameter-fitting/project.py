from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-103", title="Fitting a diode model: gradient descent vs Gauss–Newton", level="M",
    tools="Diode I–V data from the MNA simulator (Shockley diode with series resistance) plus measurement noise, own gradient descent with line search, own Gauss–Newton / Levenberg–Marquardt, convergence-rate comparison",
    summary="Extract the saturation current, ideality factor and series resistance of a diode from noisy I–V measurements by minimising the squared "
            "log-current error with three self-written optimisers, and show why plain gradient descent crawls on this ill-conditioned problem while Gauss–Newton converges in a few steps.",
    problem="Every device model is fitted to measurements. Why does the choice of optimiser matter so much?",
    theory=r"""$I = I_s(e^{(V-IR_s)/(nV_T)}-1)$. Parameters θ = (ln I_s, n, R_s) span orders of magnitude and are strongly correlated (I_s and n trade off), so the Hessian of the least-squares cost is poorly conditioned
(my guess: κ ≫ 10⁴; measured below). Gradient descent converges linearly with rate ≈ (κ−1)/(κ+1) per step — thousands of iterations; Gauss–Newton uses JᵀJ as the Hessian and converges quadratically near the optimum. Fitting ln I rather than I weights the
exponential region fairly.""",
    method="""'Measured' data: the repository's MNA simulator with a diode (I_s = 2.5 nA, n = 1.8, R_s = 0.6 Ω), V from 0.3 to 1.0 V, 1 % multiplicative noise. Implicit model solved per point by Newton; Jacobian by finite differences.
Start (ln I_s, n, R_s) = (ln 1e-12, 1.2, 0.05). GD with backtracking line search vs LM; iterations to reach cost within 1e-6 of the optimum.""",
)

VT = 0.025852


def model_I(theta, V):
    lnIs, n, Rs = theta
    Is = np.exp(lnIs); I = np.maximum(Is * np.expm1(V / (n * VT)) * 0.5, 1e-15)
    for _ in range(60):
        g = Is * np.expm1((V - I * Rs) / (n * VT)) - I
        dg = -Is * np.exp((V - I * Rs) / (n * VT)) * Rs / (n * VT) - 1
        step = g / dg
        I = np.maximum(I - step, I * 0.1)
        if np.max(np.abs(step / I)) < 1e-13:
            break
    return I


def residual(theta, V, Im):
    return np.log(model_I(theta, V)) - np.log(Im)


def jac(theta, V, Im, h=1e-6):
    r0 = residual(theta, V, Im); J = np.zeros((len(V), 3))
    for k in range(3):
        t = np.array(theta, float); t[k] += h; J[:, k] = (residual(t, V, Im) - r0) / h
    return r0, J


def run(p):
    Vs = np.linspace(0.3, 1.0, 40)
    Im = []
    for v in Vs:
        ck = Circuit("d"); ck.V("s", "a", "0", dc=v); ck.D("d", "a", "0", Is=2.5e-9, N=1.8, Rs=0.6); Im.append(-ck.op()["I(s)"])
    Im = np.array(Im) * (1 + 0.01 * p.rng.normal(size=len(Vs)))
    th0 = np.array([np.log(1e-12), 1.2, 0.05])
    th = th0.copy(); lam = 1e-3; hist_lm = []
    for it in range(100):
        r0, J = jac(th, Vs, Im); c = 0.5 * r0 @ r0; hist_lm.append(c)
        while True:
            step = np.linalg.solve(J.T @ J + lam * np.diag(np.diag(J.T @ J)), -J.T @ r0)
            rn = residual(th + step, Vs, Im)
            if 0.5 * rn @ rn < c:
                th = th + step; lam = max(lam / 10, 1e-12); break
            lam *= 10
            if lam > 1e12:
                break
        if it > 3 and abs(hist_lm[-2] - hist_lm[-1]) < 1e-15:
            break
    c_opt = 0.5 * residual(th, Vs, Im) @ residual(th, Vs, Im)
    p.compare("LM fit: saturation current I_s", 2.5e-9, np.exp(th[0]), "A", tol=15)
    p.compare("LM fit: ideality factor n", 1.8, th[1], "", tol=2)
    p.compare("LM fit: series resistance R_s", 0.6, th[2], "Ω", tol=5)
    r0, J = jac(th, Vs, Im)
    Js = J / np.linalg.norm(J, axis=0)
    kappa = np.linalg.cond(J.T @ J)
    p.metric("Condition number of JᵀJ at the optimum (raw / column-scaled)", f"{kappa:.1e} / {np.linalg.cond(Js.T @ Js):.1e}")
    it_lm = next(k for k, c in enumerate(hist_lm) if c - c_opt < 1e-6)
    th = th0.copy(); hist_gd = []
    for it in range(20000):
        r0, J = jac(th, Vs, Im); c = 0.5 * r0 @ r0
        if not np.isfinite(c):
            break
        hist_gd.append(c); g = J.T @ r0
        t = 1.0
        while t > 1e-20:
            with np.errstate(all="ignore"):
                cn = 0.5 * np.sum(residual(th - t * g, Vs, Im) ** 2)
            if np.isfinite(cn) and cn <= c - 1e-4 * t * g @ g:      # Armijo condition; non-finite trial points are rejected
                break
            t *= 0.5
        th = th - t * g
        if c - c_opt < 1e-6:
            break
    it_gd = len(hist_gd)
    p.compare("Iterations to reach the optimum cost (+1e-6): gradient descent / LM (my guess ≥ 100×)", 100, it_gd / max(it_lm, 1), "×", kind="abs", tol=1e6)
    p.metric("Iterations: LM / gradient descent", f"{it_lm} / {it_gd}{' (stopped at cap)' if it_gd >= 20000 else ''}")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(Vs, Im, "o", color=C_MEAS, ms=4, label="measured (sim + 1 % noise)"); ax[0].semilogy(Vs, model_I(th, Vs), color=C_PRED, label="fitted model")
    style_axes(ax[0], "V (V)", "I (A)", "Diode I–V fit (series R bends the top)")
    ax[1].semilogy(np.array(hist_lm) - c_opt + 1e-16, "o-", color=C_MEAS, label="Levenberg–Marquardt"); ax[1].semilogy(np.array(hist_gd) - c_opt + 1e-16, color=COLORS[1], label="gradient descent + line search")
    ax[1].set_xscale("log")
    style_axes(ax[1], "iteration", "cost − optimum", "Convergence")
    p.save(fig, "diode_fit", "Measured and fitted diode characteristics, and the convergence of the two optimisers.")
    p.discuss(f"""Levenberg–Marquardt recovers I_s, n and R_s from noisy data in {it_lm} iterations, within the uncertainty the 1 % noise allows (I_s is the least well
determined because it trades off against n). Gradient descent with a proper line search needs {it_gd}{'+' if it_gd >= 20000 else ''} iterations for the same cost: the
Hessian's condition number (~{kappa:.0e}) makes the cost surface a long, narrow valley, and steepest descent zig-zags across it. Scaling the
parameters helps somewhat, but the curvature information in JᵀJ is what makes Gauss–Newton-type methods the default for model extraction —
SPICE parameter extractors and every nonlinear least-squares library use them.""")
# tol-convention: relative tolerances are in percent
