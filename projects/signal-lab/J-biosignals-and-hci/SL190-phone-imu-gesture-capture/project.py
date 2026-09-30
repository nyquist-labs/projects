from eelab import *
from eelab.data import har

META = dict(
    id="SL-190", title="Your phone as a free sensor: IMU capture page + cadence analysis", level="M",
    tools="HTML/JS DeviceMotion capture page (records and downloads CSV from your own phone) + NumPy analysis validated on UCI-HAR raw smartphone signals",
    summary="A browser page that records your phone's accelerometer and gyroscope to CSV, plus an analysis that estimates walking cadence "
            "from the dominant acceleration frequency — validated on the raw 50 Hz signals of 30 people in the UCI-HAR dataset.",
    problem="Every phone contains a lab-grade IMU. How do you record it without an app, and what can one sensor tell you about how someone walks?",
    theory=r"""Walking produces vertical acceleration at the step frequency (typically 1.6–2.0 Hz, i.e. 95–120 steps/min for adults) with a weaker component at the stride
frequency (half of it). The acceleration magnitude's spectral peak in 1–3 Hz therefore estimates cadence; stair descent is usually faster than ascent.""",
    method="""UCI-HAR raw total acceleration (50 Hz, 2.56-s windows) for walking, upstairs, downstairs; windows concatenated per subject and activity; Welch spectrum of |a|;
cadence = 60 × peak frequency. The capture page uses the DeviceMotionEvent API (iOS asks for permission) and saves CSV at the device rate.""",
    data="Real: UCI-HAR raw inertial signals (Samsung Galaxy S II at the waist).",
)

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phone IMU Recorder</title>
<style>:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--a:#2a78d6}@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--a:#3987e5}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}main{max-width:640px;margin:auto;padding:16px}
button{font:inherit;padding:10px 16px;margin:4px 4px 4px 0;border-radius:8px;border:1px solid var(--ink2);background:transparent;color:var(--ink)}
#n{font-variant-numeric:tabular-nums;color:var(--ink2)}canvas{width:100%;height:auto}</style></head><body><main>
<h1>Phone IMU recorder</h1><p>Open this page on your phone, press Start, walk, press Stop, then Download. Data never leaves your device.</p>
<button id="s">Start</button><button id="t">Stop</button><button id="d">Download CSV</button><p id="n">0 samples</p><canvas id="c" width="600" height="200"></canvas>
</main><script>
let rec=[],on=false;const c=document.getElementById('c').getContext('2d');
function onm(e){if(!on)return;const a=e.accelerationIncludingGravity||{},g=e.rotationRate||{};rec.push([performance.now()/1000,a.x,a.y,a.z,g.alpha,g.beta,g.gamma]);
document.getElementById('n').textContent=rec.length+' samples';if(rec.length%5==0)draw();}
function draw(){const w=600,h=200,last=rec.slice(-300);c.clearRect(0,0,w,h);c.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--a');c.beginPath();
last.forEach((r,i)=>{const m=Math.hypot(r[1]||0,r[2]||0,r[3]||0);const y=h-(m/20)*h;i?c.lineTo(i*2,y):c.moveTo(0,y);});c.stroke();}
document.getElementById('s').onclick=async()=>{if(typeof DeviceMotionEvent!=='undefined'&&DeviceMotionEvent.requestPermission){await DeviceMotionEvent.requestPermission();}
rec=[];on=true;window.addEventListener('devicemotion',onm);};
document.getElementById('t').onclick=()=>{on=false;};
document.getElementById('d').onclick=()=>{const csv='t_s,ax,ay,az,gyro_alpha,gyro_beta,gyro_gamma\n'+rec.map(r=>r.join(',')).join('\n');
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='imu.csv';a.click();};
</script></body></html>"""


def run(p):
    from scipy import signal
    p.write("web/index.html", HTML, "phone IMU recorder (open on a phone)")
    X, y, subj = har("train", raw=True)
    X2, y2, s2 = har("test", raw=True)
    X = np.concatenate([X, X2]); y = np.concatenate([y, y2]); subj = np.concatenate([subj, s2])
    mag = np.sqrt((X[:, 6:9] ** 2).sum(1))
    res = {1: [], 2: [], 3: []}
    for s in np.unique(subj):
        for act in (1, 2, 3):
            m = (subj == s) & (y == act)
            if m.sum() < 8:
                continue
            sig = mag[m][:, 32:96].ravel()          # non-overlapping half of each 50 %-overlap window
            f, P = signal.welch(sig - sig.mean(), 50, nperseg=512)
            band = (f > 1.0) & (f < 3.0)
            res[act].append(60 * f[band][np.argmax(P[band])])
    walk = np.array(res[1]); up = np.array(res[2]); down = np.array(res[3])
    p.compare("Median walking cadence (adult norm ≈ 100–120 steps/min)", 110, np.median(walk), "steps/min", kind="abs")
    p.compare("Stairs down faster than stairs up (median difference > 0)", 1, int(np.median(down) > np.median(up)), "", kind="abs")
    p.metric("Median cadence: upstairs / downstairs", f"{np.median(up):.0f} / {np.median(down):.0f} steps/min")
    fig, ax = p.fig()
    ax.boxplot([walk, up, down], tick_labels=["walking", "upstairs", "downstairs"])
    style_axes(ax, None, "cadence (steps/min)", "Cadence from a waist-worn phone, 30 people", legend=False)
    p.save(fig, "cadence", "Step frequency read straight off the acceleration spectrum.")
    p.csv("cadence", walking=np.r_[walk, np.full(max(0, 30 - len(walk)), np.nan)][:30])
    p.section("Record your own", "Open [`web/index.html`](web/index.html) on your phone (the project site hosts a copy), record a walk and feed the CSV to the same analysis.")
    p.discuss("""The dominant spectral peak of the acceleration magnitude gives a cadence in the normal adult range for level walking, and descending stairs comes
out faster than ascending, as expected. The method can lock onto the stride frequency (half the step rate) or a harmonic when steps are
asymmetric, which shows up as outliers; a step detector in the time domain or a harmonic-sum spectrum is more robust. The capture page makes the
same measurement possible on any phone, with no app store.""")
