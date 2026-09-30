from eelab import *
from eelab.circuit import Circuit, e_series
from eelab.pcb import Board, Rules, to220, chip, radial_cap, terminal, mounting_hole, publish

META = dict(
    id="SL-207", title="Linear power-supply board (LM317, 12 V → 5 V, 1 A)", level="M",
    tools="eelab.pcb with IPC-2221 track widths and wide power routing, tolerance Monte-Carlo on the MNA simulator, thermal budget, DRC and fab outputs",
    summary="An adjustable-regulator board delivering 5 V at up to 1 A: resistor selection from E96, a Monte-Carlo of output voltage over part "
            "tolerances, a junction-temperature budget that sizes the heatsink, IPC-2221 track widths and the routed copper's voltage drop.",
    problem="A linear regulator is a three-pin part — so where do the real design decisions lie? Answer: tolerance, heat and copper.",
    theory=r"""$V_\text{out}=V_\text{ref}(1+R_2/R_1)+I_\text{adj}R_2$ with $V_\text{ref}$ = 1.25 V (1.20–1.30 V), $I_\text{adj}$ ≈ 50 µA (≤ 100 µA). With R1 = 240 Ω, 5.00 V needs R2 = 713 Ω → E96 715 Ω → 5.01 V
nominal. Worst case (±4 % reference, ±1 % resistors, I_adj 50–100 µA) spans ≈ 4.74–5.32 V — the reference dominates. Heat: P ≈ (12 − 5) V × 1 A = 7 W; with θ_ja ≈ 50 °C/W
(no heatsink) T_j would be ~390 °C, so a heatsink of θ_sa ≤ (125 − 40)/7 − θ_jc − θ_cs ≈ 6.6 °C/W is required at 40 °C ambient. Copper: IPC-2221 gives
0.30 mm for 1 A at 10 °C rise on 1 oz outer layers; 1.5 mm tracks cut the IR drop to a few mV per cm.""",
    method="""Regulator as a behavioural model (high-gain error amplifier holding OUT − ADJ = V_ref, I_adj into ADJ) in the MNA simulator; 5000 Monte-Carlo draws: V_ref uniform 1.20–1.30 V, resistors
uniform ±1 %, I_adj uniform 50–100 µA. Board: 2-pin terminal blocks, TO-220 (1 ADJ, 2 OUT, 3 IN), input/output 10 µF electrolytics, 10 µF ADJ bypass,
power LED; power nets routed at 1.5 mm, GND poured on both layers.""",
    data="Design + simulation (datasheet-typical LM317 parameters).",
)


def vout(vref, r1, r2, iadj, rl=5.0):
    ck = Circuit("lm317")
    ck.V("in", "vin", "0", dc=12)
    # behavioural regulator: a high-gain error amplifier drives OUT until OUT − ADJ = Vref (a floating Vref source alone
    # cannot deliver load current — my first model tried that and produced 9 mV)
    ck.V("ref", "r", "adj", dc=vref)
    ck.OPAMP("err", "r", "out", "out", A0=1e7, VSAT=20, ROUT=0.01)   # pass device: stiff output
    ck.I("adj", "0", "adj", dc=iadj)           # ADJ pin current flows into the ADJ node
    ck.R("1", "out", "adj", r1); ck.R("2", "adj", "0", r2); ck.R("L", "out", "0", rl)
    return ck.op()["out"]


def build():
    b = Board("lm317_5v_psu", 44, 32, Rules(track=0.3))
    b.add("J1", terminal(2), 6, 16, 90, "VIN 12V"); b.add("J2", terminal(2), 38, 16, 90, "VOUT 5V")
    b.add("U1", to220(), 22, 25, 0, "LM317", "TO-220 adjustable regulator")
    b.add("C1", radial_cap(), 13.5, 17, 0, "10uF 25V"); b.add("C3", radial_cap(), 30.5, 17, 0, "10uF 16V")   # first placement overlapped the terminal blocks (DRC)
    b.add("R1", chip("0805"), 25, 16, 90, "240"); b.add("R2", chip("0805"), 22, 12, 0, "715"); b.add("C2", chip("1206"), 17, 12, 0, "10uF")
    b.add("D1", chip("0805"), 30, 9, 0, "LED green"); b.add("R3", chip("0805"), 34, 9, 0, "1k")
    for k, (x, y) in enumerate(((3.5, 3.5), (40.5, 3.5), (3.5, 28.5), (40.5, 28.5)), 1):
        b.add(f"H{k}", mounting_hole(), x, y)
    b.connect("VIN", "J1.1", "U1.3", "C1.1"); b.connect("VOUT", "U1.2", "J2.1", "C3.1", "R1.2", "R3.2")
    b.connect("ADJ", "U1.1", "R1.1", "R2.2", "C2.1"); b.connect("LED", "R3.1", "D1.2")
    b.connect("GND", "J1.2", "J2.2", "C1.2", "C3.2", "R2.1", "C2.2", "D1.1")
    b.net_widths.update({"VIN": 1.5, "VOUT": 1.5})
    b.pin_widths.update({("R1", "2"): 0.3, ("R3", "2"): 0.3})     # feedback and LED taps carry mA, not amps
    return b


