from eelab import *
from eelab.web import node, page, attach
from scipy import signal

META = dict(
    id="AM-009", title="s-plane explorer: drag a pole, watch the step response", level="M",
    tools="Interactive SVG page (drag the pole pair), closed-form step responses in JavaScript, Node test harness vs SciPy, damping formulas",
    summary="A browser tool where you drag a pole pair around the s-plane and see the step response, overshoot and settling time update live. "
            "The JavaScript is verified against SciPy and the standard second-order formulas are tested across the plane.",
    problem="How exactly does moving a pole change what a system does in time?",
    theory=r"""For poles $-σ\pm jω_d$: $y(t)=1-e^{-σt}\big(\cos ω_dt+\tfrac{σ}{ω_d}\sin ω_dt\big)$. The pole angle sets the damping ratio $ζ=\cos θ = σ/\sqrt{σ^2+ω_d^2}$, overshoot is
$100\,e^{-πζ/\sqrt{1-ζ^2}}$ % — a function of the angle only — while the distance from the jω axis sets the envelope $e^{-σt}$ and the settling time ≈ 4/σ.""",
    method="""200 random pole pairs (σ ∈ [0.2, 5], ω_d ∈ [0.1, 10]): calc.js step response vs scipy.signal.step on 4000 points; overshoot from the JS output vs the ζ formula; settling
vs 4/σ. Two real poles checked the same way.""",
)

BODY = """<div class="card"><div class="row" style="align-items:flex-start"><svg id="s" viewBox="-220 -170 260 340" width="260" height="340" style="touch-action:none;border:1px solid var(--line);border-radius:8px"></svg>
<svg id="y" viewBox="0 0 480 300" style="flex:1;min-width:280px;border:1px solid var(--line);border-radius:8px"></svg></div>
<p>Pole <b id="pp"></b> · ζ = <b id="z"></b> · overshoot <b id="os"></b> · settling (2 %) <b id="ts"></b></p><p class="muted">Drag the pole (its mirror follows). Left = faster decay, higher = faster oscillation; the angle from the negative real axis alone decides the overshoot.</p></div>"""

JS = r"""let P={s:1,w:3};const S=document.getElementById('s'),Yv=document.getElementById('y'),K=20;
function draw(){let h='<line x1="-220" y1="0" x2="40" y2="0" stroke="var(--muted)"/><line x1="0" y1="-170" x2="0" y2="170" stroke="var(--muted)"/>';
for(const sg of [1,-1])h+=`<g stroke="var(--acc2)" stroke-width="3"><line x1="${-P.s*K-7}" y1="${-sg*P.w*K-7}" x2="${-P.s*K+7}" y2="${-sg*P.w*K+7}"/><line x1="${-P.s*K-7}" y1="${-sg*P.w*K+7}" x2="${-P.s*K+7}" y2="${-sg*P.w*K-7}"/></g>`;
h+=`<line x1="0" y1="0" x2="${-P.s*K}" y2="${-P.w*K}" stroke="var(--line)" stroke-dasharray="3"/>`;S.innerHTML=h;
const T=Math.max(8/P.s,10/Math.max(P.w,.1)),t=[...Array(400)].map((_,k)=>k*T/399),y=P.w>1e-3?stepPair(P.s,P.w,t):stepReal(P.s,P.s*1.0001,t),m=metrics(y,t);
const X=k=>k/399*480,Yy=v=>270-v*180;Yv.innerHTML=`<line x1="0" x2="480" y1="${Yy(1)}" y2="${Yy(1)}" stroke="var(--line)" stroke-dasharray="4"/><polyline fill="none" stroke="var(--acc)" stroke-width="2.5" points="${y.map((v,k)=>X(k)+','+Yy(v)).join(' ')}"/><text x="6" y="16" fill="var(--muted)" font-size="12">step response, 0 … ${T.toFixed(1)} s</text>`;
const z=P.s/Math.hypot(P.s,P.w);document.getElementById('pp').textContent=`−${P.s.toFixed(2)} ± j${P.w.toFixed(2)}`;document.getElementById('z').textContent=z.toFixed(3);
document.getElementById('os').textContent=m.overshoot.toFixed(1)+' %';document.getElementById('ts').textContent=m.settling.toFixed(2)+' s';}
let drag=false;S.onpointerdown=()=>drag=true;window.onpointerup=()=>drag=false;
S.onpointermove=e=>{if(!drag)return;const r=S.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*260-220,yy=(e.clientY-r.top)/r.height*340-170;P.s=Math.max(0.05,-x/K);P.w=Math.min(8,Math.abs(yy)/K);draw();};draw();"""


