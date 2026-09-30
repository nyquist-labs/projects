const s = require("./smith.js"); let seed = 7; const r = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const out = [];
for (let i = 0; i < 200; i++) {
  const zr = 1 + 200 * r(), zi = -300 + 600 * r(), x = -100 + 200 * r(), b = -0.02 + 0.04 * r();
  const g = s.gamma(zr, zi, 50);
  out.push({ zr, zi, x, b, g, vswr: s.vswr(g), rl: s.rl(g), ser: s.seriesX(zr, zi, x), sh: s.shuntB(zr, zi, b) });
}
console.log(JSON.stringify(out));
