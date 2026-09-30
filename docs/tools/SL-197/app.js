// Drag-and-drop editor for the logic playground. Uses calc.js (evaluate, truthTable, toVerilog, PRESETS).
const svg = document.getElementById("board"), NS = "http://www.w3.org/2000/svg";
let S = { inputs: [], outputs: [], gates: [] }, pending = null, drag = null, uid = 1;
const ARITY = { NOT: 1, BUF: 1 };
const W = 64, H = 44;

function load(preset) {
  const p = PRESETS[preset]; uid = 1;
  S = { inputs: p.inputs.map((n, i) => ({ id: n, x: 40, y: 50 + i * 80, v: 0 })),
        gates: [], outputs: Object.keys(p.outputs).map((n, i) => ({ id: n, x: 720, y: 60 + i * 100, src: p.outputs[n] })) };
  const level = {};
  const lv = id => { const g = p.gates.find(q => q.id === id); if (!g) return 0; return level[id] ?? (level[id] = 1 + Math.max(...g.in.map(lv))); };
  const count = {};
  p.gates.forEach(g => { const L = lv(g.id); count[L] = (count[L] || 0) + 1; S.gates.push({ ...g, in: [...g.in], x: 60 + L * 140, y: 30 + (count[L] - 1) * 90 }); });
  render();
}

function add(type) { const id = type.toLowerCase() + uid++; S.gates.push({ id, type, in: Array(ARITY[type] || 2).fill(null), x: 300, y: 40 + (S.gates.length % 5) * 70 }); render(); }
function addInput() { const n = String.fromCharCode(97 + S.inputs.length); S.inputs.push({ id: n, x: 40, y: 50 + S.inputs.length * 80, v: 0 }); render(); }
function addOutput() { const n = "y" + S.outputs.length; S.outputs.push({ id: n, x: 720, y: 60 + S.outputs.length * 100, src: null }); render(); }

function net() {
  return { inputs: S.inputs.map(i => i.id), gates: S.gates.map(g => ({ id: g.id, type: g.type, in: g.in })),
           outputs: Object.fromEntries(S.outputs.map(o => [o.id, o.src])) };
}
function outPort(id) {
  const i = S.inputs.find(q => q.id === id); if (i) return [i.x + 30, i.y + 15];
  const g = S.gates.find(q => q.id === id); return [g.x + W + 10, g.y + H / 2];
}
function inPort(g, k) { const n = g.in.length; return [g.x - 10, g.y + H * (k + 1) / (n + 1)]; }

function values() {
  const val = Object.fromEntries(S.inputs.map(i => [i.id, i.v]));
  try { for (const g of order(net())) val[g.id] = OPS[g.type](g.in.map(s => val[s])) ? 1 : 0; return { val, err: null }; }
  catch (e) {
    // partial evaluation for display
    let changed = true;
    while (changed) { changed = false; for (const g of S.gates) if (!(g.id in val) && g.in.every(s => s in val)) { val[g.id] = OPS[g.type](g.in.map(s => val[s])) ? 1 : 0; changed = true; } }
    return { val, err: e.message };
  }
}

function el(tag, attrs, parent = svg) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; }

