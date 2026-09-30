// Engineering unit helpers: SI prefixes, RKM/IEC 60062 value codes (4k7, 2u2), EIA capacitor codes (104), AWG, PCB units, temperature, RF.
const PREFIX = { y: -24, z: -21, a: -18, f: -15, p: -12, n: -9, u: -6, "µ": -6, m: -3, "": 0, k: 3, K: 3, M: 6, G: 9, T: 12, R: 0, r: 0 };

function parseEng(s) {                           // "4k7", "4.7k", "2u2", "100n", "0R1", "1.5M", "3.3e-6", "47µ"
  s = String(s).trim().replace(/\s*(Ω|[oO]hms?|F|H|V|A|Hz)$/, "");   // case-sensitive: "f" is femto, "F" is farad
  let m = s.match(/^([-+]?\d*)([yzafpnuµmRrkKMGT])(\d+)$/);           // RKM: letter is the decimal point
  if (m) return Number((m[1] || "0") + "." + m[3]) * Math.pow(10, PREFIX[m[2]]);
  m = s.match(/^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([yzafpnuµmkKMGT]?)$/);
  if (m && (m[2] === "" || m[2] in PREFIX)) return Number(m[1]) * Math.pow(10, PREFIX[m[2]]);
  throw new Error("cannot parse " + s);
}
function formatEng(v, unit = "", digits = 4) {
  if (v === 0) return "0 " + unit;
  const e = Math.max(-24, Math.min(12, 3 * Math.floor(Math.log10(Math.abs(v)) / 3)));
  const p = Object.keys(PREFIX).find(k => PREFIX[k] === e && !"uKRr".includes(k) && k !== "") ?? "";
  return +(v / Math.pow(10, e)).toPrecision(digits) + " " + (e === 0 ? "" : p) + unit;
}
function capCode(code) {                          // EIA 3-digit code in pF; third digit 8 → ×0.01, 9 → ×0.1
  const m = String(code).match(/^(\d)(\d)(\d)$/); if (!m) throw new Error("need 3 digits");
  const mult = m[3] === "9" ? 0.1 : m[3] === "8" ? 0.01 : Math.pow(10, +m[3]);
  return (10 * +m[1] + +m[2]) * mult * 1e-12;
}
function awgDiameterMm(n) { return 0.127 * Math.pow(92, (36 - n) / 39); }  // n: 0 = "1/0", -1 = "2/0", -3 = "4/0"
function awgAreaMm2(n) { const d = awgDiameterMm(n); return Math.PI * d * d / 4; }
function awgResistanceOhmPerKm(n, T = 20) { return 1.72e-8 * (1 + 0.00393 * (T - 20)) / (awgAreaMm2(n) * 1e-6) * 1000; }
const milToMm = x => x * 0.0254, mmToMil = x => x / 0.0254;
const ozToUm = oz => oz * 28.349523 / (8.96 * 929.0304) * 1e4;   // physical: 1 oz of copper (8.96 g/cm³) spread over 1 ft² = 34.1 µm
const ozToUmNominal = oz => oz * 35;               // industry convention (1.378 mil) used by IPC-2221 and fab houses
const cToF = c => c * 9 / 5 + 32, fToC = f => (f - 32) * 5 / 9, cToK = c => c + 273.15;
const hzToRad = f => 2 * Math.PI * f;
const wavelengthM = (f, vf = 1) => vf * 299792458 / f;
if (typeof module !== "undefined") module.exports = { parseEng, formatEng, capCode, awgDiameterMm, awgAreaMm2, awgResistanceOhmPerKm, milToMm, mmToMil, ozToUm, ozToUmNominal, cToF, fToC, cToK, hzToRad, wavelengthM };
