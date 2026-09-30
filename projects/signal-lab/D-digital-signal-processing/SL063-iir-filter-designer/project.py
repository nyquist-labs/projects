from eelab import *
from scipy import signal

META = dict(
    id="SL-063", title="IIR filter designer: bilinear transform, poles and quantisation", level="M",
    tools="Own bilinear-transform implementation, SciPy analog prototypes, fixed-point coefficient study",
    summary="Design Butterworth and Chebyshev IIR low-pass filters with the bilinear transform (with "
            "pre-warping), check the cutoff lands where specified, and show how coefficient quantisation "
            "pushes poles toward — and past — the unit circle.",
    problem="IIR filters are far cheaper than FIR, but their poles make them fragile. How precisely must "
            "the coefficients be stored for a narrow filter to stay stable?",
    theory=r"""Bilinear transform $s = \frac{2}{T}\frac{1-z^{-1}}{1+z^{-1}}$ maps the jω axis onto the unit circle with warping
$\Omega = \frac2T\tan\frac{\omega}{2}$; pre-warping the analog cutoff to $\frac2T\tan(\omega_c/2)$ puts the digital −3 dB point
exactly at $f_c$. Stability ⇔ all poles inside |z| = 1. A narrow low-pass (f_c ≪ f_s) has poles near z = 1, so a
direct-form denominator quantised to B bits perturbs pole radius by ~$2^{-B}$ × (sensitivity ∝ 1/distance
between poles) — second-order sections are far less sensitive.""",
    method="""f_s = 48 kHz. 6th-order Butterworth and 1 dB Chebyshev at f_c = 1 kHz and at f_c = 100 Hz. Own bilinear transform
of the analog zpk (with and without pre-warping); measure the −3 dB point. Then quantise direct-form
coefficients and SOS coefficients to 8–24 fractional bits and record max pole radius.""",
)


def bilinear_zpk(z, pz, k, fs):
    fs2 = 2 * fs
    zd = (fs2 + z) / (fs2 - z)
    pd = (fs2 + pz) / (fs2 - pz)
    zd = np.concatenate([zd, -np.ones(len(pz) - len(z))])
    kd = k * np.real(np.prod(fs2 - z) / np.prod(fs2 - pz))
    return zd, pd, kd


def design(kind, fc, fs, prewarp=True, order=6):
    wa = 2 * fs * np.tan(pi * fc / fs) if prewarp else 2 * pi * fc
    proto = signal.butter(order, wa, analog=True, output="zpk") if kind == "butter" else signal.cheby1(order, 1, wa, analog=True, output="zpk")
    return bilinear_zpk(*proto, fs)


def quant(c, bits):
    q = 2.0**-bits
    return np.round(c / q) * q


