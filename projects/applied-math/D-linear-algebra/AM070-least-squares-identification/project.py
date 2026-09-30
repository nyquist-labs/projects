from eelab import *
from scipy import signal

META = dict(
    id="AM-070", title="Least-squares system identification (ARX)", level="M",
    tools="ARX regression matrix, normal equations via QR, parameter covariance σ²(ΦᵀΦ)⁻¹, Monte-Carlo validation, bias under coloured noise",
    summary="Identify a discrete-time model of an RC-filter circuit from noisy input/output data by linear least squares, predict the "
            "parameter uncertainty from the covariance formula, verify it with 500 Monte-Carlo repetitions, and show the bias that appears when the noise is not white in the equation-error sense.",
    problem="Given measured input and output, how do you fit a model — and how much should you trust the fitted numbers?",
    theory=r"""ARX(2,2): $y[n]=-a_1y[n-1]-a_2y[n-2]+b_1u[n-1]+b_2u[n-2]+e[n]$ is linear in θ, so $\hat θ=(Φ^TΦ)^{-1}Φ^Ty$ and, for white equation error e with variance σ², $\mathrm{cov}(\hatθ)=σ^2(Φ^TΦ)^{-1}$.
If instead white noise is added to the *measured output* (output-error), the regressors contain noise and LS becomes biased — the classic errors-in-variables effect.""",
    method="""True system: a 2nd-order RC-RC low-pass discretised with ZOH at 10 kHz. Input: ±1 PRBS, N = 2000. Case 1: equation-error noise σ = 0.02 → 500 runs, empirical std vs predicted. Case 2: output noise of
the same power → bias measured. Validation: simulated output of the fitted model vs fresh data.""",
)


def truth():
    R, C = 1e3, 100e-9
    A = np.array([[-2 / (R * C), 1 / (R * C)], [1 / (R * C), -1 / (R * C)]]); B = np.array([[1 / (R * C)], [0]]); Cm = np.array([[0, 1.0]])
    d = signal.cont2discrete((A, B, Cm, np.zeros((1, 1))), 1e-4, method="zoh")
    num, den = signal.ss2tf(*d[:4])
    return num[0][1:], den


def fit(u, y):
    Phi = np.c_[-y[1:-1], -y[:-2], u[1:-1], u[:-2]]
    Q, R = np.linalg.qr(Phi)
    th = np.linalg.solve(R, Q.T @ y[2:])
    return th, Phi


def run(p):
    b, a = truth()
    theta0 = np.r_[a[1], a[2], b]
    r = p.rng
    N = 2000
    u = np.sign(r.normal(size=N))
    ths = []
    for _ in range(500):
        e = r.normal(0, 0.02, N)
        y = signal.lfilter(np.r_[0, b], a, u) + signal.lfilter([1], a, e)       # equation-error noise: e enters through 1/A
        th, Phi = fit(u, y); ths.append(th)
    ths = np.array(ths)
    covp = 0.02 ** 2 * np.linalg.inv(Phi.T @ Phi)
    pred_std = np.sqrt(np.diag(covp)); emp_std = ths.std(0)
    p.compare("Mean estimate − truth (worst parameter, equation-error noise) — unbiased", 0, np.max(np.abs(ths.mean(0) - theta0) / pred_std), "σ", kind="abs", tol=0.5)
    p.compare("Empirical std / predicted σ²(ΦᵀΦ)⁻¹ std (worst over parameters)", 1.0, np.max(emp_std / pred_std), "", tol=15)
    thb = []
    for _ in range(200):
        y = signal.lfilter(np.r_[0, b], a, u) + r.normal(0, 0.02 * np.sqrt(np.mean(1 / np.abs(np.fft.fft(a, 4096)) ** 2)), N)
        thb.append(fit(u, y)[0])
    thb = np.array(thb)
    bias = (thb.mean(0) - theta0) / thb.std(0)
    p.compare("Output-error noise: worst bias in units of the estimate's std (LS is biased)", 3, np.max(np.abs(bias)), "σ", kind="abs", tol=100)
    uv = np.sign(r.normal(size=N)); yv = signal.lfilter(np.r_[0, b], a, uv)
    th = ths.mean(0); ym = signal.lfilter(np.r_[0, th[2:]], np.r_[1, th[:2]], uv)
    p.compare("Validation on fresh data: fit percentage 100(1 − ‖y−ŷ‖/‖y−ȳ‖)", 100, 100 * (1 - np.linalg.norm(yv - ym) / np.linalg.norm(yv - yv.mean())), "%", kind="abs", tol=1)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].hist(ths[:, 0], bins=30, color=C_MEAS, alpha=.7, density=True, label="equation-error: estimates of a₁")
    xx = np.linspace(ths[:, 0].min(), ths[:, 0].max(), 200)
    ax[0].plot(xx, np.exp(-(xx - theta0[0]) ** 2 / (2 * pred_std[0] ** 2)) / (pred_std[0] * np.sqrt(2 * pi)), color=C_PRED, label="N(a₁, predicted σ²)")
    ax[0].hist(thb[:, 0], bins=30, color=COLORS[2], alpha=.6, density=True, label="output-error: biased")
    ax[0].axvline(theta0[0], color="black", ls="--")
    style_axes(ax[0], "a₁ estimate", "density", "Parameter uncertainty and bias")
    ax[1].plot(yv[:300], color="black", lw=3, alpha=.3, label="true system"); ax[1].plot(ym[:300], "--", color=C_MEAS, label="identified model")
    style_axes(ax[1], "sample", "output", "Validation on new input")
    p.save(fig, "arx", "Distribution of the identified parameter vs the covariance prediction, the output-error bias, and model validation.")
    p.discuss("""With equation-error noise, least squares is unbiased and the scatter of 500 repeated identifications matches σ²(ΦᵀΦ)⁻¹ within the Monte-Carlo
precision, so the covariance formula is a trustworthy error bar that can be computed from a single experiment. Put the same noise power on the
measured output instead — the common physical situation — and the estimates are pulled consistently away from the truth, because the noisy
past outputs sit inside the regressor matrix. The remedy is instrumental variables or output-error/prediction-error methods; the validation fit
still looks excellent either way, which is exactly why parameter bias is easy to miss.""")
# tol-convention: relative tolerances are in percent
