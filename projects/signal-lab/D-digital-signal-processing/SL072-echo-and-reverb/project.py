from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="SL-072", title="Echo and Schroeder reverb from delay lines", level="E",
    tools="Own comb/all-pass delay-line network, impulse-response RT60 measurement (Schroeder integration)",
    summary="Build a single echo and a Schroeder reverberator (4 parallel combs + 2 series all-passes), "
            "predict the reverberation time from the loop gains and measure RT60 from the impulse response.",
    problem="How do a few delay lines make a dry recording sound like a hall, and can the hall's decay time "
            "be designed exactly?",
    theory=r"""Feedback comb with delay D samples and gain g: each round trip multiplies by g, so the level falls by 60 dB after
$n=-3/\log_{10}g$ trips: $RT_{60}=\frac{-3D}{f_s\log_{10}g}$. Choosing $g_i=10^{-3D_i/(f_sRT_{60})}$ makes all combs decay
together. All-passes (|H| = 1) add echo density without colouring the spectrum. A single echo
$y=x+a\,x[n-D]$ has a comb-shaped magnitude response with notches every $f_s/D$.""",
    method="""f_s of the speech file. Combs 29.7, 37.1, 41.1, 43.7 ms; all-passes 5.0 ms (g = 0.7) and 1.7 ms (g = 0.7). Target
RT60 = 0.8, 1.5, 2.5 s. RT60 measured from the Schroeder backward-integrated energy decay curve (fit between −5 and
−35 dB, extrapolated to −60 dB). Applied to the real 'hello' recording.""",
    data="Real public-domain speech for the audio demo; impulse responses computed exactly.",
)


def comb(x, D, g):
    y = np.zeros(len(x)); buf = np.zeros(D); i = 0
    for n in range(len(x)):
        out = buf[i]; y[n] = out; buf[i] = x[n] + g * out; i = (i + 1) % D
    return y


def allpass(x, D, g):
    b = np.zeros(D + 1); b[0] = -g; b[-1] = 1
    a = np.zeros(D + 1); a[0] = 1; a[-1] = -g
    return signal.lfilter(b, a, x)


def reverb(x, fs, rt):
    Ds = [int(fs * t) for t in (0.0297, 0.0371, 0.0411, 0.0437)]
    y = sum(comb(x, D, 10 ** (-3 * D / (fs * rt))) for D in Ds) / 4
    for D in (int(fs * 0.005), int(fs * 0.0017)):
        y = allpass(y, D, 0.7)
    return y


def rt60(h, fs):
    e = np.cumsum(h[::-1] ** 2)[::-1]
    edc = 10 * np.log10(e / e[0] + 1e-30)
    t = np.arange(len(h)) / fs
    m = (edc < -5) & (edc > -35)
    slope = np.polyfit(t[m], edc[m], 1)[0]
    return -60 / slope, t, edc


def run(p):
    x, fs = speech_hello()
    fs = int(fs)
    fig, ax = p.fig()
    for i, rt in enumerate([0.8, 1.5, 2.5]):
        imp = np.zeros(int(fs * rt * 1.6)); imp[0] = 1
        h = reverb(imp, fs, rt)
        m, t, edc = rt60(h, fs)
        p.compare(f"RT60 (design {rt} s)", rt, m, "s", tol=5)
        ax.plot(t, edc, color=COLORS[i], label=f"design RT60 = {rt} s")
    ax.axhline(-60, color="gray", ls=":", lw=1); ax.set_ylim(-80, 2)
    style_axes(ax, "time (s)", "energy decay (dB)", "Schroeder energy-decay curves")
    p.save(fig, "edc", "Backward-integrated impulse-response energy falls linearly in dB; slope sets RT60.")
    D = int(0.25 * fs); a = 0.5
    w, H = signal.freqz(np.r_[1, np.zeros(D - 1), a], worN=4096, fs=fs)
    notch = np.min(db(H)); pk = np.max(db(H))
    p.compare("Single echo: comb peak (1+a)", db(1 + a), pk, "dB", kind="abs")
    p.compare("Single echo: comb notch (1−a)", db(1 - a), notch, "dB", kind="abs")
    y = reverb(np.r_[x, np.zeros(int(1.5 * fs))], fs, 1.5)
    wet = np.r_[x, np.zeros(int(1.5 * fs))] + 0.6 * y
    import soundfile as sf
    sf.write(p.dir / "data" / "hello_reverb_1p5s.wav", (wet / np.max(abs(wet)) * 0.9).astype(np.float32), fs)
    p.files.append(("data/hello_reverb_1p5s.wav", "speech with 1.5 s reverb"))
    fig, ax = p.fig()
    tt = np.arange(len(wet)) / fs
    ax.plot(tt, wet, color=C_MEAS, lw=.4, label="with reverb"); ax.plot(np.arange(len(x)) / fs, x, color="gray", lw=.4, label="dry")
    style_axes(ax, "time (s)", "amplitude", "Real speech with a 1.5 s Schroeder reverb")
    p.save(fig, "speech_reverb", "The reverb tail continues after the dry word ends.")
    p.discuss("""Measured RT60 matches the loop-gain formula within a few percent: the combs were tuned so each decays at
the same rate, and the all-passes, having unit gain, do not change the energy decay. Schroeder's 1962
design is recognisably 'metallic' because four combs give a low echo density — later designs (feedback
delay networks) mix more delay lines through an orthogonal matrix for a smoother tail.""")
