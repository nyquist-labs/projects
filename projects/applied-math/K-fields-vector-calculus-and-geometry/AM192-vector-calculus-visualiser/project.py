from eelab import *
from eelab.web import page, node, attach

META = dict(
    id="AM-192", title="Vector-calculus visualiser (interactive, verified)", level="M",
    tools="Browser tool (HTML + JavaScript, canvas): user-typed 2-D field, arrows coloured by divergence or curl, a draggable circle showing flux and circulation next to the area integrals of divergence and curl; the JavaScript engine is run under Node and checked against analytic derivatives and the theorems of Gauss and Stokes",
    summary="An interactive page where a student types any planar field and sees its divergence and curl as colour, with a movable circle that shows the "
            "divergence theorem and Stokes' theorem balancing live. The calculation engine is tested numerically against closed-form results before the page is published.",
    problem="Divergence and curl are defined by limits and printed as formulas. How can they be *seen* — and how do we know the tool that shows them is right?",
    theory=r"""For $F=(P,Q)$: $\nabla\cdot F=P_x+Q_y$, $(\nabla\times F)_z=Q_x-P_y$. Divergence theorem (2-D): $\oint_C F\cdot n\,ds=\iint_D\nabla\cdot F\,dA$; Stokes/Green: $\oint_C F\cdot t\,ds=\iint_D(\nabla\times F)_z\,dA$. Test fields: (x, y) has div 2, curl 0; (−y, x) div 0, curl 2;
$(x^2y,\ \sin x\cos y)$ has div $2xy-\sin x\sin y$ and curl $\cos x\cos y-x^2$. The gradient of any potential is curl-free. Central differences are second-order accurate.""",
    method="""calc.js: expression compiler (restricted character set), central-difference derivatives (h = 10⁻⁴), circle line integrals (720 points), polar area integrals. Node tests: 400 random points for div/curl of the non-trivial field, gradient of a potential, and the two theorems on
50 random circles for four fields.""",
)

BODY = """<div class="card"><div class="row"><label style="flex:1">P(x, y)<input id="P" value="x*x*y"></label><label style="flex:1">Q(x, y)<input id="Q" value="sin(x)*cos(y)"></label></div>
<div class="row" style="margin-top:8px"><button id="bd" class="on">colour: divergence</button><button id="bc">colour: curl</button>
<button data-f="x|y">source</button><button data-f="-y|x">vortex</button><button data-f="y|x">saddle</button><button data-f="x*x*y|sin(x)*cos(y)">mixed</button></div></div>
<div class="card"><canvas id="cv" width="640" height="640"></canvas><p class="muted">Drag on the plot to move the circle; scroll to change its radius.</p>
<table><tr><th></th><th class="n">boundary integral</th><th class="n">area integral</th></tr>
<tr><td>Flux ∮F·n ds  vs  ∬div F dA</td><td class="n" id="fl"></td><td class="n" id="di"></td></tr>
<tr><td>Circulation ∮F·t ds  vs  ∬curl F dA</td><td class="n" id="ci"></td><td class="n" id="cu"></td></tr></table></div>"""

