from eelab import *

META = dict(
    id="SL-081", title="Delay-and-sum beamforming with a uniform linear array", level="H",
    tools="NumPy array-factor computation + time-domain simulation of plane waves",
    summary="Steer an 8-element λ/2 array electronically; measure beamwidth, sidelobe level, steering "
            "accuracy and array gain against closed-form array theory, including grating lobes at d = λ.",
    problem="How can eight fixed antennas (or microphones) listen in one direction and ignore others, and "
            "what limits how sharp that 'beam' can be?",
    theory=r"""Array factor $AF(\theta)=\frac1N\sum_n e^{jkd n(\sin\theta-\sin\theta_0)}$, $|AF|=\left|\frac{\sin(N\psi/2)}{N\sin(\psi/2)}\right|$ with
$\psi=kd(\sin\theta-\sin\theta_0)$. Half-power beamwidth ≈ $0.886\,\lambda/(Nd\cos\theta_0)$ rad (= 12.8° broadside for N = 8, d = λ/2),
first sidelobe −13.26 dB, array gain for white noise = N (9.03 dB). Grating lobes appear when $d\ge\lambda/(1+|\sin\theta_0|)$.""",
    method="""N = 8, d = λ/2 at 1 kHz acoustic (λ = 34.3 cm). Pattern computed and also measured by time-domain simulation: plane waves
from −90°…90°, each channel delayed and summed with steering to 0° and 30°; output power vs angle. Array gain
measured with independent noise per element. Grating lobes: d = λ, steer 30°.""",
)


def pattern(N, d_l, th0, th):
    psi = 2 * pi * d_l * (np.sin(th) - np.sin(th0))
    return np.abs(np.exp(1j * np.outer(psi, np.arange(N))).sum(1)) / N


def run(p):
    N, c, f = 8, 343.0, 1000.0
    lam = c / f
    th = np.radians(np.linspace(-90, 90, 3601))
    fs = 48000
    t = np.arange(4800) / fs
    fig, ax = p.fig()
    for i, th0d in enumerate([0, 30]):
        th0 = np.radians(th0d)
        af = pattern(N, 0.5, th0, th)
        g = db(af)
        k0 = np.argmax(af)
        lo = find_crossing(np.degrees(th[:k0 + 1]), g[:k0 + 1], -3.0103, logx=False)
        hi = find_crossing(np.degrees(th[k0:]), g[k0:], -3.0103, logx=False)
        bw_pred = np.degrees(0.886 * 2 / (N * np.cos(th0)))
        p.compare(f"Steer {th0d}°: half-power beamwidth", bw_pred, hi - lo, "°", tol=3)
        p.compare(f"Steer {th0d}°: beam direction", th0d, np.degrees(th[k0]), "°", kind="abs")
        # time-domain simulation of delay-and-sum
        angs = np.radians(np.linspace(-90, 90, 181))
        pw = []
        for a in angs:
            ch = [np.sin(2 * pi * f * (t - n * lam / 2 * np.sin(a) / c)) for n in range(N)]
            y = sum(np.sin(2 * pi * f * (t - n * lam / 2 * np.sin(a) / c + n * lam / 2 * np.sin(th0) / c)) for n in range(N)) / N
            pw.append(np.mean(y**2) / 0.5)
        pw = 10 * np.log10(np.array(pw) + 1e-12)
        ax.plot(np.degrees(th), g, color=COLORS[i], label=f"theory, steer {th0d}°")
        ax.plot(np.degrees(angs), pw, "o", ms=3, color=COLORS[i], label=f"time-domain sim, steer {th0d}°")
        if th0d == 0:
            side = g[(np.degrees(th) > np.degrees(th[k0]) + 20)].max()
            p.compare("First sidelobe level (broadside)", -13.26, np.max(g[(np.degrees(th) > 15) & (np.degrees(th) < 40)]), "dB", kind="abs")
    ax.set_ylim(-40, 2)
    style_axes(ax, "angle (°)", "array response (dB)", "8-element ULA, d = λ/2")
    p.save(fig, "patterns", "Steering off broadside widens the beam by 1/cos θ₀.")
    snr_in = []
    ys, ns = [], []
    for _ in range(200):
        noise = p.rng.normal(size=(N, len(t)))
        s = np.sin(2 * pi * f * t)
        ys.append(np.mean(s**2)); ns.append(np.mean(noise.mean(0) ** 2))
    gain = 10 * np.log10(np.mean(ys) / np.mean(ns)) - 10 * np.log10(0.5 / 1.0)
    p.compare("Array gain (independent noise per element)", 10 * np.log10(N), gain, "dB", kind="abs")
    afg = db(pattern(N, 1.0, np.radians(30), th))
    peaks = [np.degrees(th[j]) for j in range(1, len(th) - 1) if afg[j] > -0.5 and afg[j] >= afg[j - 1] and afg[j] >= afg[j + 1]]
    pred_grating = np.degrees(np.arcsin(np.sin(np.radians(30)) - 1))
    p.compare("Grating lobe direction (d = λ, steer 30°)", pred_grating, min(peaks), "°", kind="abs")
    fig, ax = p.fig()
    ax.plot(np.degrees(th), db(pattern(N, 0.5, np.radians(30), th)), color=C_MEAS, label="d = λ/2")
    ax.plot(np.degrees(th), afg, color=COLORS[7], label="d = λ (grating lobe!)")
    ax.set_ylim(-40, 2)
    style_axes(ax, "angle (°)", "dB", "Element spacing ≥ λ creates a second full-strength beam")
    p.save(fig, "grating_lobes", "At d = λ the array cannot distinguish 30° from −30°.")
    p.discuss("""Beamwidth, direction, sidelobe level and the 9 dB array gain all match array theory, and the time-domain
delay-and-sum simulation reproduces the analytic pattern point by point. Two design rules fall out: the beam
broadens as 1/cos θ₀ when steered, and spacing must stay below λ/(1 + |sin θ₀|) or a grating lobe appears —
a full-strength copy of the main beam pointing somewhere else, which no amount of signal processing can undo.""")
