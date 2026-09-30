from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-117", title="AWGN, Rayleigh and Rician fading channels", level="M",
    tools="Monte Carlo BPSK (NumPy), closed-form fading BER, Jakes Doppler spectrum",
    summary="Compare BPSK over AWGN, Rayleigh and Rician (K = 3, 10) flat fading: verify the closed-form average BERs, show "
            "the 1/SNR slope that makes fading so costly, and generate a time-correlated Rayleigh process with the Jakes "
            "spectrum.",
    problem="A phone's signal fades in and out as it moves. How much extra power does fading cost at a target error rate?",
    theory=r"""Rayleigh: $\bar P_b=\tfrac12\left(1-\sqrt{\frac{\bar\gamma}{1+\bar\gamma}}\right)\approx\frac1{4\bar\gamma}$ — BER falls only as 1/SNR (vs exponentially on AWGN), so
10⁻⁴ needs ~34 dB instead of 8.4 dB. Rician with K-factor K interpolates between the two. Jakes: Doppler spectrum
$S(f)\propto1/\sqrt{1-(f/f_D)^2}$, envelope autocorrelation $J_0(2\pi f_D\tau)$.""",
    method="""10⁶ symbols per point, coherent detection with perfect channel knowledge. Rician BER by numerical averaging of Q over the Rician
distribution. Jakes process by sum-of-sinusoids (64 paths), f_D = 100 Hz.""",
)


def run(p):
    from scipy.special import j0
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    snr = np.arange(0, 41, 4.0)
    res = {}
    for name, K in (("AWGN", np.inf), ("Rician K=10", 10), ("Rician K=3", 3), ("Rayleigh", 0)):
        ber = []
        for s in snr:
            n = 10**6
            if np.isinf(K):
                h = np.ones(n)
            else:
                los = np.sqrt(K / (K + 1)); sc = np.sqrt(1 / (2 * (K + 1)))
                h = np.abs(los + sc * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n)))
            b = p.rng.integers(0, 2, n)
            y = h * (1 - 2 * b) + np.sqrt(1 / (2 * 10 ** (s / 10))) * p.rng.normal(size=n)
            ber.append(np.mean((y < 0) != b))
        res[name] = np.array(ber)
    g = 10 ** (snr / 10)
    th_ray = 0.5 * (1 - np.sqrt(g / (1 + g)))
    for s in (12, 24):
        k = list(snr).index(s)
        p.compare(f"Rayleigh BER at {s} dB", th_ray[k], res["Rayleigh"][k], "", tol=10)
    e_awgn = 8.4
    e_ray = 10 * np.log10(1 / (4 * 1e-4))
    p.compare("Rayleigh: SNR for BER 10⁻⁴ (≈ 1/(4γ))", e_ray, float(np.interp(-4, np.log10(np.maximum(res["Rayleigh"][::-1], 1e-7)), snr[::-1])), "dB", kind="abs")
    p.metric("Fading margin at 10⁻⁴ (Rayleigh − AWGN)", e_ray - e_awgn, "dB")
    fd, fs, N = 100.0, 10000.0, 200000
    t = np.arange(N) / fs
    M = 64
    th = p.rng.uniform(0, 2 * pi, M); ph = p.rng.uniform(0, 2 * pi, M)
    hj = np.sum(np.exp(1j * (2 * pi * fd * np.cos(th)[:, None] * t[None, :] + ph[:, None])), axis=0) / np.sqrt(M)
    ac = np.correlate(hj[:20000], hj[:20000], "full")[19999:19999 + 400] / np.sum(np.abs(hj[:20000]) ** 2)
    tau = np.arange(400) / fs
    p.compare("Jakes autocorrelation first null τ (J₀ zero at 2.405/(2πf_D))", 2.405 / (2 * pi * fd), tau[np.argmax(np.real(ac) < 0)], "s", tol=5)
    fig, ax = p.fig(1, 2)
    for i, (name, ber) in enumerate(res.items()):
        ax[0].semilogy(snr, np.maximum(ber, 1e-6), "o", color=COLORS[i], ms=4, label=f"{name} (sim)")
    ax[0].semilogy(snr, Q(np.sqrt(2 * g)), "--", color=COLORS[0], lw=1)
    ax[0].semilogy(snr, th_ray, "--", color=COLORS[3], lw=1, label="Rayleigh theory")
    ax[0].set_ylim(1e-6, 0.5)
    style_axes(ax[0], "average SNR (dB)", "BER", "BPSK in fading")
    ax[1].plot(t[:3000] * 1e3, 20 * np.log10(np.abs(hj[:3000])), color=C_MEAS)
    style_axes(ax[1], "time (ms)", "|h| (dB)", "Rayleigh fading at 100 Hz Doppler", legend=False)
    p.save(fig, "fading", "Fading turns the waterfall into a straight 1/SNR line; deep fades of −20 to −30 dB occur every few ms.")
    p.csv("ber", snr_db=snr, **{k.replace(" ", "_").replace("=", ""): v for k, v in res.items()})
    p.discuss("""Rayleigh BER matches the closed form and falls only one decade per 10 dB: reaching 10⁻⁴ costs ~26 dB more than on an AWGN
channel. A line-of-sight component (Rician K) recovers much of that. The Jakes simulation shows why: the channel
spends a small fraction of time in 20–30 dB fades, and those fades cause almost all errors — which is why real systems
use diversity (multiple antennas, interleaving + coding, OFDM with coding across subcarriers) rather than more power.""")
