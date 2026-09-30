from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-029", title="Flyback converter (isolated, coupled inductor)", level="H",
    tools="eelab mini-SPICE with mutual inductance (K), RCD clamp",
    summary="24 V → ~4 V isolated supply using a 4:1 coupled inductor — the phone-charger topology. "
            "Predict V_out = n·V_in·D/(1−D) and the leakage-inductance voltage spike the clamp must absorb.",
    problem="How does a flyback store energy in a transformer's core and release it to an isolated "
            "output, and why does every flyback need a snubber?",
    theory=r"""With turns ratio $n=N_s/N_p$ and CCM operation: $V_{out}=nV_{in}\frac{D}{1-D}$.
While the switch is off the primary is clamped at $V_{in}+V_{out}/n$ (reflected voltage).
Leakage inductance $L_{lk}=(1-k^2)L_p$ does not couple to the secondary; its energy $\tfrac12L_{lk}I_{pk}^2$
drives the drain above the reflected voltage until the RCD clamp (clamp voltage $V_{cl}$) absorbs it:
$P_{clamp}\approx \tfrac12L_{lk}I_{pk}^2 f_{sw}\frac{V_{cl}}{V_{cl}-V_{out}/n}$.""",
    method="""L_p = 100 µH, L_s = 6.25 µH (n = 0.25), k = 0.99 (≈ 2 µH leakage), f_sw = 100 kHz, D = 0.4, 22 µF output with
2 Ω load. RCD clamp: diode drain → clamp node, 10 nF ‖ 3.3 kΩ to V_in. 2.5 ms transient at 10 ns steps.""",
)


def run(p):
    Vin, Lp, n, k, fsw, Dc, RL = 24.0, 100e-6, 0.25, 0.99, 100e3, 0.4, 2.0
    Ls = Lp * n * n
    ck = Circuit("flyback")
    ck.V("in", "vin", "0", dc=Vin)
    ck.L("p", "vin", "d", Lp)
    ck.SW("q", "d", "0", lambda t: (t * fsw) % 1 < Dc, ron=0.05, roff=1e6)
    ck.L("s", "0", "sx", Ls)          # dot convention: secondary reversed -> flyback action
    ck.K("p", "s", k)
    ck.D("o", "sx", "out", Is=1e-6, N=1.02)
    ck.C("o", "out", "0", 22e-6); ck.R("L", "out", "0", RL)
    ck.D("cl", "d", "cl", Is=1e-9, N=1.5); ck.C("cl", "cl", "vin", 10e-9); ck.R("cl", "cl", "vin", 3.3e3)
    p.write("simulation/flyback.cir", ck.to_spice(), "SPICE netlist (switch as comment)")
    Vpred_ideal = n * Vin * Dc / (1 - Dc)
    tr = ck.tran(2.5e-3, 10e-9, method="be", ic={"out": Vpred_ideal})
    m = tr.t >= tr.t[-1] - 50e-6
    vo = tr.v("out")[m].mean()
    VF = 1.02 * 0.025852 * np.log(vo / RL / (1 - Dc) / 1e-6)
    p.compare("Output voltage (ideal n·V_in·D/(1−D))", Vpred_ideal, vo, "V")
    p.compare("Output voltage (minus diode drop)", Vpred_ideal - VF, vo, "V", tol=8)
    vd = tr.v("d")[m]
    Vrefl = Vin + (vo + VF) / n
    p.compare("Drain plateau (V_in + V_out/n)", Vrefl, np.median(vd[vd > Vin + 5]), "V", tol=8)
    vcl = tr.v("cl")[m].mean()
    p.metric("Peak drain voltage (leakage spike, clamped)", vd.max(), "V")
    p.metric("Clamp capacitor voltage", vcl, "V")
    Llk = (1 - k * k) * Lp
    ip = -tr.i("in")[m]
    Ipk = tr.i("p")[m].max()
    Pcl_pred = 0.5 * Llk * Ipk**2 * fsw * (vcl - Vin) / ((vcl - Vin) - (vo + VF) / n)
    Pcl = np.mean((vcl - Vin)**2 / 3.3e3 * np.ones(1))
    p.compare("Clamp dissipation", Pcl_pred, Pcl, "W", tol=30)
    eff = vo**2 / RL / np.mean(Vin * ip) * 100
    p.metric("Efficiency", eff, "%")
    t = (tr.t[m] - tr.t[m][0]) * 1e6
    fig, ax = p.fig(3, 1, h=7.5, sharex=True)
    ax[0].plot(t, vd, color=COLORS[1], lw=1)
    ax[0].axhline(Vrefl, ls="--", color=C_PRED, lw=1, label="V_in + V_out/n")
    style_axes(ax[0], None, "V_drain (V)", "Flyback steady-state waveforms")
    ax[1].plot(t, tr.i("p")[m], color=C_MEAS, label="primary"); ax[1].plot(t, tr.i("s")[m], color=COLORS[2], label="secondary")
    style_axes(ax[1], None, "current (A)")
    ax[2].plot(t, tr.v("out")[m], color=C_MEAS, label="V_out")
    style_axes(ax[2], "time (µs)", "V_out (V)")
    p.save(fig, "waveforms", "Energy stored in the primary during the on-time is released through the secondary during the off-time.")
    p.csv("waveforms", t_us=t, v_drain=vd, i_primary=tr.i("p")[m], i_secondary=tr.i("s")[m], v_out=tr.v("out")[m])
    p.discuss("""The output sits one diode drop below the ideal flyback ratio. The drain waveform shows the three
phases every flyback designer knows: the on-state near 0 V, a spike when the switch opens (leakage
inductance forcing current into the clamp), then the plateau at V_in + V_out/n while the secondary
conducts. The clamp-dissipation estimate is rough because the clamp capacitor voltage itself sets how
fast leakage current resets; it confirms the order of magnitude — leakage energy is pure loss, which is
why transformer interleaving (k → 0.999) matters so much in real chargers.""")
