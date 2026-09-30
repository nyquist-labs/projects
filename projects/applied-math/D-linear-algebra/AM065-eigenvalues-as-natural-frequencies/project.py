from eelab import *
from eelab.circuit import Circuit
import scipy.linalg as sla

META = dict(
    id="AM-065", title="Eigenvalues as natural frequencies of an LC ladder", level="H",
    tools="Generalised eigenproblem K v = ω² M v for an N-section LC ladder, analytic dispersion ω_k = 2ω0 sin(kπ/(2(N+1))), MNA AC resonance search, mode shapes",
    summary="Write the LC ladder's equations as a mass-spring-like matrix problem, predict all N natural frequencies analytically, confirm them "
            "as eigenvalues and as resonance peaks in a circuit simulation, and show the standing-wave mode shapes.",
    problem="A ladder of N identical LC sections has N resonances. Where are they, and what do they look like?",
    theory=r"""With node voltages v_i and all capacitors C to ground, series inductors L between nodes (ends grounded through L): $C\ddot v = -L^{-1}Kv$ where K is the tridiagonal (2, −1) matrix. Eigenvalues of K
are $4\sin^2\frac{kπ}{2(N+1)}$, so $ω_k = \frac{2}{\sqrt{LC}}\sin\frac{kπ}{2(N+1)}$, k = 1…N: a discrete dispersion relation with a cutoff at 2/√(LC). Mode k is a sampled sine $\sin\frac{ikπ}{N+1}$ — a standing wave.""",
    method="""N = 10 sections, L = 10 µH, C = 1 nF (2/√LC → 3.18 MHz). Eigenvalues of M⁻¹K (scipy.linalg.eigh generalised); resonances from peaks of the impedance seen by a 1 A test source at node 1 in an AC sweep
(with 0.1 Ω series loss for finite peaks).""",
)


def run(p):
    N, L, C = 10, 10e-6, 1e-9
    K = (2 * np.eye(N) - np.eye(N, k=1) - np.eye(N, k=-1)) / L
    M = C * np.eye(N)
    w2, V = sla.eigh(K, M)
    wk = np.sqrt(w2)
    k = np.arange(1, N + 1)
    pred = 2 / np.sqrt(L * C) * np.sin(k * pi / (2 * (N + 1)))
    p.compare("Eigenvalue frequencies vs 2/√(LC)·sin(kπ/2(N+1)) (worst relative)", 0, np.max(np.abs(wk / pred - 1)), "", kind="abs", tol=1e-12)
    modes = np.array([np.sin(np.arange(1, N + 1) * kk * pi / (N + 1)) for kk in k]).T
    overlap = min(abs(np.dot(V[:, i], modes[:, i])) / (np.linalg.norm(V[:, i]) * np.linalg.norm(modes[:, i])) for i in range(N))
    p.compare("Mode shapes are sampled sines (min |cos angle| between eigvec and sine)", 1.0, overlap, "", tol=1e-07)
    ck = Circuit("ladder")
    ck.I("t", "0", "n1", ac=1.0)
    prev = "0"
    for i in range(1, N + 1):
        ck.R(f"s{i}", prev, f"m{i}", 0.1); ck.L(f"{i}", f"m{i}", f"n{i}", L); ck.C(f"{i}", f"n{i}", "0", C); prev = f"n{i}"
    ck.R(f"s{N + 1}", prev, f"m{N + 1}", 0.1); ck.L(f"{N + 1}", f"m{N + 1}", "0", L)
    f = np.linspace(20e3, 3.3e6, 60000)
    Z = np.abs(ck.ac(f).v("n1"))
    from scipy.signal import find_peaks
    pk, _ = find_peaks(Z, prominence=Z.max() * 1e-4)
    fs = f[pk]
    p.compare("Resonance peaks found in the AC sweep", N, len(fs), "", kind="abs")
    if len(fs) == N:
        p.compare("AC resonances vs eigenvalues (worst relative)", 0, np.max(np.abs(fs / (wk / (2 * pi)) - 1)), "", kind="abs", tol=2e-3)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(f / 1e6, Z, color=C_MEAS, lw=.8)
    for w in wk:
        ax[0].axvline(w / (2 * pi) / 1e6, color=C_PRED, lw=.6, ls="--")
    style_axes(ax[0], "frequency (MHz)", "|Z| at node 1 (Ω)", "AC resonances (dashed: eigenvalues)", legend=False)
    for i, c in zip((0, 1, 4, 9), COLORS):
        ax[1].plot(np.arange(1, N + 1), V[:, i] / np.abs(V[:, i]).max(), "o-", color=c, label=f"mode {i + 1}")
    style_axes(ax[1], "node", "normalised voltage", "Mode shapes: standing waves")
    p.save(fig, "ladder_modes", "Resonances of the 10-section LC ladder from AC analysis and from eigenvalues, and four mode shapes.")
    p.discuss("""The generalised eigenproblem gives exactly the analytic frequencies ω_k = (2/√LC) sin(kπ/2(N+1)), its eigenvectors are sampled sine waves, and
the circuit simulator's impedance sweep shows ten resonance peaks at the same frequencies. The matrix view explains two practical facts: the modes
bunch up toward the cutoff 2/√(LC) (the discrete dispersion relation of a lumped line — above it nothing propagates, which is why an LC ladder is a
low-pass filter and an artificial transmission line), and the lowest mode's frequency falls as 1/N, approaching the continuous line's λ/2
resonance. The same eigen-analysis applies to mechanical chains and to crystal phonons.""")
# tol-convention: relative tolerances are in percent
