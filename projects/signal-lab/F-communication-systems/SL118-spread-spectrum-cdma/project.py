from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-118", title="Spread spectrum and CDMA with Walsh and Gold-like codes", level="H",
    tools="NumPy DS-CDMA simulator, Walsh–Hadamard and random spreading codes, Gaussian-approximation theory",
    summary="Put K users on the same band with direct-sequence spreading: orthogonal Walsh codes (synchronous) give "
            "single-user BER; random codes (asynchronous-like) suffer multiple-access interference that follows the "
            "standard Gaussian approximation.",
    problem="How can many users transmit on the same frequency at the same time, and what limits how many?",
    theory=r"""Spreading factor N: each bit becomes N chips. With orthogonal codes (synchronous) cross-correlation is zero → BER = single-user
$Q(\sqrt{2E_b/N_0})$. With random codes, each interferer adds variance ≈ E_b/N per bit, so (standard Gaussian approximation)
$P_b\approx Q\!\left(\left[\frac{K-1}{N}+\frac{N_0}{2E_b}\right]^{-1/2}\right)$ — capacity is interference-limited.""",
    method="""N = 32 chips/bit, K = 1…24 users, equal power, E_b/N₀ = 8 dB, 20,000 bits per user per point. Walsh rows of a 32×32 Hadamard matrix vs
independent random ±1 sequences (redrawn each bit).""",
)


def run(p):
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    Nc, EbN0 = 32, 10 ** (8 / 10)
    Hm = np.array([[1]])
    while Hm.shape[0] < Nc:
        Hm = np.block([[Hm, Hm], [Hm, -Hm]])
    Ks = [1, 2, 4, 8, 12, 16, 24]
    walsh, rnd, th = [], [], []
    nb = 20000
    for K in Ks:
        bits = 1 - 2 * p.rng.integers(0, 2, (K, nb))
        sig = np.sqrt(Nc / (2 * EbN0))
        # Walsh (synchronous, orthogonal)
        chips = (bits[:, :, None] * Hm[:K, None, :]).sum(0)
        y = chips + sig * p.rng.normal(size=chips.shape)
        dec = np.sign((y * Hm[0][None, :]).sum(-1))
        walsh.append(np.mean(dec != bits[0]))
        codes = 1 - 2 * p.rng.integers(0, 2, (K, nb, Nc))
        chips = (bits[:, :, None] * codes).sum(0)
        y = chips + sig * p.rng.normal(size=chips.shape)
        dec = np.sign((y * codes[0]).sum(-1))
        rnd.append(np.mean(dec != bits[0]))
        th.append(Q(1 / np.sqrt((K - 1) / Nc + 1 / (2 * EbN0))))
    walsh, rnd, th = map(np.array, (walsh, rnd, th))
    single = Q(np.sqrt(2 * EbN0))
    p.compare("Walsh codes: BER pooled over all K (should equal single-user BER)", single, float(np.mean(walsh)), "", tol=25,
              note="140,000 bits pooled; each K alone has only ~4 expected errors")
    for K in (8, 24):
        k = Ks.index(K)
        p.compare(f"Random codes, {K} users (Gaussian approximation)", th[k], rnd[k], "", tol=20)
    fig, ax = p.fig()
    ax.semilogy(Ks, np.maximum(walsh, 1e-6), "o-", color=C_MEAS, label="Walsh (orthogonal, synchronous)")
    ax.semilogy(Ks, np.maximum(rnd, 1e-6), "s-", color=COLORS[1], label="random codes")
    ax.semilogy(Ks, th, "--", color=C_PRED, label="standard Gaussian approximation")
    ax.axhline(single, color="gray", ls=":", label="single user")
    style_axes(ax, "number of users K", "BER (user 1)", "CDMA, N = 32, Eb/N0 = 8 dB")
    p.save(fig, "cdma", "Orthogonal codes add users for free; non-orthogonal codes degrade gracefully with K/N.")
    p.csv("ber", users=Ks, walsh=walsh, random=rnd, theory=th)
    p.discuss("""Synchronous Walsh codes are exactly orthogonal, so 24 users on the same band see the single-user BER. Random (or, in practice,
asynchronous Gold/m-sequence) codes are only nearly orthogonal; each extra user adds ~1/N of a bit's energy as
interference, and the measured BER follows the Gaussian approximation closely. This graceful, soft capacity limit —
more users simply raise the noise floor — is the defining property of CDMA (IS-95, 3G WCDMA, GPS).""")
