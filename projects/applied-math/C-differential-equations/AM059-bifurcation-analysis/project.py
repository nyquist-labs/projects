from eelab import *
from scipy.integrate import solve_ivp

META = dict(
    id="AM-059", title="Bifurcations: Hopf onset of oscillation and the period-doubling route to chaos", level="H",
    tools="Van der Pol-type oscillator with parameter μ (supercritical Hopf), amplitude scaling fit; logistic map bifurcation diagram and Feigenbaum ratio measurement",
    summary="Map how behaviour changes qualitatively with a parameter: show that an oscillator is born at μ = 0 with amplitude 2√μ (a supercritical "
            "Hopf bifurcation), then trace a period-doubling cascade and measure how fast the doublings accumulate (Feigenbaum's constant).",
    problem="When a parameter is turned slowly, a circuit can switch from silent to oscillating to chaotic. Are these transitions predictable?",
    theory=r"""$\ddot x-(μ-x^2)\dot x+x=0$: the origin's eigenvalues cross the jω axis at μ = 0 and averaging gives a limit cycle of amplitude $2\sqrt{μ}$ — it grows continuously from zero (supercritical).
Period doubling in the map $x\mapsto rx(1-x)$ (the discrete-time model of many sampled nonlinear loops): doubling points $r_n$ accumulate geometrically with ratio
$δ=\lim\frac{r_n-r_{n-1}}{r_{n+1}-r_n}=4.6692…$, a universal constant for smooth unimodal maps.""",
    method="""Hopf: μ from −0.2 to 0.5, amplitude after transients; fit a² vs μ. Logistic map: bifurcation diagram for r ∈ [2.8, 4]; doubling points located by bisection on the attractor's period (detected from
2¹⁵ iterations with tolerance 1e-9), then δ from successive intervals.""",
)


def hopf_amp(mu):
    s = solve_ivp(lambda t, y: [y[1], (mu - y[0] ** 2) * y[1] - y[0]], (0, 3000), [0.3, 0], rtol=1e-9, atol=1e-12, dense_output=True)
    t = np.linspace(2900, 3000, 20000)
    return np.abs(s.sol(t)[0]).max()


def period(r, n_trans=20000, n=2048, tol=1e-9):
    x = 0.4
    for _ in range(n_trans):
        x = r * x * (1 - x)
    orbit = [x]
    for _ in range(n):
        x = r * x * (1 - x); orbit.append(x)
    orbit = np.array(orbit)
    for pd in (1, 2, 4, 8, 16, 32, 64, 128):
        if np.abs(orbit[pd:pd + 64] - orbit[:64]).max() < tol:
            return pd
    return 0


def doubling_point(pd, lo, hi):
    for _ in range(60):
        mid = (lo + hi) / 2
        if period(mid) <= pd and period(mid) != 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def run(p):
    mus = np.array([0.02, 0.05, 0.1, 0.2, 0.3, 0.5])
    amps = np.array([hopf_amp(m) for m in mus])
    p.compare("Below the bifurcation (μ = −0.1): oscillation decays to 0", 0, hopf_amp(-0.1), "", kind="abs", tol=1e-3)
    slope = np.polyfit(mus[:4], amps[:4] ** 2, 1)[0]
    p.compare("Supercritical Hopf: a² ∝ μ with slope 4 (a = 2√μ)", 4.0, slope, "", tol=3)
    pts = [3.0]
    brackets = [(3.0, 3.46), (3.44, 3.55), (3.54, 3.567), (3.5680, 3.5696), (3.5696, 3.5699)]
    for pd, (lo, hi) in zip((2, 4, 8, 16, 32), brackets):
        pts.append(doubling_point(pd, lo, hi))
    pts = np.array(pts)
    p.compare("First doubling at r = 3 (exact) located numerically", 3.0, doubling_point(1, 2.9, 3.1), "", tol=0.01)
    p.compare("Second doubling r₂ = 1 + √6", 1 + np.sqrt(6), pts[1], "", tol=0.01)
    deltas = np.diff(pts)[:-1] / np.diff(pts)[1:]
    p.compare("Feigenbaum ratio from the last available doublings", 4.6692, deltas[-1], "", tol=3)
    p.metric("Successive doubling-interval ratios", ", ".join(f"{d:.3f}" for d in deltas))
    fig, ax = p.fig(1, 2, w=11)
    mm = np.linspace(-0.2, 0.5, 30)
    ax[0].plot(mm, [hopf_amp(m) for m in mm], "o", color=C_MEAS, ms=4, label="simulated amplitude")
    m2 = np.linspace(0, 0.5, 100); ax[0].plot(m2, 2 * np.sqrt(m2), "--", color=C_PRED, label="2√μ")
    style_axes(ax[0], "μ", "limit-cycle amplitude", "Hopf bifurcation: oscillation is born at μ = 0")
    rs = np.linspace(2.8, 4.0, 1500)
    for r in rs:
        x = 0.4
        for _ in range(500):
            x = r * x * (1 - x)
        xs = []
        for _ in range(120):
            x = r * x * (1 - x); xs.append(x)
        ax[1].plot([r] * len(xs), xs, ",", color=C_MEAS, alpha=.4)
    for r_ in pts:
        ax[1].axvline(r_, color=C_PRED, lw=.5)
    style_axes(ax[1], "r", "attractor", "Period-doubling cascade (logistic map)", legend=False)
    p.save(fig, "bifurcation", "Amplitude through the Hopf bifurcation, and the logistic-map bifurcation diagram with located doubling points.")
    p.discuss(f"""Both transitions are quantitatively predictable. The oscillator is silent for μ < 0 and its amplitude rises as 2√μ right after the Hopf point
(fitted slope of a² vs μ: {slope:.2f}); there is no jump and no hysteresis, the signature of a *supercritical* Hopf — which is what a well-designed
oscillator's start-up looks like as the loop gain crosses one. In the period-doubling cascade the first two doublings land on their exact values
(3 and 1 + √6), and the ratio of successive intervals approaches Feigenbaum's 4.669 ({deltas[-1]:.3f} from the last pair resolved in double
precision). That universality is why the same cascade is seen in driven diode circuits, phase-locked loops and switching converters on the way to chaos.""")
# tol-convention: relative tolerances are in percent
