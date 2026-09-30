from eelab import *
from eelab.circuit import Circuit
from eelab.data import fetch
from eelab.pcb import Board, Rules, Footprint, Pad, chip, header, publish
from shapely.geometry import Polygon

META = dict(
    id="SL-208", title="Arduino Uno R3 shield (LEDs, button, potentiometer, I²C port)", level="M",
    tools="Uno R3 mechanical data parsed from the official KiCad footprint library (kiutils), eelab.pcb router/DRC/exports, MNA simulation of the LED drive",
    summary="A shield laid out on the Uno R3's real header coordinates — including the famous 160-mil offset between D7 and D8 — carrying four "
            "LEDs, a push-button, a potentiometer and a Qwiic-style I²C header; LED currents and the pin current budget are simulated.",
    problem="Designing to a standard mechanical footprint means getting someone else's dimensions exactly right. How do you avoid measuring by hand?",
    theory=r"""The Uno's header rows are on a 100-mil grid except for one quirk: the gap between D7 and D8 is 160 mil (4.064 mm), which stops shields being plugged in
offset by one pin. The LED current is $(V_{OH}-V_f)/(R+R_\text{pin})$: with a 330 Ω resistor, V_f ≈ 2.0 V and an output driver of ~40 Ω, ≈ 8.1 mA per LED — well under
the 20 mA recommended per pin; four LEDs draw ≈ 32 mA. The button uses the internal pull-up (20–50 kΩ) with a 100 nF capacitor: τ ≈ 3.5 ms of debouncing.""",
    method="""Pad positions of all 32 header pins and the board outline read from KiCad's `Module.pretty/Arduino_UNO_R3.kicad_mod` (fetched from the KiCad GitLab) and interpreted in
this toolkit's y-up frame (USB side at the left, digital header along the top). LEDs on D2–D5 (0805 + 330 Ω), button on D7 to GND with 100 nF, 10 kΩ
trimmer on A0, 4-pin I²C header on SDA/SCL. LED drive simulated with a diode model fitted to V_f = 2.0 V at 10 mA and a 40 Ω pin resistance (assumed).""",
    data="Real mechanical data: KiCad footprint library (CC-BY-SA 4.0 with exception).",
)

UNO_POWER = ["NC", "IOREF", "RESET", "3V3", "5V", "GND", "GND", "VIN"]
UNO_ANALOG = ["A0", "A1", "A2", "A3", "A4", "A5"]
UNO_DLOW = [f"D{k}" for k in range(8)]
UNO_DHIGH = ["D8", "D9", "D10", "D11", "D12", "D13", "GND", "AREF", "SDA", "SCL"]


def uno_reference():
    from kiutils.footprint import Footprint as KF
    path = fetch("https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/master/Module.pretty/Arduino_UNO_R3.kicad_mod", "Arduino_UNO_R3.kicad_mod", sub="kicad")
    kf = KF.from_file(str(path))
    pads = {int(p.number): (p.position.X, p.position.Y) for p in kf.pads}
    fab = [g for g in kf.graphicItems if g.layer == "F.Fab" and hasattr(g, "start")]
    return pads, fab


def trimmer():
    pads = [Pad("1", -2.54, 0, 1.6, 1.6, "rect", 0.9), Pad("2", 0, 2.54, 1.6, 1.6, "circle", 0.9), Pad("3", 2.54, 0, 1.6, 1.6, "circle", 0.9)]
    return Footprint("Potentiometer_Trimmer_P2.54mm", pads, (6.5, 6.5), 4.5, thru=True)


def tact():
    pads = [Pad(str(i + 1), x, y, 1.8, 1.8, "circle", 1.0) for i, (x, y) in enumerate(((-3.25, 2.25), (3.25, 2.25), (-3.25, -2.25), (3.25, -2.25)))]
    return Footprint("SW_PUSH_6mm", pads, (6.0, 6.0), 5.0, thru=True)


def build(pads, outline):
    X0, Y0 = 27.94, 2.54
    b = Board("uno_shield", 68.58, 53.34, Rules())
    b.shape = Polygon([(x + X0, y + Y0) for x, y in outline])
    def place(ref, first, last, names, value):
        n = last - first + 1
        xs = [pads[k][0] + X0 for k in range(first, last + 1)]; y = pads[first][1] + Y0
        order = np.argsort(xs)                          # header() numbers pins left to right
        c = b.add(ref, header(n), (min(xs) + max(xs)) / 2, y, 0, value)
        for pin, k in enumerate(order, 1):
            net = names[k]
            if net not in ("NC",):
                b.connect(net, f"{ref}.{pin}")
        return c
    place("J1", 1, 8, UNO_POWER, "Power 1x08")
    place("J2", 9, 14, UNO_ANALOG, "Analog 1x06")
    place("J3", 15, 22, UNO_DLOW, "Digital 0-7 1x08")
    place("J4", 23, 32, UNO_DHIGH, "Digital 8-13 1x10")
    ch = chip("0805")
    for i, d in enumerate((2, 3, 4, 5)):
        x = 40 + i * 6
        b.add(f"R{i + 1}", ch, x, 40, 90, "330"); b.add(f"D{i + 1}", ch, x, 33, 90, "LED")
        b.connect(f"D{d}", f"R{i + 1}.2"); b.connect(f"LED{i + 1}", f"R{i + 1}.1", f"D{i + 1}.2"); b.connect("GND", f"D{i + 1}.1")
    b.add("SW1", tact(), 22, 30, 0, "Button"); b.add("C1", ch, 30, 30, 90, "100n")
    b.connect("D7", "SW1.1", "SW1.2", "C1.2"); b.connect("GND", "SW1.3", "SW1.4", "C1.1")
    b.add("RV1", trimmer(), 40, 16, 0, "10k"); b.connect("5V", "RV1.1"); b.connect("A0", "RV1.2"); b.connect("GND", "RV1.3")
    b.add("J5", header(4), 20, 16, 0, "I2C GND/5V/SDA/SCL"); b.connect("GND", "J5.1"); b.connect("5V", "J5.2"); b.connect("SDA", "J5.3"); b.connect("SCL", "J5.4")
    # merge nets that are the same signal on two headers (GND appears on J1 and J4; SDA/SCL on J4 and J5)
    return b


