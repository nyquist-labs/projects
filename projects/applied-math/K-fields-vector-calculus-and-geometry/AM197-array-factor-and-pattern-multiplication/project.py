from eelab import *
from eelab.nec import solve as nec_solve, far_field
from numpy.polynomial import chebyshev as Ch

META = dict(
    id="AM-197", title="Antenna arrays: array factor, beam steering and pattern multiplication", level="M",
    tools="Array-factor evaluation for linear arrays, closed-form beamwidth, sidelobe and grating-lobe predictions, Dolph–Chebyshev synthesis from Chebyshev polynomials, pattern multiplication with an element pattern, validation of pattern multiplication against a full moment-method model that includes mutual coupling",
    summary="Design linear arrays from the array factor: verify null positions, the −13.3 dB first sidelobe and the grating-lobe condition, steer the "
            "beam with phase shifts, synthesise a −30 dB equal-sidelobe Chebyshev taper, and test pattern multiplication against a moment-method model of four real dipoles.",
    problem="How do N identical antennas combine into a steerable beam, and how far can the simple 'element × array factor' picture be trusted?",
    theory=r"""N elements spaced d with progressive phase β: $AF(θ)=\sum_n a_ne^{jn(kd\cosθ+β)}$; uniform weights give $|AF|=\left|\frac{\sin(Nψ/2)}{N\sin(ψ/2)}\right|$, ψ = kd cosθ + β. First null at ψ = 2π/N; first sidelobe −13.26 dB for large N; beam points where ψ = 0, i.e. β = −kd cosθ₀. Grating lobes appear when
$d/λ>1/(1+|\cosθ_0|)$. Dolph–Chebyshev weights make all sidelobes equal to a chosen level R with the narrowest main lobe. Pattern multiplication: total = element pattern × AF — exact only if all elements carry identical currents, which mutual coupling breaks.""",
    method="""Broadside/endfire geometry along z, θ from the array axis. Uniform N = 8 and N = 32, d = λ/2; steering to θ₀ = 60°; grating-lobe scan over d. Chebyshev: N = 10, −30 dB. MoM: 4 parallel half-wave dipoles (along z, spaced 0.5λ along x),
all fed with 1 V, azimuthal pattern compared with the single-dipole pattern × AF.""",
)


def af(w, d, theta, beta=0.0):
    psi = 2 * pi * d * np.cos(theta) + beta; n = np.arange(len(w))
    return np.abs(np.exp(1j * np.outer(psi, n)) @ w) / np.abs(np.sum(w))


def chebyshev_weights(N, sll_db):
    R = 10 ** (sll_db / 20); x0 = np.cosh(np.arccosh(R) / (N - 1))
    M = 4096; psi = 2 * pi * np.arange(M) / M
    vals = Ch.chebval(x0 * np.cos(psi / 2), [0] * (N - 1) + [1])          # AF(ψ) = T_{N−1}(x0 cos(ψ/2))
    coef = np.fft.fft(vals * np.exp(1j * (N - 1) * psi / 2)) / M           # Σ a_n e^{jnψ} = AF(ψ)·e^{j(N−1)ψ/2} is 2π-periodic
    return np.real(coef[:N])


