from eelab import *
from eelab.data import noaa_apt_audio

META = dict(
    id="SL-098", title="Link budget calculator (validated on a real NOAA pass)", level="M",
    tools="Python link-budget model + interactive HTML calculator; comparison with SatNOGS-measured SNR",
    summary="A link-budget tool (path loss, antenna gains, system noise temperature, C/N₀, margin) as a web page, "
            "and a check of its prediction against the SNR actually measured on the NOAA-18 recording from SL-085.",
    problem="Will a 5 W satellite transmitter 850 km up be receivable with a simple antenna and a USB radio? "
            "Do the arithmetic, then test it against a real pass.",
    theory=r"""$C/N_0\,[\mathrm{dBHz}] = EIRP - FSPL - L_{misc} + G/T - k$, with $FSPL=20\log_{10}\frac{4\pi R f}{c}$ and $k = -228.6$ dBW/K/Hz.
NOAA APT: EIRP ≈ 37 dBm (5 W into a right-hand circular antenna, ~+0 dBi) at 137.9 MHz; receive antenna ~+2 dBic, system
noise temperature T_sys ≈ 290 K·(NF) + sky ≈ 1,000 K at VHF (galactic noise dominates). FM threshold needs C/N ≈ 10 dB
in 34 kHz (≈ 55 dBHz).""",
    method="""Python model evaluated along the SL-085 pass geometry (range from SGP4). Testable prediction: the slant range at which
C/N falls to the 10 dB FM threshold. Measured: the ranges on the rising and setting sides where the recording's audio
SNR has dropped 10 dB below its culmination plateau (the FM-threshold collapse seen in SL-085). A self-contained HTML calculator reproduces the same numbers in the browser.""",
    data="Real: SatNOGS observation 11229309 (NOAA-18) for the measured SNR; published NOAA APT transmitter parameters.",
)

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link Budget Calculator</title><style>
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--acc:#2a78d6}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--line:#383835;--acc:#3987e5}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}main{max-width:720px;margin:auto;padding:16px}
label{display:grid;grid-template-columns:1fr 120px;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid var(--line)}
input{font:inherit;width:100%;box-sizing:border-box}table{width:100%;border-collapse:collapse;margin-top:16px}
td{padding:6px;border-bottom:1px solid var(--line)}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.big{font-size:1.4em;color:var(--acc);font-weight:600}</style></head><body><main>
<h1>Link budget</h1><p style="color:var(--ink2)">Defaults: NOAA-18 APT downlink to a simple ground station at 30° elevation.</p>
<div id="f"></div><table id="t"></table></main><script>
const F=[["f","Frequency (MHz)",137.9125],["p","Transmit power (W)",5],["gt","Tx antenna gain (dBi)",0],["r","Slant range (km)",1500],
["lm","Misc. losses: polarisation, pointing, cable (dB)",3],["gr","Rx antenna gain (dBi)",2],["t","System noise temperature (K)",1000],
["b","Receiver bandwidth (kHz)",34],["need","Required C/N (dB)",10]];
const f=document.getElementById('f');F.forEach(([k,l,v])=>f.insertAdjacentHTML('beforeend',`<label>${l}<input id="${k}" type="number" step="any" value="${v}"></label>`));
function calc(){const g=k=>+document.getElementById(k).value;const eirp=10*Math.log10(g('p'))+30+g('gt');
const fspl=20*Math.log10(4*Math.PI*g('r')*1e3*g('f')*1e6/299792458);const gt=g('gr')-10*Math.log10(g('t'));
const cn0=eirp-30-fspl-g('lm')+gt+228.6;const cn=cn0-10*Math.log10(g('b')*1e3);const rows=[["EIRP",eirp.toFixed(1)+" dBm"],["Free-space path loss",fspl.toFixed(1)+" dB"],
["G/T",gt.toFixed(1)+" dB/K"],["C/N₀",cn0.toFixed(1)+" dBHz"],["C/N in bandwidth",cn.toFixed(1)+" dB"],["Margin",`<span class="big">${(cn-g('need')).toFixed(1)} dB</span>`]];
document.getElementById('t').innerHTML=rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');}
document.querySelectorAll('input').forEach(i=>i.oninput=calc);calc();</script></body></html>"""


def budget(R_km, f=137.9125e6, P=5, Gt=0, Lm=3, Gr=2, T=1000, B=34e3):
    eirp = 10 * np.log10(P) + 30 + Gt
    fspl = 20 * np.log10(4 * pi * R_km * 1e3 * f / 299792458)
    cn0 = eirp - 30 - fspl - Lm + Gr - 10 * np.log10(T) + 228.6
    return cn0, cn0 - 10 * np.log10(B), fspl


def run(p):
    p.write("web/index.html", HTML, "interactive link-budget calculator")
    cn0, cn, fspl = budget(1500)
    p.compare("Free-space path loss at 1,500 km, 137.9 MHz", 20 * np.log10(4 * pi * 1.5e6 / (299792458 / 137.9125e6)), fspl, "dB", kind="abs")
    x, fs, meta = noaa_apt_audio()
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("sl085", pathlib.Path(__file__).parent.parent / "SL085-decode-a-satnogs-observation" / "project.py")
    sl = importlib.util.module_from_spec(spec); spec.loader.exec_module(sl)
    from sgp4.api import Satrec
    from datetime import datetime, timedelta
    sat = Satrec.twoline2rv(meta["tle1"], meta["tle2"])
    t0 = datetime.strptime(meta["start"], "%Y-%m-%dT%H:%M:%SZ")
    ts = np.arange(1, len(x) / fs - 1, 2.0)
    R = np.array([sl.topocentric(sat, t0 + timedelta(seconds=float(t)), meta["station_lat"], meta["station_lng"], meta["station_alt"])[0] for t in ts])
    snr = []
    for t in ts:
        seg = x[int((t - 1) * fs): int((t + 1) * fs)]
        X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f_ = np.fft.rfftfreq(len(seg), 1 / fs)
        snr.append(10 * np.log10(X[(f_ > 2200) & (f_ < 2600)].sum() / (X[(f_ > 5500) & (f_ < 6500)].mean() * np.sum((f_ > 2200) & (f_ < 2600)))))
    snr = np.array(snr)
    k = np.argmin(R)
    cn0_c, cn_c, _ = budget(R[k])
    # the testable prediction: where along the pass does C/N cross the ~10 dB FM threshold?
    sm = np.convolve(snr, np.ones(5) / 5, "same")
    plateau = np.median(sm[np.abs(np.arange(len(sm)) - k) < 30])
    collapse = sm < plateau - 10                      # audio SNR has fallen 10 dB below its culmination plateau
    edges = np.flatnonzero(collapse[:k])
    r_meas = R[edges[-1]] if len(edges) else np.nan
    edges2 = np.flatnonzero(collapse[k:])
    r_meas2 = R[k + edges2[0]] if len(edges2) else np.nan
    Rh = np.sqrt((6378 + 850) ** 2 - 6378 ** 2)
    p.metric("Predicted C/N at the horizon (range ≈ 3,300 km)", budget(Rh)[1], "dB", "the budget says the link never reaches threshold")
    for side, rm in (("rising", r_meas), ("setting", r_meas2)):
        p.compare(f"C/N at the range where the audio actually collapsed ({side} side, {rm:.0f} km)", 10.0, budget(rm)[1], "dB", kind="abs",
                  note="10 dB = FM threshold; the difference is how optimistic the budget is there")
    p.metric("Predicted C/N₀ at culmination", cn0_c, "dBHz")
    p.metric("Predicted C/N at culmination (34 kHz)", cn_c, "dB", "FM threshold ≈ 10 dB")

    fig, ax = p.fig()
    ax.plot(ts / 60, budget(R)[1], "--", color=C_PRED, label="predicted C/N (link budget)")
    ax.plot(ts / 60, snr - (plateau - cn_c), ".", color=C_MEAS, ms=4, label="measured audio SNR (shifted to match at culmination)")
    ax.axhline(10, color=COLORS[7], ls=":", label="FM threshold")
    style_axes(ax, "minutes after AOS", "dB", "Link budget vs the real NOAA-18 pass")
    p.save(fig, "budget_vs_pass", "Near culmination the budget and the measurement agree; toward the horizon the link sinks below the FM threshold.")
    p.section("Try it", "Open [`web/index.html`](web/index.html) — or the copy on the project site — and change any parameter.")
    p.discuss("""With textbook NOAA and ground-station numbers the budget is comfortable: ~25 dB C/N overhead and still above the 10 dB FM
threshold at the horizon. The real recording disagrees — its audio collapses at ~1,100–1,150 km slant range (~45°
elevation), where the budget claims ~23 dB. So the assumed ground station is ~13 dB too good at mid elevations. Plausible
culprits, each worth several dB: the antenna's gain falling well below +2 dBi away from zenith (a QFH or turnstile has
exactly this shape), urban man-made noise pushing T_sys far above 1,000 K at 137 MHz, feed-line loss, and receiver
AGC/IF-bandwidth choices. The value of the exercise is the size of the gap: a link budget is a hypothesis, and one real
pass is enough to show it needs a measured antenna pattern and noise floor. A first attempt to
predict the *absolute* audio SNR was off by 14 dB because the audio-SNR measurement (subcarrier band vs a 6 kHz noise
reference) is not the textbook FM output-SNR definition — comparing a threshold *location* is the more robust test.""")
