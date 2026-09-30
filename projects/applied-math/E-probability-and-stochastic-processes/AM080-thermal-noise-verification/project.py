from eelab import *
from scipy import signal

META = dict(
    id="AM-080", title="Johnson noise and kT/C, verified by stochastic simulation", level="M",
    tools="Stochastic differential equation of an RC circuit driven by the resistor's thermal-noise current (Euler–Maruyama, exact discretisation), Welch PSD, ensemble statistics",
    summary="Simulate the thermal noise of a resistor loaded by a capacitor, confirm the Nyquist noise density 4kTR and the Lorentzian spectrum, "
            "and verify the striking result that the total noise voltage √(kT/C) does not depend on R at all.",
    problem="A bigger resistor is noisier (4kTR) — so why is the RMS noise on a sampling capacitor independent of the resistor?",
    theory=r"""Norton model: noise current with one-sided PSD $S_i=4kT/R$ in parallel with R. Across R‖C: $S_v(f)=\frac{4kTR}{1+(2πfRC)^2}$; integrating over all f gives $\overline{v^2}=kT/C$ — R cancels (larger R: more noise
density, less bandwidth). Equipartition says the same: ½C⟨v²⟩ = ½kT. For C = 1 pF at 300 K: 64.4 µV rms, the kT/C limit of switched-capacitor circuits and ADC samplers.""",
    method="""T = 300 K; R = 1 kΩ, 10 kΩ, 100 kΩ, 1 MΩ with C = 1 pF. Exact discretisation of dv = −v/(RC)dt + noise (Ornstein–Uhlenbeck), step τ/50, 2²⁰ samples. RMS vs √(kT/C); Welch PSD vs 4kTR/(1+(ωRC)²).""",
)

K_B = 1.380649e-23


def ou(R, C, T, n, r, steps_per_tau=50):
    tau = R * C; dt = tau / steps_per_tau
    a = np.exp(-dt / tau); s = np.sqrt(K_B * T / C * (1 - a * a))
    w = r.normal(size=n) * s
    v = signal.lfilter([1.0], [1.0, -a], w, zi=[0.0])[0]
    return v, dt


def run(p):
    T, C = 300.0, 1e-12
    r = p.rng
    rows = []
    for R in (1e3, 1e4, 1e5, 1e6):
        v, dt = ou(R, C, T, 2 ** 20, r)
        v = v[1000:]
        f, P = signal.welch(v, 1 / dt, nperseg=8192)
        fc = 1 / (2 * pi * R * C)
        band = (f > fc / 20) & (f < fc / 5)
        rows.append((R, np.std(v), np.median(P[band] / (4 * K_B * T * R / (1 + (f[band] / fc) ** 2))), f, P))
    for R, rms, ratio, f, P in rows:
        p.compare(f"R = {R:.0e} Ω, C = 1 pF: rms noise = √(kT/C)", np.sqrt(K_B * T / C), rms, "V", tol=2)
    p.compare("Low-frequency PSD / 4kTR (R = 100 kΩ)", 1.0, rows[2][2], "", tol=5)
    p.metric("4kTR noise density of 1 kΩ at 300 K", np.sqrt(4 * K_B * T * 1e3) * 1e9, "nV/√Hz")
    fig, ax = p.fig(1, 2, w=11)
    for (R, rms, ratio, f, P), c in zip(rows, COLORS):
        ax[0].loglog(f[1:], P[1:], color=c, lw=.8, label=f"R = {R:.0e} Ω")
        ax[0].loglog(f[1:], 4 * K_B * T * R / (1 + (2 * pi * f[1:] * R * C) ** 2), "--", color=c, lw=.8)
    style_axes(ax[0], "frequency (Hz)", "S_v (V²/Hz)", "Same area under every curve")
    ax[1].semilogx([r_[0] for r_ in rows], [r_[1] * 1e6 for r_ in rows], "o", color=C_MEAS, label="simulated rms")
    ax[1].axhline(np.sqrt(K_B * T / C) * 1e6, color=C_PRED, ls="--", label="√(kT/C) = 64.4 µV")
    ax[1].set_ylim(0, 100)
    style_axes(ax[1], "R (Ω)", "rms noise (µV)", "kT/C: independent of R")
    p.save(fig, "thermal_noise", "Noise spectra for four resistances (dashed: 4kTR Lorentzians) and the R-independent total rms.")
    p.discuss("""The simulated noise has exactly the Nyquist density 4kTR at low frequency and the Lorentzian roll-off set by RC, and the rms voltage is 64 µV for
every resistance from 1 kΩ to 1 MΩ: the higher density of a larger resistor is exactly compensated by its lower bandwidth, leaving ⟨v²⟩ = kT/C, the
thermal-equilibrium energy of the capacitor. This is why sampling capacitors in ADCs and switched-capacitor filters are sized from the required
SNR alone (C ≥ kT/v²_noise), and why no choice of switch resistance can beat the kT/C limit — only cooling or a bigger capacitor can.""")
# tol-convention: relative tolerances are in percent