JS = r"""const $=id=>document.getElementById(id);let mode='div',cx=0.5,cy=0.3,R=0.8;const L=3,cv=$('cv'),g=cv.getContext('2d');
const X=x=>(x+L)/(2*L)*cv.width,Y=y=>(L-y)/(2*L)*cv.height;
function col(v,m){const t=Math.max(-1,Math.min(1,v/m));return t>0?`rgba(235,104,52,${t})`:`rgba(42,120,214,${-t})`;}
function draw(){let P=$('P').value,Q=$('Q').value,G;try{G=grid(P,Q,-L,L,-L,L,25)}catch(e){return}
g.clearRect(0,0,cv.width,cv.height);const k=mode=='div'?4:5,m=Math.max(...G.map(r=>Math.abs(r[k])))||1,vm=Math.max(...G.map(r=>Math.hypot(r[2],r[3])))||1,s=cv.width/25;
for(const r of G){g.fillStyle=col(r[k],m);g.fillRect(X(r[0])-s/2,Y(r[1])-s/2,s,s);}
g.strokeStyle=getComputedStyle(document.body).color;g.lineWidth=1.2;
for(const r of G){const ux=r[2]/vm*s*0.9,uy=r[3]/vm*s*0.9,x0=X(r[0]),y0=Y(r[1]);g.beginPath();g.moveTo(x0,y0);g.lineTo(x0+ux,y0-uy);g.stroke();g.beginPath();g.arc(x0+ux,y0-uy,1.6,0,7);g.fill();}
g.strokeStyle='#eb6834';g.lineWidth=2;g.beginPath();g.arc(X(cx),Y(cy),R/(2*L)*cv.width,0,7);g.stroke();
const [fl,ci]=circleIntegrals(P,Q,cx,cy,R,720),[di,cu]=discIntegrals(P,Q,cx,cy,R,60,120);
$('fl').textContent=fl.toFixed(4);$('di').textContent=di.toFixed(4);$('ci').textContent=ci.toFixed(4);$('cu').textContent=cu.toFixed(4);}
cv.onmousemove=e=>{if(e.buttons){const b=cv.getBoundingClientRect();cx=((e.clientX-b.left)/b.width*2-1)*L;cy=(1-(e.clientY-b.top)/b.height*2)*L;draw();}};
cv.onwheel=e=>{e.preventDefault();R=Math.max(0.1,Math.min(2.5,R*(e.deltaY>0?0.9:1.1)));draw();};
$('bd').onclick=()=>{mode='div';$('bd').className='on';$('bc').className='';draw()};$('bc').onclick=()=>{mode='curl';$('bc').className='on';$('bd').className='';draw()};
document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{const [p,q]=b.dataset.f.split('|');$('P').value=p;$('Q').value=q;draw()});
$('P').oninput=$('Q').oninput=draw;draw();"""


