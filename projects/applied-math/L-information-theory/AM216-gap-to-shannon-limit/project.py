from eelab import *
from eelab.comms import conv_encode_batch, viterbi_batch
from scipy.special import erfc
from scipy.optimize import brentq
from scipy.special import logsumexp
import importlib.util, glob

META = dict(
    id="AM-216", title="How close do real codes get to the Shannon limit?", level="H",
    tools="Simulated bit-error curves of uncoded BPSK, the K = 7 convolutional code with soft Viterbi decoding, and the (3,6) LDPC code of AM-150 with belief propagation, all rate ≤ ½ on the AWGN channel; the Shannon limit for binary inputs from the constellation-constrained capacity; required E_b/N₀ at BER 10⁻⁵ and the resulting gaps",
    summary="Put three generations of coding on one plot: measure the energy per bit each needs for a bit error rate of 10⁻⁵ and compare with the "
            "theoretical minimum for their rate and modulation, turning the history of channel coding (9.6 dB → 4.4 dB → ≈ 2 dB against 0.2 dB) into numbers.",
    problem="Capacity is a limit nobody reaches exactly. How far away are the codes actually used, and where did the decibels come from?",
    theory=r"""Uncoded BPSK: $P_b=Q(\sqrt{2E_b/N_0})$, 10⁻⁵ at 9.59 dB. For rate R with binary inputs, reliable transmission requires $R<C_{BPSK}(E_s/N_0)$, $E_s=RE_b$; at R = ½ this gives E_b/N₀ ≥ 0.187 dB (and 0 dB without the binary restriction). Allowing a residual bit error $P_b$ relaxes the limit slightly (rate–distortion:
R(1 − H₂(P_b)) < C), negligible at 10⁻⁵. Classic benchmarks at 10⁻⁵: K = 7, rate-½ convolutional code ≈ 4.4 dB (gap ≈ 4.2 dB); rate-½ LDPC codes of a few thousand bits: ≈ 1.5–2 dB; the gap shrinks further with length.""",
    method="""BPSK over AWGN. Convolutional code (171,133)₈, terminated 1000-bit blocks, soft Viterbi, up to 10⁷ bits per point. LDPC: the (3,6) code of length 2000 from AM-150 with sum-product decoding (60 iterations), all-zero codeword, up to 400 blocks per point (a point with no bit errors is entered as ½ error / bits simulated). E_b/N₀ at BER 10⁻⁵
by log-linear interpolation between simulated points. Binary-input Shannon limit by Monte-Carlo mutual information and root finding.""",
)


def bpsk_mi(esn0_db, rng, n=400000):
    s2 = 1 / (2 * 10 ** (esn0_db / 10)); y = 1 + np.sqrt(s2) * rng.normal(size=n)
    return 1 - np.mean(np.logaddexp(0, -2 * y / s2)) / np.log(2)


def at_ber(ebs, bers, target=1e-5):
    bers = np.asarray(bers); ok = bers > 0; x, yv = np.array(ebs)[ok], np.log10(bers[ok])
    i = np.flatnonzero(yv < np.log10(target))
    if not len(i):
        return np.nan
    i = i[0]
    return float(x[i - 1] + (np.log10(target) - yv[i - 1]) * (x[i] - x[i - 1]) / (yv[i] - yv[i - 1]))


