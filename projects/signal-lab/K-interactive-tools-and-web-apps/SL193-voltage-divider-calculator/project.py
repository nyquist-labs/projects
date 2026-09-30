from eelab import *
from eelab.circuit import Circuit
from eelab.web import node, page, attach

META = dict(
    id="SL-193", title="Voltage divider calculator with live schematic", level="E",
    tools="HTML/SVG/JavaScript tool (GitHub Pages) + Node test harness; references: own MNA circuit simulator and brute-force search",
    summary="An interactive divider calculator: loaded output, Thevenin resistance, worst-case tolerance band, and the best pair of standard "
            "E12/E24/E96 resistors for a target ratio. The JavaScript is verified against the circuit simulator and an exhaustive search.",
    problem="Everyone needs R1 and R2 for 'turn 5 V into 3.3 V'. How close can standard values get, and what does loading do?",
    theory=r"""$V_\text{out}=V_\text{in}\,\frac{R_2\parallel R_L}{R_1+R_2\parallel R_L}$, $R_\text{th}=R_1\parallel R_2$. With $n$ values per decade the logarithmic spacing is $10^{1/n}$, so a single
resistor is within $\pm\tfrac12\cdot\ln 10/n$ (±4.8 % E24). My first guess: choosing *both* resistors gives ~n² ratios per decade pair, so the best ratio error
should be an order of magnitude smaller — ≤ 0.5 % worst case for E24 and ≤ 0.1 % for E96. (This turned out to be wrong; see the discussion.) A ±1 % pair gives at most ±2(1−k)·1 % output error, k = ratio.""",
    method="""(1) 500 random (Vin, R1, R2, RL) cases: calc.js vs the MNA simulator's DC operating point. (2) 400 target ratios 0.05–0.95: calc.js `bestPair` vs a
brute-force Python search over the same series (both constrained to 1 kΩ–1 MΩ total). (3) Worst-case band vs Monte-Carlo corners.""",
    data="Generated test vectors.",
)

BODY = """<div class="card"><div class="row"><svg id="sch" viewBox="0 0 260 200" width="260" height="200" aria-label="schematic"></svg>
<div style="flex:1;min-width:240px"><label>V<sub>in</sub> (V)<input id="vin" type="number" value="5" step="any"></label>
<label>R1 (Ω)<input id="r1" type="number" value="1800" step="any"></label><label>R2 (Ω)<input id="r2" type="number" value="3300" step="any"></label>
<label>Load R<sub>L</sub> (Ω, blank = none)<input id="rl" type="number" step="any"></label><label>Tolerance (%)<input id="tol" type="number" value="1" step="any"></label></div></div>
<p>V<sub>out</sub> = <span class="big" id="vo"></span> &nbsp; R<sub>th</sub> = <b id="rth"></b> &nbsp; <span class="muted" id="wc"></span></p></div>
<div class="card"><b>Find standard values</b><div class="row"><label style="flex:1">Target V<sub>out</sub> (V)<input id="tv" type="number" value="3.3" step="any"></label>
<label style="flex:1">Series<select id="ser"><option>12</option><option selected>24</option><option>96</option></select></label></div>
<p id="best"></p><button id="use">Use these values</button></div>"""

