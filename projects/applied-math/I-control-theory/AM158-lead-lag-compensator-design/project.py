from eelab import *
from eelab.control import exact_margins, step_info
from scipy import signal
from scipy.optimize import brentq

META = dict(
    id="AM-158", title="Lead–lag compensator design in the frequency domain", level="M",
    tools="Classical Bode-based design procedure coded step by step (static gain for K_v, lead for phase margin, lag for low-frequency gain), margins by root finding, closed-loop step and ramp simulations",
    summary="Design a lead compensator to raise the phase margin of a type-1 plant from 18° to a 50° target, then a lag section to multiply the velocity "
            "constant by ten, and verify the achieved margins, overshoot and ramp-tracking error against the design equations.",
    problem="The plant needs K_v = 10 but is nearly unstable at that gain. How do lead and lag networks buy back stability and accuracy?",
    theory=r"""Plant $G=\frac{1}{s(s+1)}$, K = 10 ⇒ $K_v=10$, PM ≈ 18°. Lead $C=\frac{αTs+1}{Ts+1}$ adds at most $φ_m=\arcsin\frac{α-1}{α+1}$ at $ω_m=\frac{1}{T\sqrtα}$ with gain $\sqrtα$ there. Procedure: needed phase = target − PM + margin ⇒ α; new crossover
where $|KG|=1/\sqrtα$; set $ω_m$ to it. Lag $\frac{s+z}{s+z/β}$ multiplies low-frequency gain by β with a phase cost of about $\arctan\frac{(β-1)\,z/ω_{gc}}{1+β (z/ω_{gc})^2}$ at crossover (≈ 5° for z = ω_gc/10). Ramp error = 1/K_v.""",
    method="""Target PM 50°, safety margin 8°. Lag: β = 10, zero a decade below crossover. Verification: exact margins of each loop, closed-loop step responses (overshoot), ramp response over 400 s (error → 1/K_v).""",
)


