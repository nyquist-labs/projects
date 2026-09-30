from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-027", title="Boost converter: continuous vs discontinuous conduction", level="M",
    tools="eelab mini-SPICE switch-level transient",
    summary="5 V → 1/(1−D) boost: show continuous (CCM) and discontinuous (DCM) inductor current and "
            "predict each mode's conversion ratio, including the CCM/DCM boundary.",
    problem="A boost converter's famous formula V_out = V_in/(1−D) silently assumes the inductor current "
            "never reaches zero. What happens at light load?",
    theory=r"""CCM: $M = V_{out}/V_{in} = 1/(1-D)$. With $K=2L/(RT_{sw})$ the converter is in DCM when
$K < D(1-D)^2$, and then
$$M_{DCM}=\frac{1+\sqrt{1+4D^2/K}}{2}$$
(Erickson & Maksimović). The DCM ratio depends on load — the converter no longer behaves like an ideal
transformer.""",
    method="""V_in = 5 V, L = 22 µH, C = 47 µF, f_sw = 100 kHz, D = 0.5, Schottky output diode. Loads 10 Ω (K = 0.44,
CCM) and 200 Ω (K = 0.022, DCM), plus a load sweep to trace M vs K. Transients of 3–8 ms.""",
)


def sim(RL, Dc, L=22e-6, C=47e-6, fsw=100e3, Vin=5.0, T=3e-3, v0=None):
    ck = Circuit("boost")
    ck.V("in", "vin", "0", dc=Vin)
    ck.L("b", "vin", "sw", L)
    ck.SW("q", "sw", "0", lambda t: (t * fsw) % 1 < Dc, ron=0.03, roff=1e6)
    ck.D("d", "sw", "out", Is=1e-6, N=1.02)
    ck.C("o", "out", "0", C); ck.R("L", "out", "0", RL)
    guess = Vin / (1 - Dc)
    v0 = guess if v0 is None else v0
    tr = ck.tran(T, 25e-9, method="be", ic={"out": v0, "I(b)": v0**2 / RL / Vin})
    return ck, tr


def run(p):
    Vin, Dc, L, fsw = 5.0, 0.5, 22e-6, 100e3
    res = []
    for RL in [10, 20, 50, 100, 200, 400]:
        K = 2 * L / (RL / fsw)
        v0 = ((1 + np.sqrt(1 + 4 * Dc**2 / K)) / 2 if K < Dc * (1 - Dc)**2 else 1 / (1 - Dc)) * Vin - 0.4
        ck, tr = sim(RL, Dc, T=4e-3, v0=v0)
        m = tr.t >= tr.t[-1] - 40e-6
        Vout = tr.v("out")[m].mean()
        VF = 0.35
        Mccm = 1 / (1 - Dc)
        Mdcm = (1 + np.sqrt(1 + 4 * Dc**2 / K)) / 2
        mode = "DCM" if K < Dc * (1 - Dc)**2 else "CCM"
        Mp = Mdcm if mode == "DCM" else Mccm
        p.compare(f"R_L = {RL} Ω ({mode}, K = {K:.3f}): V_out", Mp * Vin - (VF if mode == "CCM" else VF * 0.5), Vout, "V", tol=5)
        res.append((RL, K, Vout / Vin, Mp, mode))
        if RL in (10, 200):
            if RL == 10:
                p.write("simulation/boost.cir", ck.to_spice(), "SPICE netlist")
            wv = tr.t[m], tr.i("b")[m]
            res[-1] = res[-1] + (wv,)
    p.metric("CCM/DCM boundary (D = 0.5)", 2 * L * fsw / (Dc * (1 - Dc)**2), "Ω", "loads above this R are DCM")
    fig, ax = p.fig(1, 2)
    for r, col, lab in ((res[0], COLORS[0], "10 Ω: CCM"), (res[4], COLORS[1], "200 Ω: DCM")):
        t, il = r[5]
        ax[0].plot((t - t[0]) * 1e6, il, color=col, label=lab)
    ax[0].axhline(0, color="gray", lw=.8)
    style_axes(ax[0], "time (µs)", "I_L (A)", "Inductor current")
    Ks = np.logspace(-2.2, 0, 100)
    Mth = np.where(Ks < Dc * (1 - Dc)**2, (1 + np.sqrt(1 + 4 * Dc**2 / Ks)) / 2, 1 / (1 - Dc))
    ax[1].semilogx(Ks, Mth, "--", color=C_PRED, label="theory (CCM/DCM)")
    ax[1].semilogx([r[1] for r in res], [r[2] for r in res], "o", color=C_MEAS, ms=7, label="simulated")
    style_axes(ax[1], "K = 2L/(R·T)", "M = V_out/V_in", "Conversion ratio vs load parameter K")
    p.save(fig, "ccm_dcm", "Light load pushes the boost into DCM, where the gain rises above 1/(1−D).")
    p.csv("load_sweep", r_load=[r[0] for r in res], K=[r[1] for r in res], M_meas=[r[2] for r in res], M_pred=[r[3] for r in res], mode=[r[4] for r in res])
    p.discuss("""In CCM the output sits a diode drop below 1/(1−D)·V_in as predicted. Crossing the boundary
(R ≈ 35 Ω for these values) the inductor current returns to zero every cycle and the gain climbs
above 2 — at 400 Ω the ideal DCM ratio is ~5.3. This is why an unloaded boost
converter without a controller can overvolt its output capacitor. The DCM formula neglects the diode
drop and ringing of the switch node during the idle interval, hence the few-percent residuals.""")
