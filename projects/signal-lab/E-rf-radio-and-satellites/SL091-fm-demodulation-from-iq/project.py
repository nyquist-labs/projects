from eelab import *
from scipy import signal

META = dict(
    id="SL-091", title="FM demodulation from IQ (phase differentiator) and the FM threshold", level="M",
    tools="NumPy/SciPy complex-baseband FM modem, SNR vs CNR measurement",
    summary="Build an FM discriminator from IQ samples (angle of r[n]·r*[n−1]), measure output SNR vs CNR for "
            "deviation ratios β = 1 and 5, and compare with the 3β²(β+1) FM improvement and the ~10 dB threshold.",
    problem="FM trades bandwidth for noise immunity. Verify the trade quantitatively — and find where it breaks.",
    theory=r"""Above threshold, with a sinusoidal message and noise in the Carson bandwidth $B_T=2(\beta+1)W$:
$SNR_{out} = \tfrac32\beta^2\left(\frac{f_m}{W}\right)^2\frac{A^2/2}{N_0W} = 3\beta^2(\beta+1)\left(\frac{f_m}{W}\right)^2 CNR_{B_T}$ —
the textbook $3\beta^2(\beta+1)$ assumes the tone sits at the top of the message band (f_m = W); with a 1 kHz tone in a
3 kHz audio filter the parabolic noise below 3 kHz costs $(f_m/W)^2$ = −9.5 dB. Below CNR ≈ 10 dB 'clicks' (2π phase slips) appear and SNR collapses.""",
    method="""Message 1 kHz sine (W = 3 kHz), β = 1 and 5, 240 kS/s complex baseband. AWGN scaled to CNR in B_T. IF filter: 6th-order low-pass at 0.75·B_T (a filter
exactly B_T wide distorts wideband FM). Demodulator: y[n] = arg(r[n]r*[n−1]), 3 kHz low-pass, SNR = power at 1 kHz vs everything else in 0–3 kHz.""",
)


def run(p):
    fs, fm, W = 240000, 1000.0, 3000.0
    n = np.arange(int(0.5 * fs))
    fig, ax = p.fig()
    for i, beta in enumerate((1, 5)):
        df = beta * fm
        ph = (df / fm) * np.sin(2 * pi * fm * n / fs)          # phase deviation β rad → frequency deviation Δf = β·f_m
        s = np.exp(1j * ph)
        BT = 2 * (beta + 1) * W
        out = []
        cnrs = np.arange(0, 31, 2)
        for cnr in cnrs:
            N0 = 1 / (10 ** (cnr / 10) * BT)
            r = s + (p.rng.normal(size=len(n)) + 1j * p.rng.normal(size=len(n))) * np.sqrt(N0 * fs / 2)
            bb, aa = signal.butter(6, 0.75 * BT, fs=fs)      # IF filter wide enough to pass ~99 % of the FM spectrum undistorted
            r = signal.filtfilt(bb, aa, r)
            y = np.angle(r[1:] * np.conj(r[:-1]))
            bl, al = signal.butter(6, W, fs=fs)
            y = signal.lfilter(bl, al, y)[20000:]
            Y = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
            f = np.fft.rfftfreq(len(y), 1 / fs)
            sig = Y[(f > 950) & (f < 1050)].sum()
            noi = Y[(f > 50) & (f < W)].sum() - sig
            out.append(10 * np.log10(sig / noi))
        out = np.array(out)
        pred = 10 * np.log10(3 * beta**2 * (beta + 1) * (fm / W) ** 2) + cnrs
        j = list(cnrs).index(20)
        p.compare(f"β = {beta}: output SNR at CNR 20 dB", pred[j], out[j], "dB", kind="abs")
        thr = cnrs[np.argmax(out > pred - 1)]
        p.compare(f"β = {beta}: threshold CNR (within 1 dB of theory)", 10, thr, "dB", kind="abs")
        ax.plot(cnrs, out, "o-", color=COLORS[i], label=f"β = {beta} measured")
        ax.plot(cnrs, pred, "--", color=COLORS[i], lw=1, label=f"β = {beta}: 3β²(β+1)(f_m/W)²·CNR")
    style_axes(ax, "CNR in Carson bandwidth (dB)", "output SNR (dB)", "FM improvement and threshold")
    p.save(fig, "fm_snr", "Wideband FM buys ~25 dB of SNR above threshold; below ~10 dB CNR it collapses.")
    p.discuss("""Above threshold the measured output SNR follows the prediction within about a dB for both deviation ratios. My first
prediction used the bare 3β²(β+1) and was 9 dB optimistic for *both* β — a constant offset that pointed straight at a
missing factor: the formula assumes the test tone is at the top of the audio band, and with f_m = W/3 the (f_m/W)²
term is −9.5 dB. Wideband FM (β = 5) still turns a 20 dB CNR into ~37 dB of audio SNR. Below ~10 dB CNR the curves bend down sharply as click noise
takes over; the higher-β system falls off harder because its wider bandwidth collects more noise at the same
carrier power. This threshold is exactly what SL-085 observed in the real NOAA recording near the horizon.""")
