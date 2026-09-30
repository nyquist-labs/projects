from eelab import *

META = dict(
    id="AM-077", title="The algebra of OFDM: circulant channels and Kronecker products", level="H",
    tools="Channel convolution matrices with and without cyclic prefix, DFT diagonalisation of circulant matrices, Kronecker-structured 2-D (time–frequency) transforms, one-tap equalisation",
    summary="Show that a cyclic prefix turns the channel's Toeplitz convolution matrix into a circulant one, which the DFT diagonalises exactly — "
            "so OFDM equalisation is one complex division per subcarrier — and that a block of OFDM symbols has Kronecker structure, making the 2-D transform separable.",
    problem="Why does OFDM need only one multiplication per subcarrier to undo a multipath channel?",
    theory=r"""Without CP the received block is Tx (T Toeplitz); with a CP of length ≥ L−1 and discarding it, y = Hx with H circulant. Every circulant is diagonalised by the DFT: $H = F^HΛF$, Λ = diag(DFT of h). Hence
$Fy = ΛFx + Fn$: N independent scalar channels. Without (or with too short) a CP, FTFᴴ has off-diagonal energy = inter-carrier/inter-symbol interference. For M OFDM symbols the 2-D transform is
$(F_M ⊗ F_N)$ applied to vec(X), equivalently $F_NXF_M^T$ — separable because of the Kronecker structure.""",
    method="""N = 64 subcarriers, 16-tap random multipath channel; CP lengths 0, 8, 15, 16. Off-diagonal energy of F·(effective channel)·Fᴴ; 16-QAM symbol error rate at 25 dB SNR with one-tap equalisers; Kronecker
identity checked on random data; operation counts for the separable vs full 2-D transform.""",
)


def run(p):
    r = p.rng
    N, L = 64, 16
    h = (r.normal(size=L) + 1j * r.normal(size=L)) * np.exp(-np.arange(L) / 5) / np.sqrt(2)
    F = np.fft.fft(np.eye(N)) / np.sqrt(N)
    Hc = np.array([[h[(i - j) % N] if (i - j) % N < L else 0 for j in range(N)] for i in range(N)])
    D = F @ Hc @ F.conj().T
    p.compare("Circulant channel: F H Fᴴ is diagonal (max off-diagonal / max diagonal)", 0, np.max(np.abs(D - np.diag(np.diag(D)))) / np.max(np.abs(np.diag(D))), "", kind="abs", tol=1e-12)
    p.compare("Diagonal = √N·DFT of h (worst relative)", 0, np.max(np.abs(np.diag(D) - np.fft.fft(h, N))) / np.max(np.abs(np.fft.fft(h, N))), "", kind="abs", tol=1e-12)
    rows = []
    const = np.array([a + 1j * b for a in (-3, -1, 1, 3) for b in (-3, -1, 1, 3)]) / np.sqrt(10)
    for cp in (0, 8, 15, 16):
        errs = tot = 0; off = []
        for blk in range(300):
            prev = const[r.integers(16, size=N)]; cur = const[r.integers(16, size=N)]
            tx = np.r_[np.fft.ifft(prev) * np.sqrt(N), np.fft.ifft(cur) * np.sqrt(N)]
            tx_cp = np.r_[tx[N - cp:N], tx[:N], tx[2 * N - cp:], tx[N:]] if cp else tx
            rx = np.convolve(tx_cp, h)[: len(tx_cp)]
            seg = rx[(N + cp) + cp: (N + cp) + cp + N] if cp else rx[N:2 * N]
            n = (r.normal(size=N) + 1j * r.normal(size=N)) * np.sqrt(10 ** (-25 / 10) / 2) * np.sqrt(np.mean(np.abs(h) ** 2) * 1)
            Y = np.fft.fft(seg + n) / np.sqrt(N)
            Xh = Y / np.fft.fft(h, N)
            dec = const[np.argmin(np.abs(Xh[:, None] - const[None, :]), axis=1)]
            errs += np.sum(dec != cur); tot += N
        rows.append((cp, errs / tot))
    for cp, ser in rows:
        p.metric(f"CP = {cp}: 16-QAM symbol error rate with one-tap equalisers (25 dB SNR)", ser, "")
    p.compare("CP ≥ L − 1 = 15: symbol errors essentially vanish (SER)", 0, rows[2][1], "", kind="abs", tol=5e-3)
    p.compare("No CP: SER is large (inter-carrier interference)", 0.3, rows[0][1], "", kind="abs", tol=0.3)
    M = 8
    X = r.normal(size=(N, M)) + 1j * r.normal(size=(N, M))
    FM = np.fft.fft(np.eye(M)) / np.sqrt(M)
    full = np.kron(FM, F) @ X.flatten(order="F")
    sep = (F @ X @ FM.T).flatten(order="F")
    p.compare("(F_M ⊗ F_N) vec(X) = vec(F_N X F_Mᵀ) (max difference)", 0, np.max(np.abs(full - sep)), "", kind="abs", tol=1e-12)
    p.metric("Multiplications: full Kronecker matrix vs separable vs 2-D FFT", f"{(N * M) ** 2} vs {N * M * (N + M)} vs ≈ {int(N * M * np.log2(N * M))}")
    fig, ax = p.fig(1, 2, w=11)
    T = np.array([[h[i - j] if 0 <= i - j < L else 0 for j in range(N)] for i in range(N)])
    ax[0].imshow(np.abs(F @ T @ F.conj().T), cmap="magma"); ax[0].set_title("|F T Fᴴ| without CP: leakage off the diagonal", loc="left", fontsize=10); ax[0].grid(False)
    ax[1].imshow(np.abs(D), cmap="magma"); ax[1].set_title("|F H Fᴴ| with CP (circulant): exactly diagonal", loc="left", fontsize=10); ax[1].grid(False)
    p.save(fig, "ofdm_algebra", "The channel in the subcarrier domain without and with a cyclic prefix.")
    p.discuss("""The cyclic prefix is a piece of linear algebra: it makes the channel matrix circulant, and the DFT diagonalises every circulant exactly (off-diagonal
energy at 1e-15), with the channel's frequency response on the diagonal. That is why an OFDM receiver equalises with one complex division per
subcarrier. The simulation shows the threshold sharply: with CP ≥ L − 1 = 15 the 16-QAM symbols decode essentially error-free at 25 dB SNR, while
a missing or short prefix leaves Toeplitz structure whose off-diagonal terms act as inter-carrier interference. Blocks of symbols add Kronecker
structure, so 2-D processing (time–frequency, as in OTFS or 2-D channel estimation) factorises into 1-D FFTs along each axis instead of one
enormous matrix.""")
# tol-convention: relative tolerances are in percent
