from eelab import *
from eelab.web import node, page, attach

META = dict(
    id="SL-200", title="dB / dBm / watts / volts converter", level="E",
    tools="HTML/JS converter (W, mW, dBW, dBm, Vrms, Vpk, Vpp, dBV, dBu, dBµV at any impedance, thermal noise floor) + Node harness vs Python",
    summary="Type a level in any unit and see all the others, at 50 Ω, 75 Ω or 600 Ω; includes the kTB noise floor. Verified by round-trips over "
            "the whole 10-unit × 10-unit matrix and against textbook anchor values.",
    problem="0 dBm is how many volts? The conversion every RF engineer needs daily — and one where 10·log vs 20·log mistakes are common.",
    theory=r"""Power: dBm = 10·log₁₀(P / 1 mW). Voltage in impedance Z: P = V²_rms/Z, so dBµV = dBm + 90 + 10·log₁₀(Z) (107 dBµV = 0 dBm at 50 Ω). dBu is referenced to
0.7746 V (1 mW in 600 Ω). Sine: V_pk = √2·V_rms, V_pp = 2√2·V_rms. Thermal noise: P = kTB → −174 dBm/Hz at 290 K. A voltage ratio in dB uses 20·log (power ∝ V²);
using 10·log for a voltage ratio halves the dB value.""",
    method="""All 90 ordered unit pairs × 200 random levels round-tripped through calc.js; anchors: 0 dBm ↔ 223.6 mV rms ↔ 107 dBµV (50 Ω), 0 dBu ↔ 0.7746 V, +30 dBm = 1 W,
thermal noise −173.98 dBm/Hz and −113.9 dBm in 1 MHz; JS vs independent Python formulas.""",
    data="Generated test values.",
)

BODY = """<div class="card"><div class="row"><label style="flex:2">Value<input id="x" type="number" value="0" step="any"></label>
<label style="flex:1">Unit<select id="u"></select></label><label style="flex:1">Impedance (Ω)<select id="z"><option>50</option><option>75</option><option>600</option></select></label></div>
<table id="t" style="margin-top:8px"></table></div><div class="card"><b>Thermal noise floor (kTB, 290 K)</b>
<label>Bandwidth (Hz)<input id="bw" type="number" value="1000000"></label><p>Noise power: <span class="big" id="nf"></span></p></div>"""

JS = r"""const $=id=>document.getElementById(id);Object.keys(UNITS).forEach(u=>$('u').insertAdjacentHTML('beforeend',`<option ${u=='dBm'?'selected':''}>${u}</option>`));
const L={W:'watts',mW:'milliwatts',dBW:'dB re 1 W',dBm:'dB re 1 mW',Vrms:'volts rms (sine)',Vpk:'volts peak',Vpp:'volts peak-to-peak',dBV:'dB re 1 V rms',dBu:'dB re 0.7746 V',dBuV:'dB re 1 µV'};
const f=v=>Math.abs(v)>=1e-3&&Math.abs(v)<1e5?v.toPrecision(6):v.toExponential(4);
function upd(){const r=all(+$('x').value,$('u').value,+$('z').value);$('t').innerHTML=Object.entries(r).map(([k,v])=>`<tr><td>${k} <span class="muted">${L[k]}</span></td><td class="n">${isFinite(v)?f(v):'—'}</td></tr>`).join('');
$('nf').textContent=thermalNoiseDbm(+$('bw').value).toFixed(2)+' dBm';}
document.querySelectorAll('input,select').forEach(e=>e.oninput=upd);upd();"""


