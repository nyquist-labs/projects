from eelab import *
from eelab.control import margins, step_info
from scipy import signal

META = dict(
    id="SL-163", title="Bode/Nyquist margin analyser", level="M",
    tools="Own gain/phase-margin finder on dense frequency grids (NumPy), SciPy closed-loop step responses",
    summary="Compute gain and phase margins of a loop L(s) = K/(s(s+1)(0.1s+1)) for several gains, check them against the "
            "analytic crossover conditions, and relate phase margin to measured closed-loop overshoot.",
    problem="Phase and gain margins are how engineers judge 'how stable' a loop is. Compute them reliably and see what they "
            "mean for the step response.",
    theory=r"""Phase crossover where ∠L = −180°: $\arctan\omega+\arctan0.1\omega=90°$ ⇒ $\omega_{pc}=\sqrt{10}$ = 3.162 rad/s, and $|L(j\omega_{pc})|=K/11$, so the loop
goes unstable at K = 11 (GM = 20log(11/K)). Rule of thumb for a dominant second-order loop: overshoot ≈ 70 − PM (degrees), valid for PM ≈ 30–65°.""",
    method="""K ∈ {1, 2, 4, 6}. Margins by locating crossings on a 200,000-point log grid with unwrapped phase; closed-loop step responses with SciPy.""",
)


def run(p):
    rows = []
    fig, ax = p.fig(1, 2, w=11)
    for i, K in enumerate((1, 2, 4, 6)):
        den = np.polymul([1, 0], np.polymul([1, 1], [0.1, 1]))
        m = margins([K], den)
        p.compare(f"K = {K}: gain margin 20·log₁₀(11/K)", 20 * np.log10(11 / K), m["gm_db"], "dB", kind="abs")
        if K == 1:
            p.compare("Phase-crossover frequency √10", np.sqrt(10), m["wpc"], "rad/s", tol=0.5)
        cl = signal.lti([K], np.polyadd(den, [0, 0, 0, K]))
        t, y = signal.step(cl, T=np.linspace(0, 30, 6000))
        os_ = step_info(t, y, 1.0)["overshoot"]
        rows.append((K, m["gm_db"], m["pm_deg"], os_))
        ax[1].plot(t, y, color=COLORS[i], label=f"K = {K} (PM {m['pm_deg']:.0f}°)")
        w = np.logspace(-2, 2, 2000); _, H = signal.freqs([K], den, worN=w)
        ax[0].plot(H.real, H.imag, color=COLORS[i], label=f"K = {K}")
    for K, gm, pm, os_ in rows:
        if 30 <= pm <= 65:
            p.compare(f"K = {K}: overshoot vs '70 − PM' rule", 70 - pm, os_, "%", kind="abs")
    ax[0].plot(-1, 0, "x", color="black", ms=10); ax[0].set_xlim(-3, 1); ax[0].set_ylim(-3, 1)
    style_axes(ax[0], "Re L(jω)", "Im L(jω)", "Nyquist plots (−1 marked)")
    style_axes(ax[1], "time (s)", "output", "Closed-loop steps")
    p.save(fig, "margins", "As K grows the Nyquist curve approaches −1, margins shrink and overshoot rises.")
    import pandas as pd
    p.csv_df("margins", pd.DataFrame(rows, columns=["K", "GM_dB", "PM_deg", "overshoot_pct"]))
    p.discuss("""The numerical gain margins match 20·log(11/K) to the grid precision — the analytic phase-crossover condition and the search agree. Phase margin
predicts overshoot through the '70 − PM' rule only roughly: it is derived for a pure second-order loop, and this third-order loop's extra
pole adds lag the rule ignores. Margins remain the right design tool because they also quantify robustness to gain and delay errors,
which overshoot alone does not.""")
