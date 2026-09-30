from eelab import *
from scipy import signal

META = dict(
    id="AM-124", title="Fixed vs floating point in a DSP chain", level="H",
    tools="Bit-true Q15 fixed-point FIR and biquad IIR (rounding, saturation), float32/float64 references, SQNR measurement, 6.02B + 1.76 dB rule, zero-input limit cycles",
    summary="Implement a filter chain in Q15 fixed point and in float32, measure the signal-to-quantisation-noise ratio against a float64 reference, "
            "check the 6 dB-per-bit rule, and provoke the zero-input limit cycles that only fixed-point recursive filters suffer from.",
    problem="A DSP runs 16-bit integers. How much precision does the filter really lose, and what can go wrong that never happens in floating point?",
    theory=r"""Rounding to B bits adds white noise of variance q²/12 (q = 2^{−(B−1)}); a full-scale sine then has SQNR ≈ 6.02B + 1.76 dB (98 dB at 16 bits). In a filter, each rounding point's noise is shaped by the transfer function from that point to the output
(noise gain Σh²). Recursive fixed-point filters can sustain small oscillations with zero input (limit cycles) because rounding makes the effective pole radius ≥ 1 near zero; floating point has no such dead band.""",
    method="""Input: 997 Hz sine at −1 dBFS, fs = 48 kHz. (i) Plain quantisation to 8/12/16 bits: SQNR vs 6.02B+1.76. (ii) 64-tap FIR in Q15 (products accumulated in 32-bit, one rounding) vs float32. (iii) Direct-form-I biquad (Q15 coefficients, rounding after each product) with poles at
0.99e^{±j0.1}: output SQNR; then zero input after an impulse: amplitude of the persistent limit cycle.""",
)


def q15(x):
    return np.clip(np.round(x * 32768), -32768, 32767).astype(np.int64)


def fir_q15(h, x):
    hq = q15(h); xq = q15(x)
    acc = np.convolve(xq, hq)[: len(x)]                      # exact 64-bit accumulate (32-bit is enough here)
    return np.clip(np.round(acc / 32768), -32768, 32767) / 32768


def biquad_q15(b, a, x, n_extra=0):
    bq, aq = q15(np.array(b) / 2), q15(np.array(a) / 2)      # coefficients scaled by ½ (|a1| < 2), products shifted by 14
    xq = np.r_[q15(x), np.zeros(n_extra, np.int64)]
    y = np.zeros(len(xq), np.int64); x1 = x2 = y1 = y2 = 0
    for n in range(len(xq)):
        acc = bq[0] * xq[n] + bq[1] * x1 + bq[2] * x2 - aq[1] * y1 - aq[2] * y2
        yn = int(np.clip(np.round(acc / 16384), -32768, 32767))
        x2, x1 = x1, xq[n]; y2, y1 = y1, yn; y[n] = yn
    return y / 32768


def sqnr(ref, y):
    return 10 * np.log10(np.sum(ref ** 2) / np.sum((y - ref) ** 2))


def run(p):
    fs = 48000; t = np.arange(1 << 16) / fs; x = 10 ** (-1 / 20) * np.sin(2 * pi * 997 * t)
    for B in (8, 12, 16):
        q = 2.0 ** -(B - 1); xq = np.round(x / q) * q
        p.compare(f"{B}-bit quantisation of a −1 dBFS sine: SQNR ≈ 6.02B + 1.76 − 1 dB", 6.02 * B + 1.76 - 1, sqnr(x, xq), "dB", kind="abs", tol=1.0)
    h = signal.firwin(64, 3000, fs=fs) * 0.9
    ref = signal.lfilter(h, 1, x)
    yq = fir_q15(h, x); y32 = signal.lfilter(h.astype(np.float32), np.float32(1), x.astype(np.float32)).astype(float)
    p.metric("64-tap FIR output SQNR: Q15 / float32", f"{sqnr(ref, yq):.1f} / {sqnr(ref, y32):.1f} dB")
    p.compare("Q15 FIR with one final rounding: SQNR ≈ 6.02·16 + 1.76 + level (output ~ −1 dBFS)", 96.1, sqnr(ref, yq), "dB", kind="abs", tol=6)
    r_, th = 0.99, 0.1
    a = [1, -2 * r_ * np.cos(th), r_ * r_]; b = np.array([1.0, 0, -1.0]) * (1 - r_) * 0.5
    refb = signal.lfilter(b, a, x)
    yb = biquad_q15(b, a, x[:20000])
    p.metric("Resonant biquad (r = 0.99) output SQNR in Q15 (roundings inside the loop are amplified by the high-Q poles)", sqnr(refb[:20000], yb), "dB")
    imp = np.zeros(200); imp[0] = 0.5
    yl = biquad_q15([1.0, 0, 0], a, imp, n_extra=20000)
    tail = yl[-5000:]
    p.compare("Zero input after an impulse: fixed-point output never decays (limit cycle amplitude > 0 LSB)", 1, int(np.max(np.abs(tail)) > 0), "", kind="abs")
    p.metric("Limit-cycle amplitude (LSBs)", np.max(np.abs(tail)) * 32768, "LSB", "float64 tail: " + f"{np.max(np.abs(signal.lfilter([1.0], a, np.r_[imp, np.zeros(20000)])[-5000:])):.1e}")
    fig, ax = p.fig(1, 2, w=11)
    Bs = np.arange(4, 25)
    ax[0].plot(Bs, [sqnr(x, np.round(x / 2.0 ** -(B - 1)) * 2.0 ** -(B - 1)) for B in Bs], "o", color=C_MEAS, label="measured"); ax[0].plot(Bs, 6.02 * Bs + 0.76, "--", color=C_PRED, label="6.02B + 1.76 − 1 dB")
    style_axes(ax[0], "bits", "SQNR (dB)", "6 dB per bit")
    ax[1].plot(yl[:3000] * 32768, color=C_MEAS, lw=.8)
    style_axes(ax[1], "sample", "output (LSB)", "Q15 biquad, zero input: limit cycle", legend=False)
    p.save(fig, "fixed_point", "SQNR vs word length, and a zero-input limit cycle in a fixed-point biquad.")
    p.discuss("""Quantisation behaves like additive white noise of q²/12, so SQNR follows 6.02B + 1.76 dB (minus the 1 dB backoff) from 4 to 24 bits. A Q15 FIR with a
wide accumulator and a single rounding at the output is essentially 16-bit-perfect; float32's 24-bit mantissa is better still. The recursive filter is
where fixed point bites: roundings inside a high-Q loop are amplified by the poles, cutting the output SQNR, and with zero input the output never
reaches zero — it settles into a small oscillation of a few LSBs, a limit cycle that floating point (whose resolution scales with the signal) cannot
produce. Remedies: wider state variables, error feedback, or magnitude truncation toward zero.""")
# tol-convention: relative tolerances are in percent
