from eelab import *
from eelab.control import exact_margins, loop_with_delay, step_info
from scipy import signal

META = dict(
    id="AM-156", title="Gain and phase margins — and what they actually guarantee", level="M",
    tools="Margins by root finding on the loop frequency response, closed-loop pole computation, time-domain simulation with a true transport delay, phase-margin/overshoot rule of thumb across a gain sweep",
    summary="Compute gain and phase margins of a loop, then test their literal meaning: multiplying the gain by the gain margin puts closed-loop "
            "poles exactly on the jω axis, and adding a delay of PM/ω_gc makes a simulated loop with a real time delay oscillate indefinitely.",
    problem="A Bode plot says 'gain margin 15.6 dB, phase margin 48°'. What can actually be added to the loop before it breaks?",
    theory=r"""$L(s)=\frac{K}{s(s+1)(s+5)}$. Phase crossover where $\arctan ω+\arctan\fracω5=90°$ ⇒ $ω_{pc}=\sqrt5$, $|L|=K/30$ ⇒ GM = 30/K. At gain K·GM the closed loop has poles at ±j√5. The phase margin PM at the gain crossover $ω_{gc}$ is the extra
phase lag tolerated; a pure delay τ contributes $-ωτ$, so the **delay margin** is $τ_d=\mathrm{PM}/ω_{gc}$ (PM in radians). Rule of thumb for second-order-like loops: ζ ≈ PM/100, overshoot ≈ $e^{-πζ/\sqrt{1-ζ^2}}$.""",
    method="""K = 5. Margins by bracketing and Brent root finding. Closed-loop poles at K·GM from the characteristic polynomial. Delay test: unity-feedback simulation (exact ZOH plant stepping, 1 ms) with the error delayed by τ; critical τ found by bisection on
whether the oscillation grows. Overshoot rule checked for K = 1…15.""",
)


def growth(delay, K=5.0):
    t, y = loop_with_delay([K], np.polymul([1, 0], np.polymul([1, 1], [1, 5])), delay, 80.0)
    e = np.abs(y - 1)
    return np.max(e[(t > 60)]) / max(np.max(e[(t > 35) & (t < 55)]), 1e-12)


def run(p):
    K = 5.0; den = np.polymul([1, 0], np.polymul([1, 1], [1, 5]))
    m = exact_margins([K], den)
    p.compare("Phase-crossover frequency √5", np.sqrt(5), m["wpc"], "rad/s", tol=0.01)
    p.compare("Gain margin 30/K", 30 / K, m["gm"], "×", tol=0.01)
    poles = np.roots(np.polyadd(den, [K * m["gm"]]))
    p.compare("Gain raised by exactly the gain margin: largest real part of the closed-loop poles", 0.0, float(np.max(poles.real)), "1/s", kind="abs", tol=1e-6)
    p.compare("… and those poles sit at ±j√5", np.sqrt(5), float(np.max(np.abs(poles.imag))), "rad/s", tol=0.01)
    td = np.radians(m["pm"]) / m["wgc"]
    p.metric("Gain crossover / phase margin", f"{m['wgc']:.4f} rad/s / {m['pm']:.2f}°")
    lo, hi = 0.5 * td, 1.5 * td
    for _ in range(11):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if growth(mid) < 1 else (lo, mid)
    p.compare("Delay margin PM/ω_gc vs critical delay found by time-domain simulation", td, (lo + hi) / 2, "s", tol=1.5)
    t, y = loop_with_delay([K], den, td, 80.0)
    zc = t[1:][(y[:-1] < 1) & (y[1:] >= 1)]
    p.compare("Oscillation frequency at the critical delay = ω_gc", m["wgc"], 2 * pi / np.mean(np.diff(zc[-6:])), "rad/s", tol=1.5)
    rows = []
    for k in (1, 2, 3, 5, 8, 12, 15):
        mk = exact_margins([k], den); tt = np.linspace(0, 60, 30001)
        _, ys, _ = signal.lsim(([k], np.polyadd(den, [k])), np.ones_like(tt), tt)
        z = min(mk["pm"] / 100, 0.999); rows.append((k, mk["pm"], 100 * np.exp(-pi * z / np.sqrt(1 - z * z)), step_info(tt, ys, 1.0)["overshoot"]))
    rr = np.array(rows)
    p.compare("Rule of thumb ζ ≈ PM/100: worst overshoot error over K = 1…15 (expected: good to ~10 pp)", 0.0, float(np.max(np.abs(rr[:, 2] - rr[:, 3]))), "pp", kind="abs", tol=10)
    p.section("Phase margin vs overshoot", "| K | PM (°) | overshoot from ζ ≈ PM/100 (%) | simulated overshoot (%) |\n|---|---|---|---|\n" + "\n".join(f"| {k:.0f} | {a:.1f} | {b:.1f} | {c:.1f} |" for k, a, b, c in rr))
    fig, ax = p.fig(1, 2, w=11)
    w = np.logspace(-1.5, 1.5, 600); Lw = K / np.polyval(den, 1j * w)
    ax[0].plot(Lw.real, Lw.imag, color=C_MEAS, label="L(jω), K = 5"); ax[0].plot((Lw * m["gm"]).real, (Lw * m["gm"]).imag, color=C_PRED, ls="--", label="gain × GM")
    Ld = Lw * np.exp(-1j * w * td); ax[0].plot(Ld.real, Ld.imag, color=COLORS[2], ls=":", label="with delay PM/ω_gc")
    ax[0].plot([-1], [0], "k+", ms=12); th = np.linspace(0, 2 * pi, 200); ax[0].plot(np.cos(th), np.sin(th), color="gray", lw=.5)
    ax[0].set_xlim(-2.5, 0.5); ax[0].set_ylim(-2, 1)
    style_axes(ax[0], "Re L", "Im L", "Both margins push the Nyquist curve onto −1")
    for d, c, lab in ((0.0, COLORS[2], "no delay"), (0.8 * td, C_MEAS, "0.8·τ_d"), (td, C_PRED, "τ_d"), (1.1 * td, COLORS[1], "1.1·τ_d")):
        t_, y_ = loop_with_delay([K], den, d, 40.0); ax[1].plot(t_, y_, color=c, lw=1, label=lab)
    ax[1].set_ylim(-1, 3)
    style_axes(ax[1], "time (s)", "step response", "Adding a real delay to the loop")
    p.save(fig, "margins", "Nyquist curves at the two stability limits, and step responses with increasing loop delay.")
    p.discuss(f"""The margins mean exactly what they say. Multiplying the gain by the gain margin (×{m['gm']:.0f}) puts a closed-loop pole pair on the imaginary axis
at ±j√5, the phase-crossover frequency; and a loop simulated with a genuine transport delay starts to oscillate without decay at
τ = {(lo + hi) / 2:.3f} s, within about a percent of PM/ω_gc = {td:.3f} s, oscillating at the gain-crossover frequency. The margins are, however,
two single-direction measurements of the distance to −1: a loop can have comfortable gain *and* phase margins yet pass close to −1 in between
(the reason for the sensitivity peak M_s as a robustness measure). The familiar 'ζ ≈ PM/100' overshoot rule holds here to within
{np.max(np.abs(rr[:, 2] - rr[:, 3])):.0f} percentage points across a 15:1 gain range — useful for a first estimate, not a guarantee.""")
# tol-convention: relative tolerances are in percent
