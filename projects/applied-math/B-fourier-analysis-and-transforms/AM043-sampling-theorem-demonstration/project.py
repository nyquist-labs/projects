from eelab import *

META = dict(
    id="AM-043", title="The sampling theorem, constructively", level="M",
    tools="Band-limited random signals, Whittaker–Shannon (sinc) interpolation, reconstruction error vs sampling rate, aliasing-frequency prediction",
    summary="Reconstruct band-limited signals from their samples with sinc interpolation, measure the error as the sampling rate crosses 2B, and "
            "predict exactly where out-of-band tones alias.",
    problem="Nyquist says 2B samples per second suffice. Can we watch perfect reconstruction happen — and watch it fail?",
    theory=r"""If X(f) = 0 for |f| ≥ B and f_s > 2B, then $x(t)=\sum_n x(nT)\,\mathrm{sinc}\big((t-nT)/T\big)$ exactly. Below 2B, spectral copies overlap and a tone at f appears at
$f_a=|f-f_s\,\mathrm{round}(f/f_s)|$. With a finite number of samples the reconstruction is exact only far from the record edges (sinc tails decay as 1/t).""",
    method="""Random band-limited signals (B = 100 Hz, built as sums of 400 random sinusoids below B), sampled at f_s from 150 to 400 Hz over 20 s; reconstruction on a fine grid in the central 10 s;
RMS error relative to signal RMS. Tones at 30…970 Hz sampled at 400 Hz: apparent frequency from an FFT vs the aliasing formula.""",
)


def run(p):
    r = p.rng
    B = 100.0
    fr = r.uniform(0, B, 400); ph = r.uniform(0, 2 * pi, 400); am = r.normal(size=400)
    xf = lambda t: (am[None, :] * np.cos(2 * pi * fr[None, :] * t[:, None] + ph[None, :])).sum(1)
    tt = np.linspace(5, 15, 4001); truth = xf(tt)
    rows = []
    for fs in (150, 180, 195, 205, 220, 250, 300, 400):
        n = np.arange(0, int(20 * fs)); ts = n / fs
        xs = xf(ts)
        rec = np.sinc((tt[:, None] - ts[None, :]) * fs) @ xs
        rows.append((fs, np.sqrt(np.mean((rec - truth) ** 2) / np.mean(truth ** 2))))
    rows = np.array(rows)
    p.compare("Relative RMS reconstruction error at f_s = 400 Hz (= 4B)", 0, rows[-1, 1], "", kind="abs", tol=0.01)
    p.compare("Relative RMS error at f_s = 150 Hz (< 2B, aliasing)", 0.5, rows[0, 1], "", kind="abs", tol=0.5)
    p.metric("Error just above 2B (f_s = 205 Hz): limited by the finite 20 s sinc sum", rows[3, 1], "")
    fs = 400
    worst = 0
    ftest = np.arange(30, 980, 47.3)
    app = []
    for f in ftest:
        n = np.arange(4000); xs = np.cos(2 * pi * f * n / fs)
        X = np.abs(np.fft.rfft(xs * np.hanning(len(xs)), 1 << 16)); ff = np.fft.rfftfreq(1 << 16, 1 / fs)
        fa_meas = ff[np.argmax(X)]; fa_pred = abs(f - fs * round(f / fs))
        worst = max(worst, abs(fa_meas - fa_pred)); app.append((f, fa_meas, fa_pred))
    p.compare("Aliased tone frequencies: FFT vs |f − f_s·round(f/f_s)| (worst, 20 tones)", 0, worst, "Hz", kind="abs", tol=0.02)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(rows[:, 0] / B, rows[:, 1], "o-", color=C_MEAS)
    ax[0].axvline(2, color=C_PRED, ls="--", label="f_s = 2B")
    style_axes(ax[0], "f_s / B", "relative RMS error", "Reconstruction error vs sampling rate")
    a = np.array(app)
    ff = np.linspace(0, 1000, 2000)
    ax[1].plot(ff, np.abs(ff - fs * np.round(ff / fs)), color=C_PRED, label="predicted alias (folding)")
    ax[1].plot(a[:, 0], a[:, 1], "o", color=C_MEAS, label="measured")
    style_axes(ax[1], "true frequency (Hz)", "apparent frequency (Hz)", "Aliasing at f_s = 400 Hz")
    p.save(fig, "sampling", "Reconstruction error vs sampling rate, and the folding of tone frequencies above Nyquist.")
    p.discuss(f"""Sinc interpolation rebuilds the band-limited signal essentially perfectly once f_s is comfortably above 2B (error {rows[-1, 1]:.1e} at 4B), and the error
explodes below 2B, where overlapping spectral copies make the samples ambiguous. Just above 2B the reconstruction is exact in principle but converges
slowly: sinc tails decay only as 1/t, so a finite record leaves an error that practical systems avoid by oversampling and using better-behaved
interpolation kernels. Every tone above Nyquist lands exactly on the folding prediction — the zig-zag line — which is why anti-alias filters
must remove energy *before* sampling; no processing afterwards can tell a 370 Hz tone from a 30 Hz one at f_s = 400 Hz.""")
# tol-convention: relative tolerances are in percent
