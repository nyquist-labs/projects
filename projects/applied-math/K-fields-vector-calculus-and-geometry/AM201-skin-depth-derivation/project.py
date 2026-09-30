from eelab import *
from scipy.sparse import diags, identity
from scipy.sparse.linalg import splu
from scipy.special import jv, erfc

MU0 = 4e-7 * pi; SIG = 5.8e7

META = dict(
    id="AM-201", title="Skin depth from Maxwell's equations, verified by solving the diffusion equation", level="M",
    tools="Magneto-quasistatic reduction of Maxwell's equations to a diffusion equation, Crank–Nicolson time stepping in a copper half-space driven sinusoidally, fits of amplitude decay and phase lag, step response against the erfc similarity solution, exact AC resistance of a round wire from Bessel functions of complex argument",
    summary="Derive the skin effect instead of quoting it: inside a good conductor Maxwell's equations become a diffusion equation. Solve that equation in the time "
            "domain and watch the field settle into a decaying, phase-shifted wave whose decay length is √(2/ωμσ); then compute a wire's AC resistance exactly and check the usual approximations.",
    problem="Why does AC current crowd to the surface of a conductor, and where does δ = √(2/ωμσ) come from?",
    theory=r"""In a conductor with σ ≫ ωε, Ampère's law loses the displacement current: $\nabla\times H=σE$, and with Faraday's law $\partial_tH=\frac{1}{μσ}\nabla^2H$ — diffusion with diffusivity D = 1/(μσ). For a boundary field $H_0\cos ωt$ on a half-space the periodic solution is
$H=H_0e^{-x/δ}\cos(ωt-x/δ)$ with $δ=\sqrt{2/(ωμσ)}$ (copper: 9.3 mm at 50 Hz, 2.06 mm at 1 kHz, 0.21 mm at 100 kHz). A suddenly applied field penetrates as $H_0\,\mathrm{erfc}(x/2\sqrt{Dt})$. Round wire of radius a: internal impedance
$Z=\frac{k}{2πaσ}\frac{J_0(ka)}{J_1(ka)}$, $k=(1-j)/δ$; limits $R/R_{dc}\approx1+\frac{(a/δ)^4}{48}$ (low f) and $\frac{a}{2δ}+\frac14$ (high f).""",
    method="""1-D copper slab 30 mm deep (far side insulated), 0.02 mm cells, Crank–Nicolson with 400 steps per period, run for 8 periods at 1 kHz, amplitude and phase from a sine/cosine projection over the last period. Also 100 kHz (0.002 mm cells, 3 mm depth).
Step response at t = 5 ms by backward Euler with 0.2 µs steps (Crank–Nicolson rings after a discontinuous start). Wire: 1 mm radius, 10 Hz – 10 MHz.""",
)


def periodic(f, depth, dx, periods=8, spp=400):
    n = int(round(depth / dx)); D = 1 / (MU0 * SIG); w = 2 * pi * f; dt = 1 / (f * spp)
    main = -2 * np.ones(n); main[-1] = -1                                     # insulated far side (zero gradient)
    Lap = diags([np.ones(n - 1), main, np.ones(n - 1)], [-1, 0, 1]) / dx ** 2
    r = D * dt / 2; A = splu((identity(n) - r * Lap).tocsc()); Bm = (identity(n) + r * Lap).tocsr()
    H = np.zeros(n); cs = np.zeros(n); sn = np.zeros(n)
    for k in range(periods * spp):
        t = (k + 1) * dt; b0 = np.cos(w * (t - dt)); b1 = np.cos(w * t)
        rhs = Bm @ H
        rhs[0] += D * dt / (2 * dx ** 2) * (b0 + b1)                            # boundary node value H(0, t) = cos ωt enters the first row
        H = A.solve(rhs)
        if k >= (periods - 1) * spp:
            cs += H * np.cos(w * t) * 2 / spp; sn += H * np.sin(w * t) * 2 / spp
    x = (np.arange(n) + 1) * dx
    return x, np.hypot(cs, sn), np.arctan2(sn, cs)


