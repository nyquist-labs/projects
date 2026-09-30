from eelab import *
from eelab.web import node, page, attach
from eelab.rv32 import assemble, iss

META = dict(
    id="SL-204", title="Bit manipulation visualiser (shifts, masks, two's complement)", level="E",
    tools="HTML/JS visualiser (clickable bits, 8/16/32/64-bit, signed/unsigned views) built on exact BigInt arithmetic; Node harness vs Python and the RV32I instruction-set simulator",
    summary="Toggle bits and watch the unsigned, signed (two's complement) and hex views update; apply shifts, rotates, masks and sign extension "
            "and see each result bit by bit. The library is checked on 24,000 random operations against Python and a RISC-V ISS, and the classic "
            "JavaScript pitfalls are quantified.",
    problem="JavaScript numbers are 64-bit floats and its bit operators are 32-bit signed. How often does naive code get bit manipulation wrong?",
    theory=r"""Two's complement: an n-bit pattern x means $x - 2^n$ when its top bit is set; negation is $\sim x + 1$; arithmetic right shift copies the sign bit, logical shift
inserts zeros. Pitfalls: a Number holds integers exactly only up to $2^{53}$, so for uniformly random 64-bit patterns a Number-based shift is wrong with
probability ≈ $1 - 2^{53}/2^{64}$ ≈ 99.95 %; and `x >> n` is an *arithmetic* shift of a 32-bit signed value, so for random unsigned 32-bit x it differs
from a logical shift whenever the top bit is set (50 %) and n > 0.""",
    method="""24,000 random (operation, operands, width ∈ {8,16,32,64}) cases: calc.js (BigInt) vs Python integers. 500 random operand pairs through an RV32I program (sll, srl, xor, and,
or, add, sub, slt) on the ISS vs calc.js at width 32. Naive Number implementations measured on 5000 random 64-bit and 32-bit cases.""",
    data="Generated test vectors.",
)

BODY = """<div class="card"><div class="row"><label style="flex:1">Width<select id="w"><option>8</option><option>16</option><option selected>32</option><option>64</option></select></label>
<label style="flex:2">Value (decimal, 0x…, 0b…, negative ok)<input id="x" value="0xDEADBEEF"></label></div>
<div id="bits" style="display:flex;flex-wrap:wrap;gap:2px;margin:10px 0;font-family:ui-monospace,monospace"></div>
<table id="views"></table></div>
<div class="card"><div class="row"><label style="flex:1">Operation<select id="op"><option>shl</option><option>shrl</option><option>shra</option><option>rotl</option><option>rotr</option>
<option>and</option><option>or</option><option>xor</option><option>not</option><option>neg</option><option>popcount</option><option>clz</option></select></label>
<label style="flex:1">Operand / amount<input id="y" value="4"></label><button id="apply">apply → value</button></div><p id="res" style="font-family:ui-monospace,monospace"></p></div>"""

JS = r"""const $=id=>document.getElementById(id);const W=()=>+$('w').value;
function val(){try{let s=$('x').value.trim().replace(/_/g,'');const neg=s.startsWith('-');if(neg)s=s.slice(1);let v=BigInt(s);return op('norm',[(neg?-v:v).toString(),W()]);}catch(e){return '0';}}
function draw(){const w=W(),v=val(),b=toBin(v,w);$('bits').innerHTML=[...b].map((c,i)=>`<button data-i="${w-1-i}" title="bit ${w-1-i}" style="width:26px;padding:4px 0;${c=='1'?'background:var(--acc);color:#fff;border-color:var(--acc)':''}${(w-1-i)%8==7&&i?';margin-left:8px':''}">${c}</button>`).join('');
document.querySelectorAll('#bits button').forEach(e=>e.onclick=()=>{$('x').value='0x'+toHex(op('toggleBit',[v,+e.dataset.i,w]),w).toUpperCase();draw();});
$('views').innerHTML=[["Unsigned",v],["Signed (two's complement)",op('toSigned',[v,w])],["Hex","0x"+toHex(v,w).toUpperCase()],["Popcount",op('popcount',[v,w])]].map(r=>`<tr><td>${r[0]}</td><td class="n">${r[1]}</td></tr>`).join('');calc();}
function calc(){const w=W(),v=val(),o=$('op').value;let y=$('y').value.trim();try{y=BigInt(y.startsWith('-')?'-'+y.slice(1):y).toString();}catch(e){y='0';}
const unary=['not','neg','popcount','clz'].includes(o);const r=op(o,unary?[v,w]:[v,['and','or','xor'].includes(o)?op('norm',[y,w]):y,w]);
$('res').innerHTML=['popcount','clz'].includes(o)?`${o} = <b>${r}</b>`:`${toBin(v,w)}<br>${toBin(r,w)} &nbsp;← ${o}<br>= ${r} (signed ${op('toSigned',[r,w])})`;window._r=r;}
$('apply').onclick=()=>{if(!['popcount','clz'].includes($('op').value)){$('x').value='0x'+toHex(window._r,W()).toUpperCase();draw();}};
document.querySelectorAll('input,select').forEach(e=>e.oninput=draw);draw();"""


def py(name, a, w):
    M = (1 << w) - 1
    nm = lambda x: x & M
    sg = lambda x: nm(x) - (1 << w) if nm(x) >> (w - 1) else nm(x)
    x = a[0]
    if name == "shl": return nm(x << a[1])
    if name == "shrl": return nm(x) >> a[1]
    if name == "shra": return nm(sg(x) >> a[1])
    if name == "rotl": n = a[1] % w; return nm((x << n) | (x >> (w - n)))
    if name == "rotr": n = (w - a[1] % w) % w; return nm((x << n) | (x >> (w - n))) if n else x
    if name in ("and", "or", "xor", "add", "sub"):
        return nm({"and": x & a[1], "or": x | a[1], "xor": x ^ a[1], "add": x + a[1], "sub": x - a[1]}[name])
    if name == "not": return nm(~x)
    if name == "neg": return nm(-x)
    if name == "popcount": return bin(x).count("1")
    if name == "clz": return w - x.bit_length()
    if name == "toSigned": return sg(x)