def run(p):
    p.write("web/index.html", page("s-plane explorer", "Drag a pole pair; the step response follows.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "closed-form responses (tested)")
    js = p.dir / "web" / "calc.js"
    r = p.rng
    worst, osd, tsr = 0, [], []
    for _ in range(200):
        s, w = float(r.uniform(0.2, 5)), float(r.uniform(0.1, 10))
        T = np.linspace(0, 12 / s, 4000)
        yj = np.array(node(js, [["stepPair", [s, w, T.tolist()]]])[0])
        _, ys = signal.step(([s * s + w * w], [1, 2 * s, s * s + w * w]), T=T)
        worst = max(worst, np.max(np.abs(yj - ys)))
        m = node(js, [["metrics", [yj.tolist(), T.tolist()]]])[0]
        z = s / np.hypot(s, w)
        osd.append((100 * np.exp(-pi * z / np.sqrt(1 - z * z)), m["overshoot"], z))
        tsr.append((4 / s, m["settling"], z))
    p.compare("Max |JS step − SciPy step| over 200 pole pairs", 0, worst, "", kind="abs", tol=1e-9)
    osd = np.array(osd); tsr = np.array(tsr)
    p.compare("Overshoot: worst |measured − 100·exp(−πζ/√(1−ζ²))|", 0, np.max(np.abs(osd[:, 1] - osd[:, 0])), "pp", kind="abs", tol=0.1)
    ratio = tsr[:, 1] / tsr[:, 0]
    p.compare("Settling time / (4/σ), median over the 200 systems", 1.0, np.median(ratio), "", tol=15)
    p.metric("Settling time / (4/σ), range", f"{ratio.min():.2f} – {ratio.max():.2f}")
    T = np.linspace(0, 20, 4000)
    yr = np.array(node(js, [["stepReal", [0.5, 3.0, T.tolist()]]])[0]); _, ysr = signal.step(([1.5], [1, 3.5, 1.5]), T=T)
    p.compare("Two real poles (−0.5, −3): JS vs SciPy", 0, np.max(np.abs(yr - ysr)), "", kind="abs", tol=1e-9)
    fig, ax = p.fig(1, 2, w=11)
    zz = np.linspace(0.01, 0.99, 200)
    ax[0].plot(zz, 100 * np.exp(-pi * zz / np.sqrt(1 - zz * zz)), color=C_PRED, ls="--", label="formula")
    ax[0].plot(osd[:, 2], osd[:, 1], ".", color=C_MEAS, label="measured from calc.js")
    style_axes(ax[0], "damping ratio ζ = cos θ", "overshoot (%)", "Overshoot depends only on the pole angle")
    ax[1].scatter(tsr[:, 2], ratio, s=8, color=C_MEAS)
    ax[1].axhline(1, color=C_PRED, ls="--")
    style_axes(ax[1], "damping ratio ζ", "settling time ÷ (4/σ)", "4/σ is an envelope estimate", legend=False)
    p.save(fig, "splane", "Overshoot vs damping ratio, and how good the 4/σ settling rule is across 200 pole positions.")
    p.discuss(f"""The page's closed-form responses match SciPy to machine precision, and the overshoot measured from them lies exactly on the ζ-formula curve —
overshoot is a function of pole *angle* only, which is the key intuition the drag interaction teaches. The settling-time rule is looser: 4/σ is the
time for the envelope e^(−σt) to reach 2 %, but the response itself may leave the ±2 % band earlier (when an oscillation peak happens to fall
inside it) or later (heavy damping, where the decay is slower than the envelope suggests), giving ratios {ratio.min():.2f}–{ratio.max():.2f}.""")
# tol-convention: relative tolerances are in percent
