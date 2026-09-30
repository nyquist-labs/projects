from eelab import *
from scipy import signal

META = dict(
    id="AM-098", title="Random walks in integrators: noise that grows without bound", level="M",
    tools="Ensemble simulation of ideal and leaky integrators driven by white noise, variance growth ∝ t, Ornstein–Uhlenbeck saturation at σ²τ/2, drift from input offset",
    summary="Integrate white noise with an ideal op-amp integrator and watch the output variance grow linearly with time (a random walk); add a leak "
            "resistor and see it saturate at σ²τ/2; show that a DC offset makes the mean grow linearly too — the reasons real integrators need reset or feedback.",
    problem="Why does an integrator that is 'perfect' in theory drift away in practice?",
    theory=r"""$\dot v = n(t)$ with white noise of two-sided density σ² ⇒ Var v(t) = σ²t (Wiener process). With a leak, $\dot v = -v/τ + n$ ⇒ Var → σ²τ/2 with time constant τ/2. An input offset V_os into an integrator of gain 1/RC gives a
linear drift V_os·t/RC, which dominates the √t noise after a crossover time. Doubling the time doubles the variance but only multiplies the rms by √2.""",
    method="""Ensemble of 2000 integrators, dt = 1 ms, 20 s. σ² = 1 V²·s⁻¹ (normalised). Leak τ = 2 s. Offset case: V_os/RC = 0.05 V/s. Variance vs time, fitted slopes.""",
)


def run(p):
    r = p.rng; M, dt, T = 2000, 1e-3, 20.0; n = int(T / dt); t = np.arange(1, n + 1) * dt
    w = r.normal(0, np.sqrt(dt), (M, n))
    v = np.cumsum(w, axis=1)
    var = v.var(0)
    p.compare("Ideal integrator: Var(v) / t (= σ² = 1)", 1.0, np.polyfit(t, var, 1)[0], "", tol=5)
    p.compare("rms at 20 s = √20 V", np.sqrt(20), v[:, -1].std(), "V", tol=5)
    tau = 2.0; a = np.exp(-dt / tau)
    vl = signal.lfilter([1.0], [1.0, -a], w, axis=1)
    varl = vl.var(0)
    p.compare("Leaky integrator (τ = 2 s): saturated variance σ²τ/2", tau / 2, varl[-5000:].mean(), "", tol=5)
    k = np.argmax(varl > (1 - np.exp(-1)) * tau / 2)
    p.compare("Leaky integrator: variance approaches saturation with time constant τ/2", tau / 2, t[k], "s", tol=10)
    drift = 0.05
    vo = v + drift * t[None, :]
    t_cross = 1 / drift ** 2
    p.compare("With offset: ensemble-mean drift slope = V_os/RC (the mean of 2000 walks itself wanders ~√t/√2000 ≈ 0.1 V)", drift, np.polyfit(t, vo.mean(0), 1)[0], "V/s", tol=30)
    p.metric("Time after which offset drift exceeds the noise rms (σ√t = V_os t/RC → t = σ²/(V_os/RC)²)", t_cross, "s", "beyond this run's 20 s")
    fig, ax = p.fig(1, 2, w=11)
    for i in range(30):
        ax[0].plot(t, v[i], lw=.5, color=COLORS[7])
    ax[0].plot(t, 2 * np.sqrt(t), color=C_PRED, label="±2√t"); ax[0].plot(t, -2 * np.sqrt(t), color=C_PRED)
    style_axes(ax[0], "t (s)", "v (V)", "Ideal integrator: 30 random walks")
    ax[1].plot(t, var, color=C_MEAS, label="ideal: Var ∝ t"); ax[1].plot(t, varl, color=COLORS[2], label="leaky τ = 2 s"); ax[1].axhline(tau / 2, color=C_PRED, ls="--", label="σ²τ/2")
    style_axes(ax[1], "t (s)", "ensemble variance (V²)", "A leak bounds the variance")
    p.save(fig, "random_walk", "Random walks from integrated white noise, and ensemble variance with and without a leak.")
    p.discuss("""Integrated white noise is a random walk: the ensemble variance grows exactly linearly (slope σ²), so the output wanders without bound even though
its average is zero — any single integrator will eventually hit its supply rails. A leak resistor turns it into an Ornstein–Uhlenbeck process whose
variance saturates at σ²τ/2 with time constant τ/2, at the price of forgetting the input on the time scale τ. Offsets are worse than noise over long
times because they grow linearly rather than as √t. This is why practical integrators are reset periodically (switched-capacitor, charge
amplifiers) or placed inside a feedback loop (PLL loop filters, PI controllers) that keeps their output bounded.""")
# tol-convention: relative tolerances are in percent
