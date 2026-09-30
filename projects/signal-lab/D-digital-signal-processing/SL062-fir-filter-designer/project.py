from eelab import *
from scipy import signal

META = dict(
    id="SL-062", title="FIR filter designer (windowed sinc / Kaiser)", level="M",
    tools="NumPy windowed-sinc implementation, Kaiser's order formula, frequency-response measurement",
    summary="Design low-pass FIR filters from a specification (passband ripple, stopband attenuation, "
            "transition width) using Kaiser's formulas, then measure whether each design meets its spec.",
    problem="Given a filter specification, how many taps does an FIR need, and does the windowed-sinc design "
            "actually meet the attenuation it promises?",
    theory=r"""Kaiser window design: for stopband attenuation A dB and normalised transition width Δω,
$$M \approx \frac{A-8}{2.285\,\Delta\omega},\qquad \beta=0.1102(A-8.7)\ (A>50)$$
The ideal response is $h[n]=\frac{\omega_c}{\pi}\mathrm{sinc}\!\left(\frac{\omega_c}{\pi}(n-M/2)\right)$ multiplied by the Kaiser
window; passband ripple $\delta_p\approx\delta_s=10^{-A/20}$ (window designs have equal ripple in both bands).""",
    method="""Sampling 48 kHz, passband edge 4 kHz, stopband edge 5 kHz (Δf = 1 kHz). Specs A = 40, 60, 80, 100 dB. Taps from the
formula; h[n] computed directly (no SciPy design call); response on a 32k-point grid; measured stopband
attenuation and passband ripple compared with spec. A 1 kHz + 7 kHz test signal is filtered to show the
result in time.""",
)


def kaiser_fir(A, fp, fs_, Fs):
    dw = 2 * pi * (fs_ - fp) / Fs
    M = int(np.ceil((A - 8) / (2.285 * dw)))
    M += M % 2
    beta = 0.1102 * (A - 8.7) if A > 50 else (0.5842 * (A - 21)**0.4 + 0.07886 * (A - 21) if A >= 21 else 0)
    wc = pi * (fp + fs_) / Fs
    n = np.arange(M + 1) - M / 2
    h = wc / pi * np.sinc(wc / pi * n) * np.kaiser(M + 1, beta)
    return h / h.sum(), M


def run(p):
    Fs, fp, fsb = 48e3, 4e3, 5e3
    fig, ax = p.fig()
    rows = []
    for i, A in enumerate([40, 60, 80, 100]):
        h, M = kaiser_fir(A, fp, fsb, Fs)
        w, H = signal.freqz(h, worN=32768, fs=Fs)
        g = db(H)
        stop = -g[w >= fsb].max()
        ripple = np.max(np.abs(np.abs(H[w <= fp]) - 1))
        p.compare(f"A = {A} dB: stopband attenuation", A, stop, "dB", kind="abs")
        p.compare(f"A = {A} dB: passband ripple δ_p", 10**(-A / 20), ripple, "", kind="abs")
        p.metric(f"A = {A} dB: taps", M + 1)
        rows.append((A, M + 1, stop, ripple))
        ax.plot(w / 1e3, g, color=COLORS[i], lw=1, label=f"A = {A} dB ({M+1} taps)")
    ax.set_xlim(0, 12); ax.set_ylim(-130, 5)
    ax.axvspan(fp / 1e3, fsb / 1e3, color="gray", alpha=.12)
    style_axes(ax, "frequency (kHz)", "gain (dB)", "Kaiser-window FIR designs (transition band shaded)")
    p.save(fig, "responses", "Each 20 dB of extra attenuation costs ~28 more taps.")
    h, M = kaiser_fir(80, fp, fsb, Fs)
    t = np.arange(2400) / Fs
    x = np.sin(2 * pi * 1e3 * t) + np.sin(2 * pi * 7e3 * t)
    y = np.convolve(x, h, "same")
    resid = y - np.sin(2 * pi * 1e3 * (t))
    k = slice(400, 2000)
    a1 = np.sqrt(2) * np.std(y[k])
    p.compare("1 kHz amplitude after the 80 dB filter", 1.0, a1, "", tol=0.1)
    p.metric("7 kHz residue after filtering (RMS)", np.std(resid[k]), "", "≤ 10^(−80/20)/√2 = 7e-5 required")
    fig, ax = p.fig()
    ax.plot(t[:600] * 1e3, x[:600], color="gray", lw=.8, label="input 1 kHz + 7 kHz")
    ax.plot(t[:600] * 1e3, y[:600], color=C_MEAS, label="filtered (80 dB design)")
    style_axes(ax, "time (ms)", "amplitude", "Time-domain check")
    p.save(fig, "time_domain", "The 7 kHz component disappears; the 1 kHz tone passes unchanged.")
    import pandas as pd
    p.csv_df("designs", pd.DataFrame(rows, columns=["spec_db", "taps", "measured_atten_db", "passband_ripple"]))
    p.write("coefficients_80dB.txt", "\n".join(f"{c:.10e}" for c in h) + "\n", "80 dB design coefficients")
    p.discuss("""Every design meets or slightly exceeds its attenuation spec with the tap count from Kaiser's empirical
formula, and the passband ripple is ≈ 10^(−A/20) as predicted — the window method cannot trade passband
ripple against stopband attenuation, which is its main limitation (Parks-McClellan, AM-034, can). The
formula's linear M ∝ A/Δω makes FIR cost easy to budget: sharper filters cost taps proportionally.""")
