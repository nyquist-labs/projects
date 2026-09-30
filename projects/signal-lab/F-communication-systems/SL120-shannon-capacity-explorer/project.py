from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-120", title="Shannon capacity explorer", level="M",
    tools="HTML/JS interactive plot + Python: C = B·log₂(1+SNR), gap-to-capacity of real modulations (Monte Carlo)",
    summary="An interactive page relating bandwidth, SNR and capacity, plus a measurement of how far uncoded BPSK, QPSK and "
            "16-QAM are from the Shannon limit at BER 10⁻⁵, and the −1.59 dB ultimate limit.",
    problem="What is the maximum data rate a channel can carry, and how close do practical signals get?",
    theory=r"""$C=B\log_2(1+SNR)$. In terms of spectral efficiency η = R/B and $E_b/N_0$: reliable communication requires
$E_b/N_0\ge\frac{2^\eta-1}{\eta}$, which tends to ln 2 = −1.59 dB as η → 0. Uncoded QPSK (η = 2) needs 9.6 dB at 10⁻⁵ where the limit is
1.76 dB: a 7.8 dB gap that coding (turbo, LDPC) closes to within ~1 dB.""",
    method="""Required E_b/N₀ at BER 10⁻⁵ for BPSK, QPSK, 16-QAM from closed forms, checked by Monte Carlo near the operating point; Shannon
minimum E_b/N₀ at the same η; plotted on the η–E_b/N₀ plane. Web page: sliders for B and SNR.""",
)

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shannon Capacity</title>
<style>:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--a:#2a78d6}@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--a:#3987e5}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}main{max-width:720px;margin:auto;padding:16px}label{display:block;margin:10px 0}input{width:100%}
.big{font-size:2em;color:var(--a);font-weight:600;font-variant-numeric:tabular-nums}</style></head><body><main><h1>Shannon capacity</h1>
<label>Bandwidth: <b id="bv"></b><input id="b" type="range" min="3" max="9" step="0.01" value="6"></label>
<label>SNR: <b id="sv"></b><input id="s" type="range" min="-10" max="40" step="0.1" value="20"></label>
<p>Capacity</p><p class="big" id="c"></p><p id="e" style="color:var(--ink2)"></p></main><script>
function f(x){const u=['bit/s','kbit/s','Mbit/s','Gbit/s'];let i=0;while(x>=1000&&i<3){x/=1000;i++;}return x.toFixed(3)+' '+u[i];}
function upd(){const B=10**+b.value,S=+s.value,snr=10**(S/10),C=B*Math.log2(1+snr);bv.textContent=f(B).replace('bit/s','Hz');sv.textContent=S.toFixed(1)+' dB';c.textContent=f(C);
const eta=C/B,ebn0=10*Math.log10(snr/eta);e.textContent=`Spectral efficiency ${eta.toFixed(2)} bit/s/Hz · minimum Eb/N0 at this efficiency ${ebn0.toFixed(2)} dB (limit −1.59 dB as η→0)`;}
const b=document.getElementById('b'),s=document.getElementById('s');[b,s].forEach(x=>x.oninput=upd);upd();</script></body></html>"""


def run(p):
    p.write("web/index.html", HTML, "interactive capacity explorer")
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    from scipy.optimize import brentq
    mods = {"BPSK": (1, lambda e: Q(np.sqrt(2 * e))), "QPSK": (2, lambda e: Q(np.sqrt(2 * e))),
            "16-QAM": (4, lambda e: 3 / 8 * erfc(np.sqrt(4 * e / 10)))}
    rows = []
    for nm, (eta, f) in mods.items():
        need = 10 * np.log10(brentq(lambda e: f(e) - 1e-5, 1e-3, 1e4))
        lim = 10 * np.log10((2**eta - 1) / eta)
        e_lin = 10 ** (need / 10)
        nsim = 400000
        if nm == "16-QAM":
            lv = np.array([-3, -1, 1, 3]); i = p.rng.integers(0, 4, nsim); qq = p.rng.integers(0, 4, nsim)
            Es = 10.0; N0 = Es / (4 * e_lin)
            y = lv[i] + np.sqrt(N0 / 2) * p.rng.normal(size=nsim)
            ih = np.argmin(np.abs(y[:, None] - lv), 1)
            gray = np.array([0, 1, 3, 2]); ber = np.mean([bin(int(a) ^ int(b)).count("1") for a, b in zip(gray[ih[:40000]], gray[i[:40000]])]) / 2
        else:
            b = p.rng.integers(0, 2, nsim); y = (1 - 2 * b) + np.sqrt(1 / (2 * e_lin)) * p.rng.normal(size=nsim); ber = np.mean((y < 0) != b)
        p.compare(f"{nm}: BER at its predicted 10⁻⁵ operating point (Monte Carlo)", 1e-5, ber, "", kind="abs")
        p.metric(f"{nm}: gap to Shannon at η = {eta}", need - lim, "dB", f"needs {need:.2f} dB, limit {lim:.2f} dB")
        rows.append((nm, eta, need, lim))
    etas = np.linspace(0.01, 6, 400)
    p.compare("Ultimate Shannon limit (η → 0)", 10 * np.log10(np.log(2)), 10 * np.log10((2**0.001 - 1) / 0.001), "dB", kind="abs")
    fig, ax = p.fig()
    ax.plot(10 * np.log10((2**etas - 1) / etas), etas, color=C_PRED, label="Shannon limit")
    for i, (nm, eta, need, lim) in enumerate(rows):
        ax.plot(need, eta, "o", ms=9, color=COLORS[i], label=f"{nm} @ 10⁻⁵ (uncoded)")
        ax.annotate("", (lim, eta), (need, eta), arrowprops=dict(arrowstyle="<->", color=COLORS[i]))
    ax.axvline(-1.59, color="gray", ls=":", lw=1)
    ax.fill_betweenx(etas, -2, 10 * np.log10((2**etas - 1) / etas), color="gray", alpha=.08)
    ax.set_xlim(-2, 16)
    style_axes(ax, "Eb/N0 (dB)", "spectral efficiency η (bit/s/Hz)", "Distance to capacity (shaded: impossible)")
    p.save(fig, "shannon", "Uncoded modulations sit 7–9 dB from the Shannon limit; the arrows are what coding can recover.")
    p.section("Try it", "Open [`web/index.html`](web/index.html) to explore C = B·log₂(1 + SNR).")
    p.discuss("""Monte Carlo confirms each modulation's 10⁻⁵ operating point, and the Shannon bound puts them in perspective: uncoded QPSK
wastes ~7.8 dB relative to what is theoretically possible at 2 bit/s/Hz. That gap is the entire motivation for modern
channel coding — LDPC and turbo codes recover all but ~0.5–1 dB of it — and the −1.59 dB floor is absolute: no scheme,
however clever, works below it.""")
