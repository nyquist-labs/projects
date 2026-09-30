from eelab import *
from scipy import signal

META = dict(
    id="AM-035", title="IIR filters from analog prototypes (Butterworth, Chebyshev)", level="M",
    tools="Own analog prototype pole formulas (Butterworth circle, Chebyshev ellipse), pre-warped bilinear transform, comparison with scipy.signal.butter / cheby1",
    summary="Derive the poles of Butterworth and Chebyshev-I prototypes from their defining equations, convert them to digital filters with the "
            "pre-warped bilinear transform, and verify cutoff, ripple and agreement with SciPy's designs.",
    problem="Classical digital IIR filters are analog designs in disguise. Can they be rebuilt from the formulas alone?",
    theory=r"""Butterworth: $|H|^2=1/(1+(Ω/Ω_c)^{2N})$, poles equally spaced on a circle, $p_k=Ω_ce^{jπ(2k+N-1)/(2N)}$. Chebyshev I with ripple R dB: ε² = 10^{R/10}−1, poles on an ellipse,
$p_k=-Ω_c\sinh(a)\sin θ_k + jΩ_c\cosh(a)\cos θ_k$ with $a=\frac1N\operatorname{asinh}(1/ε)$, $θ_k=\frac{(2k-1)π}{2N}$; DC gain $1/\sqrt{1+ε^2}$ for even N. After pre-warping, the digital filter has
exactly the specified edge and ripple.""",
    method="""N = 4 and 5, f_c = 1 kHz at f_s = 8 kHz, ripple 1 dB. Pole sets vs scipy's analog prototypes; digital responses vs scipy.signal.butter/cheby1(…, fs=8000); −3 dB (Butterworth) and ripple-edge
(Chebyshev) frequency and passband ripple measured.""",
)


def butter_poles(N, Wc):
    k = np.arange(1, N + 1)
    return Wc * np.exp(1j * pi * (2 * k + N - 1) / (2 * N))


def cheby_poles(N, Wc, R):
    eps = np.sqrt(10 ** (R / 10) - 1); a = np.arcsinh(1 / eps) / N
    th = (2 * np.arange(1, N + 1) - 1) * pi / (2 * N)
    return -Wc * np.sinh(a) * np.sin(th) + 1j * Wc * np.cosh(a) * np.cos(th), eps


def to_digital(pz, fs, dc_gain):
    T = 1 / fs
    pd = (1 + pz * T / 2) / (1 - pz * T / 2); zd = -np.ones(len(pz))
    k = dc_gain * np.real(np.prod(1 - pd) / np.prod(1 - zd))
    return zd, pd, k


def run(p):
    fs, fc = 8000, 1000
    Wc = 2 * fs * np.tan(pi * fc / fs)
    rows = []
    for N in (4, 5):
        pb = butter_poles(N, Wc)
        _, pref, _ = signal.butter(N, Wc, analog=True, output="zpk")
        d1 = np.max(np.abs(np.sort_complex(pb) - np.sort_complex(pref))) / Wc
        zd, pd, k = to_digital(pb, fs, 1.0)
        w, H = signal.freqz_zpk(zd, pd, k, worN=2 ** 16, fs=fs)
        b2 = signal.butter(N, fc, fs=fs, output="zpk"); _, H2 = signal.freqz_zpk(*b2, worN=2 ** 16, fs=fs)
        f3 = w[np.argmax(db(np.abs(H)) < -3.0103)]
        rows.append(("Butterworth", N, d1, np.max(np.abs(H - H2)), f3, None))
        pc, eps = cheby_poles(N, Wc, 1.0)
        _, pref, _ = signal.cheby1(N, 1.0, Wc, analog=True, output="zpk")
        d2 = np.max(np.abs(np.sort_complex(pc) - np.sort_complex(pref))) / Wc
        dc = 1 / np.sqrt(1 + eps ** 2) if N % 2 == 0 else 1.0
        zd, pd, k = to_digital(pc, fs, dc)
        w, H = signal.freqz_zpk(zd, pd, k, worN=2 ** 16, fs=fs)
        c2 = signal.cheby1(N, 1.0, fc, fs=fs, output="zpk"); _, H2 = signal.freqz_zpk(*c2, worN=2 ** 16, fs=fs)
        pb_band = w <= fc
        ripple = db(np.abs(H[pb_band])).max() - db(np.abs(H[pb_band])).min()
        edge = w[np.flatnonzero(db(np.abs(H)) >= -1.0 - 1e-6)[-1]]
        rows.append(("Chebyshev 1 dB", N, d2, np.max(np.abs(H - H2)), edge, ripple))
    for kind, N, dpole, dresp, fedge, ripple in rows:
        p.compare(f"{kind} N = {N}: prototype poles vs SciPy (relative)", 0, dpole, "", kind="abs", tol=1e-12)
        p.compare(f"{kind} N = {N}: digital response vs SciPy design (max |ΔH|)", 0, dresp, "", kind="abs", tol=1e-9)
        p.compare(f"{kind} N = {N}: {'−3 dB' if ripple is None else 'ripple-edge'} frequency", fc, fedge, "Hz", tol=0.2)
        if ripple is not None:
            p.compare(f"{kind} N = {N}: passband ripple", 1.0, ripple, "dB", kind="abs", tol=0.01)
    fig, ax = p.fig(1, 2, w=11)
    th = np.linspace(0, 2 * pi, 300)
    ax[0].plot(Wc * np.cos(th), Wc * np.sin(th), ":", color="gray")
    pc, _ = cheby_poles(5, Wc, 1.0)
    ax[0].plot(butter_poles(5, Wc).real, butter_poles(5, Wc).imag, "x", color=C_MEAS, ms=9, mew=2, label="Butterworth (circle)")
    ax[0].plot(pc.real, pc.imag, "x", color=C_PRED, ms=9, mew=2, label="Chebyshev 1 dB (ellipse)")
    ax[0].set_aspect("equal")
    style_axes(ax[0], "Re s", "Im s", "Analog prototype poles, N = 5")
    for kind, c in (("butter", C_MEAS), ("cheby", C_PRED)):
        pz = butter_poles(5, Wc) if kind == "butter" else cheby_poles(5, Wc, 1.0)[0]
        zd, pd, k = to_digital(pz, fs, 1.0)
        w, H = signal.freqz_zpk(zd, pd, k, worN=4096, fs=fs)
        ax[1].plot(w, db(np.abs(H) + 1e-12), color=c, label=kind)
    ax[1].set_ylim(-80, 3); ax[1].axvline(fc, ls=":", color="gray")
    style_axes(ax[1], "frequency (Hz)", "|H| (dB)", "Digital filters (pre-warped bilinear)")
    p.save(fig, "iir_proto", "Butterworth and Chebyshev prototype poles and the resulting digital responses.")
    p.discuss("""Built only from their defining pole formulas — equally spaced points on a circle for Butterworth, an ellipse whose axes come from the ripple
ε for Chebyshev — the prototypes coincide with SciPy's to machine precision, and after pre-warping the digital filters hit the 1 kHz edge and the
1 dB ripple exactly. The picture explains the trade: squashing the circle into an ellipse moves the poles toward the jω axis, which sharpens the
transition (more attenuation at 2 kHz) at the cost of passband ripple and, as AM-014 showed, worse group delay. One detail that is easy to get
wrong: an even-order Chebyshev has DC gain 1/√(1+ε²), not 1.""")
# tol-convention: relative tolerances are in percent
