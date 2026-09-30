from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-026", title="Buck (step-down) converter", level="M",
    tools="eelab mini-SPICE switch-level transient (MOSFET switch + Schottky diode)",
    summary="12 V → D·12 V at 100 kHz: predict output voltage, inductor ripple and output ripple from "
            "volt-second balance, then measure them and the efficiency across duty cycle.",
    problem="How does chopping 12 V on and off produce a smooth lower voltage, and how big are the "
            "ripples that the L and C must absorb?",
    theory=r"""Volt-second balance on L in continuous conduction: $V_{out}=D\,V_{in}$ (ideal).
Inductor ripple $\Delta I_L=\frac{(V_{in}-V_{out})D}{Lf_{sw}}$; output ripple (capacitive part)
$\Delta V_{out}=\frac{\Delta I_L}{8f_{sw}C}$. Losses: switch $I^2R_{on}D$, diode $V_F I(1-D)$, so
$V_{out}\approx D V_{in} - (1-D)V_F - I R_{on} D$ (first-order).""",
    method="""V_in = 12 V, f_sw = 100 kHz, L = 47 µH (30 mΩ DCR), C = 100 µF, R_L = 5 Ω, switch R_on = 50 mΩ, Schottky
(Is = 10 µA, N = 1.05). D ∈ {0.25, 0.4, 0.5, 0.65, 0.8}; 2 ms transient at 25 ns steps starting near
the predicted steady state; measurements over the last 50 µs (ripple = median peak-to-peak per switching period,
which excludes any residual slow LC settling).""",
)


def run(p):
    Vin, fsw, L, C, RL = 12.0, 100e3, 47e-6, 100e-6, 5.0
    Ds = [0.25, 0.4, 0.5, 0.65, 0.8]
    rows = []
    for Dc in Ds:
        ck = Circuit(f"buck D={Dc}")
        ck.V("in", "vin", "0", dc=Vin)
        ck.SW("q", "vin", "sw", lambda t, Dc=Dc: (t * fsw) % 1 < Dc, ron=0.05, roff=1e6)
        ck.D("d", "0", "sw", Is=1e-5, N=1.05, Rs=0.01)
        ck.L("f", "sw", "lx", L); ck.R("dcr", "lx", "out", 0.03)
        ck.C("o", "out", "0", C); ck.R("L", "out", "0", RL)
        if Dc == 0.5:
            p.write("simulation/buck.cir", ck.to_spice(), "SPICE netlist (switch as comment)")
        Iout = Dc * Vin / RL
        V0 = Dc * Vin - (1 - Dc) * 0.3 - 0.05
        tr = ck.tran(2.0e-3, 25e-9, method="be", ic={"out": V0, "I(f)": V0 / RL})
        m = tr.t >= 2.0e-3 - 50e-6
        vo, il = tr.v("out")[m], tr.i("f")[m]
        Vout = vo.mean(); Io = Vout / RL
        VF = 1.05 * 0.025852 * np.log(Io / 1e-5) + 0.01 * Io
        Vpred = Dc * Vin - (1 - Dc) * VF - Io * (0.05 * Dc + 0.03)
        dIL = (Vin - Vout) * Dc / (L * fsw)
        dV = dIL / (8 * fsw * C)
        Pin = np.mean(Vin * -tr.i("in")[m])
        eff = Vout * Io / Pin * 100
        p.compare(f"D = {Dc}: V_out (ideal D·V_in)", Dc * Vin, Vout, "V")
        p.compare(f"D = {Dc}: V_out (with losses)", Vpred, Vout, "V", tol=2)
        p.compare(f"D = {Dc}: inductor ripple ΔI_L", dIL, il.max() - il.min(), "A", tol=10)
        per = int(round(1 / fsw / 25e-9))
        rip = np.median([np.ptp(vo[j:j + per]) for j in range(0, len(vo) - per, per)])
        p.compare(f"D = {Dc}: output ripple ΔV (per switching period)", dV, rip, "V", tol=25)
        rows.append((Dc, Vout, Vpred, eff, il.max() - il.min(), dIL))
        if Dc == 0.5:
            wave = (tr.t[m], tr.v("sw")[m], il, vo)
    Ds_, Vo, Vp, eff, dm, dp = map(np.array, zip(*rows))
    fig, ax = p.fig(1, 2)
    ax[0].plot(Ds_, Ds_ * Vin, ":", color="gray", label="ideal D·V_in")
    ax[0].plot(Ds_, Vp, "--", color=C_PRED, label="with conduction losses")
    ax[0].plot(Ds_, Vo, "o", color=C_MEAS, ms=7, label="simulated")
    style_axes(ax[0], "duty cycle D", "V_out (V)", "Buck transfer ratio")
    ax[1].plot(Ds_, eff, "o-", color=C_MEAS, label="simulated efficiency")
    style_axes(ax[1], "duty cycle D", "efficiency (%)", "Efficiency")
    p.save(fig, "transfer", "V_out follows D·V_in minus the diode and resistive drops.")
    t, vsw, il, vo = wave
    fig, ax = p.fig(3, 1, h=7, sharex=True)
    tt = (t - t[0]) * 1e6
    ax[0].plot(tt, vsw, color=COLORS[1], lw=1); style_axes(ax[0], None, "V_sw (V)", "D = 0.5 steady-state waveforms", legend=False)
    ax[1].plot(tt, il, color=C_MEAS); style_axes(ax[1], None, "I_L (A)", legend=False)
    ax[2].plot(tt, vo * 1e3 - vo.mean() * 1e3, color=COLORS[2]); style_axes(ax[2], "time (µs)", "V_out ripple (mV)", legend=False)
    p.save(fig, "waveforms", "Switch node, triangular inductor current and the parabolic output ripple.")
    p.csv("duty_sweep", duty=Ds_, vout_v=Vo, vout_pred_v=Vp, efficiency_pct=eff, ripple_meas_a=dm, ripple_pred_a=dp)
    p.discuss("""The ideal D·V_in is off by up to ~0.4 V, almost entirely because of the Schottky's forward drop
during the (1−D) freewheeling interval — which is why low-voltage bucks replace the diode with a
synchronous MOSFET. With that loss included the prediction lands within a fraction of a percent.
The measured inductor ripple matches (V_in − V_out)D/(Lf). The output ripple formula assumes an ideal
capacitor and exactly triangular current; it is a good estimate here because the capacitor has no ESR
in the model — with a real electrolytic, ESR·ΔI_L would dominate.""")