def run(p):
    rows = []
    for f, depth, dx in ((1e3, 30e-3, 0.02e-3), (1e5, 3e-3, 0.002e-3)):
        x, amp, ph = periodic(f, depth, dx); d = np.sqrt(2 / (2 * pi * f * MU0 * SIG)); m = (x > 0.2 * d) & (x < 3 * d)
        d_amp = -1 / np.polyfit(x[m], np.log(amp[m]), 1)[0]; d_ph = 1 / np.polyfit(x[m], np.unwrap(ph[m]), 1)[0]
        rows.append((f, d, d_amp, d_ph, x, amp, ph))
        p.compare(f"{f / 1e3:g} kHz: decay length of the amplitude vs δ = √(2/ωμσ)", d, d_amp, "m", tol=1)
        p.compare(f"{f / 1e3:g} kHz: phase lag rate 1/δ (distance per radian)", d, d_ph, "m", tol=1)
    D = 1 / (MU0 * SIG); T = 5e-3; n = 4000; dx = 0.02e-3; dt = 2e-7                 # 80 mm deep: the insulated far side must be out of reach
    main = -2 * np.ones(n); main[-1] = -1; Lap = diags([np.ones(n - 1), main, np.ones(n - 1)], [-1, 0, 1]) / dx ** 2
    A = splu((identity(n) - D * dt * Lap).tocsc()); H = np.zeros(n)          # backward Euler: no Crank–Nicolson ringing at the step
    for k in range(int(round(T / dt))):
        rhs = H.copy(); rhs[0] += D * dt / dx ** 2; H = A.solve(rhs)
    xs = (np.arange(n) + 1) * dx; ex = erfc(xs / (2 * np.sqrt(D * T)))
    p.compare("Step response after 5 ms vs erfc(x/2√(Dt)) (max difference)", 0.0, float(np.max(np.abs(H - ex))), "", kind="abs", tol=5e-3)
    a = 1e-3; fs = np.logspace(1, 7, 61); ratio = []
    for f in fs:
        dlt = np.sqrt(2 / (2 * pi * f * MU0 * SIG)); kk = (1 - 1j) / dlt
        Z = kk / (2 * pi * a * SIG) * jv(0, kk * a) / jv(1, kk * a); ratio.append(Z.real / (1 / (SIG * pi * a * a)))
    ratio = np.array(ratio); dl = np.sqrt(2 / (2 * pi * fs * MU0 * SIG))
    lo = (a / dl < 1); hi = (a / dl > 10)
    p.compare("Round wire, a = 1 mm, low frequency: exact R/R_dc vs 1 + (a/δ)⁴/48 (worst relative difference for a < δ)", 0.0, float(np.max(np.abs(ratio[lo] - (1 + (a / dl[lo]) ** 4 / 48)) / ratio[lo])), "", kind="abs", tol=0.01)
    p.compare("High frequency (a > 10δ): exact vs a/(2δ) + ¼ (worst relative difference)", 0.0, float(np.max(np.abs(ratio[hi] - (a / (2 * dl[hi]) + 0.25)) / ratio[hi])), "", kind="abs", tol=0.01)
    f_dbl = fs[np.argmax(ratio > 2)]
    p.metric("Frequency at which a 2 mm copper wire's resistance has doubled", f_dbl, "Hz", f"δ there = {np.sqrt(2 / (2 * pi * f_dbl * MU0 * SIG)) * 1e3:.2f} mm")
    fig, ax = p.fig(1, 3, w=13, h=3.8)
    f0, d0, _, _, x, amp, ph = rows[0]
    ax[0].semilogy(x / d0, amp, color=C_MEAS, label="Crank–Nicolson, 1 kHz"); ax[0].semilogy(x / d0, np.exp(-x / d0), "--", color=C_PRED, label="e^(−x/δ)"); ax[0].set_xlim(0, 6); ax[0].set_ylim(1e-3, 1.2)
    style_axes(ax[0], "depth x / δ", "field amplitude", "Decay into copper")
    ax[1].plot(x / d0, -np.unwrap(ph), color=C_MEAS, label="simulated phase lag"); ax[1].plot(x / d0, x / d0, "--", color=C_PRED, label="x/δ"); ax[1].set_xlim(0, 6); ax[1].set_ylim(0, 6)
    style_axes(ax[1], "depth x / δ", "phase lag (rad)", "Phase advances one radian per δ")
    ax[2].loglog(fs, ratio, color=C_MEAS, label="exact (Bessel)"); ax[2].loglog(fs, a / (2 * dl) + 0.25, "--", color=C_PRED, label="a/2δ + ¼"); ax[2].loglog(fs, 1 + (a / dl) ** 4 / 48, ":", color=COLORS[2], label="1 + (a/δ)⁴/48")
    ax[2].set_ylim(0.9, 100)
    style_axes(ax[2], "frequency (Hz)", "R_ac / R_dc", "1 mm-radius copper wire")
    p.save(fig, "skin_depth", "Amplitude and phase of the field inside copper from a time-domain diffusion solve, and a wire's exact AC resistance.")
    p.discuss(f"""Dropping the displacement current turns Maxwell's equations inside copper into a diffusion equation, and solving that equation in the time domain —
no complex exponentials assumed — produces the skin effect by itself: after a few periods the field decays with a length of {rows[0][2] * 1e3:.3f} mm at 1 kHz and
{rows[1][2] * 1e6:.1f} µm at 100 kHz, matching √(2/ωμσ), and its phase lags by exactly one radian per skin depth, i.e. the field inside is a heavily damped wave
travelling inward. A suddenly applied field follows the erfc diffusion profile, which shows the same physics from the transient side (penetration
∝ √t). For a round wire the exact Bessel-function impedance confirms both textbook limits, and shows the practical consequence: a 2 mm copper wire
already has double its DC resistance at about {f_dbl / 1e3:.0f} kHz.""")
# tol-convention: relative tolerances are in percent
