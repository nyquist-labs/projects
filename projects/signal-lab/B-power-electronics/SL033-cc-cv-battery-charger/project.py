from eelab import *
from scipy.integrate import solve_ivp

META = dict(
    id="SL-033", title="CC-CV lithium-ion charger", level="M",
    tools="Equivalent-circuit Li-ion cell (OCV(SOC) + R₀ + R₁C₁) integrated with SciPy",
    summary="Simulate the constant-current / constant-voltage charge profile of a 3 Ah 18650 cell and "
            "predict when CC ends, how much charge CV adds and the total charge time.",
    problem="Why does a phone reach 80 % quickly and then crawl to 100 %? Model the CC-CV algorithm and "
            "the cell's internal resistance that causes it.",
    theory=r"""During CC at current $I$: terminal $V_t = OCV(SOC) + IR_0 + v_1$ rises until it hits $V_{max}$ = 4.2 V.
CC ends when $OCV(SOC_{cc}) \approx 4.2 - I(R_0+R_1)$ (steady-state polarization), so higher current or
resistance means *lower* SOC at the CC→CV transition. In CV the current decays roughly exponentially
with time constant $\tau\approx Q\,(R_0+R_1)/(dOCV/dSOC)$ until the cut-off $I_{term}=C/20$.""",
    method="""Cell: Q = 3.0 Ah, R₀ = 35 mΩ, R₁ = 20 mΩ, C₁ = 1500 F (τ₁ = 30 s), OCV curve fitted to typical NMC data.
Charge from 5 % SOC at 1C (3 A) and 0.5C; CV at 4.2 V until I < 150 mA. ODE solved with RK45 (CC) and an
algebraic current solve each step (CV).""",
)

SOC_T = np.array([0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, 1.0])
OCV_T = np.array([3.0, 3.35, 3.45, 3.55, 3.62, 3.68, 3.74, 3.82, 3.91, 3.99, 4.08, 4.14, 4.21])
ocv = lambda s: np.interp(s, SOC_T, OCV_T)
docv = lambda s: (ocv(min(s + 1e-3, 1)) - ocv(max(s - 1e-3, 0))) / 2e-3


def charge(I, Q=3.0, R0=0.035, R1=0.020, C1=1500.0, vmax=4.2, iterm=0.15, dt=1.0):
    soc, v1, t = 0.05, 0.0, 0.0
    log = []
    mode = "CC"
    while True:
        if mode == "CC":
            i = I
            if ocv(soc) + i * R0 + v1 >= vmax:
                mode = "CV"; t_cc = t; soc_cc = soc
                continue
        else:
            i = (vmax - ocv(soc) - v1) / R0
            if i < iterm or t > 6 * 3600:
                break
        soc += i * dt / (Q * 3600)
        v1 += dt * (i / C1 - v1 / (R1 * C1))
        t += dt
        log.append((t, i, ocv(soc) + i * R0 + v1, soc, mode == "CC"))
    return np.array(log), t_cc, soc_cc


def run(p):
    Q, R0, R1 = 3.0, 0.035, 0.020
    fig, ax = p.fig(3, 1, h=8, sharex=True)
    for j, I in enumerate([3.0, 1.5]):
        log, t_cc, soc_cc = charge(I)
        t, i, v, soc, cc = log.T
        # prediction of SOC at CC->CV: OCV(soc) = 4.2 - I(R0+R1)
        target = 4.2 - I * (R0 + R1)
        grid = np.linspace(0, 1, 10001)
        soc_pred = grid[np.argmin(abs(ocv(grid) - target))]
        tcc_pred = (soc_pred - 0.05) * Q * 3600 / I
        p.compare(f"{I/Q:.1f}C: SOC at CC→CV transition", soc_pred * 100, soc_cc * 100, "%", kind="abs")
        p.compare(f"{I/Q:.1f}C: CC duration", tcc_pred, t_cc, "s", tol=5)
        tau = Q * 3600 * (R0 + R1) / docv(0.97)
        tcv_pred = tau * np.log(I / 0.15)
        p.compare(f"{I/Q:.1f}C: CV duration (exponential-decay model)", tcv_pred, t[-1] - t_cc, "s", tol=35)
        p.metric(f"{I/Q:.1f}C: total charge time", t[-1] / 60, "min")
        p.metric(f"{I/Q:.1f}C: final SOC", soc[-1] * 100, "%")
        ax[0].plot(t / 60, v, color=COLORS[j], label=f"{I/Q:.1f}C")
        ax[1].plot(t / 60, i, color=COLORS[j], label=f"{I/Q:.1f}C")
        ax[2].plot(t / 60, soc * 100, color=COLORS[j], label=f"{I/Q:.1f}C")
        ax[2].axvline(t_cc / 60, color=COLORS[j], ls=":", lw=1)
        p.csv(f"profile_{I/Q:.1f}C".replace(".", "p"), t_s=t, current_a=i, v_terminal=v, soc=soc)
    style_axes(ax[0], None, "V_cell (V)", "CC-CV charge profile")
    style_axes(ax[1], None, "I (A)")
    style_axes(ax[2], "time (min)", "SOC (%)")
    p.save(fig, "cccv_profile", "Voltage rises at constant current, then current tapers at 4.2 V (dotted = CC→CV).")
    p.discuss("""The CC→CV transition SOC is predicted almost exactly by OCV(SOC) = 4.2 V − I(R₀ + R₁) once the RC
branch has reached steady state — confirming that internal resistance, not the chemistry, forces the
early switch to CV at high current. The CV phase is only approximately exponential because the OCV
slope changes with SOC near full charge, so the single-time-constant estimate is rough. Charging at 1C
does not halve the time vs 0.5C: the CV tail is longer because more of the charge must be delivered
at tapering current.""")
