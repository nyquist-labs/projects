from eelab import *
from eelab.web import page, node, attach
from eelab.data import alice_text
from collections import Counter

META = dict(
    id="AM-204", title="Entropy calculator (interactive, verified on real text)", level="E",
    tools="Browser tool (HTML + JavaScript): entropy of typed probabilities, and for pasted text the block entropies H_k, conditional entropies H(Xₙ|previous k−1), Miller–Madow correction and Huffman code length; the JavaScript is verified under Node against independent Python computations on a full book",
    summary="A calculator that turns probabilities or text into bits, with the estimation pitfalls made visible: conditional entropy of English falls as more "
            "context is used, but with a finite text the estimates keep falling for the wrong reason — too few samples. The engine is checked against Python before publication.",
    problem="'English has about 1 bit per letter' — how is such a number measured, and why does a naive measurement on one book give the wrong answer?",
    theory=r"""$H(p)=-\sum p_i\log_2p_i$, maximal ($\log_2 K$) for a uniform distribution. For a text, the order-k block entropy $H_k$ of k-letter strings gives the conditional entropy $h_k=H_k-H_{k-1}$, which decreases with k toward the entropy rate (Shannon estimated ≈ 1 bit/letter for English
using human predictions). A plug-in estimate from N samples is biased low by ≈ (number of occupied cells − 1)/(2N ln 2) (Miller–Madow); once $K^k$ approaches N almost every block is unique and $h_k$ collapses toward 0 — an artefact, not information. The optimal prefix code length L satisfies H ≤ L < H + 1.""",
    method="""calc.js tested under Node: entropy and Huffman length on 300 random distributions vs Python; block and conditional entropies of 'Alice's Adventures in Wonderland' (144 k characters) for k = 1…8 vs Python counters. Shuffled-text control: the same letters in random order
(true conditional entropy = H₁ at every order) to expose the finite-sample bias.""",
    data="Project Gutenberg eBook #11 (public domain).",
)

BODY = """<div class="card"><b>Probabilities</b><label>comma-separated weights<input id="pw" value="0.5, 0.25, 0.125, 0.125"></label>
<p>H = <span class="big" id="h"></span> bits &nbsp; <span class="muted" id="hx"></span></p></div>
<div class="card"><b>Text</b><textarea id="tx" rows="6" style="width:100%;font:inherit;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px">It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness</textarea>
<table><thead><tr><th>k</th><th class="n">block entropy H_k (bits)</th><th class="n">conditional H(Xₙ | k−1 previous)</th><th class="n">distinct blocks</th></tr></thead><tbody id="tb"></tbody></table>
<p class="muted" id="warn"></p></div>"""
JS = r"""const $=id=>document.getElementById(id);
function upd(){const p=$('pw').value.split(/[ ,;]+/).map(Number).filter(x=>x>=0&&isFinite(x));if(p.length){const h=entropy(p);$('h').textContent=h.toFixed(4);
$('hx').textContent=`max for ${p.length} outcomes: ${Math.log2(p.length).toFixed(4)} · Huffman average length: ${huffmanLength(p).toFixed(4)} bits`;}
const t=$('tx').value;const r=textReport(t,6);$('tb').innerHTML=r.map(([k,b,c,n])=>`<tr><td>${k}</td><td class="n">${b.toFixed(3)}</td><td class="n">${c.toFixed(3)}</td><td class="n">${n}</td></tr>`).join('');
const n1=r[0][3];$('warn').textContent=t.length<50*Math.pow(n1,3)?`Caution: with ${t.length} characters, estimates beyond k ≈ ${Math.max(1,Math.floor(Math.log(t.length/10)/Math.log(Math.max(n1,2))))} mostly reflect the shortness of the text, not its structure.`:'';}
$('pw').oninput=upd;$('tx').oninput=upd;upd();"""


