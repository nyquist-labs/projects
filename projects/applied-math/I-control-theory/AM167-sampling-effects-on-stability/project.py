from eelab import *
from eelab.control import zoh, exact_margins
from scipy import signal
from scipy.optimize import brentq

META = dict(
    id="AM-167", title="How sampling erodes stability margins", level="H",
    tools="Continuous lead design, exact discrete loop model (ZOH plant + Tustin controller), discrete-time phase margin from the pulse transfer function, critical sample period by spectral-radius bisection, with and without one sample of computation delay, step-response overshoot versus sample period",
    summary="A digital implementation of a continuous controller behaves like the analog loop plus a delay of half a sample (plus any computation "
            "delay). Predict the phase-margin loss ω_gc·T/2 and the sample period at which the loop goes unstable, and check both on exact discrete models.",
    problem="How fast must a digital controller sample to preserve an analog design — and what exactly is lost when it samples slower?",
    theory=r"""A zero-order hold reconstructs a staircase whose fundamental lags the ideal signal by T/2: at frequencies well below Nyquist it acts as the delay $e^{-sT/2}$. Hence $\mathrm{PM}_{digital}≈\mathrm{PM}-ω_{gc}\frac{T}{2}$ (radians) and instability near
$T_{crit}≈\frac{2\,\mathrm{PM}}{ω_{gc}}$. One extra sample of computation delay makes the total 1.5 T: $T_{crit}≈\frac{2\,\mathrm{PM}}{3ω_{gc}}$. Rule of thumb: sampling at 20–30 × the closed-loop bandwidth costs only 5–10° of phase margin.
The approximations assume ω_gc ≪ π/T and degrade as T approaches the limit.""",
    method="""Plant $G=\frac{1}{s(s+1)}$ with lead $C=10\frac{0.37s+1}{0.083s+1}$ (continuous PM ≈ 50°). Discrete loop: exact ZOH plant, Tustin-discretised compensator, optional z⁻¹. Discrete phase margin from $L(e^{jωT})$ on a fine grid; T_crit by bisection
on the closed-loop spectral radius; overshoot from simulated step responses.""",
)

CN, CD = [3.7, 10.0], [0.083, 1.0]
A = np.array([[0, 1.0], [0, -1.0]]); B = np.array([[0], [1.0]]); Cm = np.array([[1.0, 0]])


def loop(T, delay=0):
    Ad, Bd = zoh(A, B, T); ng, dg = signal.ss2tf(Ad, Bd, Cm, np.zeros((1, 1)))
    cd = signal.cont2discrete((CN, CD), T, method="bilinear"); nc, dc = cd[0][0], cd[1]
    num = np.polymul(nc, ng[0]); den = np.polymul(dc, dg)
    if delay:
        den = np.polymul(den, [1.0] + [0.0] * delay)
    num = np.trim_zeros(num, "f")
    return num, den


def pm_discrete(T, delay=0):
    num, den = loop(T, delay); w = np.logspace(-1, np.log10(pi / T * 0.999), 20000); z = np.exp(1j * w * T)
    L = np.polyval(num, z) / np.polyval(den, z); mag = np.abs(L); i = np.flatnonzero(np.diff(np.sign(mag - 1)))
    if not len(i):
        return np.nan, np.nan
    k = i[0]; ph = np.unwrap(np.angle(L))
    return 180 + np.degrees(ph[k]), w[k]


def rho(T, delay=0):
    num, den = loop(T, delay)
    return np.max(np.abs(np.roots(np.polyadd(den, np.pad(num, (len(den) - len(num), 0))))))


def step(T, delay=0, t_end=6.0):
    num, den = loop(T, delay); cl = (np.pad(num, (len(den) - len(num), 0)), np.polyadd(den, np.pad(num, (len(den) - len(num), 0))))
    n = int(t_end / T); _, y = signal.dstep((cl[0], cl[1], T), n=n)
    return np.arange(n) * T, y[0][:, 0]


