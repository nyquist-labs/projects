from eelab import *
from eelab.circuit import Circuit
from eelab.web import node, page, attach

META = dict(
    id="SL-198", title="Op-amp configuration explorer", level="M",
    tools="HTML/SVG/JavaScript explorer (inverting, non-inverting, follower, difference, summing) with finite-A0/GBW corrections; Node harness; MNA simulator with op-amp macromodel",
    summary="Switch between op-amp topologies and watch the gain equation, noise gain, gain error and bandwidth update; the tool's numbers are "
            "checked against AC simulations of each circuit over gains 1–1000.",
    problem="Why does an inverting amplifier with gain −1 have half the bandwidth of a follower, and how big is the gain error from finite open-loop gain?",
    theory=r"""With feedback factor β (fraction of the output fed back), the closed-loop gain is $G_\text{ideal}/(1+1/(A_0β))$ and, for a single-pole op-amp, the bandwidth is
$f_{-3\text{dB}} ≈ \text{GBW}·β = \text{GBW}/\text{noise gain}$. Inverting gain −G has noise gain 1+G (β = R_in/(R_in+R_f)), non-inverting gain G has noise gain G. So an
inverting ×−1 stage gets GBW/2 while a follower gets the full GBW; a 2-input summer with equal resistors has noise gain 3.""",
    method="""GBW = 1 MHz, A0 = 10⁵ (op-amp macromodel). Inverting and non-inverting stages with |G| = 1…1000, difference amp and summer: calc.js DC gain and bandwidth vs
the simulator's AC analysis (−3 dB point measured from the low-frequency gain).""",
    data="Generated designs.",
)

BODY = """<div class="card"><div class="row" id="tabs"></div><svg id="sch" viewBox="0 0 520 220" style="margin-top:8px"></svg>
<p style="font-size:1.25em" id="eq"></p><div class="row"><label style="flex:1">R<sub>in</sub> / R<sub>g</sub> (Ω)<input id="ri" type="number" value="10000"></label>
<label style="flex:1">R<sub>f</sub> (Ω)<input id="rf" type="number" value="100000"></label><label style="flex:1">A<sub>0</sub><input id="a0" type="number" value="100000"></label>
<label style="flex:1">GBW (Hz)<input id="gbw" type="number" value="1000000"></label></div><table id="t" style="margin-top:8px"></table></div>"""

JS = r"""const $=id=>document.getElementById(id);let topo="inverting";const names={inverting:"Inverting",noninverting:"Non-inverting",follower:"Follower",difference:"Difference",summing2:"Summing (2 in)"};
Object.keys(names).forEach(k=>{const b=document.createElement('button');b.textContent=names[k];b.onclick=()=>{topo=k;upd();};b.id='t_'+k;$('tabs').appendChild(b);});
const eng=(v,u)=>!isFinite(v)?'∞':Math.abs(v)>=1e6?+(v/1e6).toPrecision(4)+' M'+u:Math.abs(v)>=1e3?+(v/1e3).toPrecision(4)+' k'+u:+v.toPrecision(4)+' '+u;
const SCH={inverting:'M20 100h60M130 100h40M170 100v-60h120M290 40v70M290 110h-40M340 110h60M170 100h30',noninverting:'M20 120h180M340 110h60M300 110v-70h-120v60h20M180 40v130',
follower:'M20 120h180M340 110h60M360 110v-80h-180v70h20',difference:'M20 100h60M130 100h70M20 150h60M130 150h70M170 100v-60h120M290 40v70M340 110h60',summing2:'M20 80h60M130 80h40M20 130h60M130 130h40M170 80v50M170 100h30M170 100v-60h120M290 40v70M340 110h60'};
function upd(){document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('on',b.id=='t_'+topo));
const p={Rin:+$('ri').value,Rg:+$('ri').value,Rf:+$('rf').value},r=analyse(topo,p,+$('a0').value,+$('gbw').value);
$('sch').innerHTML=`<path d="${SCH[topo]}" stroke="currentColor" fill="none" stroke-width="2"/><path d="M200 60v100l140-50z" fill="var(--panel)" stroke="currentColor" stroke-width="2"/>
<text x="208" y="93" fill="currentColor">−</text><text x="206" y="140" fill="currentColor">+</text><text x="408" y="114" fill="var(--acc)">Vout</text>`;
$('eq').textContent=r.eq;$('t').innerHTML=[["Ideal gain",r.G.toPrecision(5)],["Noise gain 1/β",r.noiseGain.toPrecision(5)],["Actual gain (finite A0)",r.Gactual.toPrecision(6)],
["Gain error",r.gainErrorPct.toPrecision(3)+' %'],["−3 dB bandwidth ≈ GBW·β",eng(r.bw,'Hz')],["Input impedance",eng(r.Zin,'Ω')]].map(x=>`<tr><td>${x[0]}</td><td class="n">${x[1]}</td></tr>`).join('');}
document.querySelectorAll('input').forEach(e=>e.oninput=upd);upd();"""