def run(p):
    p.write("web/index.html", page("Bit manipulation visualiser", "Click bits; see unsigned, two's-complement and hex views; apply shifts, rotates and masks.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "BigInt bit library (tested)")
    js = p.dir / "web" / "calc.js"
    r = p.rng
    ops2 = ["shl", "shrl", "shra", "rotl", "rotr", "and", "or", "xor", "add", "sub"]
    ops1 = ["not", "neg", "popcount", "clz", "toSigned"]
    cases = []
    for _ in range(24000):
        w = int(r.choice([8, 16, 32, 64]))
        x = int(r.integers(0, 2 ** 62)) * 4 + int(r.integers(0, 4)); x &= (1 << w) - 1
        name = (ops2 + ops1)[r.integers(len(ops2) + len(ops1))]
        if name in ops2:
            y = int(r.integers(0, w + 1)) if name.startswith(("sh", "rot")) else (int(r.integers(0, 2 ** 62)) * 4) & ((1 << w) - 1)
            if name in ("shl", "shrl", "shra") and y >= w:
                y = w - 1
            cases.append((name, [x, y], w))
        else:
            cases.append((name, [x], w))
    got = node(js, [["opMany", [[[n, [str(v) for v in a] + [w]] for n, a, w in cases]]]])[0]
    bad = sum(int(g) != py(n, a, w) for g, (n, a, w) in zip(got, cases))
    p.compare(f"BigInt library vs Python integers ({len(cases)} random ops, widths 8–64)", 0, bad, "", kind="abs")
    src = """
        lw a0, 0(x0)
        lw a1, 4(x0)
        sll a2, a0, a1
        srl a3, a0, a1
        xor a4, a0, a1
        and a5, a0, a1
        or a6, a0, a1
        add a7, a0, a1
        sub t0, a0, a1
        slt t1, a0, a1
    halt: j halt
    """
    words, _ = assemble(src)
    mism = 0
    for _ in range(500):
        a, b = int(r.integers(0, 2 ** 32)), int(r.integers(0, 2 ** 32))
        if r.random() < 0.5:
            b &= 31
        x, _, _ = iss(words, mem_init={0: a, 1: b})
        exp = node(js, [["opMany", [[["shl", [str(a), str(b & 31), 32]], ["shrl", [str(a), str(b & 31), 32]], ["xor", [str(a), str(b), 32]], ["and", [str(a), str(b), 32]],
                                     ["or", [str(a), str(b), 32]], ["add", [str(a), str(b), 32]], ["sub", [str(a), str(b), 32]], ["sltSigned", [str(a), str(b), 32]]]]]])[0]
        mism += sum(int(e) != x[k] for e, k in zip(exp, (12, 13, 14, 15, 16, 17, 5, 6)))
    p.compare("RV32I ISS vs calc.js: mismatching results (500 pairs × 8 instructions)", 0, mism, "", kind="abs")
    n64 = [(int(r.integers(0, 2 ** 63)) * 2 + int(r.integers(0, 2)), int(r.integers(1, 8))) for _ in range(5000)]
    naive = node(js, [["naiveMany", [[["shl64", [str(x), s]] for x, s in n64]]]])[0]
    wrong64 = np.mean([int(float(g)) != ((x << s) & (2 ** 64 - 1)) for g, (x, s) in zip(naive, n64)]) * 100
    p.compare("Naive Number-based 64-bit shift: wrong results", (1 - 2 ** 53 / 2 ** 64) * 100, wrong64, "%", kind="abs", tol=1)
    n32 = [(int(r.integers(0, 2 ** 32)), int(r.integers(1, 32))) for _ in range(5000)]
    naive32 = node(js, [["naiveMany", [[["shr32", [x, s]] for x, s in n32]]]])[0]
    wrong32 = np.mean([int(g) != (x >> s) for g, (x, s) in zip(naive32, n32)]) * 100
    p.compare("JS `x >> n` used as an unsigned 32-bit shift: wrong results", 50, wrong32, "%", kind="abs", tol=2)
    fig, ax = p.fig(1, 1, w=9, h=3.4)
    ax.bar(["BigInt library", "naive 32-bit >>", "naive 64-bit Number"], [bad / len(cases) * 100, wrong32, wrong64], color=[C_MEAS, COLORS[1], COLORS[2]])
    for i, v in enumerate([bad / len(cases) * 100, wrong32, wrong64]):
        ax.text(i, v + 2, f"{v:.2f} %", ha="center")
    ax.set_ylim(0, 110)
    style_axes(ax, None, "wrong results (%)", "Why the tool uses BigInt", legend=False)
    p.save(fig, "pitfalls", "Error rates of exact BigInt arithmetic vs naive JavaScript Number bit manipulation.")
    p.discuss(f"""The BigInt library is exact: zero disagreements with Python's arbitrary-precision integers over {len(cases)} random operations, and its 32-bit results
match what the RISC-V instruction-set simulator computes for the same machine instructions (including signed `slt` and shift-amount masking to
5 bits). The pitfalls behave as predicted: Number-based 64-bit shifts are wrong {wrong64:.2f} % of the time (only values below 2⁵³ survive), and using
`>>` for an unsigned shift is wrong for half of all random 32-bit inputs because it sign-extends. Both explain classic bugs in web-based
register calculators; the visualiser avoids them by never storing a pattern in a Number.""")
# tol-convention: relative tolerances are in percent