def led_current(R=330, Rpin=40, vdd=5.0):
    N = 2.0; Is = 10e-3 / np.exp(2.0 / (N * 0.025852))
    ck = Circuit("led"); ck.V("p", "pin", "0", dc=vdd); ck.R("pin", "pin", "a", Rpin); ck.R("s", "a", "k", R); ck.D("led", "k", "0", Is=Is, N=N)
    o = ck.op()
    return -o["I(p)"], o["k"]


def run(p):
    pads, fab = uno_reference()
    gap = pads[22][0] - pads[23][0]
    p.compare("D7 → D8 pin spacing from the KiCad library (the 160-mil quirk)", 0.160 * 25.4, gap, "mm", tol=0.1)
    p.compare("Power-header → analog-header spacing (VIN → A0)", 0.200 * 25.4, pads[9][0] - pads[8][0], "mm", tol=0.1)
    p.compare("Distance between the two header rows", 1.9 * 25.4, pads[15][1] - pads[1][1], "mm", tol=0.1)
    xs = [g.start.X for g in fab] + [g.end.X for g in fab if g.start.X > -27.95]
    ys = [g.start.Y for g in fab] + [g.end.Y for g in fab]
    board_x = max(g.end.X for g in fab) - (-27.94); board_y = 50.8 - (-2.54)
    p.compare("Board length (outline in the library) = 2.7 in", 2.7 * 25.4, board_x, "mm", tol=0.1)
    p.compare("Board width = 2.1 in", 2.1 * 25.4, board_y, "mm", tol=0.1)
    outline = [(-27.94, -2.54), (38.1, -2.54), (38.1, 0), (40.64, 2.54), (40.64, 35.31), (38.1, 37.85), (38.1, 49.28), (36.58, 50.8), (-27.94, 50.8)]
    b = build(pads, outline)
    offgrid = [k for k in range(23, 33) if abs(((pads[k][0] - pads[1][0]) / 2.54) - round((pads[k][0] - pads[1][0]) / 2.54)) > 1e-6]
    p.metric("Pins off the 100-mil grid of pin 1 (all of D8–SCL)", len(offgrid), "")
    fail = b.route(skip=("GND",))
    p.metric("Unrouted connections", sum(len(v) for v in fail.values()), "")
    b.stitch_pad_vias("GND"); b.pour("B", "GND")
    publish(p, b)
    I, vk = led_current()
    p.compare("LED current, 330 Ω + 40 Ω pin (formula with V_f = 2.0 V)", (5 - 2.0) / 370, I, "A", tol=5)
    p.metric("Simulated LED forward voltage", vk, "V")
    p.compare("Total for 4 LEDs vs 200 mA package limit (fraction)", 0.16, 4 * I / 0.2, "", kind="abs", tol=0.05)
    p.metric("Button debounce τ with 35 kΩ internal pull-up and 100 nF", 35e3 * 100e-9 * 1e3, "ms")
    fig, ax = p.fig(1, 1, w=9, h=6)
    from eelab.pcb import plot_board
    plot_board(ax, b, ("B", "F"))
    for k, (x, y) in pads.items():
        ax.plot(x + 27.94, y + 2.54, "+", color="#ffffff", ms=4)
    ax.annotate("160 mil", xy=((pads[22][0] + pads[23][0]) / 2 + 27.94, pads[22][1] + 2.54 + 1.5), color="#ffd166", ha="center", fontsize=9)
    ax.set_title("Shield on the Uno R3 outline (+ = library pin positions)", loc="left", fontsize=10)
    p.save(fig, "shield_top", "The shield's headers sit exactly on the pin positions from the KiCad library, including the 160-mil D7–D8 offset.")
    p.discuss(f"""Taking the mechanical data from the maintained KiCad library instead of a ruler removes the classic shield mistake: every header pin lands on
the library position, the D7→D8 spacing comes out at exactly {gap:.3f} mm (160 mil) and the outline at 2.7 × 2.1 in with the Uno's chamfered corner.
A caution on orientation: KiCad's y axis points down; I interpret the library coordinates in a y-up frame, which gives the familiar top view
(USB side left, digital header along the top, D0 at the right end), and the KiCad exporter flips y back. Before ordering boards, print the top
copper 1:1 and lay it on a real Uno — the cheapest DRC there is. The Uno's four mounting holes are not in this footprint, so the shield has none;
add them from Arduino's official drawing if the shield must be bolted down. Electrically, the LEDs draw {I * 1e3:.1f} mA each (simulated with a
diode fitted to 2.0 V at 10 mA and an assumed 40 Ω driver), {4 * I * 1e3:.0f} mA in total — comfortably inside the ATmega328P's limits.""")
# tol-convention: relative tolerances are in percent