def run(p):
    fs = 48e3
    fig, ax = p.fig()
    for i, (kind, pw) in enumerate([("butter", True), ("butter", False), ("cheby", True)]):
        z, pz, k = design(kind, 1000, fs, pw)
        b, a = signal.zpk2tf(z, pz, k)
        w, H = signal.freqz(b, a, worN=16384, fs=fs)
        g = db(H) - (0 if kind == "butter" else 0)
        lvl = -3.0103 if kind == "butter" else -1.0
        fcm = find_crossing(w[1:], g[1:], lvl, falling=True)
        lab = f"{kind} {'pre-warped' if pw else 'no pre-warp'}"
        p.compare(f"{lab}: cutoff ({'−3 dB' if kind == 'butter' else '−1 dB ripple edge'})", 1000, fcm, "Hz", tol=1 if pw else None)
        ax.semilogx(w[1:], g[1:], color=COLORS[i], label=lab)
    fw = 2 * fs / (2 * pi) * np.arctan(2 * pi * 1000 / (2 * fs)) * 2 * 1
    p.metric("Warped cutoff without pre-warp (theory)", fs / pi * np.arctan(pi * 1000 / fs), "Hz", "f_d = (f_s/π)·atan(π f_c / f_s)")
    ax.set_xlim(100, 20000); ax.set_ylim(-80, 3)
    style_axes(ax, "frequency (Hz)", "gain (dB)", "6th-order IIR low-pass via bilinear transform")
    p.save(fig, "responses", "Pre-warping puts the cutoff exactly at 1 kHz.")
    # quantisation study: narrow filter, fc = 100 Hz
    z, pz, k = design("butter", 100, fs)
    b, a = signal.zpk2tf(z, pz, k)
    sos = signal.zpk2sos(z, pz, k)
    p.metric("True max pole radius (f_c = 100 Hz)", np.max(np.abs(pz)), "")
    def bits_needed(poles):
        # first-order root sensitivity: |Δp_i| ≤ (q/2)·Σ_k |p_i|^(N−k) / Π_{j≠i}|p_i − p_j|, q = 2^−B
        N = len(poles); worst = 0
        for i, pi_ in enumerate(poles):
            den = np.prod([abs(pi_ - pj) for j, pj in enumerate(poles) if j != i])
            S = sum(abs(pi_)**(N - k) for k in range(1, N + 1)) / den
            worst = max(worst, S / (1 - abs(pi_)))
        return int(np.ceil(np.log2(worst / 2)))
    pred_df = bits_needed(pz)
    pred_sos = max(bits_needed(np.roots(s_[3:])) for s_ in sos)
    bits = np.arange(8, 41)
    rdf = np.array([np.max(np.abs(np.roots(quant(a, B)))) for B in bits])
    rsos = np.array([max(np.max(np.abs(np.roots(quant(s_[3:], B)))) for s_ in sos) for B in bits])
    first_stable = lambda r: int(bits[np.argmax(np.all([r[j:] < 1 for j in range(len(r))], axis=0) if False else r < 1)])
    stable_df = bits[np.where(rdf < 1)[0]]
    stable_df = int(next(B for j, B in enumerate(bits) if np.all(rdf[j:] < 1)))
    stable_sos = int(next(B for j, B in enumerate(bits) if np.all(rsos[j:] < 1)))
    p.compare("Direct form: bits needed for guaranteed stability", pred_df, stable_df, "bits", kind="abs",
              note="first-order root-sensitivity bound (worst case)")
    p.compare("SOS form: bits needed for guaranteed stability", pred_sos, stable_sos, "bits", kind="abs")
    fig, ax = p.fig(1, 2)
    ax[0].plot(bits, rdf, "o-", color=COLORS[1], label="direct form")
    ax[0].plot(bits, rsos, "o-", color=C_MEAS, label="second-order sections")
    ax[0].axhline(1, color=COLORS[7], ls="--", lw=1, label="unit circle")
    ax[0].set_ylim(0.97, 1.05); ax[0].set_xlim(8, 40)
    style_axes(ax[0], "coefficient fractional bits", "max |pole|", "Quantisation vs stability (f_c = 100 Hz)")
    th = np.linspace(0, 2 * pi, 400)
    ax[1].plot(np.cos(th), np.sin(th), color="gray", lw=.8)
    ax[1].plot(pz.real, pz.imag, "x", color=C_PRED, ms=9, label="ideal poles")
    rq = np.roots(quant(a, 16))
    ax[1].plot(rq.real, rq.imag, "o", mfc="none", color=COLORS[1], label="direct form, 16 bits")
    ax[1].set_xlim(0.9, 1.05); ax[1].set_ylim(-0.08, 0.08); ax[1].set_aspect("equal")
    style_axes(ax[1], "Re z", "Im z", "Poles crowd near z = 1")
    p.save(fig, "quantisation", "A narrow direct-form IIR needs ~20+ bits; the same filter as biquads needs far fewer.")
    p.csv("quantisation", bits=bits, max_pole_direct=rdf, max_pole_sos=rsos)
    p.discuss("""With pre-warping the measured cutoffs land on 1 kHz to within the frequency grid; without it the cutoff shifts
down to the value predicted by the tangent warping formula. The quantisation study shows the classic
danger: six poles clustered near z = 1 make the direct-form polynomial's roots hypersensitive, so a
16-bit direct-form implementation of a 100 Hz filter at 48 kHz is *unstable*, while the same filter as three
biquads is stable with far fewer bits. The prediction uses the first-order root-sensitivity formula
∂p_i/∂a_k = −p_i^(N−k)/Π(p_i − p_j) with worst-case rounding on every coefficient, so it is conservative:
random rounding errors partly cancel, and the simulation usually becomes stable a few bits earlier.""")