JS = r"""const $=id=>document.getElementById(id);const fmt=v=>v>=1e6?(v/1e6)+' MΩ':v>=1e3?(v/1e3)+' kΩ':v+' Ω';
function sch(){const s=$('sch');s.innerHTML=`<g stroke="currentColor" fill="none" stroke-width="2"><path d="M40 20v20M40 160v20M40 20h80M120 20v25M120 95v20M120 165v15M20 180h200"/>
<rect x="110" y="45" width="20" height="50" rx="3"/><rect x="110" y="115" width="20" height="50" rx="3"/><path d="M120 105h70"/><circle cx="40" cy="100" r="18"/></g>
<text x="32" y="106" fill="currentColor" font-size="14">V</text><text x="138" y="75" fill="currentColor" font-size="13">R1 ${fmt(+$('r1').value)}</text>
<text x="138" y="145" fill="currentColor" font-size="13">R2 ${fmt(+$('r2').value)}</text><text x="194" y="100" fill="var(--acc)" font-size="13">Vout</text>`;}
function upd(){const vin=+$('vin').value,r1=+$('r1').value,r2=+$('r2').value,rl=$('rl').value?+$('rl').value:Infinity,t=+$('tol').value/100;
$('vo').textContent=vout(vin,r1,r2,rl).toFixed(4)+' V';$('rth').textContent=fmt(+rth(r1,r2).toPrecision(4));const w=worstCase(vin,r1,r2,t);
$('wc').textContent=`±${$('tol').value} % parts: ${w[0].toFixed(3)} – ${w[1].toFixed(3)} V (unloaded)`;sch();
const b=bestPair(+$('tv').value/vin,+$('ser').value);$('best').innerHTML=b?`R1 = <b>${fmt(b.r1)}</b>, R2 = <b>${fmt(b.r2)}</b> → ${(vin*b.r2/(b.r1+b.r2)).toFixed(4)} V (ratio error ${(b.err*100).toFixed(3)} %)`:'no pair in range';window._b=b;}
document.querySelectorAll('input,select').forEach(e=>e.oninput=upd);$('use').onclick=()=>{if(window._b){$('r1').value=window._b.r1;$('r2').value=window._b.r2;upd();}};upd();"""


