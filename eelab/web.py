"""Helpers for browser tools: run a tool's JavaScript logic under Node so it can be
verified numerically against independent Python references, and a shared page shell."""
import json
import shutil
import subprocess

NODE = shutil.which("node")

STYLE = """:root{--bg:#fcfcfb;--panel:#fff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e4e3df;--acc:#2a78d6;--acc2:#eb6834}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--panel:#232322;--ink:#fff;--ink2:#c3c2b7;--muted:#8f8e86;--line:#383835;--acc:#3987e5;--acc2:#f07a4a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,sans-serif}
main{max-width:860px;margin:auto;padding:16px}h1{font-size:1.5em;margin:.4em 0}p.lead{color:var(--ink2);margin-top:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}
label{display:grid;grid-template-columns:1fr minmax(90px,150px);gap:8px;align-items:center;padding:5px 0;border-bottom:1px solid var(--line)}
input,select,button{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:6px 8px;width:100%}
button{width:auto;cursor:pointer}button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
table{width:100%;border-collapse:collapse}td,th{padding:6px;border-bottom:1px solid var(--line);text-align:left}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}.big{font-size:1.6em;font-weight:650;color:var(--acc);font-variant-numeric:tabular-nums}
.muted{color:var(--muted);font-size:.9em}svg,canvas{max-width:100%;height:auto;display:block}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}footer{color:var(--muted);font-size:.85em;margin:24px 0}"""


def page(title, lead, body, scripts=("calc.js",), inline=""):
    tags = "".join(f'<script src="{s}"></script>' for s in scripts)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{STYLE}</style></head><body><main>
<h1>{title}</h1><p class="lead">{lead}</p>
{body}
<footer>Part of Nyquist Labs by Anna Lin — the calculation code (<code>calc.js</code>) is unit-tested against independent Python references; see this project's README.</footer>
</main>{tags}<script>{inline}</script></body></html>"""


def node(js_path, calls):
    """calls: list of (function_name, [args]). Returns list of results (JSON round-trip)."""
    if NODE is None:
        raise RuntimeError("node not found: install Node.js to verify the web tools")
    script = f"""const m=require({json.dumps(str(js_path))});const calls=JSON.parse(require('fs').readFileSync(0,'utf8'));
const out=calls.map(([f,a])=>{{try{{return m[f](...a)}}catch(e){{return {{error:String(e)}}}}}});
process.stdout.write(JSON.stringify(out));"""
    r = subprocess.run([NODE, "-e", script], input=json.dumps(calls), capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)


def attach(p, relpath, describe):
    """Register a hand-written file already in the project folder."""
    assert (p.dir / relpath).exists(), relpath
    p.files.append((relpath, describe))
