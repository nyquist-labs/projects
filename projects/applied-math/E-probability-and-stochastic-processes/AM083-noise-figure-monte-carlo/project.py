from eelab import *

META = dict(
    id="AM-083", title="Receiver noise figure: Friis formula and Monte-Carlo spread", level="M",
    tools="Friis cascade formula, sample-level noise simulation of a three-stage receiver (LNA, mixer, IF amplifier), Monte-Carlo over component tolerances",
    summary="Predict a receiver's cascaded noise figure with the Friis formula, confirm it by passing sampled noise and signal through a simulated "
            "chain, and use Monte-Carlo over gain and noise-figure tolerances to find the spread and the probability of meeting a specification.",
    problem="Why does the first amplifier dominate a receiver's noise — and how much margin do tolerances eat?",
    theory=r"""$F = F_1 + \frac{F_2-1}{G_1} + \frac{F_3-1}{G_1G_2}$ (linear ratios). With an LNA (G = 20 dB, NF = 1.5 dB), a lossy mixer (G = −7 dB, NF = 7 dB) and an IF amp (G = 30 dB, NF = 4 dB): F = 1.41 + 4.01/100 + 1.51/(100·0.2) = 1.525 → NF = 1.83 dB.
Swapping the LNA behind the mixer would give NF ≈ 8.5 dB. Tolerances (±1 dB gain, ±0.3 dB NF, Gaussian 1σ) spread the cascaded NF; the first stage's NF dominates the spread.""",
    method="""Sample-level: input noise at kT0B (normalised to 1), a sine of known SNR; each stage adds its own input-referred noise (F_i − 1)·kT0B then multiplies by √G_i; output SNR measured by projecting on the
sine → NF = SNR_in/SNR_out. 50,000 Monte-Carlo chains with Gaussian tolerances; yield for NF < 2.2 dB.""",
)


def friis(G, F):
    tot = F[0]; gp = G[0]
    for g, f in zip(G[1:], F[1:]):
        tot += (f - 1) / gp; gp *= g
    return tot


def run(p):
    Gdb = np.array([20, -7, 30]); NFdb = np.array([1.5, 7.0, 4.0])
    G, F = 10 ** (Gdb / 10), 10 ** (NFdb / 10)
    nf = 10 * np.log10(friis(G, F))
    p.compare("Friis cascade NF", 1.83, nf, "dB", kind="abs", tol=0.02)
    p.metric("Same stages with the LNA moved after the mixer", 10 * np.log10(friis(G[[1, 0, 2]], F[[1, 0, 2]])), "dB")
    r = p.rng
    n = 2 ** 18; t = np.arange(n); tone = np.sqrt(2 * 100) * np.cos(2 * pi * 0.1234 * t)
    x = tone + r.normal(size=n)
    for g, f in zip(G, F):
        x = (x + r.normal(size=n) * np.sqrt(f - 1)) * np.sqrt(g)
    c = np.cos(2 * pi * 0.1234 * t); s = np.sin(2 * pi * 0.1234 * t)
    amp = 2 * np.hypot(np.mean(x * c), np.mean(x * s))
    Psig = amp ** 2 / 2; Pn = np.var(x - amp * np.cos(2 * pi * 0.1234 * t + np.arctan2(-np.mean(x * s), np.mean(x * c))))
    snr_out = Psig / Pn
    p.compare("Sample-level simulation: NF = SNR_in / SNR_out", nf, 10 * np.log10(100 / snr_out), "dB", kind="abs", tol=0.05)
    N = 50000
    Gm = Gdb[None, :] + r.normal(0, 1.0, (N, 3)); Fm = NFdb[None, :] + r.normal(0, 0.3, (N, 3))
    NF = 10 * np.log10(np.array([friis(10 ** (g / 10), 10 ** (f / 10)) for g, f in zip(Gm, Fm)]))
    p.metric("Monte-Carlo NF: mean ± std", f"{NF.mean():.2f} ± {NF.std():.2f} dB")
    p.compare("Monte-Carlo std ≈ LNA NF tolerance (first stage dominates; 0.3 dB × ∂NF/∂NF₁)", 0.3 * F[0] / friis(G, F), NF.std(), "dB", kind="abs", tol=0.05)
    p.metric("Yield for NF < 2.2 dB", np.mean(NF < 2.2) * 100, "%")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].hist(NF, bins=80, color=C_MEAS); ax[0].axvline(nf, color=C_PRED, ls="--", label="nominal (Friis)"); ax[0].axvline(2.2, color="black", ls=":", label="spec 2.2 dB")
    style_axes(ax[0], "cascaded NF (dB)", "count", "Tolerance spread (50,000 receivers)")
    lna_g = np.linspace(0, 30, 61)
    ax[1].plot(lna_g, [10 * np.log10(friis(np.array([10 ** (g / 10), G[1], G[2]]), F)) for g in lna_g], color=C_MEAS)
    ax[1].axhline(NFdb[0], color=C_PRED, ls="--", label="LNA NF alone")
    style_axes(ax[1], "LNA gain (dB)", "system NF (dB)", "LNA gain buries later stages' noise")
    p.save(fig, "noise_figure", "Monte-Carlo spread of the cascaded noise figure, and system NF vs LNA gain.")
    p.discuss(f"""The Friis formula and a brute-force simulation — adding each stage's input-referred noise to real samples and measuring SNR degradation — agree on
{nf:.2f} dB. The formula's message is in the denominators: behind 20 dB of LNA gain the lossy mixer's 7 dB noise figure contributes almost nothing,
whereas putting the mixer first would ruin the receiver (≈ 8.5 dB). The same structure shows in the Monte-Carlo: the spread of the cascaded NF is
essentially the LNA's own NF tolerance, and later-stage tolerances barely matter, so specifying (and paying for) a tight first stage is what
buys yield. The right-hand plot shows the design rule: LNA gain beyond ~20 dB buys little and costs linearity.""")
# tol-convention: relative tolerances are in percent
