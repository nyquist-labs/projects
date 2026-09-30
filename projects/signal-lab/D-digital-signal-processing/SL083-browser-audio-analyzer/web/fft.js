// Radix-2 iterative FFT + analyser helpers (shared by the web page and the Node test)
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ar = re[i + k], ai = im[i + k];
        const br = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const bi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k] = ar + br; im[i + k] = ai + bi;
        re[i + k + len / 2] = ar - br; im[i + k + len / 2] = ai - bi;
        const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
      }
    }
  }
}
function spectrumDb(x) {
  const n = x.length, re = new Float64Array(n), im = new Float64Array(n);
  let wsum = 0;
  for (let i = 0; i < n; i++) { const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / n); re[i] = x[i] * w; wsum += w; }
  fft(re, im);
  const out = new Float64Array(n / 2 + 1);
  for (let k = 0; k <= n / 2; k++) out[k] = 20 * Math.log10(2 * Math.hypot(re[k], im[k]) / wsum + 1e-12);
  return out;
}
function peak(db, fs, n) {
  let k = 1;
  for (let i = 1; i < db.length - 1; i++) if (db[i] > db[k]) k = i;
  const a = db[k - 1], b = db[k], c = db[k + 1];
  const d = 0.5 * (a - c) / (a - 2 * b + c);
  return { freq: (k + d) * fs / n, level: b - 0.25 * (a - c) * d };
}
if (typeof module !== "undefined") module.exports = { fft, spectrumDb, peak };
