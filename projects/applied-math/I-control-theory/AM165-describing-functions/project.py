from eelab import *
from eelab.control import zoh
from scipy import signal
from scipy.optimize import brentq

META = dict(
    id="AM-165", title="Describing functions: predicting limit cycles in nonlinear loops", level="H",
    tools="Describing functions of the ideal relay, relay with hysteresis and saturation; harmonic-balance solution G(jω)N(a) = −1; time-domain simulation with exact plant stepping; measured amplitude and frequency; harmonic content at the nonlinearity input",
    summary="Replace a nonlinearity by its amplitude-dependent gain for sinusoids and solve for the oscillation that sustains itself. Compare the "
            "predicted amplitude and frequency of limit cycles with simulation for three nonlinearities, and tie the prediction error to how well the plant filters harmonics.",
    problem="A loop with a relay or a saturating amplifier oscillates. Linear theory cannot say at what amplitude — what can?",
    theory=r"""Assume the input to the nonlinearity is $a\sin ωt$ and keep only the fundamental of its output: gain $N(a)$. A limit cycle needs $G(jω)=-1/N(a)$. Plant $G=\frac{K}{s(s+1)(s+2)}$: phase −180° at $ω=\sqrt2$, where $|G|=K/6$.
**Relay** ±M: $N=\frac{4M}{πa}$ ⇒ $a=\frac{2MK}{3π}$, ω = √2. **Relay with hysteresis** h: $-1/N=-\frac{π}{4M}\left(\sqrt{a^2-h^2}+jh\right)$ ⇒ $\mathrm{Im}\,G(jω)=-\frac{πh}{4M}$ fixes ω (lower than √2), then a. **Saturation** (unit slope, limit 1):
$N=\frac2π\left(\arcsin\frac1a+\frac1a\sqrt{1-\frac1{a^2}}\right)$ for a > 1; a limit cycle exists only if K > 6, with $N(a)=6/K$. Accuracy rests on the plant attenuating the 3rd harmonic.""",
    method="""Simulation: exact zero-order-hold stepping (0.5 ms) with the nonlinearity evaluated each step, 150 s, measurements over the last 40 s (amplitude = half peak-to-peak of the nonlinearity input, frequency from zero crossings).
Cases: relay M = 1, K = 3; hysteresis h = 0.2; saturation with K = 9 and K = 5; a second-order plant 2/(s(s+1)) with the hysteresis relay. Third-harmonic ratio from an FFT.""",
)


def simulate(K, nl, t_end=150.0, dt=5e-4, x0=0.3):
    A, B, C, _ = signal.tf2ss([K], [1, 3, 2, 0]); Ad, Bd = zoh(A, B, dt); Bd = Bd[:, 0]; C = C[0]
    n = int(t_end / dt); x = np.linalg.lstsq(C[None], [x0], rcond=None)[0]; e = np.zeros(n); state = 1.0
    for k in range(n):
        e[k] = -(C @ x)                                       # input to the nonlinearity (reference = 0)
        u, state = nl(e[k], state)
        x = Ad @ x + Bd * u
    return np.arange(n) * dt, e


def measure(t, e, tail=40.0):
    m = t > t[-1] - tail; ee = e[m]; tt = t[m]
    amp = (ee.max() - ee.min()) / 2
    zc = np.flatnonzero((ee[:-1] < 0) & (ee[1:] >= 0))
    tz = tt[zc] - ee[zc] * (tt[zc + 1] - tt[zc]) / (ee[zc + 1] - ee[zc])
    w = 2 * pi / np.mean(np.diff(tz)) if len(tz) > 2 else np.nan
    return amp, w


