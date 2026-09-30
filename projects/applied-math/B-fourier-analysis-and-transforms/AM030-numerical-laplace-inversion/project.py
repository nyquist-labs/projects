from eelab import *
from math import factorial
from scipy.special import erfc

META = dict(
    id="AM-030", title="Numerical Laplace inversion: Stehfest vs Talbot", level="H",
    tools="Own Gaver–Stehfest and fixed-Talbot inversion algorithms, test transforms with known inverses (including non-rational e^{−√s}/s), multiprecision-free error study",
    summary="Recover time responses from F(s) numerically with two classic algorithms, test them on smooth, oscillatory and non-rational "
            "transforms with known inverses, and measure where each breaks down.",
    problem="Many circuit and diffusion problems give F(s) in closed form but no neat inverse. How reliable are numerical inversions?",
    theory=r"""Gaver–Stehfest uses only real s: $f(t)≈\frac{\ln2}{t}\sum_{k=1}^{N}V_kF(k\ln2/t)$ with alternating combinatorial weights $V_k$ — excellent for smooth, non-oscillating f, but it cannot
represent oscillations (all samples on the real axis) and needs high precision as N grows (weights ~10^{N/2}). Fixed Talbot deforms the Bromwich contour into the left half-plane, where
$e^{st}$ decays, giving near-exponential convergence even for oscillatory f. Predictions: Stehfest ~1e-6 on e^{−t}, poor on sin t; Talbot ~1e-10 on all.""",
    method="""Test pairs: 1/(s+1) → e^{−t}; 1/(s²+1) → sin t; e^{−√s}/s → erfc(1/(2√t)) (diffusion into a half-space, an RC transmission line); t ∈ [0.1, 10]. Stehfest N = 14 (double precision), Talbot M = 32.""",
)


def stehfest_weights(N):
    V = []
    for k in range(1, N + 1):
        s = 0.0
        for j in range((k + 1) // 2, min(k, N // 2) + 1):
            s += j ** (N // 2) * factorial(2 * j) / (factorial(N // 2 - j) * factorial(j) * factorial(j - 1) * factorial(k - j) * factorial(2 * j - k))
        V.append((-1) ** (k + N // 2) * s)
    return np.array(V)


def stehfest(F, t, N=14):
    V = stehfest_weights(N); ln2 = np.log(2)
    return np.array([ln2 / tt * np.sum(V * np.array([F(k * ln2 / tt) for k in range(1, N + 1)])) for tt in t])


def talbot(F, t, M=32):
    out = []
    for tt in t:
        r = 2 * M / (5 * tt)
        s = 0.5 * np.exp(r * tt) * F(r + 0j).real
        for k in range(1, M):
            th = k * pi / M
            cot = np.cos(th) / np.sin(th)
            sk = r * th * (cot + 1j)
            sig = th + (th * cot - 1) * cot
            s += (np.exp(tt * sk) * F(sk) * (1 + 1j * sig)).real
        out.append(r / M * s)
    return np.array(out)


def run(p):
    t = np.linspace(0.1, 10, 100)
    cases = {
        "1/(s+1) → e^(−t)": (lambda s: 1 / (s + 1), np.exp(-t)),
        "1/(s²+1) → sin t": (lambda s: 1 / (s * s + 1), np.sin(t)),
        "e^(−√s)/s → erfc(1/(2√t))": (lambda s: np.exp(-np.sqrt(s)) / s, erfc(1 / (2 * np.sqrt(t)))),
    }
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    for k, (name, (F, f)) in enumerate(cases.items()):
        ys = stehfest(F, t); yt = talbot(F, t)
        es, et = np.max(np.abs(ys - f)), np.max(np.abs(yt - f))
        p.compare(f"{name}: Talbot worst error", 0, et, "", kind="abs", tol=1e-8)
        p.metric(f"{name}: Stehfest (N = 14) worst error", es, "")
        ax[k].plot(t, f, color="black", lw=3, alpha=.3, label="exact"); ax[k].plot(t, yt, "--", color=C_MEAS, label="Talbot"); ax[k].plot(t, ys, ":", color=C_PRED, label="Stehfest")
        style_axes(ax[k], "t", "f(t)" if k == 0 else None, name, legend=(k == 1))
        if "sin" in name:
            ax[k].set_ylim(-1.5, 1.5)
    p.save(fig, "laplace_inversion", "Numerical inversions of three transforms with known inverses.")
    F, f = cases["1/(s+1) → e^(−t)"]
    errs = [(N, np.max(np.abs(stehfest(F, t, N) - f))) for N in (6, 8, 10, 12, 14, 16, 18, 20, 24)]
    best = min(errs, key=lambda e: e[1])
    p.metric("Stehfest on e^(−t): best N and error (then round-off takes over)", f"N = {best[0]}, {best[1]:.1e}")
    p.discuss(f"""Fixed Talbot recovers all three responses to better than 1e-8, including the oscillating sine and the non-rational diffusion transform
e^{{−√s}}/s whose inverse (an erfc) is how a step spreads into a distributed RC line. Stehfest is accurate on the smooth exponential (best
{best[1]:.0e} at N = {best[0]}; larger N makes it *worse* because its weights grow to ~10^N/2 and double precision runs out) and on the erfc, but fails on
sin t: sampling F only on the real axis cannot distinguish oscillations. Rule of thumb confirmed: Stehfest for monotone diffusion-type problems,
Talbot (or other contour methods) when anything rings.""")
# tol-convention: relative tolerances are in percent