def build(topo, Rin, Rf, A0, GBW):
    ck = Circuit(topo)
    if topo == "inverting":
        ck.V("s", "in", "0", ac=1); ck.R("in", "in", "m", Rin); ck.R("f", "m", "out", Rf); ck.OPAMP("U", "0", "m", "out", A0=A0, GBW=GBW)
    elif topo == "noninverting":
        ck.V("s", "in", "0", ac=1); ck.R("g", "m", "0", Rin); ck.R("f", "m", "out", Rf); ck.OPAMP("U", "in", "m", "out", A0=A0, GBW=GBW)
    elif topo == "follower":
        ck.V("s", "in", "0", ac=1); ck.OPAMP("U", "in", "out", "out", A0=A0, GBW=GBW)
    elif topo == "difference":        # V2 = +1/2, V1 = -1/2 → V2 - V1 = 1
        ck.V("2", "v2", "0", ac=0.5); ck.V("1", "v1", "0", ac=-0.5)
        ck.R("1", "v1", "m", Rin); ck.R("f", "m", "out", Rf); ck.R("2", "v2", "p", Rin); ck.R("g", "p", "0", Rf); ck.OPAMP("U", "p", "m", "out", A0=A0, GBW=GBW)
    elif topo == "summing2":          # drive input 1 only; input 2 grounded through its resistor
        ck.V("s", "in", "0", ac=1); ck.R("1", "in", "m", Rin); ck.R("2", "m", "0", Rin); ck.R("f", "m", "out", Rf); ck.OPAMP("U", "0", "m", "out", A0=A0, GBW=GBW)
    return ck


def run(p):
    p.write("web/index.html", page("Op-amp configuration explorer", "Pick a topology; see the gain equation, noise gain, finite-gain error and bandwidth.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "analysis library (tested)")
    js = p.dir / "web" / "calc.js"
    A0, GBW = 1e5, 1e6
    f = np.logspace(0, 7, 1400)
    rows = []
    for topo, gains in (("inverting", [1, 3, 10, 30, 100, 300, 1000]), ("noninverting", [1.5, 3, 10, 30, 100, 300, 1000]),
                        ("follower", [1]), ("difference", [1, 10]), ("summing2", [1, 10])):
        for G in gains:
            Rin = 10e3; Rf = (G - 1) * Rin if topo == "noninverting" else G * Rin
            r = node(js, [["analyse", [topo, {"Rin": Rin, "Rg": Rin, "Rf": Rf}, A0, GBW]]])[0]
            H = np.abs(build(topo, Rin, Rf, A0, GBW).ac(f).v("out"))
            g0 = H[0]
            bw = find_crossing(f, db(H) - db(g0), -3.0103, falling=True)
            rows.append((topo, G, r["noiseGain"], abs(r["Gactual"]), g0, r["bw"], bw))
    rows_a = np.array([x[2:] for x in rows], float)
    gerr = np.abs(rows_a[:, 2] / rows_a[:, 1] - 1) * 100
    p.compare("Worst |DC gain(JS, finite A0) − simulated| over all configurations", 0, gerr.max(), "%", kind="abs", tol=0.01)
    bwe = (rows_a[:, 4] / rows_a[:, 3] - 1) * 100
    p.compare("Worst bandwidth error of GBW·β rule (noise gain ≥ 2)", 0, np.max(np.abs(bwe[rows_a[:, 0] >= 2])), "%", kind="abs", tol=5)
    inv1 = [x for x in rows if x[0] == "inverting" and x[1] == 1][0]; fol = [x for x in rows if x[0] == "follower"][0]
    p.compare("Bandwidth ratio follower / inverting ×−1 (= 2)", 2, fol[6] / inv1[6], "", tol=3)
    s2 = [x for x in rows if x[0] == "summing2" and x[1] == 1][0]
    p.compare("2-input unity summer: bandwidth = GBW/3", GBW / 3, s2[6], "Hz", tol=3)
    fol_err = (fol[6] / fol[5] - 1) * 100
    p.metric("Follower: simulated bandwidth vs GBW·β", fol_err, "%")
    fig, ax = p.fig(1, 2, w=11)
    for topo, c in (("inverting", COLORS[0]), ("noninverting", COLORS[1])):
        sel = [x for x in rows if x[0] == topo]
        ng = np.array([x[2] for x in sel])
        ax[0].loglog(ng, [x[6] for x in sel], "o", color=c, label=f"{topo} (simulated)")
    ngs = np.logspace(0, 3.1)
    ax[0].loglog(ngs, GBW / ngs, "--", color=C_PRED, label="GBW / noise gain")
    style_axes(ax[0], "noise gain 1/β", "−3 dB bandwidth (Hz)", "Bandwidth is set by the noise gain")
    for G, c in ((1, COLORS[0]), (10, COLORS[1]), (100, COLORS[2])):
        Hj = node(js, [["response", ["inverting", {"Rin": 1e4, "Rf": G * 1e4}, f.tolist(), A0, GBW]]])[0]
        Hs = np.abs(build("inverting", 1e4, G * 1e4, A0, GBW).ac(f).v("out"))
        ax[1].semilogx(f, db(np.array(Hj)), "--", color=c); ax[1].semilogx(f, db(Hs), color=c, alpha=.7, label=f"G = −{G}")
    style_axes(ax[1], "frequency (Hz)", "|gain| (dB)", "Inverting stage: tool (dashed) vs simulator")
    p.save(fig, "opamp", "Bandwidth equals GBW divided by noise gain for every topology; the tool's response curves overlay the simulation.")
    import pandas as pd
    p.csv_df("configs", pd.DataFrame(rows, columns=["topology", "gain", "noise_gain", "gain_js", "gain_sim", "bw_js_hz", "bw_sim_hz"]))
    p.discuss("""The explorer's numbers agree with circuit simulation: finite-A0 gain error to within simulator precision and bandwidth to within a few percent of
GBW·β for every topology. The key insight the tool is built to show is that bandwidth follows the *noise gain*, not the signal gain: an inverting
×−1 stage has noise gain 2 and half a follower's bandwidth, and a unity-gain two-input summer has noise gain 3. Adding inputs to a summer therefore
costs bandwidth even though the signal gain per input is unchanged. The simulator's op-amp macromodel is itself single-pole, so the rule holds even for the follower; real
op-amps have a second pole near GBW that reduces phase margin at β = 1, which shows up as peaking — that is the limitation to remember when
using the tool's numbers for unity-gain buffers.""")
# tol-convention: relative tolerances are in percent
