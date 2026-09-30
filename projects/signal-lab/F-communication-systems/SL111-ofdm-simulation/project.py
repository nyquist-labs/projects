from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-111", title="OFDM with cyclic prefix over a multipath channel", level="H",
    tools="NumPy OFDM modem (64 subcarriers, IFFT/FFT, cyclic prefix, one-tap equaliser), Monte Carlo",
    summary="Build a Wi-Fi-like OFDM link, pass it through a 6-tap multipath channel, and show that a cyclic prefix "
            "longer than the delay spread turns ISI into a per-subcarrier multiplication; measure BER with and "
            "without CP and the peak-to-average power ratio (PAPR).",
    problem="Why do Wi-Fi, LTE and 5G all use OFDM, and what is the cyclic prefix for?",
    theory=r"""With a cyclic prefix of length L ≥ channel memory, the channel's linear convolution becomes circular, so each subcarrier sees
$Y_k=H_kX_k+N_k$ — one complex tap equalises it. Per subcarrier the BER is that of flat Rayleigh-like fading averaged over
the $|H_k|$ values: $\overline{P_b}=\frac1N\sum_k Q\!\left(\sqrt{2|H_k|^2\frac{N}{N+L}E_b/N_0}\right)$ for known H (E_b counts the energy spent on the
prefix, hence the N/(N+L) factor). Without CP, inter-symbol and inter-carrier
interference create an error floor. PAPR of N subcarriers: $P(\mathrm{PAPR}>x)\approx1-(1-e^{-x})^N$.""",
    method="""N = 64, CP = 16, QPSK, channel taps [0.8, 0.5, 0.3, 0.15, 0.1, 0.05]·e^{jφ} (normalised), perfect channel knowledge; 2,000 OFDM
symbols per E_b/N₀. PAPR CCDF from 20,000 symbols (4× oversampled).""",
)


def run(p):
    N, CP = 64, 16
    h = np.array([0.8, 0.5, 0.3, 0.15, 0.1, 0.05]) * np.exp(1j * p.rng.uniform(0, 2 * pi, 6))
    h /= np.linalg.norm(h)
    H = np.fft.fft(h, N)
    Q = lambda x: 0.5 * erfc(x / np.sqrt(2))
    ebs = np.arange(0, 21, 2.0)
    res = {True: [], False: []}
    for eb in ebs:
        for cp in (True, False):
            nsym = 2000
            b = p.rng.integers(0, 2, (nsym, N, 2))
            X = ((1 - 2 * b[..., 0]) + 1j * (1 - 2 * b[..., 1])) / np.sqrt(2)
            x = np.fft.ifft(X, axis=1) * np.sqrt(N)
            if cp:
                x = np.concatenate([x[:, -CP:], x], axis=1)
            tx = x.ravel()
            rx = np.convolve(tx, h)[: len(tx)]
            Eb = 0.5
            N0 = Eb / 10 ** (eb / 10) * (N + CP) / N if cp else Eb / 10 ** (eb / 10)
            rx = rx + np.sqrt(N0 / 2) * (p.rng.normal(size=len(rx)) + 1j * p.rng.normal(size=len(rx)))
            L = N + CP if cp else N
            y = rx.reshape(nsym, L)[:, CP:] if cp else rx.reshape(nsym, L)
            Y = np.fft.fft(y, axis=1) / np.sqrt(N) / H
            bh = np.stack([Y.real < 0, Y.imag < 0], -1)
            res[cp].append(np.mean(bh != b))
    ber_cp, ber_no = np.array(res[True]), np.array(res[False])
    # the CP carries energy but no data: effective Eb/N0 per subcarrier is reduced by N/(N+CP)
    th = np.array([np.mean(Q(np.sqrt(2 * np.abs(H) ** 2 * 10 ** (eb / 10) * N / (N + CP)))) for eb in ebs])
    for eb in (8, 14):
        k = list(ebs).index(eb)
        p.compare(f"BER with CP at {eb} dB (per-subcarrier Q-average)", th[k], ber_cp[k], "", tol=20)
    p.metric("BER without CP at 20 dB (ISI floor)", ber_no[-1])
    p.metric("CP overhead", CP / (N + CP) * 100, "%", "10·log(80/64) = 0.97 dB energy cost")
    X = ((1 - 2 * p.rng.integers(0, 2, (20000, N))) + 1j * (1 - 2 * p.rng.integers(0, 2, (20000, N)))) / np.sqrt(2)
    Xo = np.zeros((20000, 4 * N), complex); Xo[:, :N // 2] = X[:, :N // 2]; Xo[:, -N // 2:] = X[:, N // 2:]
    xo = np.fft.ifft(Xo, axis=1)
    papr = np.max(np.abs(xo) ** 2, axis=1) / np.mean(np.abs(xo) ** 2, axis=1)
    xs = 10 ** (np.arange(4, 12.1, 0.5) / 10)
    ccdf = np.array([np.mean(papr > x) for x in xs])
    th_c = 1 - (1 - np.exp(-xs)) ** (N * 2.8)
    k9 = np.argmin(abs(10 * np.log10(xs) - 9))
    p.compare("PAPR CCDF at 9 dB", float(th_c[k9]), float(ccdf[k9]), "", kind="abs", note="≈ 2.8N effective samples with 4× oversampling")
    fig, ax = p.fig(1, 2)
    ax[0].semilogy(ebs, th, "--", color=C_PRED, label="theory (known channel)")
    ax[0].semilogy(ebs, np.maximum(ber_cp, 1e-6), "o-", color=C_MEAS, label="with cyclic prefix")
    ax[0].semilogy(ebs, np.maximum(ber_no, 1e-6), "s-", color=COLORS[7], label="no cyclic prefix")
    style_axes(ax[0], "Eb/N0 (dB)", "BER", "OFDM over 6-tap multipath")
    ax[1].semilogy(10 * np.log10(xs), np.maximum(ccdf, 1e-5), "o", color=C_MEAS, label="measured CCDF")
    ax[1].semilogy(10 * np.log10(xs), th_c, "--", color=C_PRED, label="1 − (1 − e^−x)^(2.8N)")
    style_axes(ax[1], "PAPR threshold (dB)", "P(PAPR > x)", "Peak-to-average power")
    p.save(fig, "ofdm", "The CP removes the ISI error floor; OFDM's price is a high PAPR.")
    p.csv("ber", ebn0_db=ebs, ber_cp=ber_cp, ber_no_cp=ber_no, theory=th)
    p.discuss("""With the cyclic prefix the measured BER follows the per-subcarrier average once the prefix's energy cost is included
(my first prediction forgot the N/(N+CP) factor and was ~1 dB optimistic): multipath has become 64 independent
flat channels, each fixed by one complex division. Without the CP the tail of each symbol leaks into the next and the
BER hits an error floor no amount of power removes. The costs of OFDM are visible too: ~1 dB of energy spent on the CP
and a PAPR that exceeds 9 dB a percent of the time, which forces power amplifiers to back off.""")
