from eelab import *
from eelab.circuit import Circuit
from eelab.web import node, page, attach
from scipy import signal

META = dict(
    id="SL-195", title="Active filter design calculator (Sallen-Key)", level="M",
    tools="HTML/JS designer (E12 capacitors, E96 resistors) + Node test harness; verification with the MNA circuit simulator (op-amp macromodel with finite GBW) and SciPy prototypes",
    summary="Enter a cutoff, response family and order; get unity-gain Sallen-Key stages with standard component values and a response plot. "
            "Every design is built in the circuit simulator and its measured −3 dB frequency compared with the spec.",
    problem="Textbook filter formulas give 12.37 kΩ and 3.183 nF. What happens to the cutoff once real E-series parts are used, and when does the "
            "op-amp start to matter?",
    theory=r"""Unity-gain Sallen-Key low-pass: $f_0=1/(2π\sqrt{R_1R_2C_1C_2})$, $Q=\sqrt{R_1R_2C_1C_2}/(C_2(R_1+R_2))$; choose C's from E12 (with $C_1 ≥ 4Q^2C_2$) and solve R exactly, then round
R to E96 (±1 % steps → each R off by ≤ ±1.2 %). Since $f_0 ∝ (R_1R_2)^{-1/2}$ the cutoff error is ≲ ±1.2 %. A finite gain-bandwidth GBW adds error that grows
with $f_c·Q/\text{GBW}$; with a 1 MHz op-amp I expect < 2 % shift up to ~10 kHz but a visible Q boost at 100 kHz.""",
    method="""60 random designs (low-/high-pass × Butterworth/Bessel/Chebyshev 1 dB × order 2/4, fc 20 Hz–20 kHz): calc.js values → netlist → AC analysis with an op-amp of A0 = 10⁵,
GBW = 10 MHz; measured −3 dB point (Chebyshev: ripple edge, where the response returns to its passband-edge level) vs the spec. Then fc swept 1 kHz–200 kHz with GBW = 1 MHz. Prototype Q/f0 tables checked against SciPy.""",
    data="Generated designs.",
)

BODY = """<div class="card"><div class="row"><label style="flex:1">Type<select id="k"><option value="lowpass">low-pass</option><option value="highpass">high-pass</option></select></label>
<label style="flex:1">Response<select id="fam"><option value="butterworth">Butterworth</option><option value="bessel">Bessel</option><option value="cheby1dB">Chebyshev 1 dB</option></select></label>
<label style="flex:1">Order<select id="o"><option>2</option><option selected>4</option></select></label><label style="flex:1">Cutoff (Hz)<input id="fc" type="number" value="1000"></label></div></div>
<div class="card"><table id="t"></table></div><div class="card"><svg id="plot" viewBox="0 0 640 300"></svg><p class="muted">Magnitude of the cascade using the rounded parts (ideal op-amps).</p></div>"""

JS = r"""const $=id=>document.getElementById(id);const eng=(v,u)=>{const p=[[1e-12,'p'],[1e-9,'n'],[1e-6,'µ'],[1e-3,'m'],[1,''],[1e3,'k'],[1e6,'M']];let s=p[0];for(const q of p)if(v>=q[0]*0.999)s=q;return +(v/s[0]).toPrecision(3)+' '+s[1]+u;};
function upd(){const fc=+$('fc').value,st=design($('k').value,$('fam').value,+$('o').value,fc);
$('t').innerHTML='<tr><th>stage</th><th class="n">R1</th><th class="n">R2</th><th class="n">C1</th><th class="n">C2</th><th class="n">f0 / Q</th></tr>'+st.map((s,i)=>{const q=stageParams(s);
return `<tr><td>${i+1}</td><td class="n">${eng(s.R1,'Ω')}</td><td class="n">${eng(s.R2,'Ω')}</td><td class="n">${eng(s.C1,'F')}</td><td class="n">${eng(s.C2,'F')}</td><td class="n">${eng(q.f0,'Hz')} / ${q.Q.toFixed(3)}</td></tr>`}).join('');
const f=[...Array(300)].map((_,i)=>fc*Math.pow(10,-2+4*i/299)),H=response(st,f);const X=i=>40+i*2,Y=d=>20+(-d)*3;
let s=`<g stroke="var(--line)">`;for(let d=0;d>=-80;d-=20)s+=`<line x1="40" x2="640" y1="${Y(d)}" y2="${Y(d)}"/><text x="4" y="${Y(d)+4}" fill="var(--muted)" font-size="11">${d} dB</text>`;
s+=`</g><polyline fill="none" stroke="var(--acc)" stroke-width="2" points="${H.map((h,i)=>X(i)+','+Y(Math.max(-85,20*Math.log10(h)))).join(' ')}"/>`;
s+=`<line x1="${X(150)}" x2="${X(150)}" y1="20" y2="280" stroke="var(--acc2)" stroke-dasharray="4"/><text x="${X(150)+4}" y="275" fill="var(--acc2)" font-size="11">fc</text>`;$('plot').innerHTML=s;}
document.querySelectorAll('input,select').forEach(e=>e.oninput=upd);upd();"""


