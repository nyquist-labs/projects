// Resistor colour code (IEC 60062): encode a value into 4/5-band colours and decode colours back.
const COLS = ["black", "brown", "red", "orange", "yellow", "green", "blue", "violet", "grey", "white"];
const MULT = { silver: -2, gold: -1, black: 0, brown: 1, red: 2, orange: 3, yellow: 4, green: 5, blue: 6, violet: 7, grey: 8, white: 9 };
const TOL = { brown: 1, red: 2, green: 0.5, blue: 0.25, violet: 0.1, grey: 0.05, gold: 5, silver: 10 };
const HEX = { black: "#1b1b1b", brown: "#7a4a1e", red: "#d62d20", orange: "#f28c1a", yellow: "#f5d400", green: "#2e9e44", blue: "#2a5bd7",
  violet: "#8a3ec9", grey: "#8d8d8d", white: "#f4f4f4", gold: "#c9a227", silver: "#b8b8b8" };

function encode(value, bands = 4, tol = 5) {
  const nd = bands === 4 ? 2 : 3;
  if (!(value > 0)) throw new Error("value must be positive");
  let exp = Math.floor(Math.log10(value)) - (nd - 1);
  let digits = Math.round(value / Math.pow(10, exp));
  if (digits >= Math.pow(10, nd)) { digits = Math.round(digits / 10); exp += 1; }
  if (exp < -2 || exp > 9) throw new Error("value out of colour-code range");
  const ds = String(digits).padStart(nd, "0").split("").map(Number);
  const mult = Object.keys(MULT).find(k => MULT[k] === exp);
  const tcol = Object.keys(TOL).find(k => TOL[k] === tol);
  if (!tcol) throw new Error("no colour for that tolerance");
  return ds.map(d => COLS[d]).concat([mult, tcol]);
}

function decode(colours) {
  const n = colours.length;
  if (n !== 4 && n !== 5) throw new Error("need 4 or 5 bands");
  const nd = n - 2;
  let digits = 0;
  for (let i = 0; i < nd; i++) {
    const d = COLS.indexOf(colours[i]);
    if (d < 0) throw new Error(`band ${i + 1}: ${colours[i]} is not a digit colour`);
    digits = digits * 10 + d;
  }
  if (!(colours[nd] in MULT)) throw new Error("bad multiplier colour");
  if (!(colours[nd + 1] in TOL)) throw new Error("bad tolerance colour");
  const value = +(digits * Math.pow(10, MULT[colours[nd]])).toPrecision(12);
  return { value, tol: TOL[colours[nd + 1]] };
}

// can the bands be read backwards as another valid code?
function reversible(colours) {
  try { decode(colours.slice().reverse()); return true; } catch (e) { return false; }
}

if (typeof module !== "undefined") module.exports = { encode, decode, reversible, COLS, MULT, TOL, HEX };