def run(p):
    K = 10.0; g_den = np.array([1.0, 1.0, 0.0])
    m0 = exact_margins([K], g_den)
    p.compare("Uncompensated phase margin 180° − 90° − arctan ω_gc", 90 - np.degrees(np.arctan(m0["wgc"])), m0["pm"], "°", kind="abs", tol=0.05)
    phi = np.radians(50 - m0["pm"] + 8); alpha = (1 + np.sin(phi)) / (1 - np.sin(phi))
    wm = brentq(lambda w: K / (w * np.sqrt(1 + w * w)) - 1 / np.sqrt(alpha), 0.1, 100); T = 1 / (wm * np.sqrt(alpha))
    lead_n, lead_d = [alpha * T, 1.0], [T, 1.0]
    n1 = K * np.array(lead_n); d1 = np.polymul(lead_d, g_den)
    m1 = exact_margins(n1, d1)
    p.compare("Lead: new gain crossover lands on ω_m", wm, m1["wgc"], "rad/s", tol=0.5)
    p.compare("Lead: achieved phase margin vs the 50° target", 50.0, m1["pm"], "°", kind="abs", tol=4)
    pred_pm = 180 - 90 - np.degrees(np.arctan(wm)) + np.degrees(phi)
    p.compare("Lead: phase margin predicted from plant phase at ω_m + φ_m", pred_pm, m1["pm"], "°", kind="abs", tol=0.2)
    beta = 10.0; z = m1["wgc"] / 10
    lag_n, lag_d = [1.0, z], [1.0, z / beta]
    n2 = np.polymul(n1, lag_n); d2 = np.polymul(d1, lag_d)
    m2 = exact_margins(n2, d2)
    loss = np.degrees(np.arctan(m2["wgc"] / (z / beta)) - np.arctan(m2["wgc"] / z))
    p.compare("Lag: phase margin lost = arctan(ω/p) − arctan(ω/z) at the crossover", m1["pm"] - loss, m2["pm"], "°", kind="abs", tol=1.5)
    t = np.linspace(0, 12, 12001); res = {}
    for name, (n_, d_) in (("K only", ([K], g_den)), ("lead", (n1, d1)), ("lead + lag", (n2, d2))):
        cl = (n_, np.polyadd(d_, np.pad(n_, (len(d_) - len(n_), 0))))
        res[name] = (signal.lsim(cl, np.ones_like(t), t)[1], cl)
    os0, os1, os2 = (step_info(t, res[k][0], 1.0)["overshoot"] for k in ("K only", "lead", "lead + lag"))
    p.compare("Overshoot drops from ≈ 60 % to ≈ 20 % with the lead (ζ ≈ PM/100 estimate for PM = 50°: 16 %)", 16.3, os1, "%", kind="abs", tol=8)
    p.metric("Overshoot: K only / lead / lead + lag", f"{os0:.1f} % / {os1:.1f} % / {os2:.1f} %")
    tr = np.linspace(0, 400, 200001)
    for name, kv in (("lead", K), ("lead + lag", K * beta)):
        yr = signal.lsim(res[name][1], tr, tr)[1]
        p.compare(f"Ramp-following error with {name}: 1/K_v", 1 / kv, tr[-1] - yr[-1], "", tol=1)
    p.metric("Lead parameters", f"α = {alpha:.2f}, T = {T:.4f} s (zero {1 / (alpha * T):.2f}, pole {1 / T:.2f} rad/s)")
    wb = np.logspace(-1, 2, 4000)
    bw = lambda cl: float(wb[np.argmax(np.abs(signal.freqs(*cl, worN=wb)[1]) < 10 ** (-3 / 20))])
    p.metric("Closed-loop −3 dB bandwidth: K only / lead", f"{bw(res['K only'][1]):.2f} / {bw(res['lead'][1]):.2f}", "rad/s")
    w = np.logspace(-3, 2.5, 800)
    fig, ax = p.fig(1, 2, w=11)
    for (n_, d_), c, lab in ((([K], g_den), COLORS[1], "K·G"), ((n1, d1), C_PRED, "with lead"), ((n2, d2), C_MEAS, "lead + lag")):
        Hh = np.polyval(n_, 1j * w) / np.polyval(d_, 1j * w)
        ax[0].semilogx(w, np.degrees(np.unwrap(np.angle(Hh))), color=c, label=lab)
    ax[0].axhline(-180, color="gray", lw=.6); ax[0].set_ylim(-200, -60)
    style_axes(ax[0], "ω (rad/s)", "loop phase (°)", "Lead lifts the phase near crossover")
    for k, c in (("K only", COLORS[1]), ("lead", C_PRED), ("lead + lag", C_MEAS)):
        ax[1].plot(t, res[k][0], color=c, label=k)
    ax[1].set_xlim(0, 6)
    style_axes(ax[1], "time (s)", "step response", "Closed-loop step responses")
    p.save(fig, "leadlag", "Loop phase before and after compensation, and the corresponding step responses.")
    p.discuss(f"""The textbook procedure works as advertised. The lead network (α = {alpha:.1f}) moves the crossover to its centre frequency and delivers a phase
margin of {m1['pm']:.1f}° against the 50° target — the 8° safety allowance almost exactly pays for the extra plant lag at the higher crossover — and
overshoot falls from {os0:.0f} % to {os1:.0f} %. The lag section then multiplies the low-frequency gain by ten: the ramp error drops from 1/10 to 1/100 exactly,
at a cost of {m1['pm'] - m2['pm']:.1f}° of phase margin, as the design formula predicts. What the Bode procedure hides is visible in the step response: the
lag's slow pole–zero pair raises the overshoot again to {os2:.0f} % and leaves a slow tail — more than the {m1['pm'] - m2['pm']:.0f}° of lost phase margin alone
would suggest, and the price of accuracy bought at low frequency.""")
# tol-convention: relative tolerances are in percent
