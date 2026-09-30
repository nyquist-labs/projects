from eelab import *
from scipy.optimize import brentq, minimize_scalar

META = dict(
    id="SL-032", title="MPPT solar tracker (perturb & observe)", level="H",
    tools="Single-diode PV model (NumPy/SciPy) + averaged boost-converter MPPT loop",
    summary="Model a 60-cell PV panel, locate its maximum power point analytically, then run a "
            "perturb-and-observe tracker through an irradiance ramp and a cloud step and measure how "
            "much energy it captures.",
    problem="A solar panel's power depends on the voltage you hold it at, and the best voltage moves "
            "with sunlight. How close does the simplest MPPT algorithm get to the true optimum?",
    theory=r"""Single-diode model: $I = I_{ph} - I_0\left(e^{(V+IR_s)/(nN_sV_T)}-1\right) - \frac{V+IR_s}{R_{sh}}$, with
$I_{ph}\propto G$ (irradiance). The maximum power point satisfies $dP/dV = 0$ ⇔ $dI/dV = -I/V$; it sits at
≈ 80 % of $V_{oc}$ and moves roughly logarithmically with G. P&O perturbs the operating voltage by ΔV and
keeps the direction if power rose — it oscillates in a ±ΔV band around the MPP, costing ≈ a few ×0.1 %.""",
    method="""Panel: 60 cells, I_sc = 9 A at 1000 W/m², I₀ = 1e-10 A, n = 1.1, R_s = 0.3 Ω, R_sh = 300 Ω, 25 °C.
Predicted MPP by numerically maximising P(V) on the implicit I–V curve (Brent root + scalar optimiser).
Tracker: boost converter averaged model sets V_pv = V_bus(1−D), P&O updates D every 10 ms with ΔD = 0.004,
bus held at 48 V. Irradiance profile over 12 s: ramp 300→1000 W/m², hold, cloud step to 400, recovery.""",
)

q, k = 1.602e-19, 1.381e-23
VT = k * 298.15 / q
NS, I0, NN, RS, RSH = 60, 1e-10, 1.1, 0.3, 300.0


def current(V, G):
    Iph = 9.0 * G / 1000
    f = lambda I: Iph - I0 * (np.exp((V + I * RS) / (NN * NS * VT)) - 1) - (V + I * RS) / RSH - I
    return brentq(f, -40, 20)


def mpp(G):
    voc = brentq(lambda V: current(V, G), 1, 48)
    r = minimize_scalar(lambda V: -V * current(V, G), bounds=(0.5 * voc, voc), method="bounded", options=dict(xatol=1e-6))
    return r.x, -r.fun, voc


def irradiance(t):
    if t < 3:
        return 300 + 700 * t / 3
    if t < 6:
        return 1000.0
    if t < 9:
        return 400.0
    return 400 + 600 * min(1, (t - 9) / 1.0)


def run(p):
    Vs = np.linspace(0, 45, 300)
    fig, ax = p.fig(1, 2)
    for i, G in enumerate([200, 400, 600, 800, 1000]):
        I = np.array([current(v, G) for v in Vs])
        P = Vs * I
        ax[0].plot(Vs, np.clip(I, 0, None), color=COLORS[i], label=f"{G} W/m²")
        ax[1].plot(Vs, np.clip(P, 0, None), color=COLORS[i], label=f"{G} W/m²")
        vm, pm, voc = mpp(G)
        ax[1].plot(vm, pm, "o", color=COLORS[i], ms=6)
        if G in (400, 1000):
            p.metric(f"G = {G}: V_mpp / V_oc", vm / voc, "", f"V_mpp = {vm:.2f} V, P_max = {pm:.1f} W")
    style_axes(ax[0], "V (V)", "I (A)", "I–V curves")
    style_axes(ax[1], "V (V)", "P (W)", "P–V curves with MPPs (dots)")
    p.save(fig, "iv_pv_curves", "The maximum power point shifts with irradiance.")
    # P&O tracker on averaged boost
    dt_ctrl, Vbus = 0.01, 48.0
    t = np.arange(0, 12, dt_ctrl)
    D, dD, Pprev, direction = 0.4, 0.004, 0.0, 1
    Vpv_log, P_log, Pmax_log, Vm_log = [], [], [], []
    for tt in t:
        G = irradiance(tt)
        Vpv = Vbus * (1 - D)
        P = Vpv * current(Vpv, G)
        if P < Pprev:
            direction = -direction
        D = np.clip(D + direction * dD, 0.05, 0.95)   # +D lowers V_pv
        Pprev = P
        vm, pm, _ = mpp(G)
        Vpv_log.append(Vpv); P_log.append(P); Pmax_log.append(pm); Vm_log.append(vm)
    P_log, Pmax_log = np.array(P_log), np.array(Pmax_log)
    eff_total = P_log.sum() / Pmax_log.sum() * 100
    steady = (t > 4) & (t < 6)
    eff_ss = P_log[steady].sum() / Pmax_log[steady].sum() * 100
    band = Vbus * dD
    p.compare("Steady-state tracking efficiency (1000 W/m²)", 100 - 100 * 0.5 * (band / Vm_log[450])**2 * 2, eff_ss, "%", kind="abs",
              note="P&O loss ≈ curvature × (ΔV)² band")
    p.compare("Energy captured over whole profile", 100.0, eff_total, "%", kind="abs")
    vm, pm, voc = mpp(1000)
    p.compare("V_mpp at 1000 W/m² (fractional-V_oc rule 0.8·V_oc)", 0.8 * voc, vm, "V", tol=5)
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    ax[0].plot(t, Pmax_log, "--", color=C_PRED, label="true maximum power")
    ax[0].plot(t, P_log, color=C_MEAS, lw=1, label="P&O tracker")
    style_axes(ax[0], None, "power (W)", "MPPT through a ramp and a cloud step")
    ax[1].plot(t, Vm_log, "--", color=C_PRED, label="V_mpp")
    ax[1].plot(t, Vpv_log, color=C_MEAS, lw=1, label="panel voltage")
    style_axes(ax[1], "time (s)", "V_pv (V)")
    p.save(fig, "tracking", "The tracker hunts in a ±ΔV band around the moving MPP and recovers from the cloud in <1 s.")
    p.csv("tracking", t_s=t, p_tracker_w=P_log, p_max_w=Pmax_log, v_pv=Vpv_log, v_mpp=Vm_log)
    p.discuss(f"""The fractional-V_oc rule of thumb (0.8·V_oc) lands within a few percent of the true MPP. P&O
captures {eff_total:.1f} % of the available energy over the whole profile; the loss comes from the ±ΔV
limit cycle in steady state and from the lag after the cloud step — during a ramp P&O can even
step the wrong way because the power change from irradiance swamps the change from its own
perturbation (the classic P&O drift problem that incremental-conductance and dP-P&O variants fix).""")