function render() {
  svg.innerHTML = "";
  const { val, err } = values();
  const wire = (a, b, on) => el("path", { d: `M${a[0]} ${a[1]} C${a[0] + 50} ${a[1]} ${b[0] - 50} ${b[1]} ${b[0]} ${b[1]}`, fill: "none",
    stroke: on ? "var(--acc)" : "var(--muted)", "stroke-width": on ? 3 : 2 });
  S.gates.forEach(g => g.in.forEach((s, k) => s && wire(outPort(s), inPort(g, k), val[s])));
  S.outputs.forEach(o => o.src && wire(outPort(o.src), [o.x, o.y + 15], val[o.src]));
  S.inputs.forEach(i => {
    const G = el("g", { transform: `translate(${i.x},${i.y})`, style: "cursor:pointer" });
    el("rect", { width: 30, height: 30, rx: 6, fill: i.v ? "var(--acc)" : "var(--panel)", stroke: "var(--ink2)" }, G);
    el("text", { x: 9, y: 20, fill: i.v ? "#fff" : "var(--ink)", "font-size": 14 }, G).textContent = i.v;
    el("text", { x: -4, y: -6, fill: "var(--ink2)", "font-size": 12 }, G).textContent = i.id;
    G.onclick = () => { if (pending == null) { i.v ^= 1; render(); } };
    port(outPort(i.id), () => { pending = i.id; render(); }, pending === i.id);
  });
  S.gates.forEach(g => {
    const G = el("g", { transform: `translate(${g.x},${g.y})`, style: "cursor:move" });
    el("rect", { width: W, height: H, rx: 10, fill: "var(--panel)", stroke: val[g.id] ? "var(--acc)" : "var(--ink2)", "stroke-width": 2 }, G);
    el("text", { x: W / 2, y: H / 2 + 5, "text-anchor": "middle", fill: "var(--ink)", "font-size": 13, "font-weight": 600 }, G).textContent = g.type;
    G.onpointerdown = e => { drag = { g, dx: e.offsetX - g.x, dy: e.offsetY - g.y }; };
    G.ondblclick = () => { S.gates = S.gates.filter(q => q !== g); S.gates.forEach(q => q.in = q.in.map(s => s === g.id ? null : s)); S.outputs.forEach(o => { if (o.src === g.id) o.src = null; }); render(); };
    g.in.forEach((s, k) => port(inPort(g, k), () => { if (pending) { g.in[k] = pending; pending = null; render(); } }, false, s == null));
    port(outPort(g.id), () => { pending = g.id; render(); }, pending === g.id);
  });
  S.outputs.forEach(o => {
    const G = el("g", { transform: `translate(${o.x},${o.y})` });
    el("circle", { cx: 15, cy: 15, r: 15, fill: val[o.src] ? "var(--acc2)" : "var(--panel)", stroke: "var(--ink2)" }, G);
    el("text", { x: 34, y: 20, fill: "var(--ink)", "font-size": 13 }, G).textContent = o.id;
    port([o.x, o.y + 15], () => { if (pending) { o.src = pending; pending = null; render(); } }, false, o.src == null);
  });
  document.getElementById("msg").textContent = err ? "⚠ " + err : pending ? `wiring from ${pending}: click an input port` : "";
  table(err);
}
function port([x, y], fn, active, open) {
  const c = el("circle", { cx: x, cy: y, r: 7, fill: active ? "var(--acc2)" : open ? "var(--bg)" : "var(--ink2)", stroke: "var(--ink2)", style: "cursor:crosshair" });
  c.onclick = e => { e.stopPropagation(); fn(); };
}
function table(err) {
  const t = document.getElementById("tt"), v = document.getElementById("vl");
  if (err || !S.outputs.length || S.inputs.length > 6) { t.innerHTML = ""; v.textContent = ""; return; }
  const rows = truthTable(net()), outs = S.outputs.map(o => o.id);
  t.innerHTML = `<tr>${S.inputs.map(i => `<th>${i.id}</th>`).join("")}${outs.map(o => `<th style="color:var(--acc)">${o}</th>`).join("")}</tr>` +
    rows.map(r => `<tr>${S.inputs.map(i => `<td>${r.in[i.id]}</td>`).join("")}${outs.map(o => `<td><b>${r.out[o]}</b></td>`).join("")}</tr>`).join("");
  v.textContent = toVerilog(net(), "playground");
}
svg.onpointermove = e => { if (drag) { drag.g.x = e.offsetX - drag.dx; drag.g.y = e.offsetY - drag.dy; render(); } };
svg.onpointerup = () => { drag = null; };
svg.onclick = () => { if (pending) { pending = null; render(); } };
const pal = document.getElementById("pal");
["AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR"].forEach(t => { const b = document.createElement("button"); b.textContent = "+ " + t; b.onclick = () => add(t); pal.appendChild(b); });
document.getElementById("addin").onclick = addInput; document.getElementById("addout").onclick = addOutput;
const ps = document.getElementById("preset"); Object.keys(PRESETS).forEach(k => ps.insertAdjacentHTML("beforeend", `<option>${k}</option>`));
ps.onchange = () => load(ps.value); document.getElementById("clear").onclick = () => { S = { inputs: [], outputs: [], gates: [] }; render(); };
ps.value = "full adder"; load("full adder");
