// Voltage divider maths: loaded Vout, Thevenin resistance, and best standard-value pair for a ratio.
const E = {
  12: [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
  24: [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1],
};
E[96] = Array.from({ length: 96 }, (_, i) => Math.round(Math.pow(10, i / 96) * 100) / 100);
// the published E96 table differs from the rounded formula at one value
E[96] = E[96].map(v => (v === 9.19 ? 9.2 : v));

function par(a, b) { return a === Infinity ? b : b === Infinity ? a : (a * b) / (a + b); }

function vout(vin, r1, r2, rload) {           // rload = Infinity for no load
  const r2e = par(r2, rload);
  return vin * r2e / (r1 + r2e);
}

function rth(r1, r2) { return par(r1, r2); }

function decadeValues(series, lo = 10, hi = 1e6) {
  const out = [];
  for (let d = Math.floor(Math.log10(lo)); d <= Math.log10(hi); d++) for (const m of E[series]) {
    const v = +(m * Math.pow(10, d)).toPrecision(3);
    if (v >= lo && v <= hi) out.push(v);
  }
  return out;
}

// best R1,R2 from a series for ratio = Vout/Vin, with R1+R2 in [rmin, rmax]
function bestPair(ratio, series = 24, rmin = 1e3, rmax = 1e6) {
  const vals = decadeValues(series, 10, 1e7);
  let best = null;
  for (const r2 of vals) {
    const r1Ideal = r2 * (1 - ratio) / ratio;
    // two nearest candidates for R1
    let i = vals.findIndex(v => v >= r1Ideal);
    for (const j of [i - 1, i]) {
      if (j < 0 || j >= vals.length) continue;
      const r1 = vals[j], tot = r1 + r2;
      if (tot < rmin || tot > rmax) continue;
      const err = r2 / (r1 + r2) / ratio - 1;
      if (!best || Math.abs(err) < Math.abs(best.err)) best = { r1, r2, err };
    }
  }
  return best;
}

// worst-case output with resistor tolerance tol (fraction)
function worstCase(vin, r1, r2, tol) {
  const hi = vout(vin, r1 * (1 - tol), r2 * (1 + tol), Infinity), lo = vout(vin, r1 * (1 + tol), r2 * (1 - tol), Infinity);
  return [lo, hi];
}

if (typeof module !== "undefined") module.exports = { vout, rth, bestPair, worstCase, decadeValues, E };
