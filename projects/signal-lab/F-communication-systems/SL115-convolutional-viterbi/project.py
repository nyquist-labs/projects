from eelab import *
from eelab.comms import conv_encode, viterbi_decode
from scipy.special import erfc

META = dict(
    id="SL-115", title="Convolutional code + Viterbi decoder: hard vs soft decisions", level="H",
    tools="k = 7, r = ½ encoder and Viterbi decoder (eelab.comms), Monte Carlo over AWGN",
    summary="Measure the coding gain of the NASA-standard k = 7 rate-½ convolutional code with hard- and soft-decision "
            "Viterbi decoding and compare with the union-bound prediction and the classic ~2 dB soft-decision advantage.",
    problem="The Viterbi algorithm finds the most likely transmitted sequence through a trellis. How much does feeding it "
            "analog ('soft') values instead of hard bits help?",
    theory=r"""The (171,133) code has free distance d_free = 10. Soft-decision union bound: $P_b\lesssim\sum_d c_d\,Q(\sqrt{2dRE_b/N_0})$ with leading
spectrum terms $c_{10}=36$, $c_{12}=211$, $c_{14}=1404$. Asymptotic coding gain $10\log_{10}(Rd_{free})$ = 7 dB; soft decisions are
worth ≈ 2 dB over hard decisions (the information lost by quantising to 1 bit).""",
    method="""20,000 information bits per E_b/N₀ point; BPSK over AWGN; hard decoding uses ±1 of the sign, soft uses the raw values.""",
)


def run(p):
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    ebs = np.arange(1, 7.1, 1.0)
    hard, soft = [], []
    for eb in ebs:
        errs_h = errs_s = tot = 0
        for rep in range(3):
            bits = p.rng.integers(0, 2, 20000).astype(np.int8)
            c = conv_encode(bits)
            sig = np.sqrt(1 / (2 * 0.5 * 10 ** (eb / 10)))
            y = (1 - 2 * c.astype(float)) + sig * p.rng.normal(size=len(c))
            errs_s += np.sum(viterbi_decode(y, len(bits)) != bits)
            errs_h += np.sum(viterbi_decode(np.sign(y), len(bits)) != bits)
            tot += len(bits)
        hard.append(errs_h / tot); soft.append(errs_s / tot)
    hard, soft = np.array(hard), np.array(soft)
    R = 0.5
    ub = np.array([sum(cd * Q(np.sqrt(2 * d * R * 10 ** (e / 10))) for d, cd in ((10, 36), (12, 211), (14, 1404))) for e in ebs])
    unc = Q(np.sqrt(2 * 10 ** (ebs / 10)))
    k = list(ebs).index(3.0)
    p.compare("Soft Viterbi BER at 3 dB vs union bound", ub[k], soft[k], "", kind="abs", note="the bound is an upper bound")
    e_s = np.interp(-4, np.log10(np.maximum(soft[::-1], 1e-7)), ebs[::-1])
    e_h = np.interp(-4, np.log10(np.maximum(hard[::-1], 1e-7)), ebs[::-1])
    p.compare("Soft − hard decision gain at BER 10⁻⁴", 2.0, e_h - e_s, "dB", kind="abs")
    from scipy.optimize import brentq
    e_u = brentq(lambda e: Q(np.sqrt(2 * 10 ** (e / 10))) - 1e-4, 0, 15)
    p.metric("Coding gain at 10⁻⁴, soft decisions", e_u - e_s, "dB")
    p.metric("Coding gain at 10⁻⁴, hard decisions", e_u - e_h, "dB")
    fig, ax = p.fig()
    ax.semilogy(ebs, unc, ":", color="gray", label="uncoded BPSK")
    ax.semilogy(ebs, np.maximum(hard, 1e-6), "s-", color=COLORS[1], label="hard-decision Viterbi")
    ax.semilogy(ebs, np.maximum(soft, 1e-6), "o-", color=C_MEAS, label="soft-decision Viterbi")
    ax.semilogy(ebs, np.minimum(ub, 0.5), "--", color=C_PRED, label="union bound (soft)")
    ax.set_ylim(1e-6, 0.5)
    style_axes(ax, "Eb/N0 (dB)", "BER", "k = 7, rate ½ convolutional code")
    p.save(fig, "viterbi", "Soft decisions buy about 2 dB over hard decisions; both beat uncoded BPSK by several dB.")
    p.csv("ber", ebn0_db=ebs, hard=hard, soft=soft, union_bound=ub, uncoded=unc)
    p.discuss("""The soft-decision Viterbi decoder tracks the union bound at moderate SNR (the bound is loose at low SNR where many error
events overlap) and runs about 2 dB ahead of the hard-decision decoder — the textbook price of throwing away the
amplitude information. Neither reaches the 7 dB asymptotic gain at 10⁻⁴ because that figure is only approached at
very low BER.""")
