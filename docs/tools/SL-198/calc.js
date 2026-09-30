// Op-amp configuration maths including finite open-loop gain A0 and gain-bandwidth product GBW.
// Every topology is reduced to (ideal signal gain G, feedback factor beta); then
//   actual DC gain = G / (1 + 1/(A0*beta)),   closed-loop -3 dB bandwidth ≈ GBW * beta  (single-pole op-amp).
const TOPO = {
  inverting:      { eq: "G = −Rf / Rin",           f: p => ({ G: -p.Rf / p.Rin, beta: p.Rin / (p.Rin + p.Rf), Zin: p.Rin }) },
  noninverting:   { eq: "G = 1 + Rf / Rg",          f: p => ({ G: 1 + p.Rf / p.Rg, beta: p.Rg / (p.Rg + p.Rf), Zin: Infinity }) },
  follower:       { eq: "G = 1",                   f: p => ({ G: 1, beta: 1, Zin: Infinity }) },
  difference:     { eq: "Vout = (Rf / Rin)(V2 − V1)", f: p => ({ G: p.Rf / p.Rin, beta: p.Rin / (p.Rin + p.Rf), Zin: 2 * p.Rin }) },
  summing2:       { eq: "Vout = −Rf (V1/R1 + V2/R2)", f: p => ({ G: -p.Rf / p.Rin, beta: 1 / (1 + p.Rf / p.Rin + p.Rf / p.Rin), Zin: p.Rin }) },
};

function analyse(topo, p, A0 = 1e5, GBW = 1e6) {
  const { G, beta, Zin } = TOPO[topo].f(p);
  const loop = A0 * beta;
  return { G, beta, noiseGain: 1 / beta, Gactual: G / (1 + 1 / loop), gainErrorPct: -100 / (1 + loop), bw: GBW * beta, Zin, eq: TOPO[topo].eq };
}

// frequency response of the closed loop with a single-pole op-amp A(s) = A0 / (1 + s A0/(2π GBW))
function response(topo, p, f, A0 = 1e5, GBW = 1e6) {
  const { G, beta } = TOPO[topo].f(p);
  return f.map(fr => {
    const wp = 2 * Math.PI * GBW / A0, w = 2 * Math.PI * fr;
    // A = A0 / (1 + j w/wp); T = A*beta; H = G * T/(1+T)
    const dr = 1, di = w / wp;                       // denominator of A
    const Tr = A0 * beta * dr / (dr * dr + di * di), Ti = -A0 * beta * di / (dr * dr + di * di);
    const nr = Tr, ni = Ti, er = 1 + Tr, ei = Ti;    // T/(1+T)
    const den = er * er + ei * ei;
    const hr = (nr * er + ni * ei) / den, hi = (ni * er - nr * ei) / den;
    return Math.abs(G) * Math.hypot(hr, hi);
  });
}

if (typeof module !== "undefined") module.exports = { analyse, response, TOPO };