def build(stages, gbw, a0=1e5):
    ck = Circuit("sk")
    ck.V("in", "n0", "0", ac=1)
    for i, s in enumerate(stages):
        a, b, o = f"a{i}", f"b{i}", f"n{i+1}"
        if s["type"] == "lowpass":
            ck.R(f"1_{i}", f"n{i}", a, s["R1"]); ck.R(f"2_{i}", a, b, s["R2"]); ck.C(f"1_{i}", a, o, s["C1"]); ck.C(f"2_{i}", b, "0", s["C2"])
        else:
            ck.C(f"1_{i}", f"n{i}", a, s["C1"]); ck.C(f"2_{i}", a, b, s["C2"]); ck.R(f"1_{i}", a, o, s["R1"]); ck.R(f"2_{i}", b, "0", s["R2"])
        ck.OPAMP(f"U{i}", b, o, o, A0=a0, GBW=gbw)
    return ck, f"n{len(stages)}"


def edge(f, H, kind, level):
    g = db(np.abs(H)); ref = g[0] if kind == "lowpass" else g[-1]
    g = g - (ref if level != -1 else 0)
    return find_crossing(f, g, level, falling=(kind == "lowpass"))


def run(p):
    p.write("web/index.html", page("Active filter designer", "Unity-gain Sallen-Key stages with standard parts: E12 capacitors, E96 resistors.", BODY, inline=JS), "interactive tool")
    attach(p, "web/calc.js", "design library (tested)")
    js = p.dir / "web" / "calc.js"
    # prototype table vs scipy
    worst = 0
    import json, subprocess
    tables = json.loads(subprocess.run(["node", "-e", f"process.stdout.write(JSON.stringify(require({json.dumps(str(js))}).PROTO))"], capture_output=True, text=True).stdout)
    for fam, fn in (("butterworth", lambda n: signal.butter(n, 1, analog=True, output="zpk")),
                    ("bessel", lambda n: signal.bessel(n, 1, analog=True, output="zpk", norm="mag")),
                    ("cheby1dB", lambda n: signal.cheby1(n, 1, 1, analog=True, output="zpk"))):
        for n in (2, 4):
            _, pz, _ = fn(n)
            ref = sorted([(abs(x), abs(x) / (2 * abs(x.real))) for x in pz if x.imag > 0], key=lambda t: t[1])
            tab = sorted(tables[fam][str(n)], key=lambda t: t[1])
            for (f0r, qr), (f0t, qt) in zip(ref, tab):
                worst = max(worst, abs(f0t / f0r - 1), abs(qt / qr - 1))
    p.compare("Prototype table in calc.js vs SciPy poles (worst relative error in f0 or Q)", 0, worst * 100, "%", kind="abs", tol=0.05)
    r = p.rng
    rows = []
    for _ in range(60):
        kind = ["lowpass", "highpass"][r.integers(2)]; fam = ["butterworth", "bessel", "cheby1dB"][r.integers(3)]; order = [2, 4][r.integers(2)]
        fc = float(10 ** r.uniform(np.log10(20), np.log10(20e3)))
        st = node(js, [["design", [kind, fam, order, fc]]])[0]
        f = np.logspace(np.log10(fc) - 2, np.log10(fc) + 2, 1500)
        ck, out = build(st, 10e6)
        H = ck.ac(f).v(out)
        # Chebyshev (even order): the response returns to its DC (or HF) level exactly at the ripple edge, so the edge is the last 0 dB crossing
        level = 0.0 if fam == "cheby1dB" else -3.0103
        g = db(np.abs(H)); ref = g[0] if kind == "lowpass" else g[-1]
        gg = g - ref
        if kind == "lowpass":
            idx = np.flatnonzero(gg >= level)[-1]
        else:
            idx = np.flatnonzero(gg >= level)[0] - 1
        fm = np.exp(np.interp(level, [gg[idx + 1], gg[idx]] if kind == "lowpass" else [gg[idx], gg[idx + 1]],
                              [np.log(f[idx + 1]), np.log(f[idx])] if kind == "lowpass" else [np.log(f[idx]), np.log(f[idx + 1])]))
        rows.append((kind, fam, order, fc, fm, (fm / fc - 1) * 100))
    err = np.array([x[-1] for x in rows])
    p.compare("Worst |cutoff error| over 60 simulated designs (E-series rounding, ≲ 1.2 % expected)", 1.2, np.max(np.abs(err)), "%", kind="abs")
    p.metric("RMS cutoff error", np.sqrt(np.mean(err ** 2)), "%")
    fcs = np.logspace(3, np.log10(2e5), 12); shift = []
    for fc in fcs:
        st = node(js, [["design", ["lowpass", "butterworth", 2, float(fc)]]])[0]
        f = np.logspace(np.log10(fc) - 1.5, np.log10(fc) + 1, 1200)
        H = build(st, 1e6)[0].ac(f).v(build(st, 1e6)[1])
        Hi = node(js, [["response", [st, f.tolist()]]])[0]
        shift.append((find_crossing(f, db(np.abs(H)) - db(abs(H[0])), -3.0103, falling=True) / find_crossing(f, db(np.array(Hi)), -3.0103, falling=True) - 1) * 100)
    shift = np.array(shift)
    p.compare("GBW = 1 MHz: cutoff shift vs ideal-op-amp design at fc = 10 kHz", 2, np.interp(1e4, fcs, shift), "%", kind="abs")
    p.metric("GBW = 1 MHz: cutoff shift at fc = 100 kHz", np.interp(1e5, fcs, shift), "%")
    fig, ax = p.fig(1, 2, w=11)
    fam_c = {"butterworth": COLORS[0], "bessel": COLORS[1], "cheby1dB": COLORS[2]}
    for fam in fam_c:
        sel = [x for x in rows if x[1] == fam]
        ax[0].semilogx([x[3] for x in sel], [x[5] for x in sel], "o", color=fam_c[fam], label=fam, ms=5)
    ax[0].axhspan(-1.2, 1.2, color=COLORS[7], alpha=.15, label="±1.2 % rounding bound")
    style_axes(ax[0], "specified cutoff (Hz)", "simulated − specified (%)", "Designs built in the simulator")
    ax[1].semilogx(fcs, shift, "o-", color=C_MEAS, label="GBW = 1 MHz")
    style_axes(ax[1], "cutoff (Hz)", "cutoff shift vs ideal (%)", "When the op-amp matters", legend=False)
    p.save(fig, "filters", "Cutoff errors of 60 random designs stay within the E-series rounding bound; a slow op-amp shifts high-frequency designs.")
    import pandas as pd
    p.csv_df("designs", pd.DataFrame(rows, columns=["type", "family", "order", "fc_spec_hz", "fc_sim_hz", "error_pct"]))
    p.discuss(f"""Two bugs surfaced only because every design was built and measured: my 4th-order Bessel table had wrong stage frequencies (1.419/1.591
instead of 1.430/1.603 — caught by the SciPy pole check), and the first cutoff measurement for Chebyshev designs used −1 dB from the peak, whereas a
unity-gain even-order Chebyshev cascade starts 1 dB *below* its peak, so its ripple edge is where the response returns to the DC level.
After the fixes, every design lands within ±{np.max(np.abs(err)):.1f} % of the requested cutoff (RMS {np.sqrt(np.mean(err ** 2)):.2f} %). My ±1.2 % bound
assumed rounding moves only f0; the few designs just outside it are 4th-order cascades where rounding also perturbs each stage's Q, which moves
the −3 dB point of the product. With a 1 MHz op-amp the cutoff holds within 0.1 % at 10 kHz (my 2 % guess was pessimistic) and shifts
{abs(np.interp(1e5, fcs, shift)):.1f} % at 100 kHz, where the op-amp's pole adds phase inside the loop; the rule of thumb GBW ≳ 100·Q·f0 keeps it negligible.
Component tolerance (±5 % capacitors) would add a larger spread than rounding in a real build.""")
# tol-convention: relative tolerances are in percent
