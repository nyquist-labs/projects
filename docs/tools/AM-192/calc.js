// Vector-calculus engine for the visualiser: parse a field F(x, y) = (P, Q), sample it on a grid and compute the
// divergence and curl by central differences, plus line integrals used to demonstrate the theorems of Gauss and Stokes.
function compile(expr) {
  const allowed = /^[\sxy0-9+\-*/().,^a-z_]*$/i;
  if (!allowed.test(expr)) throw new Error("unsupported character");
  const body = expr.replace(/\^/g, "**").replace(/\b(sin|cos|tan|exp|log|sqrt|abs|atan2|sinh|cosh|tanh|pow|min|max|PI|E)\b/g, "Math.$1");
  return new Function("x", "y", `return (${body});`);
}
function field(pExpr, qExpr) { const P = compile(pExpr), Q = compile(qExpr); return (x, y) => [P(x, y), Q(x, y)]; }
function divergence(pExpr, qExpr, x, y, h) {
  const F = field(pExpr, qExpr); h = h || 1e-4;
  return (F(x + h, y)[0] - F(x - h, y)[0]) / (2 * h) + (F(x, y + h)[1] - F(x, y - h)[1]) / (2 * h);
}
function curl(pExpr, qExpr, x, y, h) {
  const F = field(pExpr, qExpr); h = h || 1e-4;
  return (F(x + h, y)[1] - F(x - h, y)[1]) / (2 * h) - (F(x, y + h)[0] - F(x, y - h)[0]) / (2 * h);
}
function gradient(fExpr, x, y, h) {
  const f = compile(fExpr); h = h || 1e-4;
  return [(f(x + h, y) - f(x - h, y)) / (2 * h), (f(x, y + h) - f(x, y - h)) / (2 * h)];
}
// Circle of radius r centred at (cx, cy), n points (midpoint rule): outward flux ∮F·n ds and circulation ∮F·t ds.
function circleIntegrals(pExpr, qExpr, cx, cy, r, n) {
  const F = field(pExpr, qExpr); n = n || 720; let flux = 0, circ = 0; const ds = 2 * Math.PI * r / n;
  for (let k = 0; k < n; k++) {
    const t = 2 * Math.PI * (k + 0.5) / n, c = Math.cos(t), s = Math.sin(t), v = F(cx + r * c, cy + r * s);
    flux += (v[0] * c + v[1] * s) * ds; circ += (-v[0] * s + v[1] * c) * ds;
  }
  return [flux, circ];
}
// Area integrals of div and curl over the same disc (polar midpoint rule).
function discIntegrals(pExpr, qExpr, cx, cy, r, nr, nt) {
  nr = nr || 120; nt = nt || 240; let d = 0, c = 0;
  for (let i = 0; i < nr; i++) {
    const rr = r * (i + 0.5) / nr;
    for (let j = 0; j < nt; j++) {
      const t = 2 * Math.PI * (j + 0.5) / nt, x = cx + rr * Math.cos(t), y = cy + rr * Math.sin(t), dA = rr * (r / nr) * (2 * Math.PI / nt);
      d += divergence(pExpr, qExpr, x, y) * dA; c += curl(pExpr, qExpr, x, y) * dA;
    }
  }
  return [d, c];
}
function grid(pExpr, qExpr, x0, x1, y0, y1, n) {
  const F = field(pExpr, qExpr), out = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const x = x0 + (x1 - x0) * i / (n - 1), y = y0 + (y1 - y0) * j / (n - 1), v = F(x, y);
    out.push([x, y, v[0], v[1], divergence(pExpr, qExpr, x, y), curl(pExpr, qExpr, x, y)]);
  }
  return out;
}
if (typeof module !== "undefined") module.exports = { divergence, curl, gradient, circleIntegrals, discIntegrals, grid };
