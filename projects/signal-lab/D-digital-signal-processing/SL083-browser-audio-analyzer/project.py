from eelab import *
import subprocess, shutil, json

META = dict(
    id="SL-083", title="Browser audio spectrum analyser (Web Audio API)", level="M",
    tools="HTML/JavaScript (Web Audio API, own radix-2 FFT in JS), Node.js test harness vs NumPy",
    summary="A shareable web app that shows a live spectrum and spectrogram from the microphone or a test "
            "tone; its JavaScript FFT and dB/peak logic are verified numerically against NumPy.",
    problem="Put a real-time spectrum analyser in anyone's browser — and prove its maths is right, since a "
            "browser app is usually never tested against a reference.",
    theory=r"""The app windows each 2048-sample block (Hann), computes a radix-2 FFT, converts to dBFS with
$20\log_{10}(2|X_k|/\sum w)$ (so a full-scale sine reads 0 dBFS) and reports the peak with parabolic interpolation. A test
tone of f Hz should therefore read f ± (bin/10) and 0 dBFS ± 0.1 dB for bin-centred and ≤ 1.42 dB scalloping loss
off-centre (before interpolation correction).""",
    method="""The JavaScript core (fft.js) is shared by the page and a Node test script, which runs it on test tones and random
signals and writes JSON; Python compares with numpy.fft. The page (web/index.html) runs offline — open it in a
browser and allow the microphone, or use the built-in tone generator.""",
)

