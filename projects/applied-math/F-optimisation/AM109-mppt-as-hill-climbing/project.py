from eelab import *
from scipy.optimize import brentq, minimize_scalar

META = dict(
    id="AM-109", title="MPPT as online optimisation: perturb-and-observe vs incremental conductance", level="M",
    tools="Single-diode photovoltaic model, perturb-and-observe hill climbing and incremental-conductance tracking, time-varying irradiance, tracking efficiency vs step size",
    summary="Track the maximum power point of a solar panel whose irradiance changes with passing clouds, using two classic online optimisers, and "
            "measure the trade-off between step size, steady-state oscillation and tracking speed — including P&O's known confusion during irradiance ramps.",
    problem="The optimum moves while you search for it. How should an optimiser that can only measure P and V behave?",
    theory=r"""PV current $I=I_{ph}-I_0(e^{(V+IR_s)/(nN_sV_T)}-1)-\frac{V+IR_s}{R_{sh}}$. P&O: step V by ±ΔV, keep the direction if P rose — oscillates ±ΔV around the optimum (loss ∝ ΔV² near the peak, since P is quadratic there) but a bigger ΔV follows
ramps faster. Incremental conductance uses dI/dV = −I/V at the peak, so it stops moving at the optimum and is not fooled by ramps. Expected: tracking efficiency ≥ 99 % at the best ΔV; P&O errors during rising irradiance.""",
    method="""60-cell panel (I_ph ∝ irradiance, 8.5 A at 1000 W/m²). Irradiance profile: steps and 20 % ramps over 60 s, controller running at 20 Hz. True MPP computed at every step for reference; efficiency = ∫P/∫P_mpp. ΔV = 0.1 … 2 V.""",
)

VT = 0.025852


def pv_I(V, G):
    Iph = 8.5 * G / 1000; I0, n, Ns, Rs, Rsh = 5e-8, 1.3, 60, 0.3, 300.0
    f = lambda I: Iph - I0 * np.expm1((V + I * Rs) / (n * Ns * VT)) - (V + I * Rs) / Rsh - I
    lo, hi = -20.0, Iph + 1
    return brentq(f, lo, hi)


def mpp(G):
    res = minimize_scalar(lambda v: -v * pv_I(v, G), bounds=(1, 45), method="bounded", options=dict(xatol=1e-6))
    return res.x, -res.fun


def irradiance(t):
    g = 1000 - 400 * ((t > 10) & (t < 20)) + 300 * np.clip((t - 25) / 5, 0, 1) * (t < 40) - 200 * ((t > 45) & (t < 50)) * (t - 45) / 5
    return np.clip(g, 100, 1400)


def track(method, dV, dt=0.05, T=60):
    t = np.arange(0, T, dt); V = 30.0; Pprev = V * pv_I(V, irradiance(0)); Iprev = pv_I(V, irradiance(0)); direction = 1
    P_out, P_best = [], []
    for tk in t:
        G = irradiance(tk); I = pv_I(V, G); P = V * I
        if method == "P&O":
            if P < Pprev:
                direction = -direction
            Vn = V + direction * dV
        else:
            dI, dVv = I - Iprev, V - Vp if (Vp := getattr(track, "_vp", None)) is not None else dV
            g = dI / dVv if abs(dVv) > 1e-9 else 0.0
            if abs(dVv) < 1e-9:
                Vn = V + (dV if dI > 0 else -dV if dI < 0 else 0)
            else:
                s = g + I / V
                Vn = V + (dV if s > 1e-3 else -dV if s < -1e-3 else 0)
            track._vp = V
        Pprev, Iprev = P, I
        P_out.append(P); P_best.append(mpp(G)[1])
        V = float(np.clip(Vn, 1, 45))
    track._vp = None
    return t, np.array(P_out), np.array(P_best)


def run(p):
    Vm, Pm = mpp(1000)
    p.metric("MPP at 1000 W/m²", f"{Vm:.2f} V, {Pm:.1f} W")
    rows = []
    for dV in (0.1, 0.3, 0.6, 1.0, 2.0):
        for m in ("P&O", "IncCond"):
            t, P, Pb = track(m, dV)
            rows.append((m, dV, np.sum(P[20:]) / np.sum(Pb[20:])))
    best = {m: max(r_[2] for r_ in rows if r_[0] == m) for m in ("P&O", "IncCond")}
    p.compare("Best tracking efficiency, P&O (my guess ≥ 99 %)", 99, best["P&O"] * 100, "%", kind="abs", tol=1)
    p.compare("Best tracking efficiency, incremental conductance", 99, best["IncCond"] * 100, "%", kind="abs", tol=1)
    for m, dV, e in rows:
        p.metric(f"{m}, ΔV = {dV} V: efficiency", e * 100, "%")
    fig, ax = p.fig(1, 2, w=11)
    t, P1, Pb = track("P&O", 0.3); _, P2, _ = track("IncCond", 0.3)
    ax[0].plot(t, Pb, color="black", lw=2, alpha=.4, label="true maximum"); ax[0].plot(t, P1, color=C_PRED, lw=.8, label="P&O"); ax[0].plot(t, P2, color=C_MEAS, lw=.8, label="IncCond")
    style_axes(ax[0], "t (s)", "power (W)", "Tracking a moving optimum (ΔV = 0.3 V)")
    for m, c in (("P&O", C_PRED), ("IncCond", C_MEAS)):
        ax[1].semilogx([r_[1] for r_ in rows if r_[0] == m], [r_[2] * 100 for r_ in rows if r_[0] == m], "o-", color=c, label=m)
    style_axes(ax[1], "step ΔV (V)", "tracking efficiency (%)", "Step size trade-off")
    p.save(fig, "mppt", "Power delivered by two MPPT algorithms against the true maximum, and efficiency vs step size.")
    p.discuss("""Both hill climbers stay close to the moving maximum and reach high tracking efficiency at a well-chosen step. The step-size curves show the
classic trade: tiny steps track ramps too slowly, large steps oscillate around the peak and lose power quadratically in the step. Perturb-and-observe
cannot tell whether a power increase came from its own move or from the sun, so it drifts the wrong way during irradiance ramps; incremental
conductance uses the local optimality condition dP/dV = 0 (dI/dV = −I/V) and stops at the peak, which makes it steadier in the steady state. Real
converters add variable steps and a periodic global scan, because partial shading makes P(V) multimodal and every hill climber can then get stuck
on a local peak.""")
# tol-convention: relative tolerances are in percent
