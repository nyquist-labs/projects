from eelab import *
from scipy import signal

META = dict(
    id="AM-096", title="The Wiener filter: optimal linear filtering in the frequency domain", level="H",
    tools="Non-causal Wiener filter H = S_x/(S_x + S_n), theoretical minimum MSE, estimated-spectrum Wiener filter, comparison with the best ideal low-pass",
    summary="Recover a coloured random signal (an AR(2) 'resonant' process) from white noise with the Wiener filter, predict the minimum mean-squared "
            "error from the spectra, verify it by simulation, and show it beats the best possible brick-wall filter — even when the spectra must be estimated.",
    problem="Given the signal and noise spectra, which linear filter minimises the error — and how small can the error get?",
    theory=r"""For x + n with independent stationary x and n, the non-causal MMSE linear filter is $H(f)=\frac{S_x(f)}{S_x(f)+S_n(f)}$, and the minimum error is $\int\frac{S_xS_n}{S_x+S_n}df$. It attenuates each frequency by its local SNR,
unlike a brick-wall filter which keeps or discards whole bands. In practice S_x is estimated (e.g. S_x ≈ S_y − S_n from Welch), costing a little optimality.""",
    method="""x: AR(2) with poles 0.95e^{±j0.3} (a resonance), unit variance; white noise at SNR 0 dB. N = 2¹⁸. Theoretical S_x from the AR model. Filtering in the frequency domain (large FFT). Estimated version: Welch S_y minus known noise
floor, clipped at zero. Best ideal low-pass: cutoff scanned to minimise MSE with hindsight.""",
)


def run(p):
    r = p.rng; N = 2 ** 18
    a = np.real(np.poly([0.95 * np.exp(0.3j), 0.95 * np.exp(-0.3j)]))
    x = signal.lfilter([1], a, r.normal(size=N)); x /= x.std()
    sn2 = 1.0; y = x + r.normal(0, np.sqrt(sn2), N)
    f = np.fft.fftfreq(N)
    Hx = 1 / np.abs(np.polyval(a[::-1], np.exp(-2j * pi * f)) ) ** 2
    Sx = Hx / np.mean(Hx) * 1.0
    Sn = np.full(N, sn2)
    H = Sx / (Sx + Sn)
    xhat = np.fft.ifft(np.fft.fft(y) * H).real
    mmse = np.mean(Sx * Sn / (Sx + Sn))
    p.compare("Wiener filter: simulated MSE vs theoretical minimum ∫S_xS_n/(S_x+S_n)", mmse, np.mean((xhat - x) ** 2), "", tol=3)
    best = np.inf
    for fc in np.linspace(0.01, 0.5, 200):
        xl = np.fft.ifft(np.fft.fft(y) * (np.abs(f) < fc)).real; best = min(best, np.mean((xl - x) ** 2))
    p.compare("Best ideal low-pass (hindsight) is worse than Wiener (MSE ratio > 1)", 1.3, best / mmse, "×", kind="abs", tol=1)
    fw, Sy = signal.welch(y, 1.0, nperseg=1024, return_onesided=False)
    Sx_est = np.maximum(Sy / 1.0 * 1 - sn2, 0)
    He = np.interp(np.abs(f), np.abs(fw[: len(fw) // 2]), (Sx_est / (Sx_est + sn2))[: len(fw) // 2])
    xe = np.fft.ifft(np.fft.fft(y) * He).real
    p.compare("Wiener filter with *estimated* signal spectrum: MSE penalty vs ideal (ratio)", 1.0, np.mean((xe - x) ** 2) / mmse, "", tol=10)
    p.metric("Output SNR: input 0 dB → Wiener", 10 * np.log10(1 / mmse), "dB")
    fig, ax = p.fig(1, 2, w=11)
    o = np.argsort(f); ff = f[o]
    ax[0].semilogy(ff, Sx[o], color=C_MEAS, label="S_x (resonant signal)"); ax[0].semilogy(ff, Sn[o], color=COLORS[7], label="S_n (white)")
    ax[0].plot(ff, H[o], color=C_PRED, label="Wiener H (linear scale)"); ax[0].set_xlim(0, 0.5); ax[0].set_ylim(1e-3, 50)
    style_axes(ax[0], "normalised frequency", None, "Filter gain = local SNR / (1 + local SNR)")
    ax[1].plot(x[:400], color="black", lw=1.5, label="clean"); ax[1].plot(y[:400], color=COLORS[7], lw=.6, label="noisy (0 dB)"); ax[1].plot(xhat[:400], color=C_MEAS, label="Wiener estimate")
    style_axes(ax[1], "sample", None, "Recovering the resonance")
    p.save(fig, "wiener", "Signal/noise spectra with the Wiener gain, and a stretch of clean, noisy and filtered waveforms.")
    p.discuss(f"""The simulated error equals the theoretical minimum ∫S_xS_n/(S_x+S_n) within Monte-Carlo precision, and no ideal low-pass — even with its cutoff chosen
using the true signal — gets close: the best brick wall is {best / mmse:.1f}× worse, because it must either keep the noise between the resonance and the
cutoff or discard signal in the skirts. The Wiener filter weights every frequency by its own SNR. Estimating S_x from the noisy data (Welch minus
the known noise floor) costs only a small penalty, which is why spectral-subtraction noise reduction in audio is a practical Wiener filter. The
causal version (Wiener–Hopf, and its recursive form, the Kalman filter) pays additionally for not seeing the future.""")
# tol-convention: relative tolerances are in percent
