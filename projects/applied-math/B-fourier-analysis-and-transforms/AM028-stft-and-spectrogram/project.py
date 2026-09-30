from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="AM-028", title="STFT and spectrograms: the resolution trade-off", level="M",
    tools="Own short-time Fourier transform (Hann windows, hop, zero-padding), resolution measurements on a synthetic test signal, real speech recording",
    summary="Implement the STFT, measure its time and frequency resolution on a test signal with clicks and close tones for several window "
            "lengths, confirm that their product is constant, and apply it to a real recording of the word 'hello'.",
    problem="A spectrogram cannot be sharp in both time and frequency. How exactly does the window length trade one for the other?",
    theory=r"""With a Hann window of length T_w, a click smears over ≈ T_w/2 (full width at half maximum of the window's energy, ≈ 0.5 T_w for Hann... measured as FWHM of |x|² envelope) and a tone over a
mainlobe of −6 dB width 2/T_w… so Δt·Δf is a constant ≈ 1 for the half-power widths of Hann, independent of T_w. Voiced speech needs Δf < pitch (~100–200 Hz) to show
harmonics (narrow-band, T_w ≳ 20 ms) or Δt < pitch period to show glottal pulses (wide-band, T_w ≲ 5 ms).""",
    method="""Test signal at 8 kHz: clicks every 50 ms + tones at 1000 and 1060 Hz. Window lengths 4, 8, 16, 32, 64 ms; FWHM of the click in time and of the 1000 Hz line in frequency.
Real data: Wikimedia public-domain recording 'En-us-hello.ogg'.""",
    data="Real: 'En-us-hello.ogg', Wikimedia Commons, public domain.",
)


def stft(x, fs, win_s, hop_s, pad=8):
    n = int(win_s * fs); hop = max(1, int(hop_s * fs)); w = np.hanning(n)
    frames = np.array([x[i:i + n] * w for i in range(0, len(x) - n, hop)])
    S = np.abs(np.fft.rfft(frames, n * pad, axis=1)) ** 2
    t = (np.arange(len(frames)) * hop + n / 2) / fs; f = np.fft.rfftfreq(n * pad, 1 / fs)
    return t, f, S


def fwhm(x, y):
    k = np.argmax(y); half = y[k] / 2
    lo = k
    while lo > 0 and y[lo] > half:
        lo -= 1
    hi = k
    while hi < len(y) - 1 and y[hi] > half:
        hi += 1
    return x[hi] - x[lo]


def run(p):
    fs = 8000; t = np.arange(fs) / fs
    x = 0.3 * np.sin(2 * pi * 1000 * t) + 0.3 * np.sin(2 * pi * 1060 * t)
    x[(np.arange(len(t)) % 400) == 200] += 5.0
    clicks = np.zeros_like(t); clicks[len(t) // 2] = 1.0                 # resolution probes: a lone click and a lone tone
    tone1 = np.sin(2 * pi * 1000 * t)
    rows = []
    for win in (0.004, 0.008, 0.016, 0.032, 0.064):
        tt, f, S = stft(clicks, fs, win, 1 / fs)
        dt = fwhm(tt, S[:, (f > 500) & (f < 3500)].mean(axis=1))
        tt, f, S = stft(tone1, fs, win, win / 2, pad=64)
        sp = S[len(tt) // 2]; fsel = (f > 600) & (f < 1400)
        df = fwhm(f[fsel], sp[fsel])
        rows.append((win, dt, df))
    rows = np.array(rows)
    prod = rows[:, 1] * rows[:, 2]
    p.compare("Δt·Δf (half-power widths) is constant across window lengths: max/min ratio", 1.0, prod.max() / prod.min(), "", tol=25)
    p.metric("Mean Δt·Δf", prod.mean(), "", "Hann window, half-power widths")
    p.compare("Doubling the window doubles Δt (slope of log Δt vs log T_w)", 1.0, np.polyfit(np.log(rows[:, 0]), np.log(rows[:, 1]), 1)[0], "", kind="abs", tol=0.15)
    p.compare("… and halves Δf (slope)", -1.0, np.polyfit(np.log(rows[:, 0]), np.log(rows[:, 2]), 1)[0], "", kind="abs", tol=0.15)
    y, sfs = speech_hello()
    y = y if y.ndim == 1 else y.mean(axis=1)
    fig, ax = p.fig(2, 2, w=11, h=7)
    for a_, win, title in ((ax[0, 0], 0.004, "4 ms window: clicks sharp, tones merged"), (ax[0, 1], 0.064, "64 ms window: tones split, clicks smeared")):
        tt, f, S = stft(x, fs, win, 0.002, pad=4)
        a_.pcolormesh(tt, f, db(np.sqrt(S.T) + 1e-9), shading="auto", cmap="magma", vmin=db(np.sqrt(S.max())) - 60)
        a_.set_ylim(500, 2000); a_.set_title(title, loc="left", fontsize=10); a_.set_xlabel("t (s)"); a_.set_ylabel("f (Hz)")
    for a_, win, title in ((ax[1, 0], 0.004, "'hello', wide-band (4 ms): glottal pulses"), (ax[1, 1], 0.040, "'hello', narrow-band (40 ms): harmonics")):
        tt, f, S = stft(y, sfs, win, 0.001, pad=4)
        a_.pcolormesh(tt, f, db(np.sqrt(S.T) + 1e-9), shading="auto", cmap="magma", vmin=db(np.sqrt(S.max())) - 70)
        a_.set_ylim(0, 4000); a_.set_title(title, loc="left", fontsize=10); a_.set_xlabel("t (s)"); a_.set_ylabel("f (Hz)")
    p.save(fig, "spectrograms", "Short vs long windows on a test signal and on a real spoken 'hello'.")
    p.csv("resolution", window_s=rows[:, 0], dt_s=rows[:, 1], df_hz=rows[:, 2], product=prod)
    p.discuss(f"""Measured on a test signal, the time width of a click grows in proportion to the window length and the frequency width of a tone shrinks in
inverse proportion, keeping Δt·Δf ≈ {prod.mean():.2f} constant — the discrete face of the uncertainty principle (AM-029). The 1000/1060 Hz pair is only
separated by windows long enough that Δf < 60 Hz, at which point the 50 ms clicks blur. On real speech the same choice decides what you see: a
4 ms window resolves individual glottal pulses as vertical striations, a 40 ms window resolves the pitch harmonics as horizontal lines. Neither
spectrogram is 'correct'; they answer different questions.""")
# tol-convention: relative tolerances are in percent
