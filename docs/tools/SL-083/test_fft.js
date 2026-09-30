const { fft, spectrumDb, peak } = require("./fft.js");
const fs = 48000, n = 2048, out = { tones: [], random: [] };
for (const f of [440, 1000, 1234.5, 5000, 11025.7]) {
  const x = new Float64Array(n); for (let i = 0; i < n; i++) x[i] = Math.sin(2 * Math.PI * f * i / fs);
  out.tones.push({ f, ...peak(spectrumDb(x), fs, n) });
}
let seed = 1; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 - 0.5; };
const re = new Float64Array(n), im = new Float64Array(n), x = [];
for (let i = 0; i < n; i++) { re[i] = rnd(); im[i] = 0; x.push(re[i]); }
fft(re, im);
out.random = { x, re: Array.from(re), im: Array.from(im) };
console.log(JSON.stringify(out));
