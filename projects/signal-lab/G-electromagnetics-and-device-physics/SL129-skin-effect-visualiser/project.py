from eelab import *
from scipy.special import jv

META = dict(
    id="SL-129", title="Skin effect in a round copper wire", level="M",
    tools="Finite-difference solution of the 1-D radial diffusion (eddy-current) equation, exact Bessel-function solution",
    summary="Solve for the AC current density inside a 1 mm copper wire from 50 Hz to 10 MHz, compare with the exact "
            "Bessel solution, and track R_ac/R_dc against the high-frequency approximation r/(2δ).",
    problem="Why does a thick wire have more resistance at radio frequencies, and when does it start to matter?",
    theory=r"""Inside a conductor $\nabla^2 J = j\omega\mu\sigma J$; for a round wire $J(r)\propto J_0(kr)$ with $k=(1-j)/\delta$ and skin depth
$\delta=\sqrt{2/(\omega\mu\sigma)}$ (copper: 9.2 mm at 50 Hz, 66 µm at 1 MHz). At high frequency $R_{ac}/R_{dc}\approx\frac{a}{2\delta}+\frac14$.""",
    method="""Wire radius a = 0.5 mm, σ = 5.8×10⁷ S/m. Radial finite differences (400 nodes, symmetric axis condition), complex linear solve per frequency,
J(a) fixed; total current integrated; R_ac = Re(E/I) per length. Compared with the exact J₀ solution and the asymptote.""",
)


def run(p):
    a, sig, mu = 0.5e-3, 5.8e7, 4e-7 * pi
    N = 400
    r = np.linspace(0, a, N); h = r[1]
    freqs = np.logspace(1.7, 7, 25)
    rat_fd, rat_ex = [], []
    for f in freqs:
        w = 2 * pi * f
        A = np.zeros((N, N), complex); b = np.zeros(N, complex)
        A[0, 0] = -4 / h**2 - 1j * w * mu * sig; A[0, 1] = 4 / h**2
        for i in range(1, N - 1):
            A[i, i - 1] = 1 / h**2 - 1 / (2 * h * r[i]); A[i, i] = -2 / h**2 - 1j * w * mu * sig; A[i, i + 1] = 1 / h**2 + 1 / (2 * h * r[i])
        A[-1, -1] = 1; b[-1] = 1.0
        J = np.linalg.solve(A, b)
        I = np.trapezoid(J * 2 * pi * r, r)
        Rac = (1 / sig) / I          # E = J(a)/σ, R = E / I
        Rdc = 1 / (sig * pi * a * a)
        rat_fd.append(np.real(Rac) / Rdc)
        k = (1 - 1j) / np.sqrt(2 / (w * mu * sig))
        Iex = 2 * pi * a * jv(1, k * a) / (k * jv(0, k * a))
        rat_ex.append(np.real((1 / sig) / Iex) / Rdc)
        if abs(f - 1e6) / 1e6 < 0.3:
            Jshow, fshow = J, f
    rat_fd, rat_ex = np.array(rat_fd), np.array(rat_ex)
    delta = lambda f: np.sqrt(2 / (2 * pi * f * mu * sig))
    p.compare("Skin depth of copper at 1 MHz", 66.1e-6, delta(1e6), "m", tol=1)
    k = np.argmin(abs(freqs - 1e6))
    p.compare("R_ac/R_dc at ~1 MHz: FD vs exact Bessel", rat_ex[k], rat_fd[k], "", tol=1)
    p.compare("R_ac/R_dc at 10 MHz vs a/(2δ) + ¼", 0.5e-3 / (2 * delta(1e7)) + 0.25, rat_fd[-1], "", tol=3)
    f1 = freqs[np.argmax(rat_fd > 1.1)]
    p.metric("Frequency where R_ac exceeds R_dc by 10 %", f1, "Hz", "δ ≈ a at this point")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(freqs, rat_ex, "--", color=C_PRED, label="exact (Bessel)")
    ax[0].loglog(freqs, rat_fd, "o", ms=4, color=C_MEAS, label="finite differences")
    ax[0].loglog(freqs, np.maximum(0.5e-3 / (2 * delta(freqs)) + 0.25, 1), ":", color="gray", label="a/2δ + ¼")
    style_axes(ax[0], "frequency (Hz)", "R_ac / R_dc", "AC resistance of a 1 mm wire")
    ax[1].plot(r * 1e3, np.abs(Jshow) / np.abs(Jshow).max(), color=C_MEAS, label=f"|J(r)| at {fshow/1e6:.2f} MHz")
    ax[1].axvline((a - delta(fshow)) * 1e3, color=C_PRED, ls="--", label="one skin depth in from the surface")
    style_axes(ax[1], "r (mm)", "|J| / |J(a)|", "Current crowds to the surface")
    p.save(fig, "skin", "Above ~20 kHz the current retreats to a surface layer a few δ thick.")
    p.csv("rac", freq_hz=freqs, rac_rdc_fd=rat_fd, rac_rdc_exact=rat_ex)
    p.discuss("""The finite-difference solution matches the exact Bessel-function result to well under a percent across five decades, and
at high frequency R_ac/R_dc follows a/(2δ) + ¼. For this 1 mm wire the resistance is flat to ~15 kHz and then rises as √f —
which is why RF inductors use Litz wire (many insulated strands, each thinner than δ) and why high-current RF conductors
are silver-plated tubes: the middle carries almost no current.""")
