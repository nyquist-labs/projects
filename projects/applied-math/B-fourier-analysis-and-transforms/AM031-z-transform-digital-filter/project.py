from eelab import *
from scipy import signal

META = dict(
    id="AM-031", title="Designing in the z-plane: pole radius and decay", level="M",
    tools="Two-pole digital resonator placed directly in the z-plane, impulse-response envelope fitting, −3 dB bandwidth measurement",
    summary="Place a pole pair at r·e^{±jθ} to build a digital resonator, predict its ringing frequency, decay time and bandwidth from r and θ, "
            "and measure all three from the impulse and frequency responses for pole radii from 0.8 to 0.999.",
    problem="In the z-plane, what does moving a pole toward the unit circle do — quantitatively?",
    theory=r"""Poles $re^{\pm jθ}$: $h[n]\propto r^n\sin((n+1)θ)$, so the envelope decays as $r^n$ — time constant $n_τ = -1/\ln r ≈ 1/(1-r)$ samples, oscillation at $f=θf_s/2π$. Near the circle the
−3 dB bandwidth is $Δf ≈ (1-r)f_s/π$ (the pole's distance to the circle sets it, just as Re s does in the s-plane). The mapping $z=e^{sT}$ makes r ↔ e^{σT}.""",
    method="""fs = 8 kHz, θ for 1 kHz; r ∈ {0.8, 0.9, 0.95, 0.99, 0.995, 0.999}. Envelope rate from peaks of |h[n]| (log-linear fit); bandwidth from a 2¹⁸-point frequency response.""",
)


def run(p):
    fs = 8000; f0 = 1000; th = 2 * pi * f0 / fs
    rows = []
    for r in (0.8, 0.9, 0.95, 0.99, 0.995, 0.999):
        a = [1, -2 * r * np.cos(th), r * r]
        n = np.arange(int(20 / (1 - r)))
        h = signal.lfilter([1], a, np.r_[1, np.zeros(len(n) - 1)])
        pk, _ = signal.find_peaks(np.abs(h))
        slope = np.polyfit(pk, np.log(np.abs(h[pk])), 1)[0]
        w, H = signal.freqz([1], a, worN=2 ** 18, fs=fs)
        M = np.abs(H); k = np.argmax(M); half = M[k] / np.sqrt(2)
        lo = w[np.flatnonzero(M[:k] < half)[-1]]; hi = w[k + np.flatnonzero(M[k:] < half)[0]]
        zc = np.flatnonzero(np.diff(np.sign(h)) != 0)
        fosc = fs / (2 * np.mean(np.diff(zc)))
        rows.append((r, slope, np.log(r), hi - lo, (1 - r) * fs / pi, fosc, w[k]))
    for r, sl, pr, bw, bwp, fo, fpk in rows:
        p.compare(f"r = {r}: envelope decay per sample = ln r", pr, sl, "", tol=1)
    for r, sl, pr, bw, bwp, fo, fpk in rows:
        if r >= 0.95:
            p.compare(f"r = {r}: −3 dB bandwidth ≈ (1−r)·fs/π", bwp, bw, "Hz", tol=3)
    p.compare("Ringing frequency (r = 0.99) = θ·fs/2π", f0, rows[3][5], "Hz", tol=0.5)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    th_c = np.linspace(0, 2 * pi, 300); ax[0].plot(np.cos(th_c), np.sin(th_c), color="gray", lw=1)
    for (r, *_), c in zip(rows, COLORS):
        ax[0].plot([r * np.cos(th)] * 2, [r * np.sin(th), -r * np.sin(th)], "x", color=c, ms=9, mew=2, label=f"r = {r}")
    ax[0].set_aspect("equal")
    style_axes(ax[0], "Re z", "Im z", "Pole pairs")
    for (r, *_), c in zip(rows[1:4], COLORS[1:4]):
        a = [1, -2 * r * np.cos(th), r * r]; h = signal.lfilter([1], a, np.r_[1, np.zeros(399)])
        ax[1].plot(h / np.abs(h).max(), color=c, lw=.8, label=f"r = {r}")
    style_axes(ax[1], "n (samples)", "h[n] (normalised)", "Closer to the circle: longer ringing")
    rr = np.array([x[0] for x in rows]); bw = np.array([x[3] for x in rows])
    ax[2].loglog(1 - rr, bw, "o", color=C_MEAS, label="measured"); ax[2].loglog(1 - rr, (1 - rr) * fs / pi, "--", color=C_PRED, label="(1−r)fs/π")
    style_axes(ax[2], "1 − r", "−3 dB bandwidth (Hz)", "Bandwidth ∝ distance to the circle")
    p.save(fig, "resonator", "Pole positions, impulse responses and bandwidth of the digital resonator.")
    p.discuss("""The impulse-response envelope decays by exactly ln r per sample and the ringing sits at θ·fs/2π, so a pole's radius and angle directly encode
decay and frequency — the z-plane analogue of Re s and Im s. The bandwidth approximation (1−r)fs/π becomes accurate as the pole approaches
the unit circle (within 1–2 % for r ≥ 0.99) and overestimates for r = 0.95, where the two poles' skirts overlap. This is the design rule used for
notch and resonator filters in audio and communications: pick θ for frequency, pick 1−r for bandwidth.""")
# tol-convention: relative tolerances are in percent
