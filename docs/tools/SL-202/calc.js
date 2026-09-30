// IPC-2221 trace current capacity:  I = k · ΔT^0.44 · A^0.725   (I in A, ΔT in °C, A = cross-section in mil²)
// k = 0.048 external layers, 0.024 internal layers. 1 oz/ft² copper = 1.378 mil = 35 µm.
const MIL = 25.4e-6, OZ_MIL = 1.378;
function area(I, dT, external = true) { const k = external ? 0.048 : 0.024; return Math.pow(I / (k * Math.pow(dT, 0.44)), 1 / 0.725); }
function width(I, dT, oz = 1, external = true) {               // returns { mil, mm }
  const w = area(I, dT, external) / (oz * OZ_MIL);
  return { mil: w, mm: w * 0.0254 };
}
function current(width_mil, dT, oz = 1, external = true) { const k = external ? 0.048 : 0.024; return k * Math.pow(dT, 0.44) * Math.pow(width_mil * oz * OZ_MIL, 0.725); }
// resistance, voltage drop and loss of a trace (copper ρ20 = 1.72e-8 Ω·m, α = 0.00393 /°C)
function resistance(width_mm, length_mm, oz = 1, T = 20) {
  const t = oz * OZ_MIL * MIL, rho = 1.72e-8 * (1 + 0.00393 * (T - 20));
  return rho * (length_mm / 1000) / (width_mm / 1000 * t);
}
if (typeof module !== "undefined") module.exports = { area, width, current, resistance };
