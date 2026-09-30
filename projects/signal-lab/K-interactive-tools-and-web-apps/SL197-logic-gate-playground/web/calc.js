// Logic-circuit engine for the playground: evaluate a gate netlist, build truth tables, detect loops, export Verilog.
// net = { inputs: ["a","b"], gates: [{id:"g1", type:"AND", in:["a","b"]}], outputs: {y:"g1"} }
const OPS = {
  AND: v => v.every(Boolean), OR: v => v.some(Boolean), NOT: v => !v[0], BUF: v => !!v[0],
  NAND: v => !v.every(Boolean), NOR: v => !v.some(Boolean), XOR: v => v.filter(Boolean).length % 2 === 1,
  XNOR: v => v.filter(Boolean).length % 2 === 0,
};

function order(net) {                       // topological order; throws on combinational loops
  const byId = Object.fromEntries(net.gates.map(g => [g.id, g]));
  const state = {}, out = [];
  const visit = id => {
    if (!(id in byId)) { if (!net.inputs.includes(id)) throw new Error(`unconnected signal ${id}`); return; }
    if (state[id] === 1) throw new Error(`combinational loop through ${id}`);
    if (state[id] === 2) return;
    state[id] = 1; byId[id].in.forEach(visit); state[id] = 2; out.push(byId[id]);
  };
  net.gates.forEach(g => visit(g.id));
  return out;
}

function evaluate(net, assign) {
  const val = { ...assign };
  for (const g of order(net)) val[g.id] = OPS[g.type](g.in.map(s => val[s])) ? 1 : 0;
  return Object.fromEntries(Object.entries(net.outputs).map(([k, s]) => [k, val[s] ? 1 : 0]));
}

function truthTable(net) {
  const n = net.inputs.length, rows = [];
  for (let m = 0; m < (1 << n); m++) {
    const a = Object.fromEntries(net.inputs.map((s, i) => [s, (m >> (n - 1 - i)) & 1]));
    rows.push({ in: a, out: evaluate(net, a) });
  }
  return rows;
}

function toVerilog(net, name = "circuit") {
  const V = { AND: "&", OR: "|", XOR: "^" };
  const expr = g => {
    const a = g.in;
    switch (g.type) {
      case "NOT": return `~${a[0]}`;
      case "BUF": return a[0];
      case "NAND": return `~(${a.join(" & ")})`;
      case "NOR": return `~(${a.join(" | ")})`;
      case "XNOR": return `~(${a.join(" ^ ")})`;
      default: return a.join(` ${V[g.type]} `);
    }
  };
  const outs = Object.keys(net.outputs);
  let s = `module ${name}(input wire ${net.inputs.join(", ")}, output wire ${outs.join(", ")});\n`;
  net.gates.forEach(g => { s += `  wire ${g.id} = ${expr(g)};\n`; });
  outs.forEach(o => { s += `  assign ${o} = ${net.outputs[o]};\n`; });
  return s + "endmodule\n";
}

function depth(net) {                        // longest input-to-output path in gates
  const d = {};
  for (const g of order(net)) d[g.id] = 1 + Math.max(0, ...g.in.map(s => d[s] || 0));
  return Math.max(...Object.values(net.outputs).map(s => d[s] || 0));
}

const PRESETS = {
  "half adder": { inputs: ["a", "b"], gates: [{ id: "x1", type: "XOR", in: ["a", "b"] }, { id: "a1", type: "AND", in: ["a", "b"] }], outputs: { s: "x1", c: "a1" } },
  "full adder": { inputs: ["a", "b", "cin"], gates: [{ id: "x1", type: "XOR", in: ["a", "b"] }, { id: "x2", type: "XOR", in: ["x1", "cin"] },
    { id: "a1", type: "AND", in: ["a", "b"] }, { id: "a2", type: "AND", in: ["x1", "cin"] }, { id: "o1", type: "OR", in: ["a1", "a2"] }], outputs: { s: "x2", cout: "o1" } },
  "2:1 mux": { inputs: ["s", "d0", "d1"], gates: [{ id: "n1", type: "NOT", in: ["s"] }, { id: "a0", type: "AND", in: ["n1", "d0"] },
    { id: "a1", type: "AND", in: ["s", "d1"] }, { id: "o1", type: "OR", in: ["a0", "a1"] }], outputs: { y: "o1" } },
  "XOR from NANDs": { inputs: ["a", "b"], gates: [{ id: "n1", type: "NAND", in: ["a", "b"] }, { id: "n2", type: "NAND", in: ["a", "n1"] },
    { id: "n3", type: "NAND", in: ["b", "n1"] }, { id: "n4", type: "NAND", in: ["n2", "n3"] }], outputs: { y: "n4" } },
};

if (typeof module !== "undefined") module.exports = { evaluate, truthTable, toVerilog, depth, order, PRESETS, OPS };