def run(p):
    p.write("web/index.html", page("Entropy calculator", "Bits from probabilities or from text — with a warning when the text is too short for the estimate.", BODY, inline=JS), "interactive tool")
    attach(p, "web/calc.js", "calculation engine (tested under Node)")
    js = p.dir / "web" / "calc.js"; r = p.rng
    dists = [list(r.dirichlet(np.ones(int(r.integers(2, 30))) * r.uniform(0.1, 3))) for _ in range(300)]
    res = node(js, [["entropy", [d]] for d in dists] + [["huffmanLength", [d]] for d in dists])
    Hp = np.array([-np.sum(np.array(d) * np.log2(np.array(d))) for d in dists])
    p.compare("Entropy of 300 random distributions: JavaScript vs Python (max difference)", 0.0, float(np.max(np.abs(np.array(res[:300]) - Hp))), "bit", kind="abs", tol=1e-10)
    Lh = np.array(res[300:])
    p.compare("Huffman average length within [H, H + 1) for all 300 (violations)", 0, int(np.sum((Lh < Hp - 1e-12) | (Lh >= Hp + 1))), "", kind="abs")
    text = alice_text().lower(); text = "".join(ch if ch.isalpha() or ch == " " else " " for ch in text); text = " ".join(text.split())
    rep = np.array(node(js, [["textReport", [text, 8]]])[0])
    py = []
    for k in range(1, 9):
        c = Counter(text[i:i + k] for i in range(len(text) - k + 1)); v = np.array(list(c.values()), float); v /= v.sum(); py.append(-np.sum(v * np.log2(v)))
    p.compare("Block entropies H₁…H₈ of the book: JavaScript vs Python (max difference)", 0.0, float(np.max(np.abs(rep[:, 1] - np.array(py)))), "bit", kind="abs", tol=1e-9)
    hk = rep[:, 2]
    p.metric("Letters+space alphabet / N", f"{int(rep[0, 3])} symbols / {len(text)} characters")
    p.compare("Order-0 entropy of English letters + space (literature ≈ 4.1 bits)", 4.1, hk[0], "bit", tol=3)
    p.metric("Conditional entropy h_k for k = 1…8", " / ".join(f"{v:.2f}" for v in hk), "bit/letter")
    sh = "".join(r.permutation(list(text)))
    rs = np.array(node(js, [["textReport", [sh, 8]]])[0]); hs = rs[:, 2]
    bias_pred = [(rs[k - 1, 3] - rs[k - 2, 3]) / (2 * len(text) * np.log(2)) if k > 1 else 0 for k in range(1, 9)]
    p.compare("Shuffled text (true h_k = h₁ for every k): apparent drop h₁ − h₂ from finite sample size vs Miller–Madow prediction", float(bias_pred[1]), float(hs[0] - hs[1]), "bit", tol=25)
    p.metric("… apparent drop h₁ − h₄: measured / Miller–Madow", f"{hs[0] - hs[3]:.3f} / {sum(bias_pred[1:4]):.3f} bit", "", "the first-order correction fails once the number of possible blocks (28⁴ ≈ 600 000) exceeds the sample size")
    p.metric("Shuffled text: apparent h₈", hs[7], "bit/letter", f"against the true {hs[0]:.2f} — a book is far too short for 8-letter statistics")
    p.compare("Real text keeps more structure than its shuffled version at order 3 (h₃ real < h₃ shuffled − 1 bit; 1 = yes)", 1, int(hk[2] < hs[2] - 1), "", kind="abs")
    fig, ax = p.fig(1, 1, w=7.5, h=4.2)
    ks = np.arange(1, 9); ax.plot(ks, hk, "o-", color=C_MEAS, label="Alice (real text)"); ax.plot(ks, hs, "s-", color=C_PRED, label="same letters, shuffled")
    ax.axhline(1.0, color="gray", ls=":", label="Shannon's ≈ 1 bit/letter")
    style_axes(ax, "context length k", "conditional entropy h_k (bits/letter)", "Structure vs small-sample artefact")
    p.save(fig, "entropy", "Conditional entropy of a book versus context length, compared with a shuffled control.")
    p.discuss(f"""The calculator's engine matches Python to round-off on random distributions and on the block entropies of a whole book, and its Huffman lengths
always land in [H, H + 1). The interesting part is what the numbers mean. Single letters of English carry {hk[0]:.2f} bits; with two and three letters of
context the conditional entropy drops to {hk[1]:.2f} and {hk[2]:.2f} — genuine structure, as the shuffled control (which stays near {hs[0]:.2f} at low orders) shows.
Further out the estimate keeps falling, reaching {hk[7]:.2f} bits at k = 8, but the shuffled text, which has *no* structure, also falls to {hs[7]:.2f}: with
144 000 characters most 8-letter strings are seen once, and the plug-in estimate mistakes rarity for predictability. The Miller–Madow correction explains the bias while the blocks are well sampled (order 2) but not beyond, where no
simple correction rescues the estimate. That is why the tool warns when a
text is too short for the order requested, and why Shannon's ≈ 1 bit/letter came from human prediction experiments rather than counting.""")
# tol-convention: relative tolerances are in percent
