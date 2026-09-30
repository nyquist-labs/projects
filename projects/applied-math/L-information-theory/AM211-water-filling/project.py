from eelab import *
from scipy.optimize import minimize

META = dict(
    id="AM-211", title="Water-filling: optimal power allocation over parallel channels", level="M",
    tools="Own water-filling by bisection on the water level, KKT verification, independent numerical optimisation (SLSQP), OFDM subcarriers of a multipath channel, comparison with equal power and with 'invert the channel', low- and high-SNR limits",
    summary="Distribute a power budget over parallel Gaussian channels to maximise total capacity: derive the water-filling rule, check it against a "
            "general-purpose optimiser and the KKT conditions, and apply it to the subcarriers of a frequency-selective channel where it decides which carriers to leave empty.",
    problem="An OFDM link has hundreds of subcarriers with different gains. How should a fixed transmit power be divided among them?",
    theory=r"""Maximise $\sum_i\log_2(1+g_iP_i/N)$ subject to $\sum P_i=P$, $P_i\ge0$. Lagrange/KKT: $P_i=\left(μ-N/g_i\right)^+$ — pour power into the 'vessel' with floor $N/g_i$ up to a common water level μ; channels whose floor lies above μ get nothing. At high SNR equal power is almost optimal
(the gain is bounded); at low SNR all power goes to the best channel(s) and the gain over equal power is large. Channel inversion (equal SNR on all carriers) is the *worst* sensible choice for capacity.""",
    method="""(1) 200 random sets of 2–12 channels vs SLSQP maximisation from several starts. (2) OFDM: 256 subcarriers of a 6-tap Rayleigh multipath channel, total SNR swept −10…30 dB; capacity with water-filling, equal power, and channel inversion.""",
)


def waterfill(g, P, N=1.0):
    fl = N / g; lo, hi = 0.0, fl.min() + P + 1e-9
    for _ in range(200):
        mu = (lo + hi) / 2
        (lo, hi) = (mu, hi) if np.sum(np.maximum(mu - fl, 0)) < P else (lo, mu)
    mu = (lo + hi) / 2; return np.maximum(mu - fl, 0), mu


def cap(g, Pw, N=1.0):
    return float(np.sum(np.log2(1 + g * Pw / N)))


