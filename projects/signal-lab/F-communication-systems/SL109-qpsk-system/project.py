from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-109", title="QPSK: twice the bits, same BER", level="M",
    tools="Monte Carlo (NumPy), Gray-mapped QPSK, constellation and SER theory",
    summary="Show that Gray-coded QPSK carries 2 bits/symbol with exactly the BPSK bit-error rate per E_b/N₀, measure "
            "the symbol error rate against 2Q − Q², and demonstrate the double data rate in the same bandwidth.",
    problem="How can QPSK double the data rate without costing any power efficiency?",
    theory=r"""QPSK = two independent BPSK streams on cos and sin (I and Q). Per bit the energy and noise are unchanged, so
$P_b=Q(\sqrt{2E_b/N_0})$; symbol error $P_s=2Q-Q^2$ with $Q=Q(\sqrt{E_s/N_0})$, $E_s=2E_b$. Spectral efficiency 2 bit/s/Hz (Nyquist)
vs 1 for BPSK.""",
    method="""10⁶ symbols per point, Gray map 00→(+,+), 01→(−,+), 11→(−,−), 10→(+,−), AWGN, minimum-distance decisions.""",
)


def run(p):
    ebs = np.arange(0, 11, 1.0)
    ber, ser = [], []
    for eb in ebs:
        n = 10**6
        b = p.rng.integers(0, 2, (n, 2))
        s = ((1 - 2 * b[:, 0]) + 1j * (1 - 2 * b[:, 1])) / np.sqrt(2)
        N0 = 1 / (2 * 10 ** (eb / 10))                       # Es = 1 = 2 Eb
        y = s + np.sqrt(N0 / 2) * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n)) * np.sqrt(2) / np.sqrt(2)
        y = s + np.sqrt(N0 / 2 * 1) * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n))
        bh = np.c_[y.real < 0, y.imag < 0]
        ber.append(np.mean(bh != b)); ser.append(np.mean(np.any(bh != b, axis=1)))
    ber, ser = np.array(ber), np.array(ser)
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    th_b = Q(np.sqrt(2 * 10 ** (ebs / 10))); q = Q(np.sqrt(2 * 10 ** (ebs / 10))); th_s = 2 * q - q * q
    for eb in (4, 8):
        k = list(ebs).index(eb)
        p.compare(f"QPSK BER at {eb} dB (= BPSK)", th_b[k], ber[k], "", tol=10)
        p.compare(f"QPSK SER at {eb} dB (2Q − Q²)", th_s[k], ser[k], "", tol=10)
    fig, ax = p.fig(1, 2)
    ax[0].semilogy(ebs, th_b, "--", color=C_PRED, label="BPSK/QPSK BER theory")
    ax[0].semilogy(ebs, np.maximum(ber, 1e-7), "o", color=C_MEAS, label="QPSK BER (sim)")
    ax[0].semilogy(ebs, th_s, ":", color=COLORS[2], label="SER theory"); ax[0].semilogy(ebs, np.maximum(ser, 1e-7), "s", color=COLORS[2], ms=4, label="SER (sim)")
    ax[0].set_ylim(1e-6, 1)
    style_axes(ax[0], "Eb/N0 (dB)", "error rate", "QPSK error rates")
    n = 3000; b = p.rng.integers(0, 2, (n, 2)); s = ((1 - 2 * b[:, 0]) + 1j * (1 - 2 * b[:, 1])) / np.sqrt(2)
    y = s + np.sqrt(0.05) * (p.rng.normal(size=n) + 1j * p.rng.normal(size=n))
    ax[1].plot(y.real, y.imag, ".", ms=2, color=C_MEAS); ax[1].set_aspect("equal")
    for lab, pt in (("00", (1, 1)), ("01", (-1, 1)), ("11", (-1, -1)), ("10", (1, -1))):
        ax[1].text(pt[0] / np.sqrt(2) * 1.35, pt[1] / np.sqrt(2) * 1.35, lab, ha="center", fontsize=10)
    style_axes(ax[1], "I", "Q", "Gray-coded constellation (Es/N0 = 10 dB)", legend=False)
    p.save(fig, "qpsk", "Per-bit performance identical to BPSK; one symbol error usually costs only one bit thanks to Gray coding.")
    p.csv("errors", ebn0_db=ebs, ber=ber, ser=ser, ber_theory=th_b, ser_theory=th_s)
    p.discuss("""The measured QPSK BER overlays the BPSK curve exactly — the quadrature carrier is orthogonal, so it is a free second
channel in the same bandwidth. SER is roughly twice the BER at high SNR because Gray mapping makes the most likely
symbol error (to a neighbour) cost one bit out of two. Past QPSK the free lunch ends: 8-PSK and 16-QAM (SL-110) pay in
E_b/N₀ for more bits per symbol.""")
