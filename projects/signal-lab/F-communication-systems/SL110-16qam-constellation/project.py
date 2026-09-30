from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-110", title="16-QAM: constellation, EVM and symbol errors", level="M",
    tools="Monte Carlo (NumPy), square-QAM SER theory, EVM measurement",
    summary="Transmit Gray-mapped 16-QAM through AWGN, watch the constellation blur as SNR falls, and compare measured "
            "SER and EVM with 4(1−1/√M)Q(√(3E_s/((M−1)N₀))) and EVM = 1/√SNR.",
    problem="16-QAM carries 4 bits per symbol. How much more SNR does it need than QPSK, and how do engineers measure "
            "signal quality from a constellation?",
    theory=r"""Square M-QAM: $P_s\approx 1-\left(1-2(1-\tfrac1{\sqrt M})Q\!\left(\sqrt{\tfrac{3E_s}{(M-1)N_0}}\right)\right)^2$. For M = 16 the minimum distance at
equal average energy is √(2/5)·√(2/…)… i.e. ~7 dB worse than QPSK at the same SER per symbol, ~4 dB per bit. Error-vector
magnitude (RMS) = $1/\sqrt{E_s/N_0}$ when noise is the only impairment.""",
    method="""10⁶ symbols per point, normalised to E_s = 1, Gray mapping per axis, minimum-distance decisions. EVM = √(mean|y−s|²/mean|s|²).""",
)


def run(p):
    lv = np.array([-3, -1, 1, 3]) / np.sqrt(10)
    esn0 = np.arange(6, 23, 2.0)
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    ser, evm, th = [], [], []
    for es in esn0:
        n = 10**6
        i = p.rng.integers(0, 4, n); q = p.rng.integers(0, 4, n)
        s = lv[i] + 1j * lv[q]
        N0 = 10 ** (-es / 10)
        y = s + np.sqrt(N0 / 2) * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n))
        ih = np.argmin(np.abs(y.real[:, None] - lv[None, :]), axis=1); qh = np.argmin(np.abs(y.imag[:, None] - lv[None, :]), axis=1)
        ser.append(np.mean((ih != i) | (qh != q)))
        evm.append(np.sqrt(np.mean(np.abs(y - s) ** 2) / np.mean(np.abs(s) ** 2)))
        pa = 2 * (1 - 1 / 4) * Q(np.sqrt(3 * 10 ** (es / 10) / 15))
        th.append(1 - (1 - pa) ** 2)
    ser, evm, th = map(np.array, (ser, evm, th))
    for es in (14, 18):
        k = list(esn0).index(es)
        p.compare(f"SER at Es/N0 = {es} dB", th[k], ser[k], "", tol=10)
    k = list(esn0).index(20)
    p.compare("EVM at Es/N0 = 20 dB (= 1/√SNR)", 10 ** (-20 / 20), evm[k], "", tol=2)
    p.metric("Extra Es/N0 needed vs QPSK for SER 10⁻³", float(np.interp(-3, np.log10(th[::-1]), esn0[::-1]) - 10 * np.log10(2 * 3.0902**2 / 1 / 2)), "dB")
    fig, ax = p.fig(1, 3, w=12, h=4)
    for a_, es in zip(ax[:2], (22, 12)):
        n = 4000; i = p.rng.integers(0, 4, n); q = p.rng.integers(0, 4, n); s = lv[i] + 1j * lv[q]
        y = s + np.sqrt(10 ** (-es / 10) / 2) * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n))
        a_.plot(y.real, y.imag, ".", ms=1.5, color=C_MEAS); a_.set_aspect("equal"); a_.set_xlim(-1.5, 1.5); a_.set_ylim(-1.5, 1.5)
        style_axes(a_, "I", "Q", f"Es/N0 = {es} dB", legend=False)
    ax[2].semilogy(esn0, th, "--", color=C_PRED, label="theory"); ax[2].semilogy(esn0, np.maximum(ser, 1e-7), "o", color=C_MEAS, label="simulated")
    style_axes(ax[2], "Es/N0 (dB)", "SER", "16-QAM symbol errors")
    p.save(fig, "qam16", "As SNR falls the 16 clouds merge; SER follows the square-QAM formula.")
    p.csv("ser", esn0_db=esn0, ser=ser, ser_theory=th, evm=evm)
    p.discuss("""SER matches the square-QAM expression and EVM equals 1/√SNR, which is why EVM is the standard 'one number' quality
metric for Wi-Fi and LTE transmitters (e.g. 16-QAM requires EVM better than ~−19 dB). Packing 16 points into the same
average energy shrinks their spacing, costing roughly 7 dB of E_s/N₀ relative to QPSK for the same symbol-error rate.""")
