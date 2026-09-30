from eelab import *
from scipy import signal

META = dict(
    id="AM-081", title="Shot noise: Poisson electrons and the 2qI spectrum", level="M",
    tools="Poisson point-process simulation of electron arrivals, counting statistics (Fano factor), current PSD via Welch, Schottky formula",
    summary="Generate a current as individual electrons arriving at random (a Poisson process), verify the counting statistics (variance = mean), "
            "and show that the resulting current noise is white with density 2qI — Schottky's formula.",
    problem="A DC current through a diode is made of discrete charges. How much noise does that granularity produce?",
    theory=r"""Arrivals at rate λ = I/q in time T: count N ~ Poisson(λT), var N = E N (Fano factor 1). The current is a train of impulses q·δ(t − t_k); its one-sided PSD is $S_I = 2qI$ (plus the DC spike) up to frequencies
~1/(transit time). In bandwidth B: $i_{rms}=\sqrt{2qIB}$ — for 1 mA in 1 MHz, 17.9 nA. Relative noise falls as 1/√I, which is why photodetector SNR improves with signal level.""",
    method="""Currents 1 pA–1 nA simulated as Poisson arrival times in 1 s (1 pA ≈ 6.2 million electrons/s); binned at 1 MHz; count statistics in 1 ms windows; Welch PSD of the binned current compared with 2qI.""",
)

Q = 1.602176634e-19


def run(p):
    r = p.rng
    fs = 1e6; T = 1.0
    rows = []
    for I in (1e-12, 1e-11, 1e-10):
        lam = I / Q
        counts = r.poisson(lam / fs, int(fs * T))
        i = counts * Q * fs
        f, P = signal.welch(i - i.mean(), fs, nperseg=2 ** 14)
        band = (f > 100) & (f < fs / 4)
        w = counts[: int(fs * T) // 1000 * 1000].reshape(-1, 1000).sum(1)
        rows.append((I, np.mean(P[band]) / (2 * Q * I), np.var(w) / np.mean(w), f, P))
    for I, psd_ratio, fano, f, P in rows:
        p.compare(f"I = {I:.0e} A: PSD / 2qI (white, flat band)", 1.0, psd_ratio, "", tol=3)
        p.compare(f"I = {I:.0e} A: Fano factor var(N)/E(N) in 1 ms windows (±√(2/1000) ≈ 4.5 % sampling error)", 1.0, fano, "", tol=10)
    p.metric("Shot noise of 1 mA in 1 MHz", np.sqrt(2 * Q * 1e-3 * 1e6) * 1e9, "nA rms")
    fig, ax = p.fig(1, 2, w=11)
    for (I, _, _, f, P), c in zip(rows, COLORS):
        ax[0].loglog(f[1:], P[1:], color=c, lw=.8, label=f"I = {I:.0e} A"); ax[0].axhline(2 * Q * I, ls="--", color=c, lw=.8)
    style_axes(ax[0], "frequency (Hz)", "S_I (A²/Hz)", "White at 2qI (dashed)")
    ii = np.logspace(-12, -3, 50)
    ax[1].loglog(ii, np.sqrt(2 * Q * ii * 1e6) / ii, color=C_PRED, label="relative shot noise in 1 MHz")
    ax[1].loglog([r_[0] for r_ in rows], [np.sqrt(np.mean(r_[4][(r_[3] > 100) & (r_[3] < 2.5e5)]) * 1e6) / r_[0] for r_ in rows], "o", color=C_MEAS, label="simulated")
    style_axes(ax[1], "DC current (A)", "i_rms / I", "Relative noise falls as 1/√I")
    p.save(fig, "shot_noise", "Current noise spectra of simulated Poisson electron streams and the relative noise vs current.")
    p.discuss("""The simulated electron streams reproduce both faces of shot noise: counts in a window have variance equal to their mean (Fano factor 1, the Poisson
signature), and the current's spectrum is flat at 2qI across the band — Schottky's formula follows directly from charge being discrete and
arrivals independent. The relative noise falls as 1/√I, so small currents are intrinsically noisy: a 1 pA photocurrent carries ~6 million
electrons per second but still fluctuates by 0.6 % in a 1 kHz bandwidth. Real devices can deviate: space-charge in vacuum tubes and correlated
transport in some junctions suppress it (Fano < 1), while avalanche multiplication enhances it (excess noise factor).""")
# tol-convention: relative tolerances are in percent
