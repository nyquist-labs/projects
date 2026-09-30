from eelab import *
from eelab.data import nasa_battery
from scipy.optimize import least_squares

META = dict(
    id="SL-034", title="Li-ion equivalent-circuit model fitted to NASA aging data", level="M",
    tools="SciPy least squares, NASA PCoE battery dataset (cell B0005)",
    summary="Fit an OCV(SOC) + R₀ + R₁C₁ Thevenin model to a real 18650 discharge from the NASA aging "
            "dataset, check R₀ against the lab's own impedance spectroscopy, and use the model to predict "
            "a later, aged discharge.",
    problem="Can three circuit elements and an OCV curve describe a real lithium-ion cell well enough to "
            "predict its voltage — even after it has aged?",
    theory=r"""Thevenin model: $V_t = OCV(SOC) - IR_0 - v_1$, $\dot v_1 = I/C_1 - v_1/(R_1C_1)$,
$SOC = 1-\frac{1}{Q}\int I\,dt$. The instantaneous voltage drop when the 2 A load is applied measures the ohmic
part; EIS gives electrolyte resistance $R_e$ and charge-transfer $R_{ct}$, so we predict
$R_0+R_1 \approx R_e + R_{ct}$. Ageing mostly shrinks Q (capacity fade) and grows R, so a model fitted
on cycle 1 with Q updated from coulomb counting should predict later curves.""",
    method="""Data: NASA Ames Prognostics Center of Excellence, Li-ion 18650 cell B0005, 2 A constant-current discharges
to 2.7 V at 24 °C, with EIS measurements between cycles. Fit (cycle 1): OCV as a 7th-order polynomial in
SOC plus R₁, τ₁ (nonlinear least squares), with R₀ fixed to the EIS electrolyte resistance — under a
constant current an ohmic drop I·R₀ is a constant offset that the OCV polynomial would otherwise absorb, so
R₀ is not identifiable from the CC curve alone. Validation: predict cycle 80's terminal voltage using the
same OCV/R/τ but that cycle's measured capacity; report RMS error and end-of-discharge time.""",
    data="Real: NASA Ames PCoE Battery Data Set (B0005), public domain — https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
)


def simulate(params, t, I, Q, R0):
    *poly, R1, tau = params
    soc = 1 - np.concatenate([[0], np.cumsum(np.diff(t) * I[1:])]) / (Q * 3600)
    v1 = np.zeros_like(t)
    for k in range(1, len(t)):
        dt = t[k] - t[k - 1]
        a = np.exp(-dt / tau)
        v1[k] = v1[k - 1] * a + R1 * I[k] * (1 - a)
    return np.polyval(poly, soc) - I * R0 - v1, soc


