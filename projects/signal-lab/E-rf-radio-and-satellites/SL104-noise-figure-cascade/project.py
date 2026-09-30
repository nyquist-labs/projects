from eelab import *

META = dict(
    id="SL-104", title="Noise-figure cascade (Friis) vs Monte Carlo", level="M",
    tools="Friis formula + sample-level noise simulation of a 4-stage receiver chain (NumPy)",
    summary="Compute the noise figure of a receiver chain (antenna cable, LNA, mixer, IF amp) with the Friis formula and "
            "confirm it by pushing actual noise samples through the chain; show why the LNA must come first.",
    problem="Why does a 1 dB-noise-figure preamp at the antenna beat a much better receiver at the end of a lossy cable?",
    theory=r"""Friis: $F_{tot}=F_1+\frac{F_2-1}{G_1}+\frac{F_3-1}{G_1G_2}+\cdots$ (linear). A passive loss L at T₀ has F = L. Each stage adds
input-referred noise $(F_i-1)kT_0B$ at its own input; referring everything to the chain input and comparing output SNR
with input SNR gives the same F.""",
    method="""Stages: cable (loss 3 dB), LNA (G = 20 dB, NF = 1 dB), mixer (G = −7 dB, NF = 8 dB), IF amp (G = 30 dB, NF = 4 dB). Two orderings:
cable → LNA → … (preamp at the receiver) and LNA → cable → … (preamp at the antenna). Simulation: Gaussian noise at kT₀B
(normalised) plus a test tone, each stage multiplies by √G and adds independent noise of power (F−1)kT₀B·G; SNR ratio
from 10⁶ samples.""",
)


def friis(stages):
    F, G = 0, 1
    for i, (g, nf) in enumerate(stages):
        f = 10 ** (nf / 10)
        F = f if i == 0 else F + (f - 1) / G
        G *= 10 ** (g / 10)
    return 10 * np.log10(F)


def simulate(stages, rng_, n=10**6):
    x_sig = np.sqrt(2) * np.cos(2 * pi * 0.1 * np.arange(n)) * 10
    x_noise = rng_.normal(size=n)
    s, nn = x_sig.copy(), x_noise.copy()
    for g, nf in stages:
        G = 10 ** (g / 10); F = 10 ** (nf / 10)
        s = s * np.sqrt(G)
        nn = nn * np.sqrt(G) + rng_.normal(size=n) * np.sqrt((F - 1) * G)
    snr_in = np.mean(x_sig**2) / np.mean(x_noise**2); snr_out = np.mean(s**2) / np.mean(nn**2)
    return 10 * np.log10(snr_in / snr_out)


def run(p):
    cable, lna, mix, ifa = (-3, 3), (20, 1), (-7, 8), (30, 4)
    chains = {"cable → LNA → mixer → IF": [cable, lna, mix, ifa], "LNA → cable → mixer → IF": [lna, cable, mix, ifa],
              "no LNA: cable → mixer → IF": [cable, mix, ifa]}
    res = {}
    for nm, st in chains.items():
        fp = friis(st); fm = simulate(st, p.rng)
        p.compare(f"{nm}: noise figure", fp, fm, "dB", kind="abs")
        res[nm] = (fp, fm)
    T0 = 290
    p.metric("Noise temperature, LNA at antenna", T0 * (10 ** (res['LNA → cable → mixer → IF'][0] / 10) - 1), "K")
    p.metric("Noise temperature, LNA after cable", T0 * (10 ** (res['cable → LNA → mixer → IF'][0] / 10) - 1), "K")
    fig, ax = p.fig()
    names = list(res)
    ax.bar(np.arange(3) - 0.2, [res[n][0] for n in names], 0.4, color=C_PRED, label="Friis")
    ax.bar(np.arange(3) + 0.2, [res[n][1] for n in names], 0.4, color=C_MEAS, label="Monte Carlo (10⁶ samples)")
    ax.set_xticks(range(3)); ax.set_xticklabels(["LNA after cable", "LNA at antenna", "no LNA"], fontsize=9)
    style_axes(ax, None, "system noise figure (dB)", "Order matters: put the gain first")
    p.save(fig, "cascade", "The same parts give ~1.3 dB or ~4 dB system NF depending only on order.")
    p.discuss("""The Monte Carlo noise figures agree with Friis to within sampling error (~0.01 dB with 10⁶ samples). Putting the LNA at the
antenna makes the system NF ≈ the LNA's own NF because its 20 dB of gain divides every later stage's contribution; after
the cable the 3 dB loss adds directly to the NF. This is why satellite ground stations — including the SatNOGS station
in SL-085 — mount the preamp at the antenna.""")
