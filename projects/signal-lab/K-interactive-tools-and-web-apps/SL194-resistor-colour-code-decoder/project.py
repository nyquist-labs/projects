from eelab import *
from eelab.web import node, page, attach

META = dict(
    id="SL-194", title="Resistor colour-code decoder and encoder", level="E",
    tools="HTML/SVG/JavaScript two-way tool with a clickable band picker; Node test harness vs an independent Python implementation and textbook examples",
    summary="Two-way conversion between resistance and 4-/5-band colour codes with a visual resistor; verified by round-tripping every E24 and E96 value "
            "over nine to ten decades and by counting how many real codes can be misread backwards.",
    problem="Colour codes are easy to misread — especially backwards. Build a converter you can trust and quantify the ambiguity.",
    theory=r"""IEC 60062: digit bands (black 0 … white 9), multiplier band (10^k, gold 0.1, silver 0.01), tolerance band (brown 1 %, red 2 %, gold 5 %, silver 10 % …).
Two significant digits (4-band) represent every E24 value exactly; three digits (5-band) represent E96. Round-trip value → colours → value must be
exact. Reading backwards: a 4-band code with a gold/silver tolerance band can never be read backwards (gold is not a digit), but 5-band 1 % codes
end in brown, which *is* a digit — so I expect many 5-band codes to also decode (wrongly) when reversed.""",
    method="""calc.js `encode`/`decode` run under Node for all E24 values (4-band, 5 %) and E96 values (5-band, 1 %) over decades 0.1 Ω–1 GΩ; decoded values compared with the inputs;
colours compared with an independent Python encoder; five textbook examples; reverse-readability counted.""",
    data="Generated from the IEC 60063 E-series tables.",
)

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
E96 = [1.00,1.02,1.05,1.07,1.10,1.13,1.15,1.18,1.21,1.24,1.27,1.30,1.33,1.37,1.40,1.43,1.47,1.50,1.54,1.58,1.62,1.65,1.69,1.74,1.78,1.82,1.87,1.91,1.96,2.00,2.05,2.10,2.15,2.21,2.26,2.32,2.37,2.43,2.49,2.55,2.61,2.67,2.74,2.80,2.87,2.94,3.01,3.09,3.16,3.24,3.32,3.40,3.48,3.57,3.65,3.74,3.83,3.92,4.02,4.12,4.22,4.32,4.42,4.53,4.64,4.75,4.87,4.99,5.11,5.23,5.36,5.49,5.62,5.76,5.90,6.04,6.19,6.34,6.49,6.65,6.81,6.98,7.15,7.32,7.50,7.68,7.87,8.06,8.25,8.45,8.66,8.87,9.09,9.31,9.53,9.76]
DIG = ["black", "brown", "red", "orange", "yellow", "green", "blue", "violet", "grey", "white"]
MUL = {-2: "silver", -1: "gold", **{k: DIG[k] for k in range(10)}}

BODY = """<div class="card"><svg id="res" viewBox="0 0 420 110" width="420" height="110"></svg>
<div class="row"><button id="b4" class="on">4 bands</button><button id="b5">5 bands</button></div><div id="pick" class="row" style="margin-top:8px"></div>
<p>Value: <span class="big" id="val"></span> <span id="tol" class="muted"></span> <span id="warn" class="muted"></span></p></div>
<div class="card"><label>Resistance (Ω) → colours<input id="in" type="text" value="4700"></label><label>Tolerance (%)<select id="t">
<option>5</option><option>1</option><option>2</option><option>10</option><option>0.5</option></select></label><p id="enc"></p></div>"""

JS = r"""const $=id=>document.getElementById(id);let bands=["yellow","violet","red","gold"];
const opts=(i,n)=>i<n-2?COLS_:i==n-2?Object.keys(M_):Object.keys(T_);const {COLS:COLS_,MULT:M_,TOL:T_,HEX:H_}={COLS,MULT,TOL,HEX};
const fmt=v=>v>=1e6?+(v/1e6).toPrecision(4)+' MΩ':v>=1e3?+(v/1e3).toPrecision(4)+' kΩ':+v.toPrecision(4)+' Ω';
function draw(){const n=bands.length;let s=`<rect x="10" y="50" width="400" height="8" fill="#999"/><rect x="90" y="20" width="240" height="70" rx="28" fill="#d9c7a3"/>`;
bands.forEach((c,i)=>{const x=i<n-1?120+i*36:290;s+=`<rect x="${x}" y="20" width="16" height="70" fill="${H_[c]}" stroke="#0003"><title>${c}</title></rect>`;});$('res').innerHTML=s;
$('pick').innerHTML=bands.map((c,i)=>`<select data-i="${i}" style="width:auto">${opts(i,n).map(o=>`<option ${o==c?'selected':''}>${o}</option>`).join('')}</select>`).join('');
document.querySelectorAll('#pick select').forEach(e=>e.onchange=()=>{bands[+e.dataset.i]=e.value;draw();});
try{const d=decode(bands);$('val').textContent=fmt(d.value);$('tol').textContent='±'+d.tol+' %';}catch(e){$('val').textContent='—';$('tol').textContent=e.message;}
$('warn').textContent=reversible(bands)?'⚠ also decodes when read backwards: '+fmt(decode(bands.slice().reverse()).value):'';}
function enc(){try{const v=parseFloat($('in').value.replace(/k/i,'e3').replace(/M/,'e6'));const t=+$('t').value;const c=encode(v,t>=5?4:5,t);
$('enc').innerHTML=c.map(x=>`<span style="display:inline-block;width:14px;height:14px;background:${H_[x]};border:1px solid #0004;vertical-align:middle"></span> ${x}`).join(' &nbsp; ');bands=c;draw();}
catch(e){$('enc').textContent=e.message;}}
$('b4').onclick=()=>{bands=encode(decode(bands).value,4,5);$('b4').classList.add('on');$('b5').classList.remove('on');draw();};
$('b5').onclick=()=>{bands=encode(decode(bands).value,5,1);$('b5').classList.add('on');$('b4').classList.remove('on');draw();};
$('in').oninput=enc;$('t').onchange=enc;draw();"""


