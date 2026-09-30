function gamma(zr, zi, z0) { const nr = zr - z0, ni = zi, dr = zr + z0, di = zi, d = dr * dr + di * di; return [(nr * dr + ni * di) / d, (ni * dr - nr * di) / d]; }
function vswr(g) { const m = Math.hypot(g[0], g[1]); return (1 + m) / (1 - m); }
function rl(g) { return -20 * Math.log10(Math.hypot(g[0], g[1])); }
function seriesX(zr, zi, x) { return [zr, zi + x]; }
function shuntB(zr, zi, b) { const d = zr * zr + zi * zi, yr = zr / d, yi = -zi / d + b, e = yr * yr + yi * yi; return [yr / e, -yi / e]; }
function reactance(kind, val, f) { const w = 2 * Math.PI * f; return kind === "L" ? w * val : -1 / (w * val); }
function susceptance(kind, val, f) { const w = 2 * Math.PI * f; return kind === "C" ? w * val : -1 / (w * val); }
if (typeof module !== "undefined") module.exports = { gamma, vswr, rl, seriesX, shuntB, reactance, susceptance };
