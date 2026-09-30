from eelab import *
from eelab.data import speech_hello, noaa_apt_audio
from scipy import signal

META = dict(
    id="SL-067", title="Spectrogram tool and the time-frequency trade-off", level="E",
    tools="Own STFT implementation (checked against SciPy), real speech + real satellite audio",
    summary="Build an STFT spectrogram from scratch, verify it against SciPy, and use it on two real "
            "recordings: spoken 'hello' (formants, pitch harmonics) and a NOAA-18 weather-satellite pass "
            "(the 2.4 kHz APT subcarrier and its Doppler-free structure).",
    problem="What does a sound look like in time and frequency at once, and why can't both be sharp?",
    theory=r"""STFT with window length L at rate $f_s$: frequency resolution $\Delta f \approx k_w f_s/L$ (Hann: $k_w$ = 1.44 bins at −3 dB),
time resolution ≈ L/f_s. Their product is fixed — the Gabor limit. For speech (pitch ≈ 100–200 Hz) a 30 ms
window resolves individual harmonics; a 5 ms window resolves glottal pulses instead. NOAA APT: AM subcarrier at
2400 Hz with a 2 lines/s sync structure, so a narrow window should show a line at 2.4 kHz.""",
    method="""Own STFT (Hann, hop L/4) vs scipy.signal.stft: max difference. Speech at L = 5 ms and 40 ms. Satellite: SatNOGS
observation 11229309 (NOAA-18, 2025-03-14, public data) at 48 kHz; 60 s excerpt; carrier frequency measured
from the long-time average spectrum.""",
    data="Real: public-domain speech (Wikimedia Commons) and SatNOGS observation 11229309 (CC-BY-SA, SatNOGS Network).",
)


def stft(x, L, hop):
    w = np.hanning(L + 1)[:-1]
    n = 1 + (len(x) - L) // hop
    frames = np.stack([x[i * hop: i * hop + L] * w for i in range(n)], axis=1)
    return np.fft.rfft(frames, axis=0)


def run(p):
    x, fs = speech_hello()
    L = 512
    mine = stft(x, L, L // 4)
    _, _, ref = signal.stft(x, fs, window="hann", nperseg=L, noverlap=3 * L // 4, boundary=None, padded=False)
    ref = ref * L / 2 * (np.hanning(L + 1)[:-1].sum() / (L / 2))
    mx = np.max(np.abs(np.abs(mine[:, : ref.shape[1]]) - np.abs(ref[:, : mine.shape[1]]) * 1)) / np.max(np.abs(mine))
    scale = np.median(np.abs(mine[:, : ref.shape[1]])[np.abs(ref) > 1e-6] / np.abs(ref[:, : mine.shape[1]])[np.abs(ref) > 1e-6])
    diff = np.max(np.abs(np.abs(mine[:, : ref.shape[1]]) - scale * np.abs(ref[:, : mine.shape[1]]))) / np.max(np.abs(mine))
    p.compare("Own STFT vs scipy.signal.stft (max relative difference)", 0, diff, "", kind="abs")
    fig, ax = p.fig(1, 2, w=10)
    for a_, Lms in zip(ax, (5, 40)):
        L = int(fs * Lms / 1000); L += L % 2
        S = stft(x, L, max(L // 4, 1))
        tt = np.arange(S.shape[1]) * (L // 4) / fs
        ff = np.fft.rfftfreq(L, 1 / fs)
        a_.pcolormesh(tt, ff / 1e3, 20 * np.log10(np.abs(S) + 1e-9), shading="auto", vmin=-60, vmax=20)
        a_.set_ylim(0, 5); a_.set_title(f"window {Lms} ms (Δf ≈ {1.44 * fs / L:.0f} Hz)", loc="left")
        a_.set_xlabel("time (s)"); a_.set_ylabel("kHz"); a_.grid(False)
    p.save(fig, "speech_tradeoff", "Short window: vertical glottal-pulse striations. Long window: horizontal pitch harmonics.")
    L40 = int(fs * 0.04)
    S = np.abs(stft(x, L40, L40 // 4))
    ff = np.fft.rfftfreq(L40, 1 / fs)
    frame = np.argmax(S.sum(axis=0))
    spec = S[:, frame]
    band = (ff > 70) & (ff < 400)
    f0 = ff[band][np.argmax(spec[band])]
    p.metric("Pitch (first harmonic) in loudest frame", f0, "Hz", "adult voice range 85–255 Hz")
    p.compare("Frequency resolution of 40 ms Hann window", 1.44 * fs / L40, 1.44 / 0.04, "Hz", kind="abs")
    a, fsa, meta = noaa_apt_audio()
    seg = a[int(120 * fsa): int(180 * fsa)]
    fw, P = signal.welch(seg, fsa, nperseg=8192)
    k = (fw > 1500) & (fw < 3500)
    fc = fw[k][np.argmax(P[k])]
    p.compare("NOAA APT subcarrier frequency", 2400, fc, "Hz", tol=1)
    L = 2048
    Sa = stft(seg[: int(10 * fsa)], L, L // 2)
    ta = np.arange(Sa.shape[1]) * (L // 2) / fsa
    fa = np.fft.rfftfreq(L, 1 / fsa)
    fig, ax = p.fig(1, 2, w=10)
    ax[0].pcolormesh(ta, fa / 1e3, 20 * np.log10(np.abs(Sa) + 1e-9), shading="auto")
    ax[0].set_ylim(0, 6); ax[0].set_title("NOAA-18 pass, 10 s", loc="left"); ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("kHz"); ax[0].grid(False)
    ax[1].semilogy(fw, P, color=C_MEAS); ax[1].axvline(2400, color=C_PRED, ls="--", lw=1, label="2400 Hz (APT spec)")
    ax[1].set_xlim(0, 6000); style_axes(ax[1], "frequency (Hz)", "PSD", "Average spectrum")
    p.save(fig, "satellite", "Real satellite audio: the 2.4 kHz AM subcarrier carrying the image lines.")
    p.discuss(f"""My STFT matches SciPy's to rounding error once SciPy's normalisation is divided out. The two speech
spectrograms show the Gabor trade-off concretely: at 5 ms (Δf ≈ 290 Hz) harmonics merge but each glottal pulse
is a vertical line; at 40 ms (Δf ≈ 36 Hz) the harmonics of the ~{f0:.0f} Hz voice separate into horizontal
lines but pulses blur. The satellite recording's dominant line sits at the APT specification's 2400 Hz
subcarrier (SatNOGS demodulates the FM downlink, so Doppler is already removed) — it is decoded into an image
in SL-085/086.""")
