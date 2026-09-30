from eelab import *
from scipy import signal

META = dict(
    id="AM-126", title="Where round-off destroys a filter: direct form vs second-order sections", level="M",
    tools="Polynomial root sensitivity, coefficient quantisation of an 8th-order narrow-band IIR in direct form vs cascaded biquads, pole displacement and response distortion",
    summary="Quantise the coefficients of the same narrow-band filter in two structures and watch the direct form's poles scatter — some outside the "
            "unit circle — while the second-order-section form survives; explain it with the sensitivity of polynomial roots to their coefficients.",
    problem="Why does every DSP library implement high-order IIR filters as cascades of biquads?",
    theory=r"""A root of $A(z)=\sum a_kz^{-k}$ moves by $δp_i ≈ -\frac{\sum_k δa_k p_i^{N-k}}{\prod_{j\ne i}(p_i-p_j)}$: when poles cluster (narrow band, low cutoff) the denominator is tiny and a coefficient error of 2⁻¹⁶ moves poles by orders of magnitude more. In biquads each section has only two poles, so the product has
one factor — sensitivity is bounded. Prediction: 8th-order band-pass with poles near 0.99 in direct form becomes unstable at 16-bit coefficients; as SOS it stays within spec.""",
    method="""8th-order Butterworth band-pass 0.04–0.05 fs (poles clustered near z = 1). Coefficients rounded to B = 12…32 fractional bits (after scaling to |a| < 2^k). Pole radii and response error vs the float64 design; sensitivity bound
from the formula.""",
)


def quant(c, B):
    s = 2.0 ** (np.ceil(np.log2(np.max(np.abs(c)) + 1e-300)))
    return np.round(c / s * 2 ** B) / 2 ** B * s


def run(p):
    b, a = signal.butter(4, [0.08, 0.10], btype="band")        # order 8
    sos = signal.butter(4, [0.08, 0.10], btype="band", output="sos")
    p0 = np.roots(a)
    dens = []
    for i, pi_ in enumerate(p0):
        dens.append(abs(np.prod(np.delete(p0, i) - pi_)))
    p.metric("Min |Π(p_i − p_j)| over poles (small ⇒ sensitive)", min(dens), "")
    rows = []
    w, H0 = signal.freqz(b, a, worN=4096)
    for B in (12, 16, 20, 24, 32):
        aq = quant(a, B); pq = np.roots(aq)
        sq = sos.copy()
        for k in range(len(sq)):
            sq[k, 3:] = quant(sq[k, 3:], B); sq[k, :3] = quant(sq[k, :3], B)
        ps = np.concatenate([np.roots(s[3:]) for s in sq])
        _, H1 = signal.freqz(quant(b, B), aq, worN=4096); _, H2 = signal.sosfreqz(sq, worN=4096)
        rows.append((B, np.max(np.abs(pq)), np.max(np.abs(ps)), np.max(np.abs(np.abs(H1) - np.abs(H0))), np.max(np.abs(np.abs(H2) - np.abs(H0)))))
    rr = np.array(rows)
    p.compare("Direct form, 16-bit coefficients: largest pole radius ≥ 1 (unstable; 1 = yes)", 1, int(rr[1, 1] >= 1), "", kind="abs")
    p.compare("SOS, 16-bit coefficients: all poles inside the unit circle (1 = yes)", 1, int(rr[1, 2] < 1), "", kind="abs")
    p.metric("Max |ΔH| at 16 bits: direct form / SOS", f"{rr[1, 3]:.2e} / {rr[1, 4]:.2e}")
    B_ok_df = next((int(r_[0]) for r_ in rows if r_[1] < 1 and r_[3] < 0.01), None)
    p.metric("Coefficient bits needed for < 1 % response error: direct form / SOS", f"{B_ok_df} / {next((int(r_[0]) for r_ in rows if r_[4] < 0.01), None)}")
    fig, ax = p.fig(1, 2, w=11)
    th = np.linspace(0, 2 * pi, 400); ax[0].plot(np.cos(th), np.sin(th), color="gray", lw=.8)
    ax[0].plot(p0.real, p0.imag, "x", color="black", ms=9, label="exact")
    pq = np.roots(quant(a, 16)); ax[0].plot(pq.real, pq.imag, "o", mfc="none", color=C_PRED, ms=8, label="direct form, 16 bit")
    sq = sos.copy()
    for k in range(len(sq)):
        sq[k, 3:] = quant(sq[k, 3:], 16)
    ps = np.concatenate([np.roots(s[3:]) for s in sq]); ax[0].plot(ps.real, ps.imag, "s", mfc="none", color=C_MEAS, ms=8, label="SOS, 16 bit")
    ax[0].set_xlim(0.7, 1.1); ax[0].set_ylim(-0.3, 0.5); ax[0].set_aspect("equal")
    style_axes(ax[0], "Re z", "Im z", "Pole positions after quantisation")
    ax[1].semilogy(rr[:, 0], rr[:, 3], "o-", color=C_PRED, label="direct form"); ax[1].semilogy(rr[:, 0], rr[:, 4], "s-", color=C_MEAS, label="second-order sections")
    style_axes(ax[1], "coefficient bits", "max |H error|", "Response error vs word length")
    p.save(fig, "conditioning_dsp", "Quantised pole positions for both structures and response error vs coefficient word length.")
    p.discuss("""The narrow band-pass puts eight poles in a tight cluster near z ≈ 1, so the product of pole differences in the root-sensitivity formula is tiny and the
direct-form denominator polynomial is catastrophically ill-conditioned: rounding its coefficients to 16 bits throws poles outside the unit circle (an
unstable filter from a stable design). The same filter as four biquads keeps each pole pair's sensitivity bounded — each quadratic has only two roots —
and stays accurate at 16 bits. This is the numerical-analysis reason for the universal practice of cascading second-order sections (or lattice
structures), and it is also why high-order polynomials should never be expanded from their roots unless necessary (AM-078).""")
# tol-convention: relative tolerances are in percent
