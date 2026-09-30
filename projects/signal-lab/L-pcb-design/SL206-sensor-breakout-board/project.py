from eelab import *
from eelab.circuit import Circuit
from eelab.pcb import Board, Rules, soic, chip, header, mounting_hole, publish

META = dict(
    id="SL-206", title="I²C temperature-sensor breakout board", level="M",
    tools="eelab.pcb (footprints, router, pour, DRC, Gerber/KiCad export), microstrip capacitance from the routed geometry, MNA transient simulation of the open-drain bus",
    summary="A small, clean breakout for an LM75-class I²C temperature sensor (SOIC-8) with pull-ups, decoupling and a 5-pin header. The routed "
            "board's own trace capacitance feeds an I²C rise-time budget, checked by simulating the open-drain bus.",
    problem="Which pull-up resistor does an I²C breakout need — and does the board itself matter?",
    theory=r"""An open-drain line rises through R_p into the bus capacitance C_b; the I²C rise time (30 %→70 % of V_DD) is $t_r = \ln(0.7/0.3)\,R_pC_b = 0.8473\,R_pC_b$. Limits:
$t_r$ ≤ 1000 ns (standard mode, 100 kHz) or ≤ 300 ns (fast mode, 400 kHz), and $R_p ≥ (V_{DD}-0.4\,V)/3\,\text{mA}$ so a device can pull the line low.
The breakout's own contribution is its trace capacitance: for a 0.25 mm trace over a 1.6 mm board with a ground pour below, ≈ 0.05 pF/mm, i.e. a few pF —
small next to device pins (~10 pF each) and wiring (tens of pF).""",
    method="""LM75-style pinout (1 SDA, 2 SCL, 3 OS, 4 GND, 5–7 A2–A0, 8 V+), address pins strapped to GND (0x48). 4.7 kΩ pull-ups, 10 kΩ on OS, 100 nF decoupling.
C_b = routed SDA length × microstrip C′ (Hammerstad–Jensen, ε_r 4.4) + 10 pF sensor pin + 10 pF controller pin + 50 pF wiring (assumed jumper wires).
Transient: MNA simulation of R_p charging C_b when the open-drain driver (switch, 20 Ω on) releases.""",
    data="Design + simulation.",
)


def microstrip_C_per_m(w, h, er):
    u = w / h
    ee = (er + 1) / 2 + (er - 1) / 2 / np.sqrt(1 + 12 / u)
    z = 60 / np.sqrt(ee) * np.log(8 / u + u / 4) if u < 1 else 120 * pi / (np.sqrt(ee) * (u + 1.393 + 0.667 * np.log(u + 1.444)))
    return np.sqrt(ee) / (299792458 * z)


def build():
    b = Board("i2c_temp_breakout", 22, 18, Rules())
    b.add("U1", soic(8), 11, 11, 0, "LM75-class", "I2C temperature sensor SOIC-8")
    b.add("J1", header(5), 11, 3, 0, "VCC/GND/SCL/SDA/OS")
    ch = chip("0603")
    b.add("R1", ch, 4, 12, 90, "4.7k"); b.add("R2", ch, 6.5, 12, 90, "4.7k"); b.add("R3", ch, 17.5, 8, 90, "10k"); b.add("C1", ch, 16, 14, 90, "100n")   # first placement at x = 17.5 overlapped H2's courtyard (caught by DRC)
    b.add("H1", mounting_hole(2.2), 3, 16); b.add("H2", mounting_hole(2.2), 19, 16)
    b.connect("VCC", "J1.1", "U1.8", "C1.2", "R1.2", "R2.2", "R3.2")
    b.connect("GND", "J1.2", "U1.4", "U1.5", "U1.6", "U1.7", "C1.1")
    b.connect("SCL", "J1.3", "U1.2", "R2.1"); b.connect("SDA", "J1.4", "U1.1", "R1.1"); b.connect("OS", "J1.5", "U1.3", "R3.1")
    return b


def rise(Rp, Cb, vdd=3.3):
    ck = Circuit("i2c")
    ck.V("dd", "vdd", "0", dc=vdd); ck.R("p", "vdd", "sda", Rp); ck.C("b", "sda", "0", Cb)
    ck.SW("drv", "sda", "0", lambda t: t < 0, ron=20, roff=1e9)
    tau = Rp * Cb
    tr = ck.tran(6 * tau, tau / 400, method="trap", ic={"sda": 0.0})
    t, v = tr.t, tr.v("sda")
    return find_crossing(t, v, 0.7 * vdd, logx=False) - find_crossing(t, v, 0.3 * vdd, logx=False), t, v


