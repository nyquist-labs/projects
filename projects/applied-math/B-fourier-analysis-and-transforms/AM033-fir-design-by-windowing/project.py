from eelab import *
from scipy import signal

META = dict(
    id="AM-033", title="FIR low-pass design by windowing the ideal sinc", level="M",
    tools="Windowed-sinc design (own implementation), measured stopband attenuation and transition width for rectangular, Hann, Hamming, Blackman and Kaiser windows, Kaiser's design formulas",
    summary="Design low-pass FIR filters by truncating the ideal sinc with different windows, predict stopband attenuation and transition width "
            "from the window alone, and verify with measured responses — then hit a specification with Kaiser's formula.",
    problem="Truncating an ideal filter causes ripples. How much, how wide — and can the filter length be predicted from a spec?",
    theory=r"""$h[n]=2f_c\,\mathrm{sinc}(2f_c(n-\tfrac{N-1}{2}))\,w[n]$. The window's sidelobes set the stopband floor independent of N (rect ≈ 21 dB, Hann ≈ 44, Hamming ≈ 53, Blackman ≈ 74 dB) and its mainlobe
sets the transition width Δf ≈ D/N (D ≈ 0.9, 3.1, 3.3, 5.5 in fs units). Kaiser: β from the attenuation A, and $N ≈ \frac{A-8}{2.285·2πΔf}+1$.""",
    method="""f_c = 0.2 fs, N = 101. Stopband attenuation = peak sidelobe beyond the transition; transition width measured between |H| = 1 − δ and |H| = δ (δ = stopband peak). Kaiser design
for A = 60 dB, Δf = 0.02 fs; check the spec is met.""",
)

TXT = {"boxcar": (21, 0.9), "hann": (44, 3.1), "hamming": (53, 3.3), "blackman": (74, 5.5)}


def design(N, fc, win, beta=None):
    n = np.arange(N) - (N - 1) / 2
    w = signal.get_window(("kaiser", beta) if win == "kaiser" else win, N, fftbins=False)
    h = 2 * fc * np.sinc(2 * fc * n) * w
    return h / h.sum()


def measure(h, fc):
    w, H = signal.freqz(h, worN=2 ** 16, fs=1.0); M = np.abs(H)
    stop = w > fc + 0.02
    first_null = np.argmax((w > fc) & (np.r_[np.diff(M) > 0, False]))
    delta = M[first_null:].max()
    A = -db(delta)
    f_hi = w[np.argmax((w > fc) & (M <= delta * 1.0001))]
    f_lo = w[np.flatnonzero((w < fc) & (M < 1 - delta))[0]] if np.any((w < fc) & (M < 1 - delta)) else fc
    return A, f_hi - f_lo


def run(p):
    N, fc = 101, 0.2
    fig, ax = p.fig(1, 2, w=11)
    for (win, (A_t, D)), c in zip(TXT.items(), COLORS):
        h = design(N, fc, win)
        A, tw = measure(h, fc)
        p.compare(f"{win}: stopband attenuation", A_t, A, "dB", kind="abs", tol=3)
        p.compare(f"{win}: transition width ≈ {D}/N", D / N, tw, "× fs", tol=25)
        w, H = signal.freqz(h, worN=4096, fs=1.0)
        ax[0].plot(w, db(np.abs(H) + 1e-12), color=c, lw=1, label=win)
    ax[0].set_ylim(-110, 5)
    style_axes(ax[0], "frequency (× fs)", "|H| (dB)", "N = 101, f_c = 0.2 fs")
    A, df = 60, 0.02
    beta = 0.1102 * (A - 8.7)
    Nk = int(np.ceil((A - 8) / (2.285 * 2 * pi * df))) + 1
    Nk += (Nk % 2 == 0)
    hk = design(Nk, fc, "kaiser", beta)
    w, H = signal.freqz(hk, worN=2 ** 16, fs=1.0); M = np.abs(H)
    stop = w >= fc + df / 2; pas = w <= fc - df / 2
    p.metric("Kaiser design for 60 dB, Δf = 0.02 fs", f"β = {beta:.2f}, N = {Nk}")
    p.compare("Kaiser: achieved stopband attenuation beyond f_c + Δf/2", 60, -db(M[stop].max()), "dB", kind="abs", tol=1.5)
    p.compare("Kaiser: passband ripple ≈ stopband ripple (δp = δs)", 10 ** (-60 / 20), np.max(np.abs(M[pas] - 1)), "", kind="abs", tol=5e-4)
    ax[1].plot(w, db(M + 1e-12), color=C_MEAS); ax[1].axhline(-60, color=C_PRED, ls="--"); ax[1].axvspan(fc - df / 2, fc + df / 2, color=COLORS[7], alpha=.2)
    ax[1].set_ylim(-100, 5); ax[1].set_xlim(0, 0.5)
    style_axes(ax[1], "frequency (× fs)", "|H| (dB)", f"Kaiser to spec: 60 dB, Δf = 0.02 fs (N = {Nk})", legend=False)
    p.save(fig, "fir_windows", "Windowed-sinc low-pass responses for four windows, and a Kaiser design meeting a specification.")
    p.discuss("""The stopband floor is a property of the window, not of the length: rectangular truncation stalls near 21 dB (the Gibbs overshoot of AM-022
in frequency), Hann/Hamming reach 44/53 dB and Blackman ~74 dB, each paying with a proportionally wider transition band (≈ D/N). The measured
transition widths follow D/N within the tolerance of how 'edge' is defined. Kaiser's window turns this trade-off into a dial: β from the
attenuation, N from the transition width — the filter designed from the formula meets the 60 dB spec on the first try. Windowing is simple and
predictable, but not optimal: for the same N, Parks–McClellan (AM-034) spreads the error evenly and does better.""")
# tol-convention: relative tolerances are in percent