def run(p):
    Gj = lambda w, K: K / ((1j * w) * (1j * w + 1) * (1j * w + 2))
    relay = lambda e, s: (1.0 if e >= 0 else -1.0, s)
    K = 3.0; t, e = simulate(K, relay); amp, w = measure(t, e)
    p.compare("Ideal relay: limit-cycle frequency √2", np.sqrt(2), w, "rad/s", tol=4)
    p.compare("Ideal relay: amplitude 2MK/(3π)", 2 * K / (3 * pi), amp, "", tol=6)
    seg = e[t > t[-1] - 40]; S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); k1 = np.argmax(S)
    h3 = S[3 * k1 - 3: 3 * k1 + 4].max() / S[k1]
    pred3 = (1 / 3) * abs(Gj(3 * np.sqrt(2), K)) / abs(Gj(np.sqrt(2), K))
    p.compare("Third harmonic at the relay input relative to the fundamental: ⅓·|G(3jω)|/|G(jω)|", pred3, h3, "", tol=15)
    rel_trace = (t, e)
    h = 0.2

    def hyst(e_, s):
        s = 1.0 if e_ > h else (-1.0 if e_ < -h else s)
        return s, s
    wh = brentq(lambda x: np.imag(Gj(x, K)) + pi * h / 4, 0.3, np.sqrt(2) - 1e-6)
    ah = np.sqrt((4 * abs(np.real(Gj(wh, K))) / pi) ** 2 + h ** 2)
    t2, e2 = simulate(K, hyst); amp2, w2 = measure(t2, e2)
    p.compare("Relay with hysteresis: frequency from Im G(jω) = −πh/4M", wh, w2, "rad/s", tol=3)
    p.compare("Relay with hysteresis: amplitude", ah, amp2, "", tol=6)
    sat = lambda e_, s: (float(np.clip(e_, -1, 1)), s)
    Nsat = lambda a: 2 / pi * (np.arcsin(1 / a) + np.sqrt(1 - 1 / a ** 2) / a)
    K9 = 9.0; a9 = brentq(lambda a: Nsat(a) - 6 / K9, 1.0001, 50)
    t3, e3 = simulate(K9, sat, x0=0.5); amp3, w3 = measure(t3, e3)
    p.compare("Saturation, K = 9 (> 6): amplitude from N(a) = 6/K", a9, amp3, "", tol=6)
    p.compare("Saturation, K = 9: frequency √2", np.sqrt(2), w3, "rad/s", tol=2)
    t4, e4 = simulate(5.0, sat, x0=3.0); amp4, _ = measure(t4, e4)
    early = (np.max(e4[t4 < 15]) - np.min(e4[t4 < 15])) / 2
    p.compare("Saturation, K = 5 (< 6): no limit cycle — the oscillation dies out (amplitude after 110 s below 1 % of the initial swing; 1 = yes)", 1, int(amp4 < 0.01 * early), "", kind="abs")
    p.metric("… amplitude in the first 15 s / last 40 s", f"{early:.2f} / {amp4:.4f}")
    # a plant that filters harmonics poorly: K/(s(s+1)) with hysteresis relay needs phase from hysteresis only
    A2, B2, C2, _ = signal.tf2ss([2.0], [1, 1, 0]); Ad, Bd = zoh(A2, B2, 5e-4); x = np.array([0.0, 0.2]); ev = []; s = 1.0
    for _ in range(int(80 / 5e-4)):
        err = -(C2[0] @ x); s = 1.0 if err > h else (-1.0 if err < -h else s); ev.append(err); x = Ad @ x + Bd[:, 0] * s
    ev = np.array(ev); tt = np.arange(len(ev)) * 5e-4; ampl, wl = measure(tt, ev, tail=30)
    G2 = lambda w_: 2.0 / ((1j * w_) * (1j * w_ + 1))
    wl_p = brentq(lambda x_: np.imag(G2(x_)) + pi * h / 4, 0.2, 50); al_p = np.sqrt((4 * abs(np.real(G2(wl_p))) / pi) ** 2 + h ** 2)
    seg2 = ev[tt > tt[-1] - 30]; S2 = np.abs(np.fft.rfft(seg2 * np.hanning(len(seg2)))); k2 = np.argmax(S2); h3b = S2[3 * k2 - 3: 3 * k2 + 4].max() / S2[k2]
    p.compare("Second-order plant 2/(s(s+1)) with the hysteresis relay: limit-cycle frequency", wl_p, wl, "rad/s", tol=4)
    p.compare("… and amplitude", al_p, ampl, "", tol=6)
    p.metric("Third-harmonic content at the nonlinearity input: third-order plant / second-order plant", f"{h3 * 100:.1f} % / {h3b * 100:.1f} %")
    fig, ax = p.fig(1, 2, w=11)
    wv = np.logspace(-0.7, 1, 400); Gv = Gj(wv, K)
    ax[0].plot(Gv.real, Gv.imag, color=C_MEAS, label="G(jω), K = 3")
    av = np.linspace(0.01, 3, 200); ax[0].plot(-pi * av / 4, 0 * av, color=C_PRED, label="−1/N relay")
    avh = np.linspace(h, 3, 200); ax[0].plot(-pi / 4 * np.sqrt(avh ** 2 - h ** 2), -pi * h / 4 + 0 * avh, color=COLORS[2], label="−1/N hysteresis")
    ax[0].set_xlim(-1.6, 0.2); ax[0].set_ylim(-1, 0.4)
    style_axes(ax[0], "Re", "Im", "Limit cycle = intersection of G(jω) and −1/N(a)")
    m = rel_trace[0] > 140
    ax[1].plot(rel_trace[0][m], rel_trace[1][m], color=C_MEAS, label="relay input (simulated)")
    ax[1].plot(rel_trace[0][m], 2 * K / (3 * pi) * np.sin(np.sqrt(2) * (rel_trace[0][m] - rel_trace[0][m][np.argmax((rel_trace[1][m][:-1] < 0) & (rel_trace[1][m][1:] >= 0))])), "--", color=C_PRED, label="describing-function prediction")
    style_axes(ax[1], "time (s)", "e(t)", "Predicted vs simulated limit cycle")
    p.save(fig, "describing_function", "Harmonic-balance construction on the Nyquist plane and the simulated relay limit cycle against its prediction.")
    p.discuss(f"""Harmonic balance predicts all three oscillations to within a few percent: the relay loop cycles at {w:.3f} rad/s with amplitude {amp:.3f}
(predicted 1.414 and {2 * K / (3 * pi):.3f}); hysteresis lowers the frequency exactly as the shifted −1/N locus says; and the saturating loop oscillates only when
the linear gain exceeds the gain margin of 6, at the amplitude where the *effective* gain has dropped back to 6/K. With K = 5 the same loop simply
settles. The method is approximate because it ignores harmonics: here the third harmonic at the relay input is {h3 * 100:.1f} % of the fundamental
(the third-order plant attenuates it), and the predictions are off by a similar few percent. I expected a second-order plant, which filters
harmonics less ({h3b * 100:.1f} % third harmonic), to be predicted visibly worse; it was not — {abs(wl - wl_p) / wl * 100:.1f} % in frequency and {abs(ampl - al_p) / ampl * 100:.1f} % in
amplitude. The harmonic content sets the *scale* of the describing-function error, not a strict ordering: how the neglected harmonics shift the
switching instants also matters. For exact answers with relays, Tsypkin's method sums all harmonics.""")
# tol-convention: relative tolerances are in percent
