from eelab import *
from eelab.data import fsdd
from scipy import signal

META = dict(
    id="AM-215", title="Nyquist and Shannon: sampling rate, signalling rate and capacity", level="M",
    tools="Sinc interpolation of band-limited signals and its truncation error, aliasing measured on real speech with and without an anti-alias filter, raised-cosine pulses and the Nyquist ISI criterion, signalling faster than Nyquist, M-PAM throughput at the Nyquist rate versus Shannon capacity",
    summary="Two different 'Nyquist' results and one Shannon result, each tested: a signal of bandwidth B is rebuilt from 2B samples per second (and aliases "
            "predictably below that), a channel of bandwidth B carries at most 2B independent symbols per second without interference, and the bits per symbol are then capped by the SNR.",
    problem="Nyquist says 2B, Shannon says B·log₂(1 + SNR). Are they in conflict, and what does each actually limit?",
    theory=r"""Sampling theorem: $x(t)=\sum x(nT)\,\mathrm{sinc}((t-nT)/T)$ exactly if X(f) = 0 for |f| ≥ 1/(2T); energy above the new Nyquist frequency folds back (aliasing). Nyquist ISI criterion: pulses p(t) with p(nT) = δₙ (e.g. raised cosine, bandwidth (1+β)/(2T)) allow symbol rate 1/T; the
maximum ISI-free rate in bandwidth B is 2B symbols/s (β = 0). Shannon: $C=B\log_2(1+\mathrm{SNR})$ bits/s. Together: 2B symbols/s × ½log₂(1 + SNR) bits per real symbol = C — Nyquist fixes the symbol rate, Shannon the bits per symbol.""",
    method="""(1) Band-limited random signals (40 tones below B), sampled at 2.5B and 1.6B, reconstructed by sinc interpolation over ±200 samples. (2) FSDD speech (8 kHz), decimated by 2 by dropping samples vs scipy.signal.decimate (FIR anti-alias); aliased energy predicted from the
3.2–4 kHz content by the spectrum. (3) Raised cosine β = 0.35: ISI at the sampling instants for symbol rates 1/T and 1.25/T. (4) M-PAM at the Nyquist rate: symbol error vs SNR and throughput vs capacity.""",
    data="Free Spoken Digit Dataset (CC BY-SA 4.0).",
)


def rc(t, T, beta):
    x = t / T; den = 1 - (2 * beta * x) ** 2
    return np.where(np.abs(den) < 1e-8, pi / 4 * np.sinc(1 / (2 * beta)), np.sinc(x) * np.cos(pi * beta * x) / np.where(np.abs(den) < 1e-8, 1, den))