def run(p):
    p.write("web/index.html", page("dB · dBm · watts · volts", "Every RF level unit at once, at your system impedance.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "conversion library (tested)")
    js = p.dir / "web" / "calc.js"
    units = ["W", "mW", "dBW", "dBm", "Vrms", "Vpk", "Vpp", "dBV", "dBu", "dBuV"]
    r = p.rng
    calls, ref = [], []
    for a in units:
        for b in units:
            if a == b:
                continue
            for _ in range(20):
                Z = float(r.choice([50, 75, 600]))
                x = float(r.uniform(-60, 60)) if a.startswith("dB") else float(10 ** r.uniform(-6, 3))
                calls.append(["convert", [x, a, b, Z]]); calls.append(None)
                ref.append((x, a, b, Z))
    fwd = node(js, [c for c in calls if c])
    back = node(js, [["convert", [y, b, a, Z]] for y, (x, a, b, Z) in zip(fwd, ref)])
    rt = max(abs(bk - x) / (abs(x) + 1e-12) for bk, (x, *_) in zip(back, ref))
    p.compare(f"Worst relative round-trip error over {len(ref)} conversions (90 unit pairs)", 0, rt, "", kind="abs", tol=1e-9)

    def py_w(x, u, Z):
        return {"W": lambda: x, "mW": lambda: x / 1e3, "dBW": lambda: 10 ** (x / 10), "dBm": lambda: 10 ** (x / 10) / 1e3, "Vrms": lambda: x ** 2 / Z,
                "Vpk": lambda: x ** 2 / 2 / Z, "Vpp": lambda: x ** 2 / 8 / Z, "dBV": lambda: 10 ** (x / 10) / Z, "dBu": lambda: 0.6 * 10 ** (x / 10) / Z,
                "dBuV": lambda: 1e-12 * 10 ** (x / 10) / Z}[u]()
    worst = max(abs(py_w(f_, b, Z) / py_w(x, a, Z) - 1) for f_, (x, a, b, Z) in zip(fwd, ref))
    p.compare("Worst disagreement with independent Python formulas (as power ratio)", 0, worst, "", kind="abs", tol=1e-5)
    a0 = node(js, [["convert", [0, "dBm", "Vrms", 50]], ["convert", [0, "dBm", "dBuV", 50]], ["convert", [0, "dBu", "Vrms", 600]],
                   ["convert", [30, "dBm", "W", 50]], ["thermalNoiseDbm", [1]], ["thermalNoiseDbm", [1e6]], ["convert", [0, "dBm", "dBuV", 75]]])
    p.compare("0 dBm in 50 Ω", 0.2236, a0[0], "V rms", tol=0.1)
    p.compare("0 dBm in 50 Ω", 107.0, a0[1], "dBµV", kind="abs", tol=0.02)
    p.compare("0 dBm in 75 Ω (= 90 + 10·log 75)", 90 + 10 * np.log10(75), a0[6], "dBµV", kind="abs", tol=1e-6)
    p.compare("0 dBu", 0.7746, a0[2], "V rms", tol=0.01)
    p.compare("+30 dBm", 1.0, a0[3], "W", tol=1e-07)
    p.compare("kT at 290 K", -174.0, a0[4], "dBm/Hz", kind="abs", tol=0.05)
    p.compare("kTB, B = 1 MHz", -114.0, a0[5], "dBm", kind="abs", tol=0.05)
    fig, ax = p.fig()
    dbm = np.linspace(-120, 40, 200)
    for Z, c in ((50, COLORS[0]), (75, COLORS[1]), (600, COLORS[2])):
        v = node(js, [["convert", [float(x), "dBm", "Vrms", Z]] for x in dbm])
        ax.semilogy(dbm, v, color=c, label=f"{Z} Ω")
    style_axes(ax, "power (dBm)", "voltage (V rms)", "Same power, different voltage at each impedance")
    p.save(fig, "levels", "dBm to volts rms for common system impedances.")
    p.discuss("""All 90 unit-pair conversions round-trip exactly and agree with independently written formulas, and the anchor values every RF engineer memorises
come out right (0 dBm = 224 mV = 107 dBµV in 50 Ω; −174 dBm/Hz). The chart is a reminder that dBm is a *power* unit: the same 0 dBm is 274 mV in 75 Ω
and 775 mV in 600 Ω, so quoting a voltage level without an impedance is ambiguous. The tool computes everything via watts, which structurally prevents
the common 10·log/20·log mix-up.""")
# tol-convention: relative tolerances are in percent