def run(p):
    m = exact_margins(np.array(CN), np.polymul(CD, [1, 1, 0]))
    pm, wgc = m["pm"], m["wgc"]
    p.metric("Continuous design: gain crossover / phase margin", f"{wgc:.3f} rad/s / {pm:.1f}°")
    for T in (0.01, 0.03, 0.06):
        pd_, wd = pm_discrete(T)
        p.compare(f"T = {T * 1e3:.0f} ms (ω_s/ω_gc = {2 * pi / T / wgc:.0f}): discrete phase margin vs PM − ω_gc·T/2", pm - np.degrees(wgc * T / 2), pd_, "°", kind="abs", tol=1.5)
    pd1, _ = pm_discrete(0.03, delay=1)
    p.compare("T = 30 ms with one sample of computation delay: PM − 1.5·ω_gc·T", pm - np.degrees(1.5 * wgc * 0.03), pd1, "°", kind="abs", tol=2.5)
    tc = brentq(lambda T: rho(T) - 1, 0.02, 1.0); tc1 = brentq(lambda T: rho(T, 1) - 1, 0.02, 1.0)
    p.compare("Critical sample period (no computation delay): 2·PM/ω_gc", 2 * np.radians(pm) / wgc, tc, "s", tol=25)
    p.compare("Critical sample period with one sample of delay: 2·PM/(3ω_gc)", 2 * np.radians(pm) / (3 * wgc), tc1, "s", tol=25)
    p.compare("Computation delay cuts the usable sample period by about 3× (ratio of critical periods)", 3.0, tc / tc1, "×", tol=25)
    Ts = [0.005, 0.02, 0.05, 0.08, 0.12]; osv = []
    for T in Ts:
        t, y = step(T); osv.append(max(0, (y.max() - 1) * 100))
    p.metric("Step overshoot at T = 5 / 20 / 50 / 80 / 120 ms", " / ".join(f"{v:.0f} %" for v in osv))
    T20 = 2 * pi / (20 * wgc)
    p.compare("Rule of thumb: sampling at 20× the crossover frequency costs ≈ 9° of phase margin", 9.0, pm - pm_discrete(T20)[0], "°", kind="abs", tol=1.5)
    fig, ax = p.fig(1, 2, w=11)
    Tv = np.linspace(0.005, 0.2, 60); pv = np.array([pm_discrete(T)[0] for T in Tv]); pv1 = np.array([pm_discrete(T, 1)[0] for T in Tv])
    ax[0].plot(Tv * 1e3, pv, color=C_MEAS, label="discrete loop"); ax[0].plot(Tv * 1e3, pm - np.degrees(wgc * Tv / 2), "--", color=C_PRED, label="PM − ω_gc·T/2")
    ax[0].plot(Tv * 1e3, pv1, color=COLORS[2], label="with z⁻¹ computation delay"); ax[0].plot(Tv * 1e3, pm - np.degrees(1.5 * wgc * Tv), ":", color=COLORS[2])
    ax[0].axhline(0, color="gray", lw=.6); ax[0].set_ylim(-20, 60)
    style_axes(ax[0], "sample period T (ms)", "phase margin (°)", "Margin lost to sampling")
    for T, c in ((0.005, COLORS[2]), (0.05, C_MEAS), (0.12, COLORS[1])):
        t, y = step(T); ax[1].step(t, y, where="post", color=c, label=f"T = {T * 1e3:.0f} ms")
    ax[1].set_xlim(0, 4)
    style_axes(ax[1], "time (s)", "step response", "Same controller, slower sampling")
    p.save(fig, "sampling", "Phase margin of the digital loop versus sample period, and step responses at three sample rates.")
    p.discuss(f"""The half-sample-delay model is accurate where it matters: for sample rates 15–100 times the crossover frequency the exact discrete phase margin
is within about a degree of PM − ω_gc·T/2, and one sample of computation delay triples the loss, exactly as 1.5 T of delay should. Sampling at
20× the crossover costs 9° — the origin of the '20–30×' rule. Extrapolating the same formula all the way to zero margin predicts instability at
T ≈ {2 * np.radians(pm) / wgc * 1e3:.0f} ms; the exact loop fails at {tc * 1e3:.0f} ms (and at {tc1 * 1e3:.0f} ms with the extra delay), so the estimate is
right to roughly 20 % even there, where ω_gc is no longer small against the Nyquist frequency and the crossover itself has moved. The practical
reading: an analog design can be dropped into a processor only if the sample rate is fast against the loop bandwidth *and* the computation delay is
counted; otherwise the controller must be designed in discrete time from the start (AM-166).""")
# tol-convention: relative tolerances are in percent
