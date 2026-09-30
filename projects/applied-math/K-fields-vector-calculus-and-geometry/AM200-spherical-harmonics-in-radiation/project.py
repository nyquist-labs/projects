from eelab import *
from scipy.special import sph_harm_y

META = dict(
    id="AM-200", title="Spherical harmonics: radiation patterns as sums of modes", level="H",
    tools="Spherical harmonics Y_lm (SciPy), Gauss–Legendre × uniform quadrature on the sphere, orthonormality check, expansion of radiated-power patterns, directivity from the l = 0 coefficient, band-limit of an array pattern predicted from its size, rotation invariance of the per-degree power spectrum",
    summary="Decompose antenna radiation patterns into spherical harmonics: verify orthonormality numerically, recover the directivity from a single "
            "coefficient, predict from the antenna's physical size how many degrees are needed, and show that the energy per degree is unchanged when the antenna is rotated.",
    problem="A 3-D radiation pattern is a function on a sphere. What is its natural 'Fourier series', and what does the number of terms say about the antenna?",
    theory=r"""Any square-integrable function on the sphere is $U(θ,φ)=\sum_{l,m}c_{lm}Y_l^m(θ,φ)$ with $c_{lm}=\oint UY_l^{m*}dΩ$. Since $Y_0^0=1/\sqrt{4π}$, total radiated power ∝ $\oint U\,dΩ=\sqrt{4π}\,c_{00}$ and directivity $D=\sqrt{4π}\,U_{max}/c_{00}$. A source inside a sphere of radius R radiates fields with
negligible content above degree ≈ kR; the power pattern $|E|^2$ is band-limited to about 2kR. Rotations mix m within each l but leave $\sum_m|c_{lm}|^2$ unchanged. Half-wave dipole: $U∝\cos^2(\tfrac π2\cosθ)/\sin^2θ$, D = 1.641.""",
    method="""Quadrature: 120 Gauss–Legendre nodes in cos θ × 240 uniform φ (exact for band-limited functions up to high degree). Patterns: half-wave dipole; 8-element broadside array of isotropic sources along z (d = λ/2, length 3.5λ, so 2kR ≈ 22), and the same array tilted by 30°.
Coefficients up to l = 40.""",
)


def grid(nt=120, nph=240):
    x, w = np.polynomial.legendre.leggauss(nt); th = np.arccos(x); ph = 2 * pi * np.arange(nph) / nph
    TH, PH = np.meshgrid(th, ph, indexing="ij"); W = np.outer(w, np.full(nph, 2 * pi / nph))
    return TH, PH, W


def coeffs(U, TH, PH, W, L):
    return {(l, m): np.sum(U * np.conj(sph_harm_y(l, m, TH, PH)) * W) for l in range(L + 1) for m in range(-l, l + 1)}


def array_pattern(TH, PH, tilt=0.0):
    x, y, z = np.sin(TH) * np.cos(PH), np.sin(TH) * np.sin(PH), np.cos(TH)
    zr = z * np.cos(tilt) + x * np.sin(tilt)                              # array axis tilted in the x–z plane
    psi = pi * zr; n = np.arange(8)
    return np.abs(np.exp(1j * np.multiply.outer(psi, n)).sum(-1)) ** 2 / 64


