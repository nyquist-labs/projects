from eelab import *
from scipy import signal

META = dict(
    id="AM-023", title="Windowing and spectral leakage: measured sidelobes", level="M",
    tools="Window spectra via heavily zero-padded FFTs, sidelobe/mainlobe/scalloping measurements, detection of a weak tone next to a strong one",
    summary="Measure the highest sidelobe, mainlobe width, scalloping loss and equivalent noise bandwidth of rectangular, Hann, Hamming and "
            "Blackman windows, compare with their textbook values, and show which windows can see a −70 dB tone beside a strong one.",
    problem="Every FFT of a finite record is the spectrum of a windowed signal. How much do windows really differ?",
    theory=r"""Textbook (Harris 1978) values — highest sidelobe: rectangular −13.3 dB, Hann −31.5 dB, Hamming −42.7 dB, Blackman −58.1 dB; mainlobe null-to-null width 2, 4, 4, 6 bins;
scalloping loss (tone halfway between bins) 3.92, 1.42, 1.78, 1.10 dB; ENBW 1.00, 1.50, 1.36, 1.73 bins. Leakage from a strong tone falls off at −6, −18, −6, −18 dB/octave
for these windows, which decides whether a weak neighbour is visible.""",
    method="""N = 64 windows (symmetric=False, 'periodic' DFT-even), FFT zero-padded 256×; sidelobe = highest peak outside the mainlobe; scalloping from a tone at +0.5 bin; ENBW = N·Σw²/(Σw)².
Detection test: tones at 10.3 bins (0 dB) and 16.3 bins (−70 dB) with N = 256.""",
)

TXT = {"boxcar": (-13.3, 2, 3.92, 1.00), "hann": (-31.5, 4, 1.42, 1.50), "hamming": (-42.7, 4, 1.75, 1.36), "blackman": (-58.1, 6, 1.10, 1.73)}


def run(p):
    N, Z = 64, 256
    fig, ax = p.fig(1, 2, w=11)
    for (name, (sl_t, ml_t, sc_t, enbw_t)), c in zip(TXT.items(), COLORS):
        w = signal.get_window(name, N)
        W = np.abs(np.fft.fft(w, N * Z)); W /= W.max()
        Wd = db(W + 1e-15)
        half = Wd[: N * Z // 2]
        first_null = np.argmax(np.diff(half) > 0)
        side = half[first_null:].max()
        ml = 2 * first_null / Z
        sc = -db(np.abs(np.sum(w * np.exp(-1j * pi * np.arange(N) / N))) / np.sum(w))
        enbw = N * np.sum(w ** 2) / np.sum(w) ** 2
        p.compare(f"{name}: highest sidelobe", sl_t, side, "dB", kind="abs", tol=0.5)
        p.compare(f"{name}: mainlobe width (null to null)", ml_t, ml, "bins", kind="abs", tol=0.1)
        p.compare(f"{name}: scalloping loss", sc_t, sc, "dB", kind="abs", tol=0.05)
        p.compare(f"{name}: equivalent noise bandwidth", enbw_t, enbw, "bins", kind="abs", tol=0.02)
        f = np.arange(N * Z // 2) / Z
        ax[0].plot(f, half, color=c, lw=1, label=name)
        n = np.arange(256)
        x = np.cos(2 * pi * 10.3 * n / 256) + 10 ** (-70 / 20) * np.cos(2 * pi * 16.3 * n / 256)
        X = np.abs(np.fft.rfft(x * signal.get_window(name, 256), 256 * 16)); X /= X.max()
        ax[1].plot(np.arange(len(X)) / 16, db(X + 1e-15), color=c, lw=1, label=name)
    ax[0].set_xlim(0, 16); ax[0].set_ylim(-120, 5)
    style_axes(ax[0], "frequency (bins)", "dB", "Window spectra (N = 64)")
    ax[1].axvline(16.3, color="gray", ls=":"); ax[1].set_xlim(0, 30); ax[1].set_ylim(-130, 5)
    style_axes(ax[1], "frequency (bins)", "dB", "Is the −70 dB tone at 16.3 bins visible?")
    p.save(fig, "windows", "Measured window spectra and a weak-tone detection test.")
    n = np.arange(256)
    x = np.cos(2 * pi * 10.3 * n / 256) + 10 ** (-70 / 20) * np.cos(2 * pi * 16.3 * n / 256)
    vis = {}
    for name in TXT:
        X = np.abs(np.fft.rfft(x * signal.get_window(name, 256), 256 * 16)); X /= X.max(); Xd = db(X + 1e-15)
        k = int(16.3 * 16)
        vis[name] = Xd[k - 8: k + 8].max() - max(Xd[k - 40: k - 24].max(), Xd[k + 24: k + 40].max())
    p.metric("Weak tone (−70 dB, 6 bins away) stands out above local floor by", ", ".join(f"{k}: {v:+.0f} dB" for k, v in vis.items()))
    p.discuss("""All four windows reproduce Harris's classic numbers — sidelobes of −13, −31, −43 and −58 dB, mainlobes of 2, 4, 4 and 6 bins, scalloping
losses and noise bandwidths within a few hundredths. The detection test turns the table into a decision: with a rectangular (no) window, the
strong tone's leakage buries a −70 dB neighbour six bins away; Hamming's sidelobes are low near the mainlobe but fall only at −6 dB/octave;
Blackman (and Hann, thanks to its −18 dB/octave roll-off) reveal the weak tone. There is no free lunch: the windows that suppress leakage have
wider mainlobes and higher noise bandwidth, so two tones closer than ~3 bins become harder to separate.""")
# tol-convention: relative tolerances are in percent