def run(p):
    r = p.rng; worst = 0.0; kkt = 0.0
    for _ in range(200):
        k = int(r.integers(2, 13)); g = r.exponential(1, k); P = 10 ** r.uniform(-1, 1.5)
        Pw, mu = waterfill(g, P); Cw = cap(g, Pw); best = -np.inf
        for _ in range(4):
            x0 = r.dirichlet(np.ones(k)) * P
            res = minimize(lambda x: -cap(g, np.maximum(x, 0)), x0, method="SLSQP", constraints=[dict(type="eq", fun=lambda x: np.sum(x) - P)], bounds=[(0, P)] * k, options=dict(ftol=1e-12, maxiter=500))
            best = max(best, -res.fun)
        worst = max(worst, best - Cw)
        on = Pw > 1e-12; lam = g / (np.log(2) * (1 + g * Pw))            # marginal capacity per unit power
        kkt = max(kkt, float(np.ptp(lam[on]) / lam[on].mean()) if on.sum() > 1 else 0.0, float(np.max(lam[~on]) / lam[on].mean() - 1) if (~on).any() else -1.0)
    p.compare("200 random channel sets: best capacity found by SLSQP minus water-filling (never positive)", 0.0, worst, "bit", kind="abs", tol=1e-6)
    p.compare("KKT: equal marginal gain on all active channels, no inactive channel would gain more (worst relative violation)", 0.0, max(kkt, 0.0), "", kind="abs", tol=1e-6)
    h = (r.normal(size=6) + 1j * r.normal(size=6)) * np.sqrt(np.exp(-np.arange(6) / 2) / 2); h /= np.sqrt(np.sum(np.abs(h) ** 2))
    g = np.abs(np.fft.fft(h, 256)) ** 2
    rows = []
    for snr in np.arange(-10, 31, 2.5):
        P = 256 * 10 ** (snr / 10); Pw, mu = waterfill(g, P)
        Ce = cap(g, np.full(256, P / 256)); Ci = cap(g, P / np.sum(1 / g) / g); rows.append((snr, cap(g, Pw) / 256, Ce / 256, Ci / 256, np.mean(Pw > 0)))
    rr = np.array(rows)
    p.compare("High SNR (30 dB): water-filling gain over equal power is small (< 1 %)", 0.0, (rr[-1, 1] / rr[-1, 2] - 1) * 100, "%", kind="abs", tol=1.0)
    p.compare("Low SNR (−10 dB): water-filling gain over equal power is large (> 30 %; 1 = yes)", 1, int(rr[0, 1] / rr[0, 2] > 1.3), "", kind="abs")
    p.compare("Channel inversion never beats equal power on capacity (violations over the SNR sweep)", 0, int(np.sum(rr[:, 3] > rr[:, 2] + 1e-12)), "", kind="abs")
    p.metric("Fraction of subcarriers used by water-filling at −10 / 0 / 10 / 30 dB", " / ".join(f"{np.interp(s_, rr[:, 0], rr[:, 4]) * 100:.0f} %" for s_ in (-10, 0, 10, 30)))
    p.metric("Capacity at 0 dB (bit/subcarrier): water-filling / equal power / inversion", f"{np.interp(0, rr[:, 0], rr[:, 1]):.3f} / {np.interp(0, rr[:, 0], rr[:, 2]):.3f} / {np.interp(0, rr[:, 0], rr[:, 3]):.3f}")
    fig, ax = p.fig(1, 2, w=11)
    P0 = 256 * 10 ** (0 / 10); Pw, mu = waterfill(g, P0); fl = 1 / g; k = np.arange(256)
    ax[0].bar(k, np.minimum(fl, mu * 3), color=COLORS[7], width=1, label="floor N/g (clipped)"); ax[0].bar(k, Pw, bottom=fl, color=C_MEAS, width=1, label="allocated power")
    ax[0].axhline(mu, color=C_PRED, ls="--", label="water level μ"); ax[0].set_ylim(0, mu * 2.5)
    style_axes(ax[0], "subcarrier", "power", "Water-filling at 0 dB")
    ax[1].plot(rr[:, 0], rr[:, 1], color=C_MEAS, label="water-filling"); ax[1].plot(rr[:, 0], rr[:, 2], "--", color=C_PRED, label="equal power"); ax[1].plot(rr[:, 0], rr[:, 3], ":", color=COLORS[2], label="channel inversion")
    style_axes(ax[1], "average SNR (dB)", "bit per subcarrier", "OFDM over a multipath channel")
    p.save(fig, "waterfilling", "Water-filling across 256 subcarriers and capacity of three allocation rules versus SNR.")
    p.discuss(f"""The water-filling rule is the exact optimum: a general-purpose constrained optimiser never found a better allocation on 200 random problems, and
the KKT conditions hold — every used channel has the same marginal return, and every unused one would return less. On a real-looking OFDM channel
the rule is intuitive: at 0 dB it switches off the {100 - np.interp(0, rr[:, 0], rr[:, 4]) * 100:.0f} % of subcarriers sitting in spectral nulls and pours their power into the good ones.
Its value depends strongly on SNR: at −10 dB it beats equal power by {(rr[0, 1] / rr[0, 2] - 1) * 100:.0f} %, at 30 dB by only {(rr[-1, 1] / rr[-1, 2] - 1) * 100:.2f} %, which is why many OFDM systems adapt
modulation per carrier but keep power flat. Inverting the channel — giving every carrier equal SNR — is intuitive and consistently worst: it spends
most of the power fighting the deepest fades.""")
# tol-convention: relative tolerances are in percent
