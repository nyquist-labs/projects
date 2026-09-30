from eelab import *

META = dict(
    id="SL-035", title="MOSFET loss & junction-temperature model", level="M",
    tools="Loss equations + electro-thermal fixed point + Foster thermal network transient (NumPy)",
    summary="Estimate conduction and switching losses of a buck-converter MOSFET vs frequency, solve the "
            "self-consistent junction temperature (R_ds(on) rises with T) and check it with a thermal "
            "transient.",
    problem="How hot will the switch get? Losses raise temperature, and temperature raises R_ds(on) and "
            "therefore losses — find where this loop settles, or whether it runs away.",
    theory=r"""Conduction: $P_{cond}=I_{rms}^2R_{ds}(T_j)$, $R_{ds}(T)=R_{25}(1+\alpha(T-25))$ with α ≈ 0.6 %/K.
Switching: $P_{sw}=\tfrac12V_{in}I(t_r+t_f)f_{sw}+\tfrac12C_{oss}V_{in}^2f_{sw}$.
Thermal: $T_j = T_a + R_{\theta JA}\,P(T_j)$ — a fixed point that exists iff $R_{\theta JA}\,\partial P/\partial T<1$,
giving the closed form $T_j=\frac{T_a+R_\theta(P_0 - P_{c25}\alpha\cdot25)}{1-R_\theta P_{c25}\alpha}$ (linear in T).""",
    method="""Buck: 24 V → 12 V, 10 A, D = 0.5. MOSFET: R_ds25 = 8 mΩ, t_r = t_f = 15 ns, C_oss = 600 pF. R_θJA = 25 K/W
(small PCB copper), T_a = 40 °C. Closed-form prediction vs iterative solve vs a 3-stage Foster network
(τ = 1 ms, 50 ms, 5 s) integrated in time to steady state. Frequency sweep 50 kHz–1 MHz.""",
)


def losses(Tj, fsw, I=10.0, Vin=24.0, D=0.5, R25=8e-3, alpha=0.006, tr=15e-9, coss=600e-12):
    Irms2 = I * I * D
    pc = Irms2 * R25 * (1 + alpha * (Tj - 25))
    ps = 0.5 * Vin * I * 2 * tr * fsw + 0.5 * coss * Vin**2 * fsw
    return pc, ps


def run(p):
    Rth, Ta, alpha = 25.0, 40.0, 0.006
    freqs = np.array([50e3, 100e3, 200e3, 300e3, 500e3, 750e3, 1e6])
    Tpred, Titer, Ttran = [], [], []
    for f in freqs:
        pc25, ps = losses(25, f)
        Pc_slope = pc25 * alpha
        P0 = pc25 - Pc_slope * 25 + ps
        denom = 1 - Rth * Pc_slope
        Tp = (Ta + Rth * P0) / denom if denom > 0 else np.inf
        Tj = Ta
        for _ in range(500):
            pc, ps = losses(Tj, f)
            Tn = Ta + Rth * (pc + ps)
            if abs(Tn - Tj) < 1e-9 or Tn > 1000:
                break
            Tj = Tn
        Tpred.append(Tp); Titer.append(Tj)
        # Foster network transient
        Rs, taus = np.array([2.0, 8.0, 15.0]), np.array([1e-3, 50e-3, 5.0])
        th = np.zeros(3); dt = 1e-3
        hist = []
        for n in range(int(40 / dt)):
            T = Ta + th.sum()
            pc, ps = losses(T, f)
            P = pc + ps
            th += dt * (P * Rs - th) / taus
            if n % 100 == 0:
                hist.append(T)
        Ttran.append(Ta + th.sum())
        if f == 300e3:
            hist300 = np.array(hist)
    for f, a, b, c in zip(freqs, Tpred, Titer, Ttran):
        if f in (100e3, 500e3, 1e6):
            p.compare(f"T_j at {f/1e3:g} kHz: closed form vs Foster transient", a, c, "°C", tol=1)
    p.metric("Iterative fixed point = closed form", max(abs(np.array(Tpred) - np.array(Titer))), "°C", "max difference")
    pcs = np.array([losses(T, f)[0] for T, f in zip(Titer, freqs)]); pss = np.array([losses(25, f)[1] for f in freqs])
    fmax = freqs[np.argmax(np.array(Titer) > 125)] if np.any(np.array(Titer) > 125) else np.nan
    p.metric("Highest frequency keeping T_j < 125 °C", float(np.interp(125, Titer, freqs)), "Hz")
    fig, ax = p.fig(1, 2)
    ax[0].plot(freqs / 1e3, pcs, "o-", color=COLORS[0], label="conduction")
    ax[0].plot(freqs / 1e3, pss, "o-", color=COLORS[1], label="switching")
    style_axes(ax[0], "f_sw (kHz)", "loss (W)", "Loss breakdown")
    ax[1].plot(freqs / 1e3, Tpred, "--", color=C_PRED, label="closed-form fixed point")
    ax[1].plot(freqs / 1e3, Ttran, "o", color=C_MEAS, label="Foster-network transient")
    ax[1].axhline(125, color=COLORS[7], lw=1, ls=":", label="125 °C limit")
    style_axes(ax[1], "f_sw (kHz)", "T_j (°C)", "Junction temperature")
    p.save(fig, "loss_temperature", "Switching loss grows linearly with frequency and dominates above ~150 kHz.")
    fig, ax = p.fig()
    ax.plot(np.arange(len(hist300)) * 0.1, hist300, color=C_MEAS, label="T_j(t), 300 kHz")
    ax.axhline(Tpred[3], ls="--", color=C_PRED, label="predicted steady state")
    style_axes(ax, "time (s)", "T_j (°C)", "Thermal transient (three time constants)")
    p.save(fig, "transient", "Fast die heating, then the slower board and ambient time constants.")
    p.csv("sweep", fsw_hz=freqs, tj_closed_form=Tpred, tj_iterative=Titer, tj_transient=Ttran, p_cond_w=pcs, p_sw_w=pss)
    p.discuss("""Because R_ds(on) rises linearly with temperature the electro-thermal loop is linear and has an
exact closed-form fixed point; the transient simulation converges to it (differences are only the
finite 40 s simulation window against the 5 s slowest time constant). The loop gain R_θ·∂P/∂T here is
small (≈ 0.006), far from the thermal-runaway condition of 1, but the frequency sweep shows the real
design constraint: switching loss scales with f_sw and pushes T_j past 125 °C well before 1 MHz.""")
