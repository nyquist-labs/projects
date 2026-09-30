// Entropy calculator engine: probabilities → entropy, text → empirical block/conditional entropies and Huffman code length.
function entropy(p) { const s = p.reduce((a, b) => a + b, 0); let h = 0; for (const x of p) if (x > 0) h -= (x / s) * Math.log2(x / s); return h; }
function counts(text, k) { const m = new Map(); for (let i = 0; i + k <= text.length; i++) { const w = text.slice(i, i + k); m.set(w, (m.get(w) || 0) + 1); } return m; }
function blockEntropy(text, k) { return entropy([...counts(text, k).values()]); }
// H(X_n | previous k−1 symbols) = H_k − H_{k−1}
function conditionalEntropy(text, k) { return k <= 1 ? blockEntropy(text, 1) : blockEntropy(text, k) - blockEntropy(text, k - 1); }
function millerMadow(text, k) { const c = counts(text, k); const n = text.length - k + 1; return entropy([...c.values()]) + (c.size - 1) / (2 * n * Math.LN2); }
function huffmanLength(p) {
  const s = p.reduce((a, b) => a + b, 0); let heap = p.filter(x => x > 0).map(x => x / s); if (heap.length === 1) return 1; let total = 0;
  while (heap.length > 1) { heap.sort((a, b) => a - b); const a = heap.shift(), b = heap.shift(); total += a + b; heap.push(a + b); }
  return total;                 // expected code length = sum of the merged probabilities
}
function textReport(text, kmax) {
  const out = []; for (let k = 1; k <= kmax; k++) out.push([k, blockEntropy(text, k), conditionalEntropy(text, k), counts(text, k).size]); return out;
}
if (typeof module !== "undefined") module.exports = { entropy, blockEntropy, conditionalEntropy, millerMadow, huffmanLength, textReport };