def py_encode(v, nd):
    e = int(np.floor(np.log10(v))) - (nd - 1)
    d = int(round(v / 10 ** e))
    if d >= 10 ** nd:
        d //= 10; e += 1
    return [DIG[int(c)] for c in str(d).zfill(nd)] + [MUL[e]]


def run(p):
    p.write("web/index.html", page("Resistor colour code", "Click the bands, or type a value. Warns when a code can also be read backwards.", BODY, inline=JS), "interactive tool")
    attach(p, "web/calc.js", "encode/decode library (tested)")
    js = p.dir / "web" / "calc.js"
    vals4 = [round(m * 10 ** d, 12) for d in range(-1, 9) for m in E24]
    vals5 = [round(m * 10 ** d, 12) for d in range(0, 9) for m in E96]
    sub = node(js, [["encode", [round(m * 0.1, 12), 5, 1]] for m in E96])
    p.metric("E96 values below 1 Ω that 5 bands cannot encode (smallest multiplier is silver ×0.01)", sum(isinstance(x, dict) and "error" in x for x in sub), f"of {len(E96)}")
    enc4 = node(js, [["encode", [v, 4, 5]] for v in vals4]); enc5 = node(js, [["encode", [v, 5, 1]] for v in vals5])
    dec4 = node(js, [["decode", [c]] for c in enc4]); dec5 = node(js, [["decode", [c]] for c in enc5])
    bad = sum(abs(d["value"] / v - 1) > 1e-9 for d, v in zip(dec4 + dec5, vals4 + vals5))
    p.compare(f"Round-trip failures over {len(vals4)} E24 + {len(vals5)} E96 values (E24 0.1 Ω–910 MΩ, E96 1 Ω–976 MΩ)", 0, bad, "", kind="abs")
    mism = sum(c[:-1] != py_encode(v, 2) for c, v in zip(enc4, vals4)) + sum(c[:-1] != py_encode(v, 3) for c, v in zip(enc5, vals5))
    p.compare("Colour mismatches vs independent Python encoder", 0, mism, "", kind="abs")
    book = [(["brown", "black", "orange", "gold"], 10e3), (["yellow", "violet", "red", "gold"], 4.7e3), (["red", "red", "brown", "gold"], 220),
            (["brown", "black", "black", "red", "brown"], 10e3), (["orange", "orange", "black", "gold", "brown"], 33.0)]
    got = node(js, [["decode", [c]] for c, _ in book])
    p.compare("Textbook examples decoded correctly", len(book), sum(abs(g["value"] - v) < 1e-9 for g, (_, v) in zip(got, book)), "", kind="abs")
    rev4 = node(js, [["reversible", [c]] for c in enc4]); rev5 = node(js, [["reversible", [c]] for c in enc5])
    p.compare("4-band 5 % codes readable backwards (gold is not a digit → 0 %)", 0, np.mean(rev4) * 100, "%", kind="abs")
    # prediction for 5-band 1 %: reversed code = [brown, mult, d3, d2, d1]; needs mult ∈ digit colours (not gold/silver) and d1 ∈ tolerance colours
    tolset = {"brown", "red", "green", "blue", "violet", "grey"}
    pred5 = np.mean([(c[3] in DIG) and (c[0] in tolset) for c in enc5]) * 100
    p.compare("5-band 1 % codes that also decode when read backwards", pred5, np.mean(rev5) * 100, "%", kind="abs")
    fig, ax = p.fig(1, 1, w=9, h=3.2)
    first = [c[0] for c in enc5]
    cnt = [sum(f == c for f in first) for c in DIG[1:]]
    revc = [sum(r and f == c for r, f in zip(rev5, first)) for c in DIG[1:]]
    x = np.arange(9)
    ax.bar(x, cnt, color=COLORS[7], label="all 5-band codes"); ax.bar(x, revc, color=C_MEAS, label="also valid backwards")
    ax.set_xticks(x); ax.set_xticklabels(DIG[1:], rotation=30)
    style_axes(ax, "first band colour", "number of E96 codes", "Backwards-readable 5-band codes")
    p.save(fig, "reversible", "A 5-band code is ambiguous when its first digit colour is also a tolerance colour and its multiplier is a digit.")
    p.discuss(f"""Every E24 value from 0.1 Ω and every E96 value from 1 Ω up to the GΩ range survives value → colours → value exactly, and the colours agree with an independently written encoder,
so the tool is trustworthy as a converter. (Sub-ohm precision values cannot be written in five bands at all — three digits × 0.01 bottoms out at
1.00 Ω — so such parts are marked with printed codes instead.) The more interesting result is ambiguity: 4-band 5 % resistors can never be read backwards
because gold is not a digit colour, but {np.mean(rev5) * 100:.0f} % of 5-band 1 % codes decode to a *different valid value* when reversed — exactly the
fraction predicted by counting codes whose first digit is also a tolerance colour and whose multiplier band is a digit colour. That is why
5-band parts usually have a wider gap before the tolerance band, and why the tool shows the warning.""")
# tol-convention: relative tolerances are in percent