def run(p):
    r = p.rng; B = 1.0; fr = r.uniform(0, 0.98 * B, 40); ph = r.uniform(0, 2 * pi, 40); am = r.normal(size=40)
    xf = lambda t: np.sum(am[:, None] * np.cos(2 * pi * fr[:, None] * t[None] + ph[:, None]), 0)
    tt = np.linspace(100, 150, 2001); res = {}
    for fs in (2.5 * B, 1.6 * B):
        T = 1 / fs; n = np.arange(int(250 / T)); xs = xf(n * T)
        rec = np.array([np.sum(xs * np.sinc((t - n * T) / T)) for t in tt]); res[fs] = np.sqrt(np.mean((rec - xf(tt)) ** 2) / np.mean(xf(tt) ** 2))
    alias_pred = np.sqrt(np.sum(am[fr > 0.8 * B] ** 2) / np.sum(am ** 2)) * np.sqrt(2)
    p.compare("Sampling at 2.5B: sinc reconstruction error (only truncation of the series)", 0.0, res[2.5 * B], "", kind="abs", tol=0.02)
    p.compare("Sampling at 1.6B: reconstruction error ≈ √2 × (energy share of tones above 0.8B)^½ — they alias", alias_pred, res[1.6 * B], "", tol=25)
    sp = np.concatenate([a_ for _, _, _, a_, _ in fsdd()[:300]]).astype(float); fs0 = 8000
    f, P = signal.welch(sp, fs0, nperseg=1024); share = np.trapezoid(P[f > 2000], f[f > 2000]) / np.trapezoid(P, f)
    naive = sp[::2]; good = signal.decimate(sp, 2, ftype="fir")
    ref = signal.resample_poly(sp, 1, 2, window=("kaiser", 12.0))
    def alias_energy(y):
        f2, Py = signal.welch(y, 4000, nperseg=512); f1, Pr = signal.welch(ref[: len(y)], 4000, nperseg=512)
        return np.trapezoid(np.abs(Py - Pr), f2) / np.trapezoid(Pr, f1)
    ea_naive = np.mean((naive[: len(ref)] - ref[: len(naive)]) ** 2) / np.mean(ref ** 2); ea_good = np.mean((good[: len(ref)] - ref[: len(good)]) ** 2) / np.mean(ref ** 2)
    p.compare("Speech decimated 8 → 4 kHz by dropping samples: error energy vs the share of speech energy above 2 kHz (which folds back)", share, ea_naive, "", tol=30)
    p.compare("With an FIR anti-alias filter the error is at least 20 dB smaller (1 = yes)", 1, int(10 * np.log10(ea_naive / ea_good) > 20), "", kind="abs")
    p.metric("Speech energy above 2 kHz / aliased error energy: dropping samples / FIR decimation", f"{share * 100:.1f} % / {ea_naive * 100:.1f} % / {ea_good * 100:.3f} %")
    T = 1.0; beta = 0.35; k = np.arange(-50, 51); k = k[k != 0]
    isi1 = np.sum(np.abs(rc(k * T, T, beta))); isi2 = np.sum(np.abs(rc(k * 0.8 * T, T, beta)))
    p.compare("Raised cosine at symbol rate 1/T: sum of |ISI| at the sampling instants", 0.0, float(isi1), "", kind="abs", tol=1e-12)
    p.metric("Same pulse at 1.25/T (faster than Nyquist): worst-case ISI", isi2, "", "relative to the wanted sample 1.0 — the eye closes")
    snrs = np.array([10, 20, 30.0]); rows = []
    for snr in snrs:
        C = np.log2(1 + 10 ** (snr / 10))                                        # bits per complex dimension pair = per Hz: 2B real symbols × ½log₂
        best = 0
        for M in (2, 4, 8, 16, 32, 64):
            a = np.arange(M) * 2.0 - (M - 1); a /= np.sqrt(np.mean(a ** 2)); s2 = 10 ** (-snr / 10)
            i = r.integers(0, M, 200000); y = a[i] + np.sqrt(s2) * r.normal(size=i.size); d = np.argmin(np.abs(y[:, None] - a[None]), 1)
            if np.mean(d != i) < 1e-3:
                best = max(best, np.log2(M))
        rows.append((snr, C, 2 * best))
    rr = np.array(rows)
    p.compare("Uncoded PAM at the Nyquist rate (largest M with SER < 10⁻³) never exceeds Shannon's capacity (bit/s per Hz; violations)", 0, int(np.sum(rr[:, 2] > rr[:, 1])), "", kind="abs")
    p.metric("Spectral efficiency at 10 / 20 / 30 dB: uncoded PAM (SER < 10⁻³) vs capacity", " ; ".join(f"{a_:.0f} vs {b_:.2f}" for _, b_, a_ in rr), "bit/s/Hz", "the gap is what coding recovers")
    fig, ax = p.fig(1, 2, w=11)
    tq = np.linspace(-6, 6, 1201)
    for b_, c in ((0.0, COLORS[1]), (0.35, C_MEAS), (1.0, COLORS[2])):
        ax[0].plot(tq, rc(tq, 1.0, b_ if b_ > 0 else 1e-6), color=c, label=f"β = {b_}")
    ax[0].plot(np.arange(-6, 7), np.r_[np.zeros(6), 1, np.zeros(6)], "ko", ms=4, label="sampling instants"); ax[0].axhline(0, color="gray", lw=.5)
    style_axes(ax[0], "t / T", "p(t)", "Nyquist pulses: zero at every other symbol")
    ax[1].semilogy(f, P, color=C_MEAS); ax[1].axvline(2000, color=C_PRED, ls="--", label="new Nyquist frequency")
    style_axes(ax[1], "frequency (Hz)", "PSD", "Speech: energy above 2 kHz aliases when decimating")
    p.save(fig, "nyquist_shannon", "Raised-cosine pulses satisfying the Nyquist criterion, and the speech spectrum relevant to decimation.")
    p.discuss(f"""The three statements measure different things. The sampling theorem holds numerically: a signal band-limited below B is rebuilt from samples at
2.5B with {res[2.5 * B] * 100:.1f} % error (the truncated sinc series), while sampling at 1.6B lets the tones above 0.8B fold back, with the error predicted from their
energy. On real speech, simply dropping every other sample leaves an error equal to the {share * 100:.0f} % of energy above the new 2 kHz limit, and a proper FIR
decimator cuts it by more than 20 dB. The *other* Nyquist result concerns transmission: raised-cosine pulses have exactly zero interference at the
sampling instants at 1/T symbols per second and noticeable interference when pushed 25 % faster. Neither limits the bits per symbol — that is
Shannon's contribution, and uncoded PAM stays well below it ({rr[1, 2]:.0f} vs {rr[1, 1]:.1f} bit/s/Hz at 20 dB). Nyquist sets how many symbols, Shannon how much each
can say.""")
# tol-convention: relative tolerances are in percent
