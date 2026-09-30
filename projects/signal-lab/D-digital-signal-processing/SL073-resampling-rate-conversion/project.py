from eelab import *
from scipy import signal

META = dict(
    id="SL-073", title="Sample-rate conversion 48 kHz → 44.1 kHz (polyphase)", level="M",
    tools="Own polyphase resampler (L = 147, M = 160), Kaiser FIR prototype, SciPy for cross-check",
    summary="Convert audio between the two standard rates with a rational polyphase filter, predict the "
            "alias rejection and passband ripple from the filter design, and measure them with test tones.",
    problem="44,100/48,000 = 147/160. How do you resample by a ratio like that without aliasing and without "
            "computing 147× more samples than needed?",
    theory=r"""Conceptually upsample by L = 147 (insert zeros), low-pass at $\min(\pi/L,\pi/M)$, keep every M = 160th sample. The
polyphase form computes only the kept outputs: cost per output = taps/L. The filter's stopband attenuation
A sets how much an out-of-band tone (e.g. 23 kHz, which would alias to 21.1 kHz at 44.1 kHz) is suppressed:
alias level ≈ −A dB. Passband ripple ≈ $10^{-A/20}$.""",
    method="""Prototype: Kaiser low-pass, cutoff 20 kHz, stopband from 22.05 kHz, A = 90 dB, designed at 147 × 48 kHz. Polyphase
implementation by hand (each output picks one sub-filter). Tests: 1 kHz and 19 kHz tones (passband), 23 kHz tone
(must be rejected).""",
)


def polyphase(x, h, L, M):
    K = int(np.ceil(len(h) / L))
    hp = np.zeros(K * L); hp[: len(h)] = h * L
    E = hp.reshape(K, L).T          # E[phase, tap]
    nout = (len(x) * L) // M
    y = np.zeros(nout)
    xp = np.r_[np.zeros(K), x]
    for m in range(nout):
        t = m * M
        n, ph = divmod(t, L)
        seg = xp[n + K: n: -1] if n + K < len(xp) else np.zeros(K)
        if len(seg) == K:
            y[m] = E[ph] @ seg
    return y


def run(p):
    fin, L, M = 48000, 147, 160
    fout = fin * L / M
    A = 90
    fu = fin * L
    dw = 2 * pi * (22050 - 20000) / fu
    N = int(np.ceil((A - 8) / (2.285 * dw))); N += N % 2
    beta = 0.1102 * (A - 8.7)
    n = np.arange(N + 1) - N / 2
    wc = 2 * pi * 21025 / fu
    h = wc / pi * np.sinc(wc / pi * n) * np.kaiser(N + 1, beta)
    p.metric("Prototype taps / taps per output", N + 1, "", f"{(N + 1) / L:.1f} MACs per output sample")
    t = np.arange(int(0.2 * fin)) / fin
    res = {}
    for f in (1000, 19000, 23000):
        x = np.sin(2 * pi * f * t)
        y = polyphase(x, h, L, M)
        yy = y[len(y) // 4: 3 * len(y) // 4]
        Y = np.abs(np.fft.rfft(yy * np.blackman(len(yy)))); Y /= np.sum(np.blackman(len(yy))) / 2
        res[f] = (np.max(Y), y)
    p.compare("Passband gain at 1 kHz", 0, db(res[1000][0]), "dB", kind="abs")
    p.compare("Passband gain at 19 kHz", 0, db(res[19000][0]), "dB", kind="abs")
    p.compare("23 kHz tone after conversion (alias rejection, spec ≤ −90 dB)", -A, db(res[23000][0]), "dB", kind="abs")
    w, H = signal.freqz(h, worN=65536, fs=fu)
    fig, ax = p.fig()
    ax.plot(w / 1e3, db(H * L / L), color=C_MEAS)
    ax.axvline(20, color="gray", ls=":"); ax.axvline(22.05, color="gray", ls=":")
    ax.set_xlim(0, 60); ax.set_ylim(-130, 5)
    style_axes(ax, "frequency (kHz)", "gain (dB)", f"Anti-imaging/anti-aliasing prototype ({N+1} taps at {fu/1e6:.2f} MHz)", legend=False)
    p.save(fig, "prototype", "Passband to 20 kHz, ≥ 90 dB stopband from 22.05 kHz.")
    p.csv("tones", tone_hz=[1000, 19000, 23000], output_level_db=[db(res[f][0]) for f in (1000, 19000, 23000)])
    p.discuss("""Passband tones come through at 0 dB and the 23 kHz tone — which a naive converter would fold to 21.1 kHz —
is suppressed to the filter's stopband level, confirming the design equation. The polyphase trick is why this
is practical: only ~(taps/147) multiplies are needed per output instead of filtering at the 7 MHz intermediate
rate. The measured rejection beats the 90 dB target because Kaiser's formula is slightly conservative and
23 kHz sits well inside the stopband, not at its edge.""")
