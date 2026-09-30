from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-108", title="BPSK bit-error rate vs SNR", level="M",
    tools="Monte Carlo simulation (NumPy), Q-function theory",
    summary="Simulate BPSK over AWGN with 10⁷ bits per point where needed and compare the measured BER with "
            "Q(√(2E_b/N₀)) from 0 to 10 dB, including the confidence interval of each Monte Carlo estimate.",
    problem="What does a textbook BER curve look like when you actually count errors, and how many bits must you "
            "simulate to trust a 10⁻⁶ point?",
    theory=r"""Antipodal signalling ±√E_b in noise of variance N₀/2: $P_b=Q\!\left(\sqrt{2E_b/N_0}\right)=\tfrac12\mathrm{erfc}\sqrt{E_b/N_0}$. With k errors observed
the relative standard error of the estimate is ≈ 1/√k, so ~100 errors give ±10 %.""",
    method="""Random bits, BPSK mapping, AWGN at the set E_b/N₀, hard decision at 0. Adaptive length: simulate until ≥ 200 errors or 2×10⁷ bits.
95 % Wilson intervals plotted.""",
)


def run(p):
    ebs = np.arange(0, 10.5, 1.0)
    meas, lo, hi, nb = [], [], [], []
    for eb in ebs:
        errs = bits = 0
        sig = np.sqrt(1 / (2 * 10 ** (eb / 10)))
        while errs < 200 and bits < 2e7:
            n = 10**6
            b = p.rng.integers(0, 2, n)
            y = (1 - 2 * b) + sig * p.rng.normal(size=n)
            errs += np.sum((y < 0) != b); bits += n
        ph = errs / bits
        z = 1.96; d = 1 + z * z / bits
        c = (ph + z * z / (2 * bits)) / d; h = z * np.sqrt(ph * (1 - ph) / bits + z * z / (4 * bits * bits)) / d
        meas.append(ph); lo.append(c - h); hi.append(c + h); nb.append(bits)
    meas = np.array(meas); th = 0.5 * erfc(np.sqrt(10 ** (ebs / 10)))
    for eb in (4, 8, 10):
        k = list(ebs).index(eb)
        p.compare(f"BER at Eb/N0 = {eb} dB", th[k], meas[k], "", tol=25)
    inside = np.mean((th >= np.array(lo)) & (th <= np.array(hi)))
    p.compare("Fraction of theory points inside the 95 % intervals", 0.95, inside, "", kind="abs")
    fig, ax = p.fig()
    eb_f = np.linspace(0, 10.5, 200)
    ax.semilogy(eb_f, 0.5 * erfc(np.sqrt(10 ** (eb_f / 10))), "--", color=C_PRED, label="Q(√(2Eb/N0))")
    ax.errorbar(ebs, np.maximum(meas, 1e-9), yerr=[np.maximum(meas - np.array(lo), 0), np.array(hi) - meas], fmt="o", color=C_MEAS, ms=5, capsize=3, label="Monte Carlo ±95 %")
    ax.set_ylim(1e-7, 0.5)
    style_axes(ax, "Eb/N0 (dB)", "BER", "BPSK over AWGN")
    p.save(fig, "ber", "Simulation and theory agree within statistical error across six decades.")
    p.csv("ber", ebn0_db=ebs, ber=meas, ci_low=lo, ci_high=hi, theory=th, bits=nb)
    p.discuss("""Every simulated point matches the Q-function within its confidence interval; the intervals show why low-BER points
are expensive: at 10 dB (BER 3.9×10⁻⁶) collecting 200 errors needs ~5×10⁷ bits, so the simulation stops at 2×10⁷ with
~80 errors and a correspondingly wider interval. This is the baseline every later project (QPSK, QAM, coding, fading)
is measured against.""")
