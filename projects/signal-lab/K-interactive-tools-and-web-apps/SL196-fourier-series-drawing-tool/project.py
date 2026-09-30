from eelab import *
from eelab.web import node, page, attach

META = dict(
    id="SL-196", title="Fourier-series drawing tool (epicycles)", level="M",
    tools="HTML canvas + JavaScript DFT/epicycle animator (draw any closed shape) + Node test harness vs NumPy FFT; convergence-rate analysis",
    summary="Draw a closed shape and watch rotating circles trace it; the tool's DFT is verified against NumPy, and the approximation error vs number "
            "of circles is predicted from the smoothness of the shape (smooth, cornered, or with a jump) and measured.",
    problem="How many circles does it take to draw a shape — and why do some shapes need far more than others?",
    theory=r"""A closed path $z(t)=x+iy$ has $z(t)=\sum_k c_k e^{2πikt}$. How fast $|c_k|$ decays is set by smoothness: a path with a corner (continuous, kinked) has
$|c_k|∼k^{-2}$; a path with a jump (e.g. an unclosed stroke) $|c_k|∼k^{-1}$; an analytic path decays exponentially. Keeping the N largest terms leaves an
RMS error $\big(\sum_{|k|>N/2}|c_k|^2\big)^{1/2}$: ∝ $N^{-3/2}$ for corners, $N^{-1/2}$ for jumps, and faster than any power for smooth shapes.""",
    method="""Shapes sampled at 1024 points: a square (4 corners), an open 'C' stroke closed by a jump (via its uniform-in-time sampling), and a smooth epitrochoid.
calc.js `dft` vs `numpy.fft.fft/N`; `reconstruct` with N = 4…512 terms vs the true path; log-log slope of RMS error fitted over N = 8…64 (well below the 1024-sample limit: the square's symmetry makes only every 4th harmonic nonzero, so ~256 terms already reproduce the sampled path exactly).""",
    data="Generated shapes.",
)

BODY = """<div class="card"><p class="muted">Draw a closed shape with your mouse or finger in the box (or keep the default), then press play.</p>
<canvas id="c" width="640" height="420" style="border:1px solid var(--line);border-radius:8px;touch-action:none;width:100%"></canvas>
<div class="row" style="margin-top:8px"><button id="play">▶ play</button><button id="clear">clear</button>
<label style="flex:1;min-width:260px">circles: <b id="nv">64</b><input id="n" type="range" min="1" max="256" value="64"></label></div></div>"""

JS = r"""const cv=document.getElementById('c'),ctx=cv.getContext('2d');let raw=[],coeffs=null,t=0,trace=[],playing=false,drawing=false;
const col=()=>getComputedStyle(document.documentElement);
function heart(){raw=[];for(let i=0;i<300;i++){const a=2*Math.PI*i/300;raw.push([320+160*Math.pow(Math.sin(a),3),200-(130*Math.cos(a)-50*Math.cos(2*a)-20*Math.cos(3*a)-10*Math.cos(4*a))]);}}
function prep(){coeffs=dft(resample(raw,512));trace=[];t=0;}
function pos(e){const r=cv.getBoundingClientRect(),p=e.touches?e.touches[0]:e;return[(p.clientX-r.left)*cv.width/r.width,(p.clientY-r.top)*cv.height/r.height];}
cv.onpointerdown=e=>{drawing=true;playing=false;raw=[pos(e)];};cv.onpointermove=e=>{if(drawing){raw.push(pos(e));frame();}};
cv.onpointerup=()=>{drawing=false;if(raw.length>10){prep();playing=true;}};
document.getElementById('play').onclick=()=>{if(raw.length>10){prep();playing=true;}};document.getElementById('clear').onclick=()=>{raw=[];coeffs=null;playing=false;frame();};
document.getElementById('n').oninput=e=>{document.getElementById('nv').textContent=e.target.value;trace=[];t=0;};
function frame(){ctx.clearRect(0,0,cv.width,cv.height);ctx.strokeStyle=col().getPropertyValue('--line');ctx.lineWidth=1;ctx.beginPath();raw.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.stroke();
if(playing&&coeffs){const n=+document.getElementById('n').value;let x=0,y=0;ctx.strokeStyle=col().getPropertyValue('--muted');
for(const c of coeffs.slice(0,n)){const a=2*Math.PI*c.f*t,nx=x+c.re*Math.cos(a)-c.im*Math.sin(a),ny=y+c.re*Math.sin(a)+c.im*Math.cos(a);
ctx.beginPath();ctx.arc(x,y,c.amp,0,7);ctx.stroke();ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(nx,ny);ctx.stroke();x=nx;y=ny;}
trace.push([x,y]);if(trace.length>512)trace.shift();ctx.strokeStyle=col().getPropertyValue('--acc');ctx.lineWidth=2.5;ctx.beginPath();trace.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.stroke();t=(t+1/512)%1;}}
(function loop(){if(playing)frame();requestAnimationFrame(loop);})();heart();prep();playing=true;"""


