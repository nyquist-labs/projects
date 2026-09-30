from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-036", title="Gate resistance vs switching loss and EMI", level="H",
    tools="eelab mini-SPICE (square-law MOSFET with C_gs and Miller C_gd, clamped inductive load)",
    summary="Turn on a MOSFET into a 5 A clamped inductive load with gate resistors from 2 Ω to 47 Ω; "
            "measure turn-on energy and drain dV/dt, and predict both from the Miller plateau.",
    problem="A bigger gate resistor slows switching edges (less EMI) but costs energy. Quantify the "
            "trade-off with the gate-charge model.",
    theory=r"""During the current rise the gate charges C_gs from $V_{th}$ to the Miller plateau
$V_{pl}=V_{th}+\sqrt{2I_L/K}$; during the voltage fall the gate is stuck at $V_{pl}$ and the drive current
$(V_{drv}-V_{pl})/R_g$ discharges $C_{gd}$:
$$t_{fv}=\frac{R_gC_{gd}V_{DD}}{V_{drv}-V_{pl}},\qquad \frac{dV}{dt}=\frac{V_{drv}-V_{pl}}{R_gC_{gd}}$$
$E_{on}\approx\tfrac12V_{DD}I_L(t_{ri}+t_{fv})$ with $t_{ri}\approx R_g(C_{gs}+C_{gd})\ln\frac{V_{drv}-V_{th}}{V_{drv}-V_{pl}}$.""",
    method="""V_DD = 48 V, I_L = 5 A (ideal current source through a freewheeling diode to V_DD), gate drive 0→12 V step.
MOSFET: K = 20 A/V², V_th = 3 V, C_gs = 1 nF, C_gd = 100 pF. R_g ∈ {2, 5, 10, 22, 47} Ω. 400 ns transient at
20 ps steps; E_on = ∫v_DS·i_D dt over the edge, dV/dt = max slope of v_DS.""",
)


def run(p):
    Vdd, IL, K, Vth, Cgs, Cgd, Vdrv = 48.0, 5.0, 20.0, 3.0, 1e-9, 100e-12, 12.0
    Vpl = Vth + np.sqrt(2 * IL / K)
    Rgs = [2, 5, 10, 22, 47]
    res = []
    for Rg in Rgs:
        ck = Circuit(f"gate Rg={Rg}")
        ck.V("dd", "vdd", "0", dc=Vdd)
        ck.V("g", "drv", "0", wave=lambda t: Vdrv if t > 5e-9 else 0.0)
        ck.R("g", "drv", "g", Rg)
        ck.M("1", "d", "g", "0", pol="n", K=K, VT0=Vth, LAMBDA=0.0, NSUB=1.3, Cgs=Cgs, Cgd=Cgd)
        ck.I("L", "vdd", "d", dc=IL)                   # load current into the drain node
        ck.D("fw", "d", "vdd", Is=1e-9, N=1.2)        # freewheel diode clamps drain at V_DD
        if Rg == 10:
            p.write("simulation/gate_drive.cir", ck.to_spice(), "SPICE netlist (R_g = 10 Ω)")
        T = 60e-9 + 12 * Rg * (Cgs + Cgd) + 3 * Rg * Cgd * Vdd / (Vdrv - Vpl)
        dt = T / 6000
        tr = ck.tran(T, dt, method="trap", ic={"d": Vdd + 0.5})
        t, vd, vg = tr.t, tr.v("d"), tr.v("g")
        idr = np.array([0.0])
        # drain current = load current minus diode current: compute from device law
        vgs = vg; u = (vgs - Vth) / (1.3 * 0.025852); vov = 1.3 * 0.025852 * np.logaddexp(0, u)
        id_ = np.where(vd < vov, K * (vov * vd - 0.5 * vd * vd), 0.5 * K * vov**2)
        id_ = np.minimum(id_, IL + 5)
        Eon = np.trapezoid(vd * id_, t)
        dvdt = -np.min(np.gradient(vd, t))
        tfv_pred = Rg * Cgd * Vdd / (Vdrv - Vpl)
        tri_pred = Rg * (Cgs + Cgd) * np.log((Vdrv - Vth) / (Vdrv - Vpl))
        E_pred = 0.5 * Vdd * IL * (tri_pred + tfv_pred)
        dvdt_pred = (Vdrv - Vpl) / (Rg * Cgd)
        res.append((Rg, Eon, E_pred, dvdt, dvdt_pred))
        p.compare(f"R_g = {Rg} Ω: drain dV/dt", dvdt_pred, dvdt, "V/s", tol=15)
        p.compare(f"R_g = {Rg} Ω: turn-on energy E_on", E_pred, Eon, "J", tol=25)
        if Rg == 10:
            wave = (t, vd, vg, id_)
    p.metric("Miller plateau voltage", Vpl, "V", "V_th + √(2I/K)")
    Rg_, E, Ep, dv, dvp = map(np.array, zip(*res))
    fig, ax = p.fig(1, 2)
    ax[0].loglog(Rg_, Ep * 1e6, "--", color=C_PRED, label="gate-charge model"); ax[0].loglog(Rg_, E * 1e6, "o", color=C_MEAS, label="simulated")
    style_axes(ax[0], "R_g (Ω)", "E_on (µJ)", "Turn-on loss")
    ax[1].loglog(Rg_, dvp / 1e9, "--", color=C_PRED, label="(V_drv−V_pl)/(R_g·C_gd)"); ax[1].loglog(Rg_, dv / 1e9, "o", color=C_MEAS, label="simulated")
    style_axes(ax[1], "R_g (Ω)", "dV/dt (V/ns)", "Edge rate (EMI proxy)")
    p.save(fig, "tradeoff", "Loss rises ∝ R_g while dV/dt falls ∝ 1/R_g — the gate resistor sets the EMI/efficiency trade.")
    t, vd, vg, id_ = wave
    fig, ax = p.fig(2, 1, h=6, sharex=True)
    ax[0].plot(t * 1e9, vg, color=COLORS[2], label="v_GS"); ax[0].axhline(Vpl, ls="--", color=C_PRED, lw=1, label="predicted Miller plateau")
    style_axes(ax[0], None, "V", "Turn-on with R_g = 10 Ω")
    ax[1].plot(t * 1e9, vd, color=C_MEAS, label="v_DS"); ax[1].plot(t * 1e9, id_ * 5, color=COLORS[1], label="i_D × 5")
    style_axes(ax[1], "time (ns)", "V / scaled A")
    p.save(fig, "waveforms", "Gate voltage stalls on the Miller plateau while the drain voltage falls.")
    p.csv("sweep", rg_ohm=Rg_, eon_j=E, eon_pred_j=Ep, dvdt_v_per_s=dv, dvdt_pred=dvp)
    p.discuss("""The Miller plateau is clearly visible and sits at the predicted V_th + √(2I/K). dV/dt follows the
gate-charge formula closely because C_gd is constant in this model; in a real MOSFET C_gd rises sharply
at low V_DS, so the last part of the voltage fall slows down (the 'tail' in datasheet curves). The
energy estimate uses straight-line current and voltage transitions and ignores the diode's reverse
recovery (not modelled), so it is a lower bound; real E_on is often 1.5–2× larger. The gap is largest at R_g = 2 Ω, where the
predicted edges last only a few ns and second-order effects the model ignores — the gate-drive
loop's own RC delay before V_th and the finite time the freewheel diode needs to hand over current —
become comparable to the edges themselves.""")
