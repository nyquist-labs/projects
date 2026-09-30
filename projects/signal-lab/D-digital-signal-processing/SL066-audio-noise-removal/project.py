from eelab import *
from eelab.data import speech_hello
from scipy import signal

META = dict(
    id="SL-066", title="Spectral-subtraction noise removal", level="M",
    tools="STFT/ISTFT (SciPy), own spectral subtraction with over-subtraction and spectral floor",
    summary="Add white noise at 0–20 dB SNR to a real speech recording, remove it with spectral subtraction, "
            "and measure the SNR gain in dB against the clean reference.",
    problem="How much noise can a simple frequency-domain gate remove before it starts eating the speech "
            "itself (musical noise)?",
    theory=r"""Estimate the noise power spectrum $\hat N(f)$ from a speech-free segment, then per STFT frame
$|\hat S|^2=\max(|X|^2-\alpha\hat N,\ \beta|X|^2)$, keep the noisy phase. For white noise with a speech signal that occupies a
fraction ρ of the time-frequency plane, the ideal output SNR gain is roughly $10\log_{10}(1/\rho)$ dB at low input SNR
(noise is removed everywhere speech is absent). A sharper yardstick is the *oracle ideal binary mask*: keep exactly the
STFT cells where speech power exceeds noise power. It needs the clean signal, so it is an upper bound on what any
single-channel time-frequency mask (spectral subtraction included) can achieve.""",
    method="""Clean signal: public-domain 'hello' recording padded with 0.3 s silence (noise-estimation region).
Noise: Gaussian, scaled to input SNR 0, 5, 10, 15, 20 dB (10 random seeds each). STFT 512/75 % overlap,
α = 2, β = 0.02. SNR computed against the clean waveform after aligning.""",
    data="Real speech ('En-us-hello.ogg', Wikimedia Commons, public domain) + synthetic Gaussian noise of known level.",
)


def subtract(xn, fs, noise_len, alpha=2.0, beta=0.02):
    f, t, X = signal.stft(xn, fs, nperseg=512, noverlap=384)
    nf = int(noise_len * fs / 128)
    Npow = np.mean(np.abs(X[:, :max(nf - 4, 1)]) ** 2, axis=1, keepdims=True)
    P = np.maximum(np.abs(X) ** 2 - alpha * Npow, beta * np.abs(X) ** 2)
    S = np.sqrt(P) * np.exp(1j * np.angle(X))
    _, y = signal.istft(S, fs, nperseg=512, noverlap=384)
    return y[: len(xn)], X, S


def snr(ref, x):
    return 10 * np.log10(np.sum(ref**2) / np.sum((x - ref) ** 2))


def run(p):
    x, fs = speech_hello()
    pad = np.zeros(int(0.3 * fs))
    clean = np.r_[pad, x, pad[:1000]]
    f, t, C = signal.stft(clean, fs, nperseg=512, noverlap=384)
    E = np.abs(C) ** 2
    rho = np.mean(E > 0.01 * E.max())
    p.metric("Speech occupancy ρ of the TF plane (>−20 dB)", rho)
    snrs = [0, 5, 10, 15, 20]
    gains, oracle = [], []
    for s in snrs:
        g, go = [], []
        for seed in range(10):
            rng_ = np.random.default_rng(seed)
            n = rng_.normal(size=len(clean)); n *= np.sqrt(np.sum(clean**2) / np.sum(n**2) / 10**(s / 10))
            y, X, S = subtract(clean + n, fs, 0.3)
            g.append(snr(clean, y) - snr(clean, clean + n))
            # oracle ideal binary mask: keep cells where speech power exceeds noise power (needs the clean signal)
            _, _, Nn = signal.stft(n, fs, nperseg=512, noverlap=384)
            _, yo = signal.istft(X * (np.abs(C) > np.abs(Nn)), fs, nperseg=512, noverlap=384)
            go.append(snr(clean, yo[: len(clean)]) - snr(clean, clean + n))
        gains.append(np.mean(g)); oracle.append(np.mean(go))
    for k_ in (0, 2, 4):
        p.compare(f"SNR gain at {snrs[k_]} dB input vs oracle ideal binary mask", oracle[k_], gains[k_], "dB", kind="abs",
                  note="oracle = best TF mask, knows the clean speech")

    fig, ax = p.fig()
    ax.plot(snrs, gains, "o-", color=C_MEAS, label="measured (mean of 10 seeds)")
    ax.plot(snrs, oracle, "s--", color=C_PRED, label="oracle ideal binary mask (upper bound)")
    style_axes(ax, "input SNR (dB)", "SNR improvement (dB)", "Spectral subtraction on real speech")
    p.save(fig, "snr_gain", "Large gains at low SNR; diminishing returns as the speech itself gets distorted.")
    rng_ = np.random.default_rng(0)
    n = rng_.normal(size=len(clean)); n *= np.sqrt(np.sum(clean**2) / np.sum(n**2) / 10**(5 / 10))
    y, X, S = subtract(clean + n, fs, 0.3)
    fig, ax = p.fig(1, 2, w=10)
    for a_, Z, ttl in ((ax[0], X, "noisy (5 dB SNR)"), (ax[1], S, "after spectral subtraction")):
        a_.pcolormesh(t, f / 1e3, 20 * np.log10(np.abs(Z) + 1e-6), vmin=-90, vmax=-20, shading="auto")
        a_.set_title(ttl, loc="left"); a_.set_xlabel("time (s)"); a_.set_ylabel("kHz"); a_.grid(False)
    p.save(fig, "spectrograms", "Noise between and around the speech harmonics is removed; isolated residual 'musical noise' dots remain.")
    import soundfile as sf
    sf.write(p.dir / "data" / "noisy_5dB.wav", ((clean + n) / np.max(abs(clean + n)) * 0.9).astype(np.float32), int(fs))
    sf.write(p.dir / "data" / "denoised_5dB.wav", (y / np.max(abs(y)) * 0.9).astype(np.float32), int(fs))
    p.files += [("data/noisy_5dB.wav", "noisy input"), ("data/denoised_5dB.wav", "denoised output")]
    p.csv("snr_gain", input_snr_db=snrs, gain_db=gains, oracle_gain_db=oracle)
    p.discuss("""The simple occupancy estimate 10·log₁₀(1/ρ) (≈ 18 dB here) badly overstates what is achievable because
speech energy is spread thinly over many low-level cells; the oracle ideal-binary-mask bound is the fair
comparison, and spectral subtraction recovers roughly half of it (in dB) — without knowing the clean
signal. As input SNR rises the remaining error is mostly the
algorithm's own distortion of the speech (phase is left noisy, low-level speech cells are floored), so the
gain collapses toward 0 dB and would go negative with stronger over-subtraction. The spectrogram shows the
characteristic 'musical noise' — isolated surviving cells — which is why modern systems use smoother
Wiener/decision-directed gains (AM-096).""")