def run(p):
    r1 = 240.0
    r2_ideal = (5.0 - 1.25) / (1.25 / r1 + 50e-6)
    r2 = 715.0
    p.metric("Ideal R2 for 5.00 V", r2_ideal, "Ω", "E96 choice: 715 Ω")
    p.compare("Nominal output with E96 parts", 1.25 * (1 + r2 / r1) + 50e-6 * r2, vout(1.25, r1, r2, 50e-6), "V", tol=0.0001)
    r = p.rng
    N = 5000
    vr = r.uniform(1.20, 1.30, N); a = r1 * r.uniform(0.99, 1.01, N); bb = r2 * r.uniform(0.99, 1.01, N); ia = r.uniform(50e-6, 100e-6, N)
    mc = np.array([vout(*x) for x in zip(vr, a, bb, ia)])
    lo = 1.20 * (1 + r2 * 0.99 / (r1 * 1.01)) + 50e-6 * r2 * 0.99
    hi = 1.30 * (1 + r2 * 1.01 / (r1 * 0.99)) + 100e-6 * r2 * 1.01
    p.compare("Worst-case low output (analytic) vs Monte-Carlo minimum", lo, mc.min(), "V", tol=1)
    p.compare("Worst-case high output (analytic) vs Monte-Carlo maximum", hi, mc.max(), "V", tol=1)
    share = np.var(vr * (1 + r2 / r1)) / np.var(mc)
    p.metric("Share of output variance from V_ref alone", share * 100, "%")
    P = (12 - 5) * 1.0 + 12 * 5e-3
    p.metric("Regulator dissipation at 1 A", P, "W")
    p.metric("T_j with no heatsink (θ_ja ≈ 50 °C/W, 40 °C ambient)", 40 + 50 * P, "°C", "— impossible: thermal shutdown")
    p.metric("Required heatsink θ_sa (θ_jc 5, θ_cs 0.5 °C/W, T_j ≤ 125 °C)", (125 - 40) / P - 5 - 0.5, "°C/W")
    w_ipc = (1.0 / (0.048 * 10 ** 0.44)) ** (1 / 0.725) / 1.378 * 0.0254
    p.compare("IPC-2221 minimum width for 1 A, 10 °C rise, 1 oz outer", 0.30, w_ipc, "mm", tol=5)
    b = build()
    fail = b.route(skip=("GND",))
    p.metric("Unrouted connections", sum(len(v) for v in fail.values()), "")
    b.stitch_pad_vias("GND"); b.pour("B", "GND"); b.pour("F", "GND")
    publish(p, b)
    Lout = b.track_length("VOUT") * 1e-3
    R_out = 1.72e-8 * Lout / (1.5e-3 * 35e-6)
    p.metric("Routed VOUT copper length / resistance", f"{Lout * 1e3:.1f} mm / {R_out * 1e3:.2f} mΩ")
    p.compare("IR drop in VOUT copper at 1 A (≤ 10 mV target)", 10e-3, R_out * 1.0, "V", kind="abs", tol=10e-3)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].hist(mc, bins=60, color=C_MEAS, alpha=.8, label="Monte-Carlo (5000)")
    ax[0].axvline(lo, ls="--", color=C_PRED, label="analytic worst case"); ax[0].axvline(hi, ls="--", color=C_PRED)
    style_axes(ax[0], "output voltage (V)", "count", "Output spread: the reference dominates")
    Ps = np.linspace(0.5, 10, 50)
    for th, c, lab in ((50, COLORS[2], "no heatsink (θ_ja 50)"), (5 + 0.5 + 15, COLORS[1], "small clip-on (θ_sa 15)"), (5 + 0.5 + 6, COLORS[0], "θ_sa 6 °C/W")):
        ax[1].plot(Ps, 40 + th * Ps, color=c, label=lab)
    ax[1].axhline(125, ls=":", color="gray"); ax[1].axvline(P, ls=":", color="gray")
    ax[1].set_ylim(0, 300)
    style_axes(ax[1], "dissipation (W)", "junction temperature (°C)", "Heat, not voltage, limits a linear supply")
    p.save(fig, "tolerance_thermal", "Output-voltage distribution vs analytic bounds, and junction temperature vs dissipation for three thermal paths.")
    p.discuss(f"""The E96 resistor pair lands the nominal output at 5.01 V, but the Monte-Carlo shows the part-to-part spread is 4.8–5.3 V, almost all of it
({share * 100:.0f} % of the variance) from the ±4 % reference — spending money on 0.1 % resistors would not help; a trim or a better regulator
would. The analytic worst case bounds the Monte-Carlo, as it must. Heat is the real constraint: at 1 A from 12 V the regulator burns 7 W, which
needs a ≲ {(125 - 40) / P - 5.5:.1f} °C/W heatsink; without one the part would hit thermal shutdown within seconds. On the board, power paths are
routed at 1.5 mm (5× the IPC-2221 minimum) so the output copper drops only {R_out * 1e3:.1f} mV at 1 A, both layers carry ground pours, and the ADJ
bypass capacitor sits beside the ADJ pin. A switching regulator would cut the 7 W to under 1 W — the linear design is chosen here for its low noise
and simplicity, and the board makes its cost visible. Two first-attempt errors are worth recording: my first regulator model was a floating 1.25 V source,
which cannot deliver load current to ground (it 'regulated' to 9 mV), and the first placement put both electrolytics' courtyards on top of the
terminal blocks — the DRC caught it.""")
# tol-convention: relative tolerances are in percent