def shapes(M=1024):
    t = np.arange(M) / M
    # square traversed at constant speed
    s = (t * 4) % 1; side = (t * 4).astype(int)
    corners = np.array([[1, 1], [-1, 1], [-1, -1], [1, -1], [1, 1]])
    sq = corners[side] + (corners[side + 1] - corners[side]) * s[:, None]
    # open 'C' stroke: an arc from 45° to 315°; the path jumps back to its start between the last and first sample
    a = np.deg2rad(45 + 270 * t); cstroke = np.c_[np.cos(a), np.sin(a)]
    # smooth epitrochoid
    w = 2 * np.pi * t; smooth = np.c_[np.cos(w) + 0.3 * np.cos(5 * w), np.sin(w) - 0.3 * np.sin(5 * w)]
    return {"square (corners)": (sq, -1.5), "open stroke (jump)": (cstroke, -0.5), "smooth epitrochoid": (smooth, None)}


def run(p):
    p.write("web/index.html", page("Fourier drawing machine", "Rotating circles, largest first, tracing any closed shape you draw.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "DFT / epicycle library (tested)")
    js = p.dir / "web" / "calc.js"
    Ns = np.array([4, 8, 16, 32, 64, 128, 256, 512])
    fig, ax = p.fig(1, 2, w=11)
    worst = 0
    for i, (name, (P, slope_pred)) in enumerate(shapes().items()):
        co = node(js, [["dft", [P.tolist()]]])[0]
        C = np.fft.fft(P[:, 0] + 1j * P[:, 1]) / len(P)
        for c in co[:50]:
            worst = max(worst, abs(complex(c["re"], c["im"]) - C[c["f"] % len(P)]))
        errs = []
        for n in Ns:
            R = np.array(node(js, [["reconstruct", [co, int(n), len(P)]]])[0])
            errs.append(np.sqrt(np.mean(np.sum((R - P) ** 2, 1))))
        errs = np.array(errs)
        ax[0].loglog(Ns, errs, "o-", color=COLORS[i], label=name)
        if slope_pred is not None:
            m = (Ns >= 8) & (Ns <= 64)
            sl = np.polyfit(np.log(Ns[m]), np.log(errs[m]), 1)[0]
            p.compare(f"{name}: RMS error ∝ N^slope — slope", slope_pred, sl, "", kind="abs")
        else:
            p.compare("smooth epitrochoid: error with 4 circles (it has exactly 2 nonzero terms → exact)", 0, errs[0], "", kind="abs", tol=1e-9)
        amps = np.sort(np.abs(C))[::-1]
        ax[1].loglog(np.arange(1, 400), amps[:399] + 1e-18, color=COLORS[i], label=name)
    p.compare("Max |c_k(JS) − c_k(NumPy FFT)| over the 50 largest terms", 0, worst, "", kind="abs", tol=1e-9)
    style_axes(ax[0], "number of circles N", "RMS path error", "Convergence depends on smoothness")
    ax[1].set_ylim(1e-8, 2)
    style_axes(ax[1], "rank of coefficient", "|c_k|", "Coefficient decay (sorted)")
    p.save(fig, "convergence", "Error vs number of circles: corners converge as N^-1.5, jumps as N^-0.5, smooth shapes immediately.")
    sq = shapes()["square (corners)"][0]
    co = node(js, [["dft", [sq.tolist()]]])[0]
    fig2, a2 = p.fig(1, 4, w=12, h=3.2)
    for a_, n in zip(a2, (4, 8, 32, 128)):
        R = np.array(node(js, [["reconstruct", [co, n, 1024]]])[0])
        a_.plot(sq[:, 0], sq[:, 1], color=COLORS[7], lw=1); a_.plot(R[:, 0], R[:, 1], color=C_MEAS, lw=1.5)
        a_.set_aspect("equal"); a_.axis("off"); a_.set_title(f"{n} circles", fontsize=10)
    p.save(fig2, "square", "A square drawn with 4, 8, 32 and 128 circles.")
    p.discuss("""The JavaScript DFT agrees with NumPy's FFT to rounding error, so the animation is mathematically exact. The convergence rates follow the
smoothness argument: the square's error falls about as N^-1.5 (corners → |c_k| ∝ 1/k²), the open stroke only as N^-0.5 (the jump from its end
back to its start gives |c_k| ∝ 1/k and a Gibbs overshoot that never goes away), and the smooth curve is exact once its two terms are included.
Practical lesson for the drawing tool: close your shape! A drawing whose end does not meet its start needs hundreds of circles to look right,
while a closed shape with a few corners looks good with ~50. (Past ~256 circles the square's error plunges to zero: sampled at 1024 points, its symmetry leaves only 256 nonzero harmonics.) The tool sorts circles by size, so the first few already capture the silhouette.""")
# tol-convention: relative tolerances are in percent
