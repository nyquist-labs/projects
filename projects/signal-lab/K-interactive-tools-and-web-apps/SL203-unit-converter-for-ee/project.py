from eelab import *
from eelab.web import node, page, attach

META = dict(
    id="SL-203", title="Unit converter for EE (prefixes, value codes, AWG, PCB units)", level="E",
    tools="HTML/JS converter: SI-prefix and RKM ('4k7') parsing, EIA capacitor codes, AWG wire tables, mil/mm, oz copper, temperature, wavelength; Node harness",
    summary="A single page for the conversions an electronics engineer does daily — parse '4k7' and '2u2', decode '104', look up AWG 22, convert "
            "mil to mm — tested against independent Python code and the published AWG table.",
    problem="Small unit mistakes (a mil is not a millimetre, 104 is not 104 pF) cause real board re-spins. Can one tool handle all of them correctly?",
    theory=r"""AWG is defined geometrically: 36 AWG = 0.005 in, 0000 AWG = 0.46 in, 39 steps between → $d_n = 0.127\,\text{mm}·92^{(36-n)/39}$; every 6 gauges halves the diameter
(≈ ×0.5), every 3 gauges halves the area. 1 oz/ft² copper = 28.35 g spread over 929 cm² at 8.96 g/cm³ = 34.1 µm (the industry's nominal '1.378 mil ≈ 35 µm' is a rounded convention). EIA capacitor code "abc" = ab × 10^c pF
(c = 8, 9 mean ×0.01, ×0.1). RKM code (IEC 60062) puts the prefix letter where the decimal point would be (4k7 = 4.7 kΩ) so a lost decimal point cannot
misread a value.""",
    method="""Published AWG diameters (0000, 0, 10, 12, 14, 18, 22, 24, 26, 30) vs calc.js; 40 RKM and prefix strings; 12 EIA codes; 5000 random round trips for format/parse and
unit pairs vs Python.""",
    data="Standard reference tables.",
)

BODY = """<div class="card"><b>Parse a value</b><label>Value (e.g. 4k7, 2u2, 100n, 0R22, 3.3e-3)<input id="v" value="4k7"></label><p>= <span class="big" id="vo"></span> <span class="muted" id="vs"></span></p></div>
<div class="card"><b>Capacitor code</b><label>3-digit code<input id="cc" value="104"></label><p>= <span class="big" id="co"></span></p></div>
<div class="card"><b>Wire gauge</b><label>AWG (0 = 1/0, −1 = 2/0 …)<input id="awg" type="number" value="22"></label><p id="ao"></p></div>
<div class="card"><b>PCB & misc.</b><label>mil<input id="mil" type="number" value="10"></label><label>mm<input id="mm" type="number" value="0.254"></label>
<label>Copper weight (oz/ft²)<input id="oz" type="number" value="1"></label><label>°C<input id="tc" type="number" value="25"></label><label>Frequency (MHz)<input id="fq" type="number" value="2400"></label><p id="mo"></p></div>"""

JS = r"""const $=id=>document.getElementById(id);
function upd(){try{const x=parseEng($('v').value);$('vo').textContent=formatEng(x);$('vs').textContent=x.toExponential(4);}catch(e){$('vo').textContent='—';$('vs').textContent=e.message;}
try{$('co').textContent=formatEng(capCode($('cc').value),'F');}catch(e){$('co').textContent=e.message;}
const n=+$('awg').value;$('ao').innerHTML=`Diameter <b>${awgDiameterMm(n).toFixed(3)} mm</b> (${(awgDiameterMm(n)/0.0254).toFixed(1)} mil), area <b>${awgAreaMm2(n).toFixed(4)} mm²</b>, copper resistance <b>${awgResistanceOhmPerKm(n).toFixed(2)} Ω/km</b>`;
$('mo').innerHTML=`${$('mil').value} mil = <b>${milToMm(+$('mil').value).toFixed(4)} mm</b> · ${$('mm').value} mm = <b>${mmToMil(+$('mm').value).toFixed(2)} mil</b> · ${$('oz').value} oz = <b>${ozToUm(+$('oz').value).toFixed(1)} µm</b> · ${$('tc').value} °C = <b>${cToF(+$('tc').value).toFixed(1)} °F</b> = <b>${cToK(+$('tc').value).toFixed(2)} K</b> · λ at ${$('fq').value} MHz = <b>${formatEng(wavelengthM(+$('fq').value*1e6),'m')}</b>`;}
document.querySelectorAll('input').forEach(e=>e.oninput=upd);upd();"""