def run(p):
    th = np.linspace(0, pi, 20001)
    for N in (8, 32):
        A = af(np.ones(N), 0.5, th); db = 20 * np.log10(A + 1e-15)
        null = th[np.argmax(th > pi / 2)]; left = th[(th > pi / 2)][np.argmax(np.diff(A[th > pi / 2]) > 0)]
        p.compare(f"N = {N}, d = λ/2 broadside: first null at arcsin(2/N) from broadside", np.degrees(np.arcsin(2 / N)), np.degrees(left - pi / 2), "°", tol=0.5)
        main = np.abs(th - pi / 2) < np.arcsin(2 / N)
        p.compare(f"N = {N}: first sidelobe level (−13.26 dB for large N)", -13.26 if N == 32 else -12.8, float(db[~main].max()), "dB", kind="abs", tol=0.3)
    N = 8; beta = -2 * pi * 0.5 * np.cos(np.radians(60)); A = af(np.ones(N), 0.5, th, beta)
    p.compare("Steering: β = −kd cos θ₀ puts the beam at θ₀ = 60°", 60.0, np.degrees(th[np.argmax(A)]), "°", kind="abs", tol=0.05)
    gl = []
    for d in np.linspace(0.4, 1.0, 61):
        A = af(np.ones(16), d, th, -2 * pi * d * np.cos(np.radians(60))); peaks = th[(A > 0.9)]
        gl.append((d, np.any(np.abs(np.degrees(peaks) - 60) > 10)))
    d_first = min(d for d, g in gl if g)
    p.compare("Grating lobe first appears (16 elements, steered to 60°) at d/λ ≈ 1/(1 + |cos θ₀|)", 1 / (1 + 0.5), d_first, "λ", tol=6)
    w = chebyshev_weights(10, 30); A = af(w, 0.5, th); db = 20 * np.log10(A + 1e-15)
    nulls = np.flatnonzero((A[1:-1] < A[:-2]) & (A[1:-1] < A[2:])) + 1; first_null = th[nulls[nulls > len(th) // 2][0]]
    side = np.abs(th - pi / 2) > (first_null - pi / 2)
    lobes = db[1:-1][(db[1:-1] > db[:-2]) & (db[1:-1] > db[2:]) & side[1:-1]]
    p.compare("Dolph–Chebyshev N = 10, −30 dB: highest sidelobe", -30.0, float(lobes.max()), "dB", kind="abs", tol=0.1)
    p.compare("… all sidelobes equal (spread between highest and lowest local maxima)", 0.0, float(lobes.max() - lobes.min()), "dB", kind="abs", tol=0.2)
    hp = lambda A_: np.degrees(2 * (th[(th > pi / 2) & (A_ < 1 / np.sqrt(2))][0] - pi / 2))
    p.metric("Half-power beamwidth, N = 10: uniform / Chebyshev −30 dB", f"{hp(af(np.ones(10), 0.5, th)):.1f}° / {hp(A):.1f}°", "", "lower sidelobes cost a wider main lobe")
    p.metric("Chebyshev weights (normalised to the edge element)", ", ".join(f"{v / w[0]:.2f}" for v in w[: 5]), "", "symmetric")
    xs = [0.0, 0.5, 1.0, 1.5]; phis = np.linspace(0, 2 * pi, 361); th0 = np.array([pi / 2])
    cur4, _ = nec_solve([(x, 0.5, True) for x in xs], lam=1.0, nseg=41, radius=1e-3)
    cur1, _ = nec_solve([(0.0, 0.5, True)], lam=1.0, nseg=41, radius=1e-3)
    full = np.array([far_field(cur4, 1.0, th0, ph)[0] for ph in phis]); single = np.array([far_field(cur1, 1.0, th0, ph)[0] for ph in phis])
    afx = np.abs(np.sum(np.exp(1j * 2 * pi * np.outer(np.cos(phis), xs)), axis=1)) / 4
    mult = single * afx
    fn, mn = full / full.max(), mult / mult.max()
    feeds = [c_[2][np.argmin(np.abs(c_[1]))] for c_ in cur4]
    p.compare("Pattern multiplication vs full MoM with coupling: worst pattern difference (normalised amplitude)", 0.0, float(np.max(np.abs(fn - mn))), "", kind="abs", tol=0.05)
    p.metric("Feed currents of the 4 equally driven dipoles (magnitude relative to the outer one)", ", ".join(f"{abs(f_) / abs(feeds[0]):.2f}" for f_ in feeds), "", "coupling makes 'identical elements' carry different currents")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    for N_, c in ((8, C_MEAS), (32, COLORS[2])):
        ax[0].plot(np.degrees(th), 20 * np.log10(af(np.ones(N_), 0.5, th) + 1e-9), color=c, label=f"uniform N = {N_}")
    ax[0].plot(np.degrees(th), db, color=C_PRED, label="Chebyshev N = 10, −30 dB"); ax[0].set_ylim(-50, 1)
    style_axes(ax[0], "θ from the array axis (°)", "|AF| (dB)", "Broadside arrays, d = λ/2")
    for d, c in ((0.5, C_MEAS), (0.8, C_PRED)):
        ax[1].plot(np.degrees(th), 20 * np.log10(af(np.ones(16), d, th, -2 * pi * d * 0.5) + 1e-9), color=c, label=f"d = {d}λ")
    ax[1].set_ylim(-40, 1)
    style_axes(ax[1], "θ (°)", "|AF| (dB)", "Steered to 60°: grating lobe at d = 0.8λ")
    ax[2].plot(np.degrees(phis), 20 * np.log10(fn + 1e-9), color=C_MEAS, label="MoM, coupled"); ax[2].plot(np.degrees(phis), 20 * np.log10(mn + 1e-9), "--", color=C_PRED, label="element × AF")
    ax[2].set_ylim(-40, 1)
    style_axes(ax[2], "azimuth φ (°)", "normalised |E| (dB)", "4 dipoles, 0.5λ apart")
    p.save(fig, "arrays", "Array factors of uniform and Chebyshev arrays, the onset of a grating lobe, and pattern multiplication against a coupled MoM model.")
    p.discuss(f"""The array factor predicts linear-array behaviour quantitatively: nulls where Nψ/2 = π, the familiar −13.3 dB first sidelobe for large uniform arrays
(slightly lower for N = 8), a beam that goes exactly where the phase gradient sends it, and a grating lobe that appears when the spacing exceeds
1/(1 + |cos θ₀|) wavelengths ({d_first:.2f}λ measured for 60° steering). Chebyshev synthesis gives precisely equal −30 dB sidelobes at the cost of a wider main
beam. Pattern multiplication is the one idealisation tested against a fuller model: with four real, coupled dipoles driven by equal voltages, the
currents differ by up to {max(abs(f_) / abs(feeds[0]) for f_ in feeds) * 100 - 100:.0f} % between elements, yet the product 'element × AF' still reproduces the MoM pattern to {np.max(np.abs(fn - mn)):.3f} in normalised
amplitude — a little worse than the 0.05 I expected, with the differences concentrated away from the main beam. Coupling matters for the input impedances (and deep nulls) more than for the main beam.""")
# tol-convention: relative tolerances are in percent
