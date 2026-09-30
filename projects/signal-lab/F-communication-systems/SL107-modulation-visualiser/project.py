from eelab import *
from scipy.special import jv

META = dict(
    id="SL-107", title="AM / FM / PM modulation visualiser", level="E",
    tools="HTML/JS interactive explainer + NumPy verification of spectra (Bessel sidebands, Carson's rule)",
    summary="An in-browser explainer that draws AM, FM and PM waveforms and spectra live as you move the sliders; the "
            "spectra it shows are checked in Python against Bessel-function sideband amplitudes and Carson's rule.",
    problem="Three ways of putting a message on a carrier look similar in time but very different in frequency. Make "
            "the difference visible and verify it numerically.",
    theory=r"""AM: carrier + two sidebands of amplitude m/2. FM/PM with a sinusoidal message: $\cos(\omega_ct+\beta\sin\omega_mt)=\sum_n J_n(\beta)\cos((\omega_c+n\omega_m)t)$,
so the n-th sideband amplitude is $|J_n(\beta)|$ — the carrier vanishes at β = 2.405. Carson's rule: 98 % of the power lies
within $B\approx2(\beta+1)f_m$.""",
    method="""Signals synthesised at 100 kHz, carrier 10 kHz, message 500 Hz; FFT sideband amplitudes vs J_n(β) for β = 0.5, 1, 2.405, 5; 98 %-power
bandwidth vs Carson. The web page (web/index.html) computes the same spectra with a JS DFT.""",
)

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Modulation Visualiser</title>
<style>:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e4e3df;--a:#2a78d6;--b:#eb6834}@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#383835;--a:#3987e5;--b:#d95926}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}main{max-width:900px;margin:auto;padding:16px}canvas{width:100%;height:auto;border:1px solid var(--grid);border-radius:6px;margin:6px 0}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}</style></head><body><main><h1>AM · FM · PM</h1>
<div class="row"><label>Mode <select id="mode"><option>AM</option><option>FM</option><option>PM</option></select></label>
<label>index <input id="k" type="range" min="0" max="8" step="0.05" value="1"> <span id="kv">1</span></label></div>
<canvas id="t" width="880" height="220"></canvas><canvas id="f" width="880" height="220"></canvas><p id="info" style="color:var(--ink2)"></p></main>
<script>const fs=100000,fc=10000,fm=500,N=4000;const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v);
function sig(mode,k){const x=new Float64Array(N);for(let n=0;n<N;n++){const t=n/fs,m=Math.sin(2*Math.PI*fm*t);
x[n]=mode==='AM'?(1+k/8*m)*Math.cos(2*Math.PI*fc*t):mode==='FM'?Math.cos(2*Math.PI*fc*t-k*Math.cos(2*Math.PI*fm*t)):Math.cos(2*Math.PI*fc*t+k*m);}return x;}
function spec(x){const out=[];for(let f=5000;f<=15000;f+=50){let re=0,im=0;for(let n=0;n<N;n++){re+=x[n]*Math.cos(2*Math.PI*f*n/fs);im-=x[n]*Math.sin(2*Math.PI*f*n/fs);}out.push([f,2*Math.hypot(re,im)/N]);}return out;}
function draw(){const mode=document.getElementById('mode').value,k=+document.getElementById('k').value;document.getElementById('kv').textContent=mode==='AM'?(k/8).toFixed(2)+' (m)':k.toFixed(2)+' (β)';
const x=sig(mode,k),T=document.getElementById('t').getContext('2d'),F=document.getElementById('f').getContext('2d');
[T,F].forEach(c=>{c.fillStyle=css('--bg');c.fillRect(0,0,880,220);});T.strokeStyle=css('--a');T.beginPath();for(let n=0;n<800;n++){const y=110-x[n]*50;n?T.lineTo(n*1.1,y):T.moveTo(0,y);}T.stroke();
const s=spec(x);F.fillStyle=css('--b');s.forEach(([f,a],i)=>{F.fillRect(i*4.35,210-a*190,3,a*190);});
document.getElementById('info').textContent=mode==='AM'?'AM: carrier plus two sidebands at ±500 Hz.':`Carson bandwidth 2(β+1)fm = ${(2*(k+1)*fm/1000).toFixed(2)} kHz; sideband n has amplitude |Jn(β)|.`;}
document.querySelectorAll('select,input').forEach(e=>e.oninput=draw);draw();</script></body></html>"""


def run(p):
    p.write("web/index.html", HTML, "interactive explainer")
    fs, fc, fm, N = 100000, 10000, 500, 100000
    t = np.arange(N) / fs
    rows = []
    for beta in (0.5, 1.0, 2.405, 5.0):
        x = np.cos(2 * pi * fc * t + beta * np.sin(2 * pi * fm * t))
        X = 2 * np.abs(np.fft.rfft(x)) / N
        f = np.fft.rfftfreq(N, 1 / fs)
        amps = [X[np.argmin(abs(f - (fc + n * fm)))] for n in range(0, 8)]
        err = max(abs(amps[n] - abs(jv(n, beta))) for n in range(8))
        p.compare(f"β = {beta}: max |sideband − |J_n(β)||", 0, err, "", kind="abs")
        P = X**2; order = np.argsort(np.abs(f - fc)); cum = np.cumsum(P[order]) / P.sum()
        bw98 = 2 * np.abs(f[order][np.argmax(cum >= 0.98)] - fc)
        p.compare(f"β = {beta}: 98 %-power bandwidth vs Carson 2(β+1)f_m", 2 * (beta + 1) * fm, bw98, "Hz", tol=25)
        rows.append((beta, amps))
    fig, ax = p.fig(1, 2)
    b = np.linspace(0, 8, 400)
    for n in range(4):
        ax[0].plot(b, jv(n, b), color=COLORS[n], label=f"J{n}(β)")
    for beta, amps in rows:
        for n in range(4):
            ax[0].plot(beta, amps[n], "o", color=COLORS[n], ms=5)
    ax[0].axhline(0, color="gray", lw=.6)
    style_axes(ax[0], "β", "sideband amplitude", "Bessel functions (lines) vs FFT (dots, magnitudes)")
    x = np.cos(2 * pi * fc * t + 5 * np.sin(2 * pi * fm * t)); X = 2 * np.abs(np.fft.rfft(x)) / N; f = np.fft.rfftfreq(N, 1 / fs)
    ax[1].stem((f[(f > 5000) & (f < 15000)] - fc) / 1e3, X[(f > 5000) & (f < 15000)], basefmt=" ")
    ax[1].axvspan(-3, 3, color=COLORS[1], alpha=.1, label="Carson ±3 kHz")
    style_axes(ax[1], "offset from carrier (kHz)", "amplitude", "FM spectrum, β = 5")
    p.save(fig, "fm_sidebands", "Sideband amplitudes follow |J_n(β)|; the carrier vanishes at β ≈ 2.405.")
    p.section("Try it", "Open [`web/index.html`](web/index.html) (or the project site copy) and drag the index slider.")
    p.discuss("""FFT sideband magnitudes equal |J_n(β)| to numerical precision, including the vanishing carrier at β = 2.405 (the classic
way to calibrate an FM deviation meter). Carson's rule captures ≥ 98 % of the power as advertised; it is slightly
generous at small β and slightly tight at large β, where the 98 % contour is set by the last significant Bessel term.""")
