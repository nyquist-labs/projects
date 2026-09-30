from eelab import *
from eelab.control import zoh

META = dict(
    id="SL-160", title="Cruise control: rejecting a hill with PI feedback", level="M",
    tools="Nonlinear car longitudinal model (aerodynamic drag, rolling resistance, grade), PI controller with saturation",
    summary="Hold 25 m/s through a 5 % climb: predict the steady-state throttle, the speed dip for P-only and PI control from the "
            "linearised disturbance transfer function, and measure them on the nonlinear model.",
    problem="A hill is a disturbance the driver can't see coming. How much speed does cruise control lose, and why does it need "
            "integral action?",
    theory=r"""m·dv/dt = F − ½ρC_dAv² − C_r m g − m g sin θ. Linearised at v₀: time constant τ = m/(ρC_dAv₀). A grade adds a force m g sinθ ≈ 490 N·… With P control of gain K_p
(N per m/s) the steady-state speed error is $\Delta F_{hill}/(K_p+\rho C_dAv_0)$; PI removes it, with a transient dip ≈ that error scaled by the loop damping.""",
    method="""m = 1,000 kg, ρC_dA = 0.84 kg/m (C_d·A = 0.7 m²), C_r = 0.01, v₀ = 25 m/s, force limit 0–5,000 N. Hill of 5 % from t = 20 s to 80 s. P: K_p = 500 N/(m/s);
PI: K_p = 500, K_i = 100. 10 ms steps.""",
)


def run(p):
    m, rCA, Cr, g, v0 = 1000.0, 0.84, 0.01, 9.81, 25.0
    F0 = 0.5 * rCA * v0**2 + Cr * m * g
    p.compare("Cruise force on the flat (½ρC_dAv² + C_r mg)", 0.5 * rCA * v0**2 + Cr * m * g, F0, "N", tol=0.1)
    dt = 0.01; T = 120
    res = {}
    for nm, (Kp, Ki) in {"P": (500, 0), "PI": (500, 100)}.items():
        v = v0; I = 0.0; vs = []
        for k in range(int(T / dt)):
            t = k * dt
            th = np.arctan(0.05) if 20 <= t < 80 else 0.0
            e = v0 - v
            I += e * dt
            F = np.clip(F0 + Kp * e + Ki * I, 0, 5000)
            dv = (F - 0.5 * rCA * v * v - Cr * m * g * np.cos(th) - m * g * np.sin(th)) / m
            v += dv * dt; vs.append(v)
        res[nm] = np.array(vs)
    t = np.arange(len(res["P"])) * dt
    dF = m * g * np.sin(np.arctan(0.05)) - Cr * m * g * (1 - np.cos(np.arctan(0.05)))
    kd = rCA * v0
    p.compare("P control: steady speed loss on the hill ΔF/(K_p + ρC_dAv₀)", dF / (500 + kd), v0 - res["P"][int(75 / dt)], "m/s", tol=5)
    p.compare("PI control: steady speed error on the hill", 0, v0 - res["PI"][int(75 / dt)], "m/s", kind="abs")
    p.metric("PI control: maximum speed dip", v0 - res["PI"].min(), "m/s")
    fig, ax = p.fig()
    ax.plot(t, res["P"] * 3.6, color=COLORS[1], label="P only"); ax.plot(t, res["PI"] * 3.6, color=C_MEAS, label="PI")
    ax.axvspan(20, 80, color="gray", alpha=.1, label="5 % grade")
    ax.axhline(v0 * 3.6, color="gray", ls=":")
    style_axes(ax, "time (s)", "speed (km/h)", "Cruise control through a hill")
    p.save(fig, "cruise", "P control settles to a lower speed on the hill; PI recovers the set speed.")
    p.discuss("""P-only control loses exactly the speed predicted by the linearised force balance, because a constant extra force (the hill) needs a
constant error to produce it. The integral term accumulates that error until it supplies the extra ~490 N itself, so PI returns to
25 m/s; the price is a transient dip and a small overshoot when the car crests the hill. Real cruise controllers add feed-forward from
an inclination sensor or map data to shrink the dip.""")
