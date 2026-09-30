// Antenna dimension rules of thumb. c = 299 792 458 m/s. k = end-effect (shortening) factor, default 0.95 for wire antennas.
const C = 299792458;
function wavelength(fHz, vf = 1) { return vf * C / fHz; }
function dipole(fHz, k = 0.95) { const L = k * wavelength(fHz) / 2; return { total: L, leg: L / 2 }; }
function monopole(fHz, k = 0.95) { return { height: k * wavelength(fHz) / 4 }; }
function fiveEighths(fHz, k = 0.95) { return { height: k * 0.625 * wavelength(fHz) }; }
function loop(fHz) { return { circumference: 1.02 * wavelength(fHz) }; }   // full-wave loop resonates slightly above 1 λ
// 3-element Yagi rule of thumb: reflector 0.5 λ, driven 0.47 λ, director 0.44 λ, spacing 0.2 λ
function yagi3(fHz) { const l = wavelength(fHz); return { reflector: 0.5 * l, driven: 0.47 * l, director: 0.44 * l, spacing: 0.2 * l }; }
function coaxStub(fHz, vf = 0.66) { return { quarterWave: wavelength(fHz, vf) / 4 }; }
if (typeof module !== "undefined") module.exports = { wavelength, dipole, monopole, fiveEighths, loop, yagi3, coaxStub, C };
