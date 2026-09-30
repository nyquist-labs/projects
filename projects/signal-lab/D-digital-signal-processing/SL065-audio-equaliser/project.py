from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="SL-065", title="Multi-band audio equaliser (peaking biquads)", level="M",
    tools="RBJ Audio-EQ-Cookbook biquads (own implementation), SciPy lfilter, real speech recording",
    summary="A 5-band graphic equaliser built from peaking-EQ biquads; verify each band's centre gain and "
            "bandwidth against the design, then apply it to a real public-domain speech recording and "
            "compare before/after spectra.",
    problem="How does a graphic EQ boost 3 kHz by 6 dB without touching the rest of the spectrum, and "
            "how independent are neighbouring bands?",
    theory=r"""RBJ peaking filter: $A=10^{G/40}$, $\omega_0=2\pi f_0/f_s$, $\alpha=\sin\omega_0/(2Q)$;
$b=[1+\alpha A,\,-2\cos\omega_0,\,1-\alpha A]$, $a=[1+\alpha/A,\,-2\cos\omega_0,\,1-\alpha/A]$.
At $f_0$ the gain is exactly G dB; far away it is 0 dB. Cascaded bands multiply (add in dB), so the total response
≈ sum of the individual dB curves where bands overlap.""",
    method="""Bands 125 Hz, 500 Hz, 1 kHz, 3 kHz, 8 kHz, Q = 1.4, gains {−6, +3, 0, +6, −9} dB at the speech file's sample
rate. Measure each band alone, then the cascade vs the dB-sum prediction. Real audio: 'hello' spoken by a
US-English speaker (Wikimedia Commons, public domain). Output spectra by Welch's method.""",
    data="Real: public-domain speech recording 'En-us-hello.ogg' (Wikimedia Commons).",
)


def peaking(f0, G, Q, fs):
    A = 10 ** (G / 40); w0 = 2 * pi * f0 / fs; al = np.sin(w0) / (2 * Q)
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A]); a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return b / a[0], a / a[0]


def run(p):
    x, fs = speech_hello()
    bands = [(125, -6), (500, 3), (1000, 0), (3000, 6), (8000, -9)]
    Q = 1.4
    f = np.logspace(1.5, np.log10(fs / 2 * 0.98), 800)
    tot = np.ones(len(f), complex); sum_db = np.zeros(len(f))
    fig, ax = p.fig()
    for i, (f0, G) in enumerate(bands):
        b, a = peaking(f0, G, Q, fs)
        _, H = signal.freqz(b, a, worN=f, fs=fs)
        tot *= H; sum_db += db(H)
        p.compare(f"{f0} Hz band: gain at centre", G, db(np.interp(f0, f, np.abs(H))), "dB", kind="abs")
        ax.semilogx(f, db(H), color=COLORS[i], lw=1, ls=":")
    k = np.argmin(abs(f - 3000))
    p.compare("Cascade at 3 kHz vs dB-sum of bands", sum_db[k], db(tot[k]), "dB", kind="abs")
    p.compare("Cascade max deviation from dB-sum (whole band)", 0, np.max(abs(db(tot) - sum_db)), "dB", kind="abs")
    ax.semilogx(f, db(tot), color=C_MEAS, lw=2, label="cascade (5 biquads)")
    style_axes(ax, "frequency (Hz)", "gain (dB)", "5-band peaking EQ (dotted = individual bands)")
    p.save(fig, "eq_response", "Individual band responses and the cascaded equaliser.")
    y = x.copy()
    for f0, G in bands:
        b, a = peaking(f0, G, Q, fs); y = signal.lfilter(b, a, y)
    fw, Px = signal.welch(x, fs, nperseg=1024); _, Py = signal.welch(y, fs, nperseg=1024)
    change = 10 * np.log10(Py[1:] / Px[1:])
    _, Hw = signal.freqz(np.poly1d([1]), 1, worN=fw[1:], fs=fs)
    Htot = np.ones(len(fw) - 1, complex)
    for f0, G in bands:
        b, a = peaking(f0, G, Q, fs); Htot *= signal.freqz(b, a, worN=fw[1:], fs=fs)[1]
    sel = (fw[1:] > 100) & (fw[1:] < 0.9 * fs / 2) & (Px[1:] > Px.max() * 1e-6)
    p.compare("Speech spectrum change vs |H|² (median error)", 0, np.median(change[sel] - db(Htot[sel])), "dB", kind="abs")
    fig, ax = p.fig()
    ax.semilogx(fw[1:], 10 * np.log10(Px[1:]), color="gray", label="original speech")
    ax.semilogx(fw[1:], 10 * np.log10(Py[1:]), color=C_MEAS, label="equalised")
    style_axes(ax, "frequency (Hz)", "PSD (dB)", "Real speech before and after the EQ")
    p.save(fig, "speech_spectra", "The 3 kHz presence boost and the 8 kHz cut are visible in the real recording.")
    import soundfile as sf
    sf.write(p.dir / "data" / "hello_equalised.wav", (y / np.max(abs(y)) * 0.9).astype(np.float32), int(fs))
    p.files.append(("data/hello_equalised.wav", "equalised audio"))
    p.metric("Recording length / sample rate", len(x) / fs, "s", f"{fs:.0f} Hz")
    p.discuss("""Every band hits its gain at f₀ exactly (the RBJ design is exact there). The cascade matches the dB-sum
closely because biquads in series multiply — the only deviation is where neighbouring bands overlap in
phase-sensitive ways (none here, since magnitudes of cascaded filters simply multiply). On the real recording
the measured spectral change equals |H(f)|² wherever the speech has energy; at very high frequency the
original has almost none, so the ratio is noise-dominated.""")
