// Fixed-width bit manipulation with BigInt (exact for any width up to 64 and beyond).
// All functions take and return unsigned patterns as decimal strings or BigInt-compatible values.
const B = x => BigInt(x);
const mask = w => (1n << B(w)) - 1n;
const norm = (x, w) => ((B(x) % (1n << B(w))) + (1n << B(w))) % (1n << B(w));      // wrap into [0, 2^w)
function toSigned(x, w) { x = norm(x, w); return x >> (B(w) - 1n) ? x - (1n << B(w)) : x; }
function toBin(x, w) { return norm(x, w).toString(2).padStart(w, "0"); }
function toHex(x, w) { return norm(x, w).toString(16).padStart(Math.ceil(w / 4), "0"); }
const shl = (x, n, w) => norm(B(x) << B(n), w);
const shrl = (x, n, w) => norm(x, w) >> B(n);
const shra = (x, n, w) => norm(toSigned(x, w) >> B(n), w);
const rotl = (x, n, w) => { n = B(n) % B(w); x = norm(x, w); return norm((x << n) | (x >> (B(w) - n)), w); };
const rotr = (x, n, w) => rotl(x, B(w) - (B(n) % B(w)), w);
const and = (a, b, w) => norm(B(a) & B(b), w), or = (a, b, w) => norm(B(a) | B(b), w), xor = (a, b, w) => norm(B(a) ^ B(b), w);
const not = (a, w) => norm(~B(a), w);
const add = (a, b, w) => norm(B(a) + B(b), w), sub = (a, b, w) => norm(B(a) - B(b), w);
const neg = (a, w) => norm(-B(a), w);
const setBit = (x, i, w) => norm(B(x) | (1n << B(i)), w), clearBit = (x, i, w) => norm(B(x) & ~(1n << B(i)), w), toggleBit = (x, i, w) => norm(B(x) ^ (1n << B(i)), w);
function popcount(x, w) { let c = 0n, v = norm(x, w); while (v) { c += v & 1n; v >>= 1n; } return c; }
function clz(x, w) { const v = norm(x, w); return v === 0n ? B(w) : B(w - v.toString(2).length); }
const signExtend = (x, from, to) => norm(toSigned(x, from), to);
const sltSigned = (a, b, w) => (toSigned(a, w) < toSigned(b, w) ? 1n : 0n);

// String-in/string-out wrapper so Node tests and the page can call any op with plain JSON
function op(name, args) {
  const f = { toSigned, shl, shrl, shra, rotl, rotr, and, or, xor, not, add, sub, neg, setBit, clearBit, toggleBit, popcount, clz, signExtend, sltSigned, norm }[name];
  return f(...args.map(a => (typeof a === "string" ? BigInt(a) : a))).toString();
}
function opMany(list) { return list.map(([n, a]) => op(n, a)); }

// Naive implementations using ordinary JS Numbers — what goes wrong without BigInt
function naiveShl64(x, n) { return String((Number(x) * Math.pow(2, n)) % Math.pow(2, 64)); }
function naiveShr32(x, n) { return String(Number(x) >> n); }          // arithmetic, 32-bit signed!
function naiveMany(list) { return list.map(([n, a]) => (n === "shl64" ? naiveShl64(...a) : naiveShr32(...a))); }

if (typeof module !== "undefined") module.exports = { op, opMany, naiveMany, toBin, toHex, toSigned };
