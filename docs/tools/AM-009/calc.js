// Step response of a unity-DC-gain system with two poles: a complex pair -s ± j w (w > 0) or two real poles (w = 0 → p1, p2 given).
function stepPair(sigma, wd, t) {            // poles -sigma ± j wd, H(s) = (sigma²+wd²)/((s+sigma)²+wd²)
  return t.map(tt => 1 - Math.exp(-sigma * tt) * (Math.cos(wd * tt) + (sigma / wd) * Math.sin(wd * tt)));
}
function stepReal(a, b, t) {                  // poles -a, -b (a ≠ b), H(s) = ab/((s+a)(s+b))
  return t.map(tt => 1 - (b * Math.exp(-a * tt) - a * Math.exp(-b * tt)) / (b - a));
}
function metrics(y, t) {
  const yf = 1, peak = Math.max(...y), os = Math.max(0, (peak - yf) * 100);
  let ts = 0; for (let k = y.length - 1; k >= 0; k--) if (Math.abs(y[k] - yf) > 0.02) { ts = t[Math.min(k + 1, t.length - 1)]; break; }
  let tr0 = t.find((_, k) => y[k] >= 0.1), tr1 = t.find((_, k) => y[k] >= 0.9);
  return { overshoot: os, settling: ts, rise: (tr1 ?? NaN) - (tr0 ?? NaN) };
}
if (typeof module !== "undefined") module.exports = { stepPair, stepReal, metrics };
