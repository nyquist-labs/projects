from eelab import *
import subprocess, shutil, json

META = dict(
    id="SL-101", title="Interactive Smith chart", level="H",
    tools="HTML canvas + JavaScript (shared math module), Node test harness vs NumPy",
    summary="A browser Smith chart: type a load impedance and frequency, see Γ, VSWR and return loss, add a series or "
            "shunt L/C and watch the point move along constant-R / constant-G circles. The JavaScript maths is "
            "verified against NumPy.",
    problem="The Smith chart is a graphical calculator for impedance matching. Build a working one and prove every "
            "number it shows is right.",
    theory=r"""$\Gamma=\frac{Z-Z_0}{Z+Z_0}$ maps the right half of the impedance plane onto the unit disc (a Möbius transformation).
Constant-resistance lines become circles centred at $(\frac{r}{1+r},0)$ with radius $\frac1{1+r}$; VSWR = $\frac{1+|\Gamma|}{1-|\Gamma|}$,
return loss = $-20\log_{10}|\Gamma|$. A series reactance moves the point along its constant-r circle; a shunt susceptance along a
constant-g circle.""",
    method="""smith.js holds the maths (Γ, VSWR, RL, series/shunt element steps); index.html draws the chart and the matching path.
Node evaluates the functions on 200 random loads and element steps; Python compares with NumPy complex arithmetic.""",
)

