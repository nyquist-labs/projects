// Power / voltage level conversions. Everything goes through watts (power) or volts rms (voltage) with a reference impedance Z.
const kB = 1.380649e-23;
const UNITS = {
  W:     { toW: (x, Z) => x,                                  fromW: (w, Z) => w },
  mW:    { toW: (x, Z) => x / 1e3,                            fromW: (w, Z) => w * 1e3 },
  dBW:   { toW: (x, Z) => Math.pow(10, x / 10),               fromW: (w, Z) => 10 * Math.log10(w) },
  dBm:   { toW: (x, Z) => Math.pow(10, x / 10) / 1e3,         fromW: (w, Z) => 10 * Math.log10(w * 1e3) },
  Vrms:  { toW: (x, Z) => x * x / Z,                          fromW: (w, Z) => Math.sqrt(w * Z) },
  Vpk:   { toW: (x, Z) => (x / Math.SQRT2) ** 2 / Z,          fromW: (w, Z) => Math.sqrt(w * Z) * Math.SQRT2 },
  Vpp:   { toW: (x, Z) => (x / (2 * Math.SQRT2)) ** 2 / Z,    fromW: (w, Z) => Math.sqrt(w * Z) * 2 * Math.SQRT2 },
  dBV:   { toW: (x, Z) => Math.pow(10, x / 20) ** 2 / Z,      fromW: (w, Z) => 20 * Math.log10(Math.sqrt(w * Z)) },
  dBu:   { toW: (x, Z) => (0.7745967 * Math.pow(10, x / 20)) ** 2 / Z, fromW: (w, Z) => 20 * Math.log10(Math.sqrt(w * Z) / 0.7745967) },
  dBuV:  { toW: (x, Z) => (1e-6 * Math.pow(10, x / 20)) ** 2 / Z, fromW: (w, Z) => 20 * Math.log10(Math.sqrt(w * Z) / 1e-6) },
};
function convert(x, from, to, Z = 50) { return UNITS[to].fromW(UNITS[from].toW(x, Z), Z); }
function all(x, from, Z = 50) { const w = UNITS[from].toW(x, Z); return Object.fromEntries(Object.keys(UNITS).map(u => [u, UNITS[u].fromW(w, Z)])); }
function ratioDb(a, b, kind = "power") { return (kind === "power" ? 10 : 20) * Math.log10(a / b); }
function thermalNoiseDbm(bwHz, T = 290) { return 10 * Math.log10(kB * T * bwHz * 1e3); }
if (typeof module !== "undefined") module.exports = { convert, all, ratioDb, thermalNoiseDbm, UNITS };