def run(p):
    b = build()
    fail = b.route(skip=("GND",))
    p.metric("Unrouted connections", sum(len(v) for v in fail.values()), "")
    b.stitch_pad_vias("GND"); b.pour("B", "GND")
    publish(p, b)
    Lsda = b.track_length("SDA") * 1e-3
    Cp = microstrip_C_per_m(0.25e-3, 1.6e-3, 4.4)
    Ctrace = Cp * Lsda
    p.compare("Microstrip capacitance per mm of 0.25 mm track over the pour (my guess ≈ 0.05 pF/mm)", 0.05, Cp * 1e-3 * 1e12, "pF/mm", kind="abs", tol=0.02)
    p.metric("Routed SDA length on the breakout", Lsda * 1e3, "mm")
    p.metric("SDA trace capacitance of the breakout", Ctrace * 1e12, "pF")
    Cb = Ctrace + 10e-12 + 10e-12 + 50e-12
    tr_meas, t, v = rise(4.7e3, Cb)
    p.compare("SDA rise time with 4.7 kΩ (0.8473·Rp·Cb)", 0.8473 * 4.7e3 * Cb, tr_meas, "s", tol=1)
    rp_min = (3.3 - 0.4) / 3e-3
    rp_max_std, rp_max_fast = 1000e-9 / (0.8473 * Cb), 300e-9 / (0.8473 * Cb)
    p.metric("Allowed pull-up range, standard mode (100 kHz)", f"{rp_min:.0f} Ω – {rp_max_std / 1e3:.1f} kΩ")
    p.metric("Allowed pull-up range, fast mode (400 kHz)", f"{rp_min:.0f} Ω – {rp_max_fast / 1e3:.2f} kΩ")
    p.compare("4.7 kΩ meets fast-mode 300 ns? (1 = yes)", 1, int(tr_meas <= 300e-9), "", kind="abs")
    fig, ax = p.fig(1, 2, w=11)
    for Rp, c in ((2.2e3, COLORS[0]), (4.7e3, COLORS[1]), (10e3, COLORS[2])):
        _, tt, vv = rise(Rp, Cb)
        ax[0].plot(tt * 1e9, vv, color=c, label=f"R_p = {Rp / 1e3:g} kΩ")
    ax[0].axhline(0.3 * 3.3, ls=":", color="gray"); ax[0].axhline(0.7 * 3.3, ls=":", color="gray")
    style_axes(ax[0], "time after release (ns)", "SDA (V)", f"Bus release, C_b = {Cb * 1e12:.0f} pF")
    cbs = np.linspace(20e-12, 400e-12, 50)
    ax[1].fill_between(cbs * 1e12, rp_min / 1e3, 300e-9 / (0.8473 * cbs) / 1e3, color=COLORS[0], alpha=.25, label="fast mode OK")
    ax[1].fill_between(cbs * 1e12, rp_min / 1e3, 1000e-9 / (0.8473 * cbs) / 1e3, color=COLORS[0], alpha=.1, label="standard mode OK")
    ax[1].plot([Cb * 1e12], [4.7], "o", color=C_PRED, label="this design")
    ax[1].set_ylim(0, 25)
    style_axes(ax[1], "bus capacitance C_b (pF)", "pull-up R_p (kΩ)", "I²C pull-up design window")
    p.save(fig, "i2c", "Open-drain rise for three pull-ups (simulated) and the allowed pull-up window vs bus capacitance.")
    p.discuss(f"""The breakout routes cleanly on two layers with a ground pour, and the numbers show why its layout barely matters for I²C timing: the whole
SDA trace is {Lsda * 1e3:.0f} mm long and adds only {Ctrace * 1e12:.1f} pF, compared with ~20 pF of device pins and ~50 pF of jumper wiring. With 4.7 kΩ
pull-ups the simulated rise time is {tr_meas * 1e9:.0f} ns, matching 0.8473·R_pC_b — comfortably inside standard mode, and
{'inside' if tr_meas <= 300e-9 else 'outside'} fast mode's 300 ns. The design window plot is the practical takeaway: breakouts ship with pull-ups, and when
several are wired in parallel the pull-ups combine (three 4.7 kΩ ≈ 1.6 kΩ), creeping toward the 967 Ω minimum at 3.3 V — which is why good
breakouts put the pull-ups behind solder jumpers. The first placement put C1's courtyard over a mounting hole — the DRC flagged it and C1 moved 1.5 mm. The 50 pF wiring figure is an assumption; measure your own bus with a scope if it is long.""")
# tol-convention: relative tolerances are in percent
