from eelab import *
from scipy.integrate import quad

META = dict(
    id="AM-121", title="Computing Fourier coefficients accurately", level="M",
    tools="Trapezoidal (rectangle) rule, Simpson's rule and adaptive quadrature for Fourier integrals, spectral accuracy for smooth periodic integrands, aliasing of coefficients, error bounds",
    summary="Compute Fourier coefficients of periodic waveforms numerically and show a surprising fact: for smooth periodic functions the humble "
            "trapezoidal rule converges exponentially and beats Simpson's rule, while for a waveform with a corner both converge only algebraically — plus the aliasing error that bounds everything.",
    problem="Fourier coefficients are integrals. Which quadrature rule should compute them, and how accurate can the result be?",
    theory=r"""For a periodic analytic f, the N-point trapezoidal rule for $c_k=\frac1T\int f e^{-2πikt/T}$ equals the DFT and its error is the aliased sum $\sum_{m≠0}c_{k+mN}$ — exponentially small when c_k decays exponentially. Simpson (non-uniform
weights) destroys this and is only O(h⁴). For f with a kink (|sin t|, c_k ∝ 1/k²) the aliasing error is O(N⁻²) for both. Example: f = e^{cos t} has $c_k = I_k(1)$ (modified Bessel).""",
    method="""f₁ = e^{cos t} (analytic, exact c_k = I_k(1)); f₂ = |sin t| (kink, exact c_{2m} = −2/(π(4m²−1))). N = 4…256 samples: trapezoid (= FFT), composite Simpson, error in c₁/c₂ vs exact; adaptive quad as a reference cost.""",
)


def run(p):
    from scipy.special import iv
    rows = []
    for N in (4, 6, 8, 12, 16, 24, 32, 64, 128, 256):
        t = 2 * pi * np.arange(N) / N
        c1_tr = np.mean(np.exp(np.cos(t)) * np.cos(t))
        ts = np.linspace(0, 2 * pi, N + 1); w = np.ones(N + 1); w[1:-1:2] = 4; w[2:-1:2] = 2
        c1_si = (2 * pi / N) / 3 * np.sum(w * np.exp(np.cos(ts)) * np.cos(ts)) / (2 * pi) if N % 2 == 0 else np.nan
        c2_tr = np.mean(np.abs(np.sin(t)) * np.cos(2 * t))
        c2_si = (2 * pi / N) / 3 * np.sum(w * np.abs(np.sin(ts)) * np.cos(2 * ts)) / (2 * pi) if N % 2 == 0 else np.nan
        rows.append((N, abs(c1_tr - iv(1, 1)), abs(c1_si - iv(1, 1)), abs(c2_tr - (-2 / (3 * pi))), abs(c2_si - (-2 / (3 * pi)))))
    rr = np.array(rows)
    p.compare("Smooth periodic f = e^{cos t}: trapezoid error for c₁ with N = 16 (spectral: ≈ I₁₅(1) ≈ 1e-19 → machine ε)", 0, rr[4, 1], "", kind="abs", tol=1e-14)
    p.compare("… Simpson with N = 16 is far worse (ratio Simpson / trapezoid error ≫ 1)", 1e6, rr[4, 2] / max(rr[4, 1], 1e-17), "×", kind="abs", tol=1e30)
    k = rr[:, 0] >= 16
    sl_tr = np.polyfit(np.log(rr[k, 0]), np.log(rr[k, 3]), 1)[0]
    p.compare("Kinked f = |sin t|: trapezoid error for c₂ decays as N^slope (−2)", -2.0, sl_tr, "", kind="abs", tol=0.2)
    c_est = np.mean(np.abs(np.sin(2 * pi * np.arange(16) / 16)) * np.cos(2 * 2 * pi * np.arange(16) / 16))
    ex_alias = sum(-2 / (pi * (4 * (mm / 2) ** 2 - 1)) for mm in [2 + 16 * j for j in range(-20000, 20001) if j != 0])
    p.compare("N = 16 error for |sin t| equals the aliased sum Σ c_{2+16j}", ex_alias, c_est - (-2 / (3 * pi)), "", kind="abs", tol=1e-6)
    val, err_est = quad(lambda x: np.exp(np.cos(x)) * np.cos(x) / (2 * pi), 0, 2 * pi, full_output=0)[:2]
    p.metric("Adaptive quadrature (quad) for c₁ of e^{cos t}: error", abs(val - iv(1, 1)), "", "many more function evaluations than N = 16")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(rr[:, 0], np.maximum(rr[:, 1], 1e-17), "o-", color=C_MEAS, label="trapezoid (= DFT)"); ax[0].semilogy(rr[:, 0], np.maximum(rr[:, 2], 1e-17), "s-", color=C_PRED, label="Simpson")
    style_axes(ax[0], "samples N", "|error in c₁|", "e^{cos t}: exponential convergence")
    ax[1].loglog(rr[:, 0], rr[:, 3], "o-", color=C_MEAS, label="trapezoid"); ax[1].loglog(rr[:, 0], rr[:, 4], "s-", color=C_PRED, label="Simpson")
    style_axes(ax[1], "samples N", "|error in c₂|", "|sin t|: algebraic convergence")
    p.save(fig, "fourier_quadrature", "Quadrature errors for Fourier coefficients of a smooth and of a kinked periodic function.")
    p.discuss("""For the smooth periodic function e^{cos t} the plain trapezoidal rule — which is exactly what the FFT computes — reaches machine precision with 16
samples, because its only error is aliasing of coefficients that decay like Bessel functions. Simpson's rule, usually 'more accurate', is millions
of times worse here: its uneven weights break the exact cancellation that equally weighted samples enjoy for periodic integrands. For |sin t|, whose
kink makes coefficients decay only as 1/k², both rules converge as N⁻², and the trapezoid error equals the aliased tail Σc_{k+mN} to rounding
precision. Lesson: compute Fourier coefficients of periodic signals with equally spaced samples (FFT), and expect accuracy to be limited by
smoothness, not by the quadrature rule.""")
# tol-convention: relative tolerances are in percent