def run(p):
    p.write("web/index.html", page("Voltage divider calculator", "Loaded output, Thevenin resistance, tolerance band and best standard resistor pair.", BODY, inline=JS), "interactive tool")
    attach(p, "web/calc.js", "calculation library (tested)")
    js = p.dir / "web" / "calc.js"
    r = p.rng
    cases = []
    for _ in range(500):
        vin = r.uniform(1, 30); r1, r2 = 10 ** r.uniform(2, 6, 2); rl = 10 ** r.uniform(2, 7) if r.random() < 0.6 else None
        cases.append((vin, r1, r2, rl))
    jsv = np.array(node(js, [["vout", [v, a, b, (l if l else 1e300)]] for v, a, b, l in cases]))
    sim = []
    for v, a, b, l in cases:
        ck = Circuit("div"); ck.V("in", "i", "0", dc=v); ck.R("1", "i", "o", a); ck.R("2", "o", "0", b)
        if l:
            ck.R("L", "o", "0", l)
        sim.append(ck.op()["o"])
    sim = np.array(sim)
    p.compare("Max |Vout(JS) − Vout(MNA simulator)| over 500 random loaded dividers", 0, np.max(np.abs(jsv - sim)), "V", kind="abs", tol=1e-6)
    vals = {s: np.array(node(js, [["decadeValues", [s, 10, 1e7]]])[0]) for s in (12, 24, 96)}
    E96_REF = [1.00,1.02,1.05,1.07,1.10,1.13,1.15,1.18,1.21,1.24,1.27,1.30,1.33,1.37,1.40,1.43,1.47,1.50,1.54,1.58,1.62,1.65,1.69,1.74,1.78,1.82,1.87,1.91,1.96,2.00,2.05,2.10,2.15,2.21,2.26,2.32,2.37,2.43,2.49,2.55,2.61,2.67,2.74,2.80,2.87,2.94,3.01,3.09,3.16,3.24,3.32,3.40,3.48,3.57,3.65,3.74,3.83,3.92,4.02,4.12,4.22,4.32,4.42,4.53,4.64,4.75,4.87,4.99,5.11,5.23,5.36,5.49,5.62,5.76,5.90,6.04,6.19,6.34,6.49,6.65,6.81,6.98,7.15,7.32,7.50,7.68,7.87,8.06,8.25,8.45,8.66,8.87,9.09,9.31,9.53,9.76]
    e96 = np.array(node(js, [["decadeValues", [96, 1, 9.9]]])[0])
    p.compare("E96 table in calc.js vs IEC 60063 values (mismatches)", 0, int(np.sum(np.abs(e96 - np.array(E96_REF)) > 1e-9)), "", kind="abs")
    ratios = np.linspace(0.05, 0.95, 400)
    errs = {}
    for s in (12, 24, 96):
        bp = node(js, [["bestPair", [float(k), s]] for k in ratios])
        e_js = np.array([abs(b["err"]) for b in bp]) * 100
        v = vals[s]; V1, V2 = np.meshgrid(v, v); tot = V1 + V2; ok = (tot >= 1e3) & (tot <= 1e6); rat = np.where(ok, V2 / tot, np.nan)
        e_bf = np.array([np.nanmin(np.abs(rat / k - 1)) for k in ratios]) * 100
        errs[s] = (e_js, e_bf)
        env = (1 - ratios) * np.log(10) / (2 * s) * 100
        if s == 24:
            p.compare("E24: corrected model — worst error ÷ (1−k)·ln10/(2n) envelope (≤ 1 expected)", 1, np.max(e_js / env), "", kind="abs")
        if s != 12:
            p.compare(f"E{s}: worst best-pair ratio error over 400 targets", 0.5 if s == 24 else 0.1, e_js.max(), "%", kind="abs")
        p.metric(f"E{s}: JS search misses the brute-force optimum by at most", np.max(e_js - e_bf), "pp")
    tol = 0.01; mc = []
    for _ in range(4000):
        a, b = 1800 * (1 + r.uniform(-tol, tol)), 3300 * (1 + r.uniform(-tol, tol)); mc.append(5 * b / (a + b))
    lo, hi = node(js, [["worstCase", [5, 1800, 3300, tol]]])[0]
    k = 3300 / 5100
    p.compare("±1 % pair, 5 V → 3.24 V: worst-case half-width = 2(1−k)·1 %·Vout", 2 * (1 - k) * tol * 5 * k, (hi - lo) / 2, "V", tol=2)
    p.metric("Monte-Carlo (uniform ±1 %) spread stays inside the band", int(min(mc) >= lo and max(mc) <= hi), "")
    fig, ax = p.fig(1, 2, w=11)
    for s, c in zip((12, 24, 96), (COLORS[2], COLORS[1], COLORS[0])):
        ax[0].semilogy(ratios, np.maximum(errs[s][0], 1e-4), color=c, lw=1, label=f"E{s}")
    ax[0].semilogy(ratios, (1 - ratios) * np.log(10) / 48 * 100, "--", color=C_PRED, label="(1−k)·ln10/(2·24) envelope")
    style_axes(ax[0], "target ratio Vout/Vin", "|ratio error| of best pair (%)", "Pairs help less than n² suggests")
    ax[1].plot(sim, jsv - sim, ".", color=C_MEAS, ms=3)
    style_axes(ax[1], "Vout from MNA simulator (V)", "JS − simulator (V)", "JavaScript vs circuit simulator", legend=False)
    p.save(fig, "divider", "Best standard-value pair error across target ratios, and agreement of the web tool with the simulator.")
    p.discuss(f"""The web tool's arithmetic matches the circuit simulator to floating-point precision, and its search finds the same optimum as a brute-force
scan. But my headline prediction was wrong: the worst E24 pair error is {errs[24][0].max():.1f} %, not ≤ 0.5 %. The n²-combinations argument
fails because the E-series is (almost) geometric — values are ≈ 10^(i/n) — so the ratio R1/R2 ≈ 10^((i−j)/n) takes only about n distinct values per
decade, the *same* spacing as a single resistor. Since k = 1/(1 + R1/R2), a relative step in R1/R2 moves k by (1−k) times as much, giving the corrected
envelope (1−k)·ln10/(2n): bad for small ratios (attenuating dividers), excellent near k → 1. The historical rounding of E24 values (3.0, 3.3, 3.6 …
are not exactly geometric) is what occasionally beats the envelope. Practical consequences: use E96, use three resistors (series/parallel trim),
or accept the error; and resistor tolerance still matters — a ±1 % pair already moves 3.3 V by ±23 mV. Loading matters more than either: the tool
shows how an RL comparable to R2 collapses the output, which is why dividers feeding ADCs are kept low-impedance or buffered.""")
# tol-convention: relative tolerances are in percent