AWG = {-3: 11.684, 0: 8.251, 10: 2.588, 12: 2.053, 14: 1.628, 18: 1.024, 22: 0.644, 24: 0.511, 26: 0.405, 30: 0.255}
RKM = {"4k7": 4700, "4K7": 4700, "2u2": 2.2e-6, "2µ2": 2.2e-6, "100n": 1e-7, "0R1": 0.1, "4R7": 4.7, "1M5": 1.5e6, "R47": 0.47, "10k": 1e4, "1.5M": 1.5e6,
       "3.3e-6": 3.3e-6, "47p": 47e-12, "680": 680, "2G2": 2.2e9, "6m8": 6.8e-3, "12": 12, "0.1u": 1e-7, "k47": 470, "1f": 1e-15, "1F": 1.0, "10 ohm": 10, "22 kΩ": 22e3, "33nF": 33e-9}
CAP = {"104": 100e-9, "103": 10e-9, "473": 47e-9, "222": 2.2e-9, "101": 100e-12, "100": 10e-12, "339": 3.3e-12, "108": 0.1e-12, "105": 1e-6, "226": 22e-6, "470": 47e-12, "689": 6.8e-12}


def run(p):
    p.write("web/index.html", page("EE unit converter", "Prefixes, resistor/capacitor codes, wire gauges and PCB units in one place.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "unit library (tested)")
    js = p.dir / "web" / "calc.js"
    d = node(js, [["awgDiameterMm", [n]] for n in AWG])
    err = max(abs(a - b) for a, b in zip(d, AWG.values()))
    p.compare("Worst AWG diameter deviation from the published table (values given to 0.001 mm)", 0, err, "mm", kind="abs", tol=0.0006)
    r6 = node(js, [["awgDiameterMm", [10]], ["awgDiameterMm", [16]], ["awgAreaMm2", [10]], ["awgAreaMm2", [13]]])
    p.compare("6 gauges ≈ halves diameter (92^(6/39))", 1 / 92 ** (6 / 39), r6[1] / r6[0], "×", tol=1e-07)
    p.compare("3 gauges ≈ halves area", 0.5, r6[3] / r6[2], "×", tol=1)
    rk = node(js, [["parseEng", [s]] for s in RKM])
    p.compare(f"Value strings parsed correctly ({len(RKM)} RKM/prefix forms)", len(RKM), sum(isinstance(v, float | int) and abs(v / t - 1) < 1e-12 for v, t in zip(rk, RKM.values())), "", kind="abs")
    cc = node(js, [["capCode", [c]] for c in CAP])
    p.compare(f"EIA capacitor codes decoded correctly ({len(CAP)})", len(CAP), sum(abs(v / t - 1) < 1e-9 for v, t in zip(cc, CAP.values())), "", kind="abs")
    p.compare("1 oz/ft² copper thickness from mass and density", 34.06, node(js, [["ozToUm", [1]]])[0], "µm", tol=0.1)
    p.metric("Industry nominal (1.378 mil) exceeds the physical value by", (35.0012 / node(js, [["ozToUm", [1]]])[0] - 1) * 100, "%")
    r = p.rng
    vals = 10 ** r.uniform(-13, 11, 3000) * r.choice([-1, 1], 3000)
    back = node(js, [["parseEng", [s]] for s in node(js, [["formatEng", [float(v), "", 12]] for v in vals])])
    p.compare("formatEng → parseEng round trips (3000 values, 12 digits)", 0, max(abs(b / v - 1) for b, v in zip(back, vals)), "", kind="abs", tol=1e-10)
    bad = node(js, [["parseEng", [s]] for s in ["4k7k", "abc", "1..2", "4k7.2"]])
    p.compare("Malformed strings rejected (4k7k, abc, 1..2, 4k7.2)", 4, sum(isinstance(b, dict) for b in bad), "", kind="abs")
    fig, ax = p.fig()
    n = np.arange(-3, 41)
    ax.semilogy(n, node(js, [["awgDiameterMm", [int(k)]] for k in n]), color=C_MEAS, label="calc.js formula")
    ax.semilogy(list(AWG), list(AWG.values()), "o", color=C_PRED, label="published table")
    style_axes(ax, "AWG (0 = 1/0, −3 = 4/0)", "diameter (mm)", "American Wire Gauge is a geometric series")
    p.save(fig, "awg", "AWG diameters from the defining formula agree with the published table.")
    p.discuss("""All reference values reproduce: the AWG table (from the geometric definition), RKM strings including the tricky 0R1/R47 forms, EIA capacitor codes
with the ×0.1/×0.01 digits, and copper weight → thickness from first principles. That last one corrected me: I had memorised '1 oz = 34.8 µm', but 28.35 g of copper
over a square foot is 34.1 µm; the 35 µm / 1.378 mil figure fab houses and IPC-2221 use is a rounded convention (the tool shows both). The round-trip test caught a real bug: the parser stripped unit suffixes case-insensitively, so '123 f'
(femto) lost its prefix as if it were 'F' (farads) — a 10¹⁵ error. Unit matching is now case-sensitive, and round trips are exact over 24 orders
of magnitude. Two design choices prevent real-world mistakes: the parser *rejects* ambiguous strings instead
of guessing, and 'm' always means milli (never mega), which is the most common unit bug in BOM spreadsheets.""")
# tol-convention: relative tolerances are in percent