def run(p):
    r = p.rng
    lim = brentq(lambda e: bpsk_mi(e, np.random.default_rng(3)) - 0.5, -5, 5) - 10 * np.log10(0.5)
    p.compare("Shannon limit for rate ½ with binary inputs (E_b/N₀)", 0.187, lim, "dB", kind="abs", tol=0.05)
    unc = brentq(lambda e: 0.5 * erfc(np.sqrt(10 ** (e / 10))) - 1e-5, 0, 15)
    p.compare("Uncoded BPSK: E_b/N₀ for BER 10⁻⁵", 9.59, unc, "dB", kind="abs", tol=0.02)
    G = (0o171, 0o133); ebs = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]; cb = []
    for e in ebs:
        sig = np.sqrt(1 / (2 * 0.5 * 10 ** (e / 10))); err = tot = 0; target = 10_000_000 if e >= 4 else 2_000_000
        while tot < target and not (err > 300 and tot > 400000):
            u = r.integers(0, 2, (1000, 1000), dtype=np.int8); y = 1 - 2.0 * conv_encode_batch(u, G, 7) + sig * r.normal(size=(1000, 1006, 2))
            err += int(np.sum(viterbi_batch(y, G, 7)[:, :1000] != u)); tot += u.size
        cb.append(err / tot)
    e_conv = at_ber(ebs, cb)
    p.compare("K = 7 convolutional code, soft Viterbi: E_b/N₀ for BER 10⁻⁵ (textbook ≈ 4.4 dB)", 4.4, e_conv, "dB", kind="abs", tol=0.3)
    path = glob.glob(str(ROOT_DIR() / "projects/applied-math/H-*/AM150*/project.py"))[0]
    spec = importlib.util.spec_from_file_location("ldpc150", path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    Hm, vs, cs = m.build(2000, 3, 6, r); order = np.argsort(vs, kind="stable")
    ebl = [1.4, 1.6, 1.8, 2.0, 2.2, 2.4]; lb = []
    for e in ebl:
        s2 = 1 / (2 * 0.5 * 10 ** (e / 10)); err = tot = 0
        for _ in range(8):
            y = 1 + np.sqrt(s2) * r.normal(size=(50, 2000)); hard, _ = m.bp(2 * y / s2, vs, cs, order, 3, 6)
            err += int(hard.sum()); tot += hard.size
            if err > 200 and tot >= 200000:
                break
        lb.append(max(err, 0.5) / tot)                             # no errors seen: use half an error as an upper-bound estimate
    e_ldpc = at_ber(ebl, lb)
    p.compare("(3,6) LDPC, n = 2000, belief propagation: E_b/N₀ for BER 10⁻⁵ (between the ensemble threshold 1.11 dB and ≈ 2.5 dB)", 1.8, e_ldpc, "dB", kind="abs", tol=0.7)
    p.metric("Gap to the rate-½ binary Shannon limit at BER 10⁻⁵: uncoded (rate 1 limit differs) / convolutional / LDPC", f"{unc - lim:.1f} / {e_conv - lim:.1f} / {e_ldpc - lim:.1f} dB")
    p.metric("Coding gain over uncoded BPSK at BER 10⁻⁵: convolutional / LDPC", f"{unc - e_conv:.1f} / {unc - e_ldpc:.1f} dB")
    p.csv("ber_curves", code=["conv"] * len(ebs) + ["ldpc"] * len(ebl), ebn0_db=ebs + ebl, ber=cb + lb)
    fig, ax = p.fig(1, 1, w=8, h=4.6)
    e_ = np.linspace(0, 11, 200); ax.semilogy(e_, 0.5 * erfc(np.sqrt(10 ** (e_ / 10))), color=COLORS[7], label="uncoded BPSK")
    ax.semilogy(ebs, np.maximum(cb, 1e-9), "o-", color=C_PRED, label="K = 7 conv., soft Viterbi"); ax.semilogy(ebl, np.maximum(lb, 1e-9), "s-", color=C_MEAS, label="(3,6) LDPC, n = 2000")
    ax.axvline(lim, color="k", ls="--", label=f"Shannon limit, R = ½ binary ({lim:.2f} dB)"); ax.axvline(-1.59, color="gray", ls=":", label="ultimate limit −1.59 dB")
    ax.axhline(1e-5, color="gray", lw=.5); ax.set_ylim(1e-7, 0.2); ax.set_xlim(-2, 11)
    style_axes(ax, "E_b/N₀ (dB)", "bit error rate", "Seventy years of coding on one plot")
    p.save(fig, "gap_to_shannon", "Bit-error curves of uncoded, convolutionally coded and LDPC-coded BPSK against the Shannon limits.")
    p.discuss(f"""At a bit error rate of 10⁻⁵ uncoded BPSK needs {unc:.1f} dB. The rate-½ K = 7 convolutional code with soft Viterbi decoding — the 1970s deep-space and
satellite workhorse — needs {e_conv:.1f} dB, a coding gain of {unc - e_conv:.1f} dB but still {e_conv - lim:.1f} dB from the limit of {lim:.2f} dB that no rate-½ binary code can beat.
A modest 2000-bit LDPC code decoded by belief propagation needs {e_ldpc:.1f} dB, closing all but {e_ldpc - lim:.1f} dB; longer and irregular LDPC or turbo codes get within
tenths of a decibel. Each decibel is worth about 26 % of transmit power or 12 % of range, which is why the move from convolutional to iterative
codes in the 1990s–2000s (Wi-Fi, DVB-S2, 5G) mattered so much. The last fraction of a decibel costs block length, i.e. latency.""")


def ROOT_DIR():
    from eelab.core import ROOT
    return ROOT
# tol-convention: relative tolerances are in percent
