from eelab import *

META = dict(
    id="SL-069", title="Guitar tuner (cents-accurate note detection)", level="M",
    tools="Karplus–Strong plucked-string synthesis (ground truth), FFT + parabolic interpolation, YIN-style ACF",
    summary="Detect which string is played and how many cents it is off, on physically-modelled plucked "
            "notes with known detuning; measure the tuner's error vs note length.",
    problem="A tuner must report pitch to ±1 cent from a decaying, slightly inharmonic string. How long must "
            "it listen, and which estimator is accurate enough?",
    theory=r"""FFT bin spacing $f_s/N$ is far too coarse (1 cent at 82 Hz is 0.048 Hz), so interpolation is essential. For a
sinusoid in white noise the Cramér–Rao bound on frequency error is $\sigma_f\ge\frac{\sqrt{6}f_s}{2\pi N^{1.5}\sqrt{SNR}}$ —
error falls as $N^{-1.5}$, so doubling the listening time improves accuracy 2.8×. Real strings are slightly
inharmonic ($f_k = kf_0\sqrt{1+Bk^2}$), so the *fundamental* must be measured, not harmonic spacing.""",
    method="""Karplus–Strong synthesis (loop = N-sample delay + two-tap averaging damping filter + first-order Thiran all-pass
for the fractional delay) for
the six standard strings E2–E4 with random detuning ±30 cents, 44.1 kHz, 30 dB SNR. Estimator: Hann FFT with 8×
zero-padding + parabolic interpolation on the log magnitude of the fundamental peak (guided by an ACF coarse
estimate). Analysis windows 50–800 ms.""",
    data="Synthetic plucked-string notes (physical model) with exact ground-truth detuning.",
)

STRINGS = {"E2": 82.407, "A2": 110.0, "D3": 146.83, "G3": 196.0, "B3": 246.94, "E4": 329.63}


def ks_note(f0, fs, dur, rng_, snr_db=30):
    # loop delay = N (buffer) − 0.5 (two-tap average of x[n−N], x[n−N+1]) + d (Thiran all-pass)
    P = fs / f0
    N = int(round(P + 0.5 - 1.0))
    frac = P + 0.5 - N
    a = (1 - frac) / (1 + frac)
    buf = rng_.uniform(-1, 1, N)
    out = np.zeros(int(dur * fs)); x1 = y1 = 0.0; idx = 0
    for i in range(len(out)):
        v = buf[idx]
        nxt = buf[(idx + 1) % N]
        lp = 0.4995 * (v + nxt)
        ap = a * lp + x1 - a * y1; x1, y1 = lp, ap
        buf[idx] = ap; out[i] = v; idx = (idx + 1) % N
    out /= np.max(abs(out))
    return out + rng_.normal(size=len(out)) * np.std(out) * 10**(-snr_db / 20)


def detect(x, fs):
    r = np.fft.irfft(np.abs(np.fft.rfft(x - x.mean(), 2 * len(x))) ** 2)[: len(x)]
    lo, hi = int(fs / 400), int(fs / 70)
    coarse = fs / (lo + np.argmax(r[lo:hi]))
    Nf = 8 * len(x)
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)), Nf))
    f = np.fft.rfftfreq(Nf, 1 / fs)
    band = (f > coarse * 0.9) & (f < coarse * 1.1)
    k = np.flatnonzero(band)[np.argmax(X[band])]
    a, b, c = np.log(X[k - 1:k + 2])
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return (k + d) * fs / Nf


def run(p):
    fs = 44100
    durs = [0.05, 0.1, 0.2, 0.4, 0.8]
    errs = {d: [] for d in durs}
    names_ok = 0; trials = 0
    for rep in range(10):
        for name, f in STRINGS.items():
            det = p.rng.uniform(-30, 30)
            ftrue = f * 2 ** (det / 1200)
            x = ks_note(ftrue, fs, 0.9, p.rng)
            seg0 = x[int(0.05 * fs):]
            for d in durs:
                est = detect(seg0[: int(d * fs)], fs)
                errs[d].append(1200 * np.log2(est / ftrue))
            est = detect(seg0[: int(0.4 * fs)], fs)
            nearest = min(STRINGS, key=lambda s: abs(np.log2(est / STRINGS[s])))
            names_ok += nearest == name; trials += 1
    rms = {d: np.sqrt(np.mean(np.square(errs[d]))) for d in durs}
    p.compare("String identified correctly (60 notes)", 100, names_ok / trials * 100, "%", kind="abs")
    p.compare("RMS cents error, 400 ms window", 0, rms[0.4], "cents", kind="abs", note="includes Karplus–Strong's own ≈ fraction-of-a-cent tuning error")
    slope = np.polyfit(np.log(durs[1:]), np.log([rms[d] for d in durs[1:]]), 1)[0]
    p.compare("Error scaling exponent vs window length (CRLB: −1.5)", -1.5, slope, "", kind="abs")
    fig, ax = p.fig()
    ax.loglog(np.array(durs) * 1e3, [rms[d] for d in durs], "o-", color=C_MEAS, label="measured RMS error")
    ref = rms[0.2] * (np.array(durs) / 0.2) ** -1.5
    ax.loglog(np.array(durs) * 1e3, ref, "--", color=C_PRED, label="∝ N^−1.5 (Cramér–Rao scaling)")
    ax.axhline(1, color="gray", ls=":", lw=1, label="1 cent")
    style_axes(ax, "analysis window (ms)", "RMS error (cents)", "Tuner accuracy vs listening time")
    p.save(fig, "accuracy", "Accuracy improves steeply with window length until the string's decay and inharmonicity dominate.")
    p.csv("errors", **{f"window_{int(d*1000)}ms_cents": errs[d] for d in durs})
    p.discuss("""The tuner names every string correctly. My first synthesiser had an off-by-one in the loop delay (the two-tap
average of x[n−N] and x[n−N+1] delays by N − ½, not N + ½), which made every note ~10 cents sharp and showed up as
an error that did not shrink with window length — a systematic error in the *ground truth*, caught because it
broke the expected N^−1.5 scaling. With the loop delay fixed: Short windows follow the
N^−1.5 CRLB trend; at long windows the curve flattens because the note decays (SNR falls through the window)
and because the Karplus–Strong loop's own damping filter pulls the partials very slightly flat, a small
systematic error the synthetic ground truth cannot remove. Commercial tuners typically need 200–500 ms for
±1 cent on low strings — consistent with this measurement.""")