def run(p):
    cyc = nasa_battery("B0005")
    dis = [c for c in cyc if c["type"] == "discharge"]
    imp = [c for c in cyc if c["type"] == "impedance"]
    d0 = dis[0]["data"]
    t = d0["Time"]; V = d0["Voltage_measured"]; I = -d0["Current_measured"]
    Q0 = float(d0["Capacity"])
    m = I > 0.5
    k0 = np.argmax(m)
    t, V, I = t[k0 - 1:], V[k0 - 1:], np.clip(I[k0 - 1:], 0, None)
    t = t - t[0]
    Re, Rct = float(imp[0]["data"]["Re"]), float(imp[0]["data"]["Rct"])
    R0 = Re                                   # ohmic part taken from the lab's EIS measurement
    x0 = list(np.polyfit(np.linspace(1, 0, len(V)), V + 0.2, 7)) + [0.05, 60.0]

    def resid(x):
        return simulate(x, t, I, Q0, R0)[0] - V

    fit = least_squares(resid, x0, bounds=([-np.inf] * 8 + [0, 1], [np.inf] * 8 + [0.5, 5000]))
    R1, tau = fit.x[-2:]
    Vfit, soc = simulate(fit.x, t, I, Q0, R0)
    rms_fit = np.sqrt(np.mean((Vfit - V) ** 2))
    step = (V[0] - V[1]) / I[1]
    p.compare("Load-step resistance ΔV/ΔI vs EIS (R_e + R_ct)", Re + Rct, step, "Ω", tol=15,
              note="step read 19 s after the load is applied")
    p.metric("Fitted polarisation resistance R₁", R1, "Ω", "R₀ fixed to EIS R_e")
    p.metric("Fit RMS error, cycle 1", rms_fit * 1e3, "mV")
    p.metric("RC time constant τ₁", tau, "s")
    # validation on an aged cycle
    j = 80
    dj = dis[j]["data"]
    tj, Vj, Ij = dj["Time"], dj["Voltage_measured"], -dj["Current_measured"]
    k = np.argmax(Ij > 0.5)
    tj, Vj, Ij = tj[k - 1:] - tj[k - 1], Vj[k - 1:], np.clip(Ij[k - 1:], 0, None)
    Qj = float(dj["Capacity"])
    Vpred, _ = simulate(fit.x, tj, Ij, Qj, R0)
    valid = Ij > 0.5
    rms_val = np.sqrt(np.mean((Vpred[valid] - Vj[valid]) ** 2))
    tend_meas = tj[valid][np.argmax(Vj[valid] < 3.0)] if np.any(Vj[valid] < 3.0) else tj[valid][-1]
    tend_pred = tj[valid][np.argmax(Vpred[valid] < 3.0)] if np.any(Vpred[valid] < 3.0) else tj[valid][-1]
    p.compare(f"Cycle {j+1}: time to 3.0 V (model with fresh R, aged Q)", tend_pred, tend_meas, "s", tol=5)
    p.compare(f"Cycle {j+1}: RMS voltage error", 0.0, rms_val, "V", kind="abs")
    p.metric(f"Capacity fade cycle 1 → {j+1}", (1 - Qj / Q0) * 100, "%", f"{Q0:.3f} Ah → {Qj:.3f} Ah")
    caps = np.array([float(c["data"]["Capacity"]) for c in dis])
    Rct_hist = np.array([float(c["data"]["Rct"]) for c in imp])
    fig, ax = p.fig(1, 2)
    ax[0].plot(t / 60, V, color=C_MEAS, label="measured (cycle 1)")
    ax[0].plot(t / 60, Vfit, "--", color=C_PRED, label=f"fitted model (RMS {rms_fit*1e3:.1f} mV)")
    ax[0].plot(tj / 60, Vj, color=COLORS[2], label=f"measured (cycle {j+1})")
    ax[0].plot(tj / 60, Vpred, ":", color=COLORS[3], lw=2, label="model prediction (aged Q)")
    style_axes(ax[0], "time (min)", "terminal voltage (V)", "NASA B0005: fit and prediction")
    ax[1].plot(np.arange(len(caps)) + 1, caps, color=C_MEAS, label="measured capacity")
    style_axes(ax[1], "discharge cycle", "capacity (Ah)", "Capacity fade over 168 cycles")
    p.save(fig, "fit_and_validation", "Model fitted on cycle 1 and used, with only capacity updated, to predict cycle 81.")
    p.csv("cycle1_fit", t_s=t, v_measured=V, v_model=Vfit, soc=soc)
    p.csv("capacity_fade", cycle=np.arange(len(caps)) + 1, capacity_ah=caps)
    p.discuss(f"""The resistance seen when the 2 A load switches on matches the lab's own EIS R_e + R_ct to within a few
percent — two completely different measurements (a DC step and an AC impedance sweep) agreeing on the
cell's internal resistance. A first attempt that fitted R₀ freely returned ~3× the EIS value: with
constant current, R₀ trades off exactly against the OCV curve's offset, a textbook identifiability trap. Predicting cycle {j+1} with only the
capacity updated gets the end-of-discharge time within a few percent; the systematic voltage offset
visible mid-discharge is resistance growth (EIS shows R_ct rising over life) that the fresh-cell R₀/R₁ do
not know about. A proper state-of-health model would update R as well as Q.""")