def run(p):
    TH, PH, W = grid()
    worst = 0.0
    ls = [(l, m) for l in range(0, 11) for m in range(-l, l + 1)]
    Ys = {lm: sph_harm_y(lm[0], lm[1], TH, PH) for lm in ls}
    for i, a in enumerate(ls):
        for b in ls[i: i + 25]:
            v = np.sum(Ys[a] * np.conj(Ys[b]) * W); worst = max(worst, abs(v - (1.0 if a == b else 0.0)))
    p.compare("Orthonormality ⟨Y_lm, Y_l′m′⟩ = δ (l ≤ 10; worst deviation)", 0.0, worst, "", kind="abs", tol=1e-12)
    U = np.cos(pi / 2 * np.cos(TH)) ** 2 / np.sin(TH) ** 2
    c = coeffs(U, TH, PH, W, 12)
    D = np.sqrt(4 * pi) * U.max() / c[(0, 0)].real
    p.compare("Half-wave dipole: directivity from the l = 0 coefficient, √(4π)·U_max/c₀₀", 1.641, D, "", tol=0.1)
    nz = [lm for lm, v in c.items() if abs(v) > 1e-10]
    p.compare("Dipole pattern is axially symmetric and even: coefficients with m ≠ 0 or odd l (count above 10⁻¹⁰)", 0, sum(1 for l, m in nz if m != 0 or l % 2), "", kind="abs")
    Lmax = 40; A0 = array_pattern(TH, PH); ca = coeffs(A0, TH, PH, W, Lmax)
    Pl = np.array([sum(abs(ca[(l, m)]) ** 2 for m in range(-l, l + 1)) for l in range(Lmax + 1)])
    cum = np.cumsum(Pl) / Pl.sum(); l_bl = int(np.argmax(cum > 1 - 1e-6)); l_12 = int(np.argmax(cum > 1 - 1e-12))
    kR = 2 * pi * 3.5 / 2
    p.compare("8-element array (length 3.5λ): degree containing all but 10⁻⁶ of the pattern energy vs 2kR", 2 * kR, l_bl, "", tol=25)
    p.metric("… and all but 10⁻¹²", l_12, "", "beyond 2kR the spectrum falls super-exponentially, so the band edge depends on the accuracy demanded")
    A1 = array_pattern(TH, PH, tilt=np.radians(30)); c1 = coeffs(A1, TH, PH, W, Lmax)
    P1 = np.array([sum(abs(c1[(l, m)]) ** 2 for m in range(-l, l + 1)) for l in range(Lmax + 1)])
    sig = Pl > 1e-8 * Pl.max()
    p.compare("Rotating the array by 30°: per-degree power Σₘ|c_lm|² unchanged (worst relative change, significant degrees)", 0.0, float(np.max(np.abs(P1[sig] - Pl[sig]) / Pl[sig])), "", kind="abs", tol=1e-6)
    p.metric("Non-zero coefficients: upright array / tilted array (|c| > 10⁻⁸)", f"{sum(1 for v in ca.values() if abs(v) > 1e-8)} / {sum(1 for v in c1.values() if abs(v) > 1e-8)}", "", "rotation spreads energy over m, not over l")
    errs = []
    for Lt in (4, 8, 12, 16, 20, 24):
        rec = sum(ca[(l, m)] * sph_harm_y(l, m, TH, PH) for l in range(Lt + 1) for m in range(-l, l + 1) if abs(ca[(l, m)]) > 0)
        errs.append(np.sqrt(np.sum(np.abs(rec - A0) ** 2 * W) / np.sum(A0 ** 2 * W)))
    p.metric("Relative reconstruction error of the array pattern truncated at L = 4 / 8 / 12 / 16 / 20 / 24", " / ".join(f"{e:.1e}" for e in errs))
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(np.arange(Lmax + 1), np.maximum(Pl, 1e-30) / Pl.max(), "o-", ms=3, color=C_MEAS, label="upright"); ax[0].semilogy(np.arange(Lmax + 1), np.maximum(P1, 1e-30) / Pl.max(), "x", color=C_PRED, label="tilted 30°")
    ax[0].axvline(2 * kR, color="gray", ls="--", label="2kR"); ax[0].set_ylim(1e-30, 2)
    style_axes(ax[0], "degree l", "Σₘ|c_lm|² (normalised)", "Band-limit set by the array's size")
    th1 = np.linspace(0, pi, 400)
    TH1, PH1 = np.meshgrid(th1, [0.0], indexing="ij")
    rec8 = sum(ca[(l, m)] * sph_harm_y(l, m, TH1, PH1) for l in range(9) for m in range(-l, l + 1) if abs(ca[(l, m)]) > 0).real[:, 0]
    rec20 = sum(ca[(l, m)] * sph_harm_y(l, m, TH1, PH1) for l in range(21) for m in range(-l, l + 1) if abs(ca[(l, m)]) > 0).real[:, 0]
    ax[1].plot(np.degrees(th1), array_pattern(TH1, PH1)[:, 0], color="k", lw=2, label="exact"); ax[1].plot(np.degrees(th1), rec8, color=C_PRED, label="L = 8"); ax[1].plot(np.degrees(th1), rec20, "--", color=C_MEAS, label="L = 20")
    style_axes(ax[1], "θ (°)", "power pattern", "Truncated harmonic series")
    p.save(fig, "harmonics", "Energy per spherical-harmonic degree for an 8-element array, upright and tilted, and truncated reconstructions.")
    p.discuss(f"""On a Gauss–Legendre grid the spherical harmonics are orthonormal to {worst:.0e}, so expansion coefficients can be trusted. A pattern's l = 0
coefficient alone gives the radiated power, hence the directivity: {D:.3f} for the half-wave dipole, whose expansion contains only even l and m = 0 —
its symmetry, read off the coefficients. The array example shows what the number of terms means physically: the 3.5λ-long array's power pattern
has all but 10⁻⁶ of its energy below degree {l_bl}, near the 2kR ≈ {2 * kR:.0f} predicted from its size (and all but 10⁻¹² below {l_12}), which is why antenna near-field measurements can sample a sphere at a
finite density. Tilting the array redistributes its energy across m but leaves the energy in each degree exactly the same: degree is a property of
the antenna, orientation only of the coordinate system.""")
# tol-convention: relative tolerances are in percent