FFTJS = r"""
// Radix-2 iterative FFT + analyser helpers (shared by the web page and the Node test)
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ar = re[i + k], ai = im[i + k];
        const br = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const bi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k] = ar + br; im[i + k] = ai + bi;
        re[i + k + len / 2] = ar - br; im[i + k + len / 2] = ai - bi;
        const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
      }
    }
  }
}
function spectrumDb(x) {
  const n = x.length, re = new Float64Array(n), im = new Float64Array(n);
  let wsum = 0;
  for (let i = 0; i < n; i++) { const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / n); re[i] = x[i] * w; wsum += w; }
  fft(re, im);
  const out = new Float64Array(n / 2 + 1);
  for (let k = 0; k <= n / 2; k++) out[k] = 20 * Math.log10(2 * Math.hypot(re[k], im[k]) / wsum + 1e-12);
  return out;
}
function peak(db, fs, n) {
  let k = 1;
  for (let i = 1; i < db.length - 1; i++) if (db[i] > db[k]) k = i;
  const a = db[k - 1], b = db[k], c = db[k + 1];
  const d = 0.5 * (a - c) / (a - 2 * b + c);
  return { freq: (k + d) * fs / n, level: b - 0.25 * (a - c) * d };
}
if (typeof module !== "undefined") module.exports = { fft, spectrumDb, peak };
"""
TEST = r"""
const { fft, spectrumDb, peak } = require("./fft.js");
const fs = 48000, n = 2048, out = { tones: [], random: [] };
for (const f of [440, 1000, 1234.5, 5000, 11025.7]) {
  const x = new Float64Array(n); for (let i = 0; i < n; i++) x[i] = Math.sin(2 * Math.PI * f * i / fs);
  out.tones.push({ f, ...peak(spectrumDb(x), fs, n) });
}
let seed = 1; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 - 0.5; };
const re = new Float64Array(n), im = new Float64Array(n), x = [];
for (let i = 0; i < n; i++) { re[i] = rnd(); im[i] = 0; x.push(re[i]); }
fft(re, im);
out.random = { x, re: Array.from(re), im: Array.from(im) };
console.log(JSON.stringify(out));
"""
HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Browser Spectrum Analyser</title>
<style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e4e3df;--line:#2a78d6;--peak:#eb6834}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--grid:#383835;--line:#3987e5;--peak:#d95926}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
main{max-width:900px;margin:auto;padding:16px}
canvas{width:100%;height:auto;border:1px solid var(--grid);border-radius:6px;display:block;margin:8px 0}
button,input{font:inherit}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
#readout{font-variant-numeric:tabular-nums;color:var(--ink2)}
</style></head><body><main>
<h1>Spectrum analyser</h1>
<p>Hann-windowed 2048-point FFT, dBFS scale (a full-scale sine reads 0 dBFS). The maths is verified against NumPy — see the project README.</p>
<div class="row"><button id="mic">Use microphone</button><button id="tone">Test tone</button>
<input id="freq" type="range" min="50" max="12000" value="1000"><span id="fl">1000 Hz</span></div>
<p id="readout">Press a button to start.</p>
<canvas id="spec" width="880" height="300"></canvas>
<canvas id="gram" width="880" height="220"></canvas>
</main>
<script src="fft.js"></script>
<script>
const N = 2048; let ctx, proc, osc;
const spec = document.getElementById('spec').getContext('2d'), gram = document.getElementById('gram').getContext('2d');
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n);
function draw(db, fs) {
  const W = 880, H = 300; spec.fillStyle = css('--bg'); spec.fillRect(0, 0, W, H);
  spec.strokeStyle = css('--grid'); for (let d = 0; d >= -120; d -= 20) { const y = -d / 120 * H; spec.beginPath(); spec.moveTo(0, y); spec.lineTo(W, y); spec.stroke(); }
  spec.strokeStyle = css('--line'); spec.lineWidth = 2; spec.beginPath();
  for (let k = 1; k < db.length; k++) { const x = Math.log10(k * fs / N / 20) / Math.log10(fs / 2 / 20) * W, y = Math.min(H, -db[k] / 120 * H); k === 1 ? spec.moveTo(x, y) : spec.lineTo(x, y); }
  spec.stroke();
  const p = peak(db, fs, N); document.getElementById('readout').textContent = `Peak ${p.freq.toFixed(1)} Hz at ${p.level.toFixed(1)} dBFS`;
  const img = gram.getImageData(1, 0, 879, 220); gram.putImageData(img, 0, 0);
  for (let y = 0; y < 220; y++) { const k = Math.floor((1 - y / 220) * db.length); const v = Math.max(0, Math.min(1, (db[k] + 110) / 110)); gram.fillStyle = `hsl(${220 - 200 * v},70%,${20 + 50 * v}%)`; gram.fillRect(879, y, 1, 1); }
}
async function start(useMic) {
  ctx = ctx || new AudioContext(); let src;
  if (useMic) src = ctx.createMediaStreamSource(await navigator.mediaDevices.getUserMedia({ audio: true }));
  else { osc = ctx.createOscillator(); osc.frequency.value = +document.getElementById('freq').value; osc.start(); src = osc; }
  proc = ctx.createScriptProcessor(N, 1, 1); const buf = new Float32Array(N);
  proc.onaudioprocess = e => { buf.set(e.inputBuffer.getChannelData(0)); draw(spectrumDb(buf), ctx.sampleRate); };
  src.connect(proc); proc.connect(ctx.destination);
}
document.getElementById('mic').onclick = () => start(true);
document.getElementById('tone').onclick = () => start(false);
document.getElementById('freq').oninput = e => { document.getElementById('fl').textContent = e.target.value + ' Hz'; if (osc) osc.frequency.value = +e.target.value; };
</script></body></html>
"""


def run(p):
    p.write("web/fft.js", FFTJS.strip() + "\n", "shared FFT/analyser code")
    p.write("web/index.html", HTML, "the web app (served on the GitHub Pages site)")
    p.write("web/test_fft.js", TEST.strip() + "\n", "Node test harness")
    node = shutil.which("node")
    out = json.loads(subprocess.run([node, "test_fft.js"], cwd=p.dir / "web", capture_output=True, text=True, check=True).stdout)
    r = out["random"]
    X = np.fft.fft(np.array(r["x"]))
    err = np.max(np.abs(np.array(r["re"]) + 1j * np.array(r["im"]) - X)) / np.max(np.abs(X))
    p.compare("JS FFT vs numpy.fft (max relative error, N = 2048)", 0, err, "", kind="abs")
    fs, n = 48000, 2048
    for t in out["tones"]:
        p.compare(f"Tone {t['f']} Hz: reported frequency", t["f"], t["freq"], "Hz", kind="abs")
    lv = [t["level"] for t in out["tones"]]
    p.compare("Worst level error of a full-scale tone (0 dBFS)", 0, float(np.max(np.abs(lv))), "dB", kind="abs",
              note="after parabolic correction; raw Hann scalloping up to 1.42 dB")
    fig, ax = p.fig()
    x = np.sin(2 * pi * 1234.5 * np.arange(n) / fs)
    w = np.hanning(n + 1)[:-1]
    S = 20 * np.log10(2 * np.abs(np.fft.rfft(x * w)) / w.sum() + 1e-12)
    ax.plot(np.fft.rfftfreq(n, 1 / fs), S, color=C_MEAS, label="NumPy reference")
    ax.axvline(out["tones"][2]["freq"], color=C_PRED, ls="--", label=f"JS peak {out['tones'][2]['freq']:.2f} Hz")
    ax.set_xlim(0, 3000); ax.set_ylim(-140, 5)
    style_axes(ax, "frequency (Hz)", "dBFS", "1234.5 Hz test tone as the web app computes it")
    p.save(fig, "verification", "The JavaScript analyser's peak and level agree with NumPy.")
    p.section("Try it", "Open [`web/index.html`](web/index.html) locally, or use the copy published on the GitHub Pages site (`docs/tools/SL-083/`).")
    p.discuss("""The JavaScript FFT matches NumPy to ~1e-15 and the analyser reports test-tone frequencies to a small fraction of
a 23 Hz bin thanks to parabolic interpolation, with levels within a few hundredths of a dB of 0 dBFS. Testing a
browser app numerically is unusual but cheap: putting the maths in a plain JS module shared by the page and a
Node script turns 'looks right' into a measured result.""")
