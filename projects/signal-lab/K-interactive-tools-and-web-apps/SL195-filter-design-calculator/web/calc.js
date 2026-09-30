// Active filter designer: unity-gain Sallen-Key low-pass / high-pass stages for Butterworth, Bessel or Chebyshev responses,
// with capacitors from E12 and resistors rounded to E96.
const E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2];
const E96 = Array.from({ length: 96 }, (_, i) => Math.round(Math.pow(10, i / 96) * 100) / 100).map(v => (v === 9.19 ? 9.2 : v));

function nearest(v, table) {
  const d = Math.pow(10, Math.floor(Math.log10(v)));
  let best = null;
  for (const m of table.concat([10])) { const c = m * d; if (!best || Math.abs(Math.log(c / v)) < Math.abs(Math.log(best / v))) best = c; }
  return +best.toPrecision(3);
}
function ceilE(v, table) {            // smallest table value >= v
  const d = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of table.concat([10])) if (m * d >= v * (1 - 1e-9)) return +(m * d).toPrecision(3);
}

// normalised stage (f0 multiplier, Q) for order 2 and 4 prototypes (cutoff = -3 dB for Butterworth/Bessel, ripple edge for Chebyshev)
const PROTO = {
  butterworth: { 2: [[1, 0.7071]], 4: [[1, 0.5412], [1, 1.3066]] },
  bessel:      { 2: [[1.2720, 0.5774]], 4: [[1.4302, 0.5219], [1.6034, 0.8055]] },
  cheby1dB:    { 2: [[1.0500, 0.9565]], 4: [[0.5286, 0.7845], [0.9932, 3.5590]] },
};

// Low-pass: R1 (in→a), R2 (a→b), C1 (a→out), C2 (b→gnd). f0 = 1/(2π√(R1R2C1C2)), Q = √(R1R2C1C2)/(C2(R1+R2))
function lowpassStage(f0, Q, rTarget = 10e3) {
  const w = 2 * Math.PI * f0;
  const C2 = nearest(1 / (2 * Q * w * rTarget), E12);
  const C1 = ceilE(4 * Q * Q * C2 * 1.05, E12);        // need C1 >= 4Q²C2 for real resistors
  const s = Math.sqrt(1 - 4 * Q * Q * C2 / C1);
  const R1i = (1 + s) / (2 * w * Q * C2), R2i = (1 - s) / (2 * w * Q * C2);
  return { type: "lowpass", C1, C2, R1: nearest(R1i, E96), R2: nearest(R2i, E96), R1ideal: R1i, R2ideal: R2i };
}
// High-pass: C1 (in→a), C2 (a→b), R1 (a→out), R2 (b→gnd); equal C: R1 = 1/(2Qω C), R2 = 4Q² R1
function highpassStage(f0, Q, rTarget = 10e3) {
  const w = 2 * Math.PI * f0;
  const C = nearest(1 / (w * rTarget), E12);
  const R1i = 1 / (2 * Q * w * C), R2i = 4 * Q * Q * R1i;
  return { type: "highpass", C1: C, C2: C, R1: nearest(R1i, E96), R2: nearest(R2i, E96), R1ideal: R1i, R2ideal: R2i };
}

function stageParams(st) {                     // f0 and Q actually realised by rounded parts
  const { R1, R2, C1, C2 } = st;
  const f0 = 1 / (2 * Math.PI * Math.sqrt(R1 * R2 * C1 * C2));
  const Q = st.type === "lowpass" ? Math.sqrt(R1 * R2 * C1 * C2) / (C2 * (R1 + R2)) : Math.sqrt(R1 * R2 * C1 * C2) / (R1 * (C1 + C2));
  return { f0, Q };
}

function design(kind, family, order, fc) {
  const stages = PROTO[family][order].map(([k, Q]) => {
    const f0 = kind === "lowpass" ? fc * k : fc / k;
    return kind === "lowpass" ? lowpassStage(f0, Q) : highpassStage(f0, Q);
  });
  return stages;
}

function response(stages, f) {               // |H| of the cascade using realised parts, ideal op-amps
  return f.map(fr => {
    let mag = 1;
    for (const st of stages) {
      const { f0, Q } = stageParams(st), x = fr / f0;
      const num = st.type === "lowpass" ? 1 : x * x;
      mag *= num / Math.sqrt((1 - x * x) ** 2 + (x / Q) ** 2);
    }
    return mag;
  });
}

if (typeof module !== "undefined") module.exports = { design, response, stageParams, lowpassStage, highpassStage, nearest, PROTO };