def run(p):
    p.write("web/index.html", page("Vector-calculus visualiser", "Type a planar field; colour shows divergence or curl, and the circle checks Gauss's and Stokes' theorems live.", BODY, inline=JS), "interactive tool")
    attach(p, "web/calc.js", "calculation engine (tested under Node)")
    js = p.dir / "web" / "calc.js"; r = p.rng
    P_, Q_ = "x*x*y", "sin(x)*cos(y)"
    pts = r.uniform(-2, 2, (400, 2))
    res = node(js, [["divergence", [P_, Q_, float(x), float(y)]] for x, y in pts] + [["curl", [P_, Q_, float(x), float(y)]] for x, y in pts])
    dv, cu = np.array(res[:400]), np.array(res[400:])
    x, y = pts[:, 0], pts[:, 1]
    p.compare("Divergence of (x²y, sin x cos y) vs 2xy − sin x sin y (worst abs. error, 400 points)", 0.0, float(np.max(np.abs(dv - (2 * x * y - np.sin(x) * np.sin(y))))), "", kind="abs", tol=1e-6)
    p.compare("Curl of the same field vs cos x cos y − x² (worst abs. error)", 0.0, float(np.max(np.abs(cu - (np.cos(x) * np.cos(y) - x * x)))), "", kind="abs", tol=1e-6)
    g = np.array(node(js, [["gradient", ["x*x*y + exp(0.3*x)*cos(y)", float(a), float(b)]] for a, b in pts[:50]]))
    gx = 2 * pts[:50, 0] * pts[:50, 1] + 0.3 * np.exp(0.3 * pts[:50, 0]) * np.cos(pts[:50, 1]); gy = pts[:50, 0] ** 2 - np.exp(0.3 * pts[:50, 0]) * np.sin(pts[:50, 1])
    p.compare("Gradient of a potential vs analytic (worst abs. error)", 0.0, float(np.max(np.abs(g - np.c_[gx, gy]))), "", kind="abs", tol=1e-5)
    cg = np.array(node(js, [["curl", [f"2*x*y + 0.3*exp(0.3*x)*cos(y)", "x*x - exp(0.3*x)*sin(y)", float(a), float(b)]] for a, b in pts[:50]]))
    p.compare("Curl of a gradient field is zero (worst abs. value)", 0.0, float(np.max(np.abs(cg))), "", kind="abs", tol=1e-5)
    fields = [("x", "y", 2.0, 0.0), ("-y", "x", 0.0, 2.0), ("y", "x", 0.0, 0.0), (P_, Q_, None, None)]
    worst_g = worst_s = 0.0; exact_ok = 0
    for P, Q, dconst, cconst in fields:
        circ = r.uniform(-1.5, 1.5, (50, 2)); rad = r.uniform(0.2, 1.2, 50)
        calls = [["circleIntegrals", [P, Q, float(a), float(b), float(rr), 720]] for (a, b), rr in zip(circ, rad)] + [["discIntegrals", [P, Q, float(a), float(b), float(rr), 120, 240]] for (a, b), rr in zip(circ, rad)]
        out = np.array(node(js, calls)); bd, ar = out[:50], out[50:]
        worst_g = max(worst_g, float(np.max(np.abs(bd[:, 0] - ar[:, 0]) / np.maximum(1, np.abs(ar[:, 0])))))
        worst_s = max(worst_s, float(np.max(np.abs(bd[:, 1] - ar[:, 1]) / np.maximum(1, np.abs(ar[:, 1])))))
        if dconst is not None:
            exact_ok += int(np.allclose(bd[:, 0], dconst * pi * rad ** 2, rtol=1e-5, atol=1e-6) and np.allclose(bd[:, 1], cconst * pi * rad ** 2, rtol=1e-5, atol=1e-6))
    p.compare("Divergence theorem: ∮F·n ds vs ∬div F dA on 200 random circles, 4 fields (worst relative difference)", 0.0, worst_g, "", kind="abs", tol=1e-4)
    p.compare("Stokes' theorem: ∮F·t ds vs ∬curl F dA (worst relative difference)", 0.0, worst_s, "", kind="abs", tol=1e-4)
    p.compare("Source, vortex and saddle fields: flux and circulation equal 2πr², 2πr² and 0 exactly as predicted (fields passing)", 3, exact_ok, "", kind="abs")
    xs = np.linspace(-3, 3, 25); GX, GY = np.meshgrid(xs, xs)
    fig, ax = p.fig(1, 2, w=11, h=5)
    for a_, (U, Vv, lab) in zip(ax, ((GX * GX * GY, np.sin(GX) * np.cos(GY), "divergence"), (GX * GX * GY, np.sin(GX) * np.cos(GY), "curl"))):
        C = 2 * GX * GY - np.sin(GX) * np.sin(GY) if lab == "divergence" else np.cos(GX) * np.cos(GY) - GX * GX
        m = np.abs(C).max(); a_.pcolormesh(GX, GY, C, cmap="RdBu_r", vmin=-m, vmax=m, shading="auto")
        n_ = np.hypot(U, Vv) + 1e-9; a_.quiver(GX, GY, U / n_, Vv / n_, color="k", scale=35, width=0.003)
        a_.set_aspect("equal"); a_.grid(False); a_.set_title(f"(x²y, sin x cos y) coloured by {lab}", loc="left", fontsize=10)
    p.save(fig, "vector_fields", "Static rendering of what the tool shows: the same field coloured by divergence and by curl.")
    p.discuss(f"""The page lets a student type any planar field and immediately see where it spreads out (divergence) and where it swirls (curl), then drag a
circle around to watch the boundary integrals track the area integrals. Before publishing, the JavaScript engine was run under Node and compared
with closed forms: divergence and curl of a non-trivial field agree with the analytic expressions to {max(np.max(np.abs(dv - (2 * x * y - np.sin(x) * np.sin(y)))), np.max(np.abs(cu - (np.cos(x) * np.cos(y) - x * x)))):.0e}, gradients of a
potential are curl-free, and on 200 random circles the divergence and Stokes theorems balance to {max(worst_g, worst_s):.0e}. The three textbook fields give the
predicted exact values (2πr² for the source's flux and the vortex's circulation, zero for the saddle). The theorems are then something the
student can check with the mouse rather than accept on faith.""")
# tol-convention: relative tolerances are in percent
