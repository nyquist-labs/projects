from eelab import *
from scipy import signal

META = dict(
    id="AM-032", title="Bilinear transform and frequency pre-warping", level="H",
    tools="Own zpk bilinear mapping z = (1+sT/2)/(1−sT/2) with gain matching, frequency-warping formula, comparison with scipy.signal.bilinear_zpk",
    summary="Map an analog Butterworth prototype to a digital filter with the bilinear transform, predict exactly how far the cutoff moves without "
            "pre-warping, implement pre-warping, and verify both against the measured digital responses.",
    problem="The bilinear transform keeps stable filters stable — but it squeezes the whole analog frequency axis into [0, fs/2]. Where does a 3 kHz cutoff end up at fs = 8 kHz?",
    theory=r"""With $s=\frac2T\frac{z-1}{z+1}$, the jΩ axis maps onto the unit circle with $Ω=\frac2T\tan\frac{ω}{2}$ (ω = digital rad/sample). An analog cutoff Ω_c therefore lands at
$f_d=\frac{f_s}{π}\arctan\frac{πf_c}{f_s}$ = 2207 Hz for f_c = 3 kHz, f_s = 8 kHz (−26 %). Pre-warping designs the analog prototype at $Ω_c=\frac2T\tan\frac{πf_c}{f_s}$ so the digital cutoff lands exactly on f_c.
Poles map as $z_p=\frac{1+p T/2}{1-p T/2}$; zeros at infinity go to z = −1.""",
    method="""4th-order Butterworth, f_c ∈ {500, 1000, 2000, 3000, 3500} Hz at f_s = 8 kHz, with and without pre-warping. Own mapping vs scipy.signal.bilinear_zpk; −3 dB point measured on a 2¹⁸-point
frequency response.""",
)


def bilinear(z, pz, k, fs):
    T = 1 / fs
    zd = (1 + z * T / 2) / (1 - z * T / 2); pd = (1 + pz * T / 2) / (1 - pz * T / 2)
    zd = np.r_[zd, -np.ones(len(pz) - len(z))]
    # gain: match H(s=0) → H(z=1)
    Ha = k * np.prod(-z) / np.prod(-pz) if len(z) else k / np.prod(-pz)
    Hd = np.prod(1 - zd) / np.prod(1 - pd)
    return zd, pd, np.real(Ha / Hd)


def cutoff(zd, pd, kd, fs):
    w, H = signal.freqz_zpk(zd, pd, kd, worN=2 ** 18, fs=fs)
    return w[np.argmax(db(np.abs(H)) < -3.0103)]


def run(p):
    fs = 8000
    rows = []
    for fc in (500, 1000, 2000, 3000, 3500):
        for warp in (False, True):
            Wc = 2 * fs * np.tan(pi * fc / fs) if warp else 2 * pi * fc
            z, pz, k = signal.butter(4, Wc, analog=True, output="zpk")
            zd, pd, kd = bilinear(z, pz, k, fs)
            zs, ps, ks = signal.bilinear_zpk(z, pz, k, fs)
            diff = max(np.max(np.abs(np.sort_complex(pd) - np.sort_complex(ps))), abs(kd - ks) / ks)
            rows.append((fc, warp, cutoff(zd, pd, kd, fs), diff))
    p.compare("Own bilinear mapping vs scipy.signal.bilinear_zpk (worst pole/gain difference)", 0, max(r[3] for r in rows), "", kind="abs", tol=1e-9)
    for fc, warp, fm, _ in rows:
        if fc in (1000, 3000):
            pred = fc if warp else fs / pi * np.arctan(pi * fc / fs)
            p.compare(f"f_c = {fc} Hz {'with' if warp else 'without'} pre-warping: digital −3 dB point", pred, fm, "Hz", tol=0.2)
    fig, ax = p.fig(1, 2, w=11)
    f = np.linspace(0, 20000, 500)
    ax[0].plot(f, fs / pi * np.arctan(pi * f / fs), color=C_PRED, label="f_d = (fs/π)·arctan(πf/fs)")
    ax[0].plot([r[0] for r in rows if not r[1]], [r[2] for r in rows if not r[1]], "o", color=C_MEAS, label="measured, no pre-warp")
    ax[0].plot(f, f, ":", color="gray"); ax[0].axhline(fs / 2, color="gray", ls="--"); ax[0].set_ylim(0, 4500); ax[0].set_xlim(0, 20000)
    style_axes(ax[0], "analog cutoff (Hz)", "digital cutoff (Hz)", "Frequency warping")
    for warp, c, lab in ((False, COLORS[1], "without pre-warp"), (True, C_MEAS, "with pre-warp")):
        Wc = 2 * fs * np.tan(pi * 3000 / fs) if warp else 2 * pi * 3000
        z, pz, k = signal.butter(4, Wc, analog=True, output="zpk")
        zd, pd, kd = bilinear(z, pz, k, fs)
        w, H = signal.freqz_zpk(zd, pd, kd, worN=4096, fs=fs)
        ax[1].plot(w, db(np.abs(H) + 1e-12), color=c, label=lab)
    ax[1].axvline(3000, color=C_PRED, ls="--", label="spec 3 kHz"); ax[1].set_ylim(-60, 3)
    style_axes(ax[1], "frequency (Hz)", "|H| (dB)", "4th-order Butterworth, f_c = 3 kHz, fs = 8 kHz")
    p.save(fig, "bilinear", "The bilinear frequency warp, and a 3 kHz design with and without pre-warping.")
    p.discuss("""The measured digital cutoffs land exactly on the warping curve (fs/π)·arctan(πf/fs): a 3 kHz design drops to 2207 Hz, a 26 % error, while
at 500 Hz the error is under 1 % — the warp is negligible only far below Nyquist. Pre-warping fixes the one frequency it is aimed at exactly, but
the rest of the response is still compressed toward fs/2 (the stop-band steepens), which is harmless for low-pass designs and matters for band
shapes that must be preserved everywhere (use impulse invariance or direct digital design then). The own zpk mapping agrees with SciPy's to
rounding error, including the extra zeros that the 4 poles' implicit zeros at s = ∞ contribute at z = −1.""")
# tol-convention: relative tolerances are in percent
