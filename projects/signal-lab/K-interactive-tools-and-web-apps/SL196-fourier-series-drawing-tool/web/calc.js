// Complex Fourier series of a closed path (epicycles). Points are [x, y] = x + iy, sampled uniformly in time.
function dft(pts) {
  const N = pts.length, out = [];
  for (let k = 0; k < N; k++) {
    const f = k <= N / 2 ? k : k - N;        // signed frequency
    let re = 0, im = 0;
    for (let n = 0; n < N; n++) {
      const a = -2 * Math.PI * k * n / N, c = Math.cos(a), s = Math.sin(a);
      re += pts[n][0] * c - pts[n][1] * s; im += pts[n][0] * s + pts[n][1] * c;
    }
    out.push({ f, re: re / N, im: im / N, amp: Math.hypot(re, im) / N, phase: Math.atan2(im, re) });
  }
  return out.sort((a, b) => b.amp - a.amp);   // biggest circles first (nicest drawing)
}

// reconstruct the path at M time samples using the `terms` largest circles
function reconstruct(coeffs, terms, M) {
  const use = coeffs.slice(0, terms), out = [];
  for (let m = 0; m < M; m++) {
    const t = m / M; let x = 0, y = 0;
    for (const c of use) { const a = 2 * Math.PI * c.f * t; x += c.re * Math.cos(a) - c.im * Math.sin(a); y += c.re * Math.sin(a) + c.im * Math.cos(a); }
    out.push([x, y]);
  }
  return out;
}

// resample a hand-drawn polyline to N points equally spaced along its arc length (closing it)
function resample(poly, N) {
  const P = poly.concat([poly[0]]), seg = [];
  let L = 0;
  for (let i = 1; i < P.length; i++) { const d = Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]); seg.push(d); L += d; }
  const out = []; let i = 0, acc = 0;
  for (let n = 0; n < N; n++) {
    const s = n * L / N;
    while (acc + seg[i] < s && i < seg.length - 1) { acc += seg[i]; i++; }
    const u = seg[i] ? (s - acc) / seg[i] : 0;
    out.push([P[i][0] + u * (P[i + 1][0] - P[i][0]), P[i][1] + u * (P[i + 1][1] - P[i][1])]);
  }
  return out;
}

if (typeof module !== "undefined") module.exports = { dft, reconstruct, resample };
