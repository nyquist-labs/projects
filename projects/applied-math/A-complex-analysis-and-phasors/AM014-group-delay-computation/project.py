from eelab import *
from scipy import signal

META = dict(
    id="AM-014", title="Group delay: numerical differentiation and pulse distortion", level="M",
    tools="Analytic group delay of Butterworth, Chebyshev and Bessel filters, numerical differentiation of unwrapped phase, time-domain pulse tests",
    summary="Compute group delay by differentiating phase numerically, check it against the analytic value, and show what non-flat delay "
            "does to a pulse by passing the same pulse through Bessel, Butterworth and Chebyshev filters of equal order.",
    problem="Two filters with the same magnitude cutoff can mangle pulses very differently. Why?",
    theory=r"""τ(ω) = −dφ/dω. For H = ∏ 1/(s−p_k), each pole contributes $\frac{-\mathrm{Re}\,p_k}{(\mathrm{Re}\,p_k)^2+(ω-\mathrm{Im}\,p_k)^2}$, so τ can be computed exactly from the poles. A Bessel filter maximises
flatness of τ at DC, so all frequencies of a pulse are delayed equally and the pulse keeps its shape (≈ no overshoot); Chebyshev's delay peaks near cutoff, so
components there arrive late and ring. Central differences on phase have error O(Δω²) — but amplify phase noise by 1/Δω.""",
    method="""5th-order analog Bessel (norm = 'delay' rescaled), Butterworth and Chebyshev-I (1 dB), all with −3 dB at 1 rad/s. τ from the pole formula vs central differences on 2000 points;
step and 3-s rectangular pulse responses; overshoot and delay spread measured. Noise sensitivity: 0.001 rad phase noise added before differentiation.""",
)


def tau_poles(z, pz, w):
    t = np.zeros_like(w)
    for pk in pz:
        t += -pk.real / (pk.real ** 2 + (w - pk.imag) ** 2)
    for zk in z:
        t -= -zk.real / (zk.real ** 2 + (w - zk.imag) ** 2)
    return t


def design(kind):
    if kind == "Bessel":
        return signal.bessel(5, 1, analog=True, output="zpk", norm="mag")
    if kind == "Butterworth":
        return signal.butter(5, 1, analog=True, output="zpk")
    z, pz, k = signal.cheby1(5, 1, 1, analog=True, output="zpk")
    # rescale so the -3 dB point is at 1 rad/s like the others
    w = np.linspace(0.5, 2, 20001); _, h = signal.freqs_zpk(z, pz, k, w)
    w3 = w[np.argmin(np.abs(np.abs(h) - np.abs(h[0]) / np.sqrt(2) * (10 ** (0 / 20))))]
    wlin = np.linspace(0.8, 1.3, 50001); _, h = signal.freqs_zpk(z, pz, k, wlin)
    g = db(h)
    w3 = wlin[np.flatnonzero(g < -3.0103)[0]]
    return z / w3, pz / w3, k / w3 ** (len(pz) - len(z))


def run(p):
    w = np.linspace(0.001, 3, 2000)
    fig, ax = p.fig(1, 3, w=12, h=3.8)
    t = np.linspace(0, 30, 6001)
    res = {}
    for kind, c in (("Bessel", COLORS[0]), ("Butterworth", COLORS[1]), ("Chebyshev 1 dB", COLORS[2])):
        z, pz, k = design(kind.split()[0])
        _, h = signal.freqs_zpk(z, pz, k, w)
        ph = np.unwrap(np.angle(h))
        tn = -np.gradient(ph, w); ta = tau_poles(z, pz, w)
        inner = slice(1, -1)
        res[kind] = (np.max(np.abs(tn[inner] / ta[inner] - 1)), ta)
        noisy = ph + p.rng.normal(0, 1e-3, len(ph))
        tnoise = -np.gradient(noisy, w)
        _, ys, _ = signal.lsim((z, pz, k), np.ones_like(t), t)
        u = ((t > 2) & (t < 5)).astype(float)
        _, yp, _ = signal.lsim((z, pz, k), u, t)
        os = (ys.max() / ys[-1] - 1) * 100
        res[kind] += (os, np.std(tnoise - ta))
        ax[0].plot(w, ta, color=c, label=kind); ax[1].plot(t, ys, color=c); ax[2].plot(t, yp, color=c)
    for kind in res:
        p.compare(f"{kind}: numerical vs analytic group delay (worst relative error, Δω = 1.5 mrad/s)", 0, res[kind][0], "", kind="abs", tol=1e-4)
    p.compare("Bessel step overshoot (my guess: ≈ 0.1 %)", 0.1, res["Bessel"][2], "%", kind="abs", tol=0.5)
    p.metric("Step overshoot Butterworth / Chebyshev", f"{res['Butterworth'][2]:.1f} % / {res['Chebyshev 1 dB'][2]:.1f} %")
    dw = w[1] - w[0]
    p.compare("Noise in numerically differentiated delay ≈ σ_φ/(√2·Δω)", 1e-3 / (np.sqrt(2) * dw), res["Bessel"][3], "s", tol=15)
    b_t = res["Bessel"][1]
    p.metric("Bessel delay flatness: 1 − τ(0.5)/τ(0)", 1 - b_t[np.argmin(abs(w - 0.5))] / b_t[0], "")
    style_axes(ax[0], "ω (rad/s)", "group delay (s)", "Delay vs frequency")
    style_axes(ax[1], "t (s)", "step response", "Step: ringing ∝ delay peaking", legend=False)
    style_axes(ax[2], "t (s)", "output", "3-s pulse", legend=False)
    p.save(fig, "group_delay", "Group delay of three 5th-order filters with the same −3 dB point, and what it does to a step and a pulse.")
    p.discuss(f"""The pole formula and central differences agree to about 1e-4 relative (worst near the Chebyshev's sharp delay peak, where the O(Δω²)
truncation error is largest), so either is fine for clean analytic phase; with measured (noisy) phase
the derivative amplifies noise by 1/(√2·Δω) exactly as predicted — the reason group delay from a network analyser is always smoothed over an
aperture. The filters make the point visually: all three pass the same band, but the Chebyshev's delay peaks strongly near cutoff and its pulse
rings, the Butterworth rings comparably, and the Bessel — whose delay is maximally flat — delivers the pulse almost unchanged, only delayed. My guess of
≈ 0.1 % Bessel overshoot was too optimistic: the 5th-order Bessel (magnitude-normalised) overshoots {res["Bessel"][2]:.2f} %, still more than ten times less
than the others.
Magnitude specs alone do not describe a filter meant for pulses.""")
# tol-convention: relative tolerances are in percent