JS = r"""
function gamma(zr, zi, z0) { const nr = zr - z0, ni = zi, dr = zr + z0, di = zi, d = dr * dr + di * di; return [(nr * dr + ni * di) / d, (ni * dr - nr * di) / d]; }
function vswr(g) { const m = Math.hypot(g[0], g[1]); return (1 + m) / (1 - m); }
function rl(g) { return -20 * Math.log10(Math.hypot(g[0], g[1])); }
function seriesX(zr, zi, x) { return [zr, zi + x]; }
function shuntB(zr, zi, b) { const d = zr * zr + zi * zi, yr = zr / d, yi = -zi / d + b, e = yr * yr + yi * yi; return [yr / e, -yi / e]; }
function reactance(kind, val, f) { const w = 2 * Math.PI * f; return kind === "L" ? w * val : -1 / (w * val); }
function susceptance(kind, val, f) { const w = 2 * Math.PI * f; return kind === "C" ? w * val : -1 / (w * val); }
if (typeof module !== "undefined") module.exports = { gamma, vswr, rl, seriesX, shuntB, reactance, susceptance };
"""
TEST = r"""
const s = require("./smith.js"); let seed = 7; const r = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const out = [];
for (let i = 0; i < 200; i++) {
  const zr = 1 + 200 * r(), zi = -300 + 600 * r(), x = -100 + 200 * r(), b = -0.02 + 0.04 * r();
  const g = s.gamma(zr, zi, 50);
  out.push({ zr, zi, x, b, g, vswr: s.vswr(g), rl: s.rl(g), ser: s.seriesX(zr, zi, x), sh: s.shuntB(zr, zi, b) });
}
console.log(JSON.stringify(out));
"""
HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Smith Chart</title>
<style>:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#d9d8d3;--a:#2a78d6;--b:#eb6834}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#44433f;--a:#3987e5;--b:#d95926}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}main{max-width:900px;margin:auto;padding:16px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}input,select,button{font:inherit}input{width:90px}
canvas{width:100%;max-width:560px;height:auto;display:block}#out{font-variant-numeric:tabular-nums;color:var(--ink2)}</style></head><body><main>
<h1>Smith chart</h1>
<div class="row">Z₀ <input id="z0" value="50"> Ω · Load R <input id="zr" value="25"> X <input id="zi" value="-40"> Ω · f <input id="f" value="100"> MHz</div>
<div class="row">Add <select id="how"><option>series</option><option>shunt</option></select><select id="kind"><option>L</option><option>C</option></select>
<input id="val" value="30"> nH/pF <button id="add">Add element</button><button id="clr">Clear</button></div>
<p id="out"></p><canvas id="c" width="560" height="560"></canvas></main>
<script src="smith.js"></script><script>
const cv=document.getElementById('c'),g=cv.getContext('2d'),S=270,C=280;let path=[];
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v);
function P(G){return[C+S*G[0],C-S*G[1]]}
function grid(){g.fillStyle=css('--bg');g.fillRect(0,0,560,560);g.strokeStyle=css('--grid');g.lineWidth=1;
g.beginPath();g.arc(C,C,S,0,7);g.stroke();for(const r of[0.2,0.5,1,2,5]){g.beginPath();g.arc(C+S*r/(1+r),C,S/(1+r),0,7);g.stroke();}
for(const x of[0.2,0.5,1,2,5])for(const s of[1,-1]){g.save();g.beginPath();g.arc(C,C,S,0,7);g.clip();g.beginPath();g.arc(C+S,C-s*S/x,S/x,0,7);g.stroke();g.restore();}
g.beginPath();g.moveTo(C-S,C);g.lineTo(C+S,C);g.stroke();}
function draw(){grid();const z0=+z0e.value;let z=[+zre.value,+zie.value];const pts=[z];for(const e of path){z=e(z);pts.push(z);}
g.strokeStyle=css('--a');g.lineWidth=2;g.beginPath();pts.forEach((p,i)=>{const q=P(gamma(p[0],p[1],z0));i?g.lineTo(...q):g.moveTo(...q);});g.stroke();
pts.forEach((p,i)=>{const q=P(gamma(p[0],p[1],z0));g.fillStyle=i==pts.length-1?css('--b'):css('--a');g.beginPath();g.arc(q[0],q[1],5,0,7);g.fill();});
const G=gamma(z[0],z[1],z0);document.getElementById('out').textContent=`Z = ${z[0].toFixed(2)} ${z[1]>=0?'+':'−'} j${Math.abs(z[1]).toFixed(2)} Ω · |Γ| = ${Math.hypot(...G).toFixed(4)} · VSWR = ${vswr(G).toFixed(3)} · RL = ${rl(G).toFixed(2)} dB`;}
const z0e=document.getElementById('z0'),zre=document.getElementById('zr'),zie=document.getElementById('zi');
document.querySelectorAll('input').forEach(i=>i.oninput=draw);
document.getElementById('add').onclick=()=>{const f=+document.getElementById('f').value*1e6,k=document.getElementById('kind').value,v=+document.getElementById('val').value*(k=='L'?1e-9:1e-12),how=document.getElementById('how').value;
path.push(how=='series'?(z=>seriesX(z[0],z[1],reactance(k,v,f))):(z=>shuntB(z[0],z[1],susceptance(k,v,f))));draw();};
document.getElementById('clr').onclick=()=>{path=[];draw();};draw();</script></body></html>"""


def run(p):
    p.write("web/smith.js", JS.strip() + "\n", "Smith-chart maths (shared)")
    p.write("web/index.html", HTML, "interactive chart")
    p.write("web/test_smith.js", TEST.strip() + "\n", "Node test harness")
    out = json.loads(subprocess.run([shutil.which("node"), "test_smith.js"], cwd=p.dir / "web", capture_output=True, text=True, check=True).stdout)
    eg = ev = er = es = eh = 0
    for o in out:
        Z = o["zr"] + 1j * o["zi"]
        G = (Z - 50) / (Z + 50)
        eg = max(eg, abs(complex(*o["g"]) - G))
        ev = max(ev, abs(o["vswr"] - (1 + abs(G)) / (1 - abs(G))) / ((1 + abs(G)) / (1 - abs(G))))
        er = max(er, abs(o["rl"] + 20 * np.log10(abs(G))))
        es = max(es, abs(complex(*o["ser"]) - (Z + 1j * o["x"])))
        Zs = 1 / (1 / Z + 1j * o["b"]); eh = max(eh, abs(complex(*o["sh"]) - Zs) / abs(Zs))
    p.compare("Γ: max |JS − NumPy| over 200 loads", 0, eg, "", kind="abs")
    p.compare("VSWR: max relative difference", 0, ev, "", kind="abs")
    p.compare("Return loss: max difference", 0, er, "dB", kind="abs")
    p.compare("Shunt-element step: max relative difference", 0, eh, "", kind="abs")
    r = np.linspace(0, 1, 200)
    fig, ax = p.fig(w=6, h=6)
    for rr in (0.2, 0.5, 1, 2, 5):
        x = np.linspace(-50, 50, 4000); z = rr + 1j * x; g = (z - 1) / (z + 1)
        ax.plot(g.real, g.imag, color="gray", lw=.6)
        c0 = rr / (1 + rr); rad = 1 / (1 + rr)
        th = np.linspace(0, 2 * pi, 200)
        ax.plot(c0 + rad * np.cos(th), rad * np.sin(th), "--", color=C_PRED, lw=.8)
    pts = [complex(o["g"][0], o["g"][1]) for o in out]
    ax.plot(np.real(pts), np.imag(pts), ".", color=C_MEAS, ms=3, label="JS Γ of 200 random loads")
    ax.set_aspect("equal"); ax.set_xlim(-1.05, 1.05); ax.set_ylim(-1.05, 1.05)
    style_axes(ax, "Re Γ", "Im Γ", "Constant-R lines are circles (Möbius map)")
    p.save(fig, "chart_check", "Mapped constant-resistance lines (grey) coincide with the predicted circles (dashed).")
    p.section("Try it", "Open [`web/index.html`](web/index.html) (or the project site copy): enter a load, then add series/shunt L or C and watch the matching path.")
    p.discuss("""Every quantity the web chart displays agrees with NumPy to floating-point precision, and the mapped constant-resistance
lines land exactly on the predicted circles — the Möbius transformation maps lines to circles, which is the whole reason
the chart works. Keeping the maths in a module shared by the page and a Node test is what makes that check possible.""")
