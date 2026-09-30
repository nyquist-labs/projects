from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-018", title="Charge pump / voltage doubler", level="M",
    tools="eelab mini-SPICE transient (Schottky diodes, square-wave drive)",
    summary="A diode-capacitor doubler turns a 0–5 V, 50 kHz square wave into ~9 V with no inductor; "
            "predict the output vs load current from 2V_p − 2V_D − I/(fC) and measure it.",
    problem="How can capacitors and diodes alone produce a voltage higher than the supply, and how "
            "fast does it sag under load?",
    theory=r"""The flying capacitor C₁ is charged to $V_{in}-V_D$ while the drive is low; when the drive goes high
its bottom plate lifts by $V_p$ so its top reaches $2V_p - V_D$, and D₂ transfers charge into C₂.
Unloaded: $V_{out}=2V_p-2V_D$. Each cycle the load removes $Q = I/f$, which the flying capacitor
must replace. Charge-pump theory gives two limits for the output resistance: the slow-switching limit
$R_{SSL}=1/(fC)$ = 2 Ω (capacitors fully settle each phase) and the fast-switching limit
$R_{FSL}=2\sum R_{phase}$ = 40 Ω (charge moves through resistances in half a period, as happens here since
$\tau = 10\,\Omega\cdot10\,\mu F = 100\,\mu s \gg$ 10 µs). Using $R_{out}\approx\sqrt{R_{SSL}^2+R_{FSL}^2}$:
$$V_{out}\approx 2V_p - 2V_D - I_L R_{out}$$""",
    method="""5 V square wave at 50 kHz (10 Ω driver resistance), C₁ = C₂ = 10 µF, Schottky diodes (Is = 1 µA, N = 1.05).
Loads 1 kΩ…50 Ω; 6 ms transient per load, output averaged over the last millisecond. V_D taken from the
diode equation at the measured average current.""",
)


def run(p):
    f, Vp, C = 50e3, 5.0, 10e-6
    loads = [5000, 2000, 1000, 500, 200, 100, 50]
    Il, Vm, Vpred = [], [], []
    for RL in loads:
        ck = Circuit("doubler")
        ck.V("drv", "sq", "0", wave=lambda t: Vp if (t * f) % 1 >= 0.5 else 0.0)
        ck.R("drv", "sq", "b", 10)
        ck.V("dc", "vdd", "0", dc=Vp)
        ck.D("1", "vdd", "top", Is=1e-6, N=1.05)
        ck.C("1", "b", "top", C)
        ck.D("2", "top", "out", Is=1e-6, N=1.05)
        ck.C("2", "out", "0", C); ck.R("L", "out", "0", RL)
        if RL == 1000:
            p.write("simulation/doubler.cir", ck.to_spice(), "SPICE netlist (1 kΩ load)")
        tr = ck.tran(6e-3, 0.2e-6, method="be", uic=True)
        v = tr.v("out")[tr.t > 5e-3].mean()
        I = v / RL
        VD = 1.05 * 0.025852 * np.log(1 + max(I, 1e-9) * 2 / 1e-6)   # ~2× avg current flows in the pulse
        R_ssl = 1 / (f * C)                       # slow-switching limit (charge sharing)
        R_fsl = 2 * 10 + 2 * 10                   # fast-switching limit: 2R per phase, two phases through the 10 Ω driver
        pred = 2 * Vp - 2 * VD - I * np.hypot(R_ssl, R_fsl)
        Il.append(I); Vm.append(v); Vpred.append(pred)
        p.compare(f"V_out at R_L = {'open' if RL > 1e8 else f'{RL:g} Ω'}", pred, v, "V", tol=5)
        if RL == 200:
            wave = tr
    Il, Vm = np.array(Il), np.array(Vm)
    slope = -np.polyfit(Il, Vm, 1)[0]
    p.compare("Output resistance (slope)", np.hypot(1 / (f * C), 40), slope, "Ω", tol=25,
              note="√(R_SSL² + R_FSL²)")
    fig, ax = p.fig()
    ax.plot(np.array(Il) * 1e3, Vpred, "--", color=C_PRED, label="2V_p − 2V_D − I/(fC) − 2I·R_drv")
    ax.plot(Il * 1e3, Vm, "o-", color=C_MEAS, label="simulated")
    style_axes(ax, "load current (mA)", "V_out (V)", "Voltage doubler regulation")
    p.save(fig, "vout_vs_load", "Output falls linearly with load: the pump behaves like a source with R_out ≈ 1/(fC).")
    t = wave.t; m = t > 5.9e-3
    fig, ax = p.fig()
    ax.plot((t[m] - t[m][0]) * 1e6, wave.v("out")[m], color=C_MEAS, label="V_out")
    ax.plot((t[m] - t[m][0]) * 1e6, wave.v("top")[m], color=COLORS[2], lw=1, label="flying-cap top")
    ax.plot((t[m] - t[m][0]) * 1e6, wave.v("b")[m], color=COLORS[1], lw=1, label="drive")
    style_axes(ax, "time (µs)", "V", "Waveforms at 200 Ω load")
    p.save(fig, "waveforms", "The flying capacitor's top plate is lifted above V_DD every half-cycle.")
    p.csv("load_sweep", iload_a=Il, vout_v=Vm, predicted_v=Vpred)
    p.discuss("""The first design intuition — R_out = 1/(fC) = 2 Ω — is badly wrong here, and the simulation shows
why: the 10 Ω driver and 10 µF give a 100 µs time constant, ten times the 10 µs half-period, so the
capacitors never settle and the pump operates in its fast-switching limit where resistance, not
capacitance, sets R_out. With R_FSL included the prediction tracks the simulation; the remaining error
at heavy load comes from the diodes' dynamic resistance, which rises the load-dependent drop. The measured slope gives the pump's effective output resistance — the single number that
datasheets of charge-pump ICs quote.""")
