from eelab import *
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

META = dict(
    id="SL-135", title="PN junction from device physics (Poisson + drift-diffusion)", level="H",
    tools="Nonlinear Poisson–Boltzmann solver (Newton), minority-carrier diffusion solver (finite differences)",
    summary="Solve Poisson's equation self-consistently across a silicon p-n junction to get the built-in potential, "
            "depletion width and field, then solve minority-carrier diffusion to build the forward I–V curve; compare "
            "with the depletion approximation and the Shockley diode law.",
    problem="The diode equation I = I_s(e^{V/V_T} − 1) is usually just given. Derive it — and its limits — from the "
            "physics of electrons and holes.",
    theory=r"""Built-in potential $V_{bi}=V_T\ln\frac{N_AN_D}{n_i^2}$; depletion approximation: $W=\sqrt{\frac{2\varepsilon(V_{bi}-V)}{q}\frac{N_A+N_D}{N_AN_D}}$, peak field
$E_{max}=2(V_{bi}-V)/W$. Long-base diode: $I_s=qAn_i^2\left(\frac{D_n}{L_nN_A}+\frac{D_p}{L_pN_D}\right)$, ideality 1.""",
    method="""Si, T = 300 K, N_A = 10¹⁶, N_D = 10¹⁷ cm⁻³, n_i = 9.65×10⁹ cm⁻³, μ_n = 1350, μ_p = 480 cm²/Vs, τ = 1 µs, A = 1 mm². Equilibrium: Poisson with
Boltzmann carriers on a 2,000-point graded grid over 20 µm, Newton iteration. Bias: minority-carrier diffusion equation in each neutral region
solved numerically with law-of-the-junction boundary values, currents summed; compared with Shockley.""",
)

q, kB, T = 1.602e-19, 1.381e-23, 300.0
VT = kB * T / q
eps = 11.7 * 8.854e-14   # F/cm


def run(p):
    NA, ND, ni = 1e16, 1e17, 9.65e9
    L = 20e-4; N = 2000
    x = np.linspace(-L / 2, L / 2, N); h = x[1] - x[0]
    dop = np.where(x < 0, -NA, ND)
    psi = np.where(x < 0, -VT * np.log(NA / ni), VT * np.log(ND / ni))
    for it in range(200):
        n = ni * np.exp(psi / VT); pp = ni * np.exp(-psi / VT)
        rho = q * (pp - n + dop)
        F = np.zeros(N); F[1:-1] = (psi[2:] - 2 * psi[1:-1] + psi[:-2]) / h**2 + rho[1:-1] / eps
        Jd = np.zeros(N); Jd[1:-1] = -2 / h**2 - q * (pp[1:-1] + n[1:-1]) / (VT * eps)
        A = diags([np.r_[np.ones(N - 2) / h**2, 0], np.r_[1, Jd[1:-1], 1], np.r_[0, np.ones(N - 2) / h**2]], [-1, 0, 1]).tocsc()
        F[0] = F[-1] = 0
        d = spsolve(A, -F)
        psi += np.clip(d, -0.2, 0.2)
        if np.max(np.abs(d)) < 1e-10:
            break
    Vbi_num = psi[-1] - psi[0]
    Vbi = VT * np.log(NA * ND / ni**2)
    p.compare("Built-in potential", Vbi, Vbi_num, "V", tol=0.5)
    E = -np.gradient(psi, h)
    W_pred = np.sqrt(2 * eps * Vbi / q * (NA + ND) / (NA * ND))
    n = ni * np.exp(psi / VT); pp = ni * np.exp(-psi / VT)
    dep = (pp < 0.5 * NA) & (n < 0.5 * ND)
    W_num = np.ptp(x[dep])
    p.compare("Depletion width (depletion approximation vs 50 % carrier criterion)", W_pred * 1e-2, W_num * 1e-2, "m", tol=10)
    p.compare("Peak electric field 2V_bi/W", 2 * Vbi / W_pred * 100, np.max(np.abs(E)) * 100, "V/m", tol=10)
    p.metric("Newton iterations", it + 1)
    Dn, Dp = VT * 1350, VT * 480
    tau = 1e-6
    Ln, Lp = np.sqrt(Dn * tau), np.sqrt(Dp * tau)
    A_ = 1e-2
    Is = q * A_ * ni**2 * (Dn / (Ln * NA) + Dp / (Lp * ND))
    Vs = np.linspace(0.2, 0.7, 11); I_num = []
    for V in Vs:
        tot = 0
        for (Dm, Lm, Nm) in ((Dn, Ln, NA), (Dp, Lp, ND)):
            M = 400; xs = np.linspace(0, 10 * Lm, M); hh = xs[1]
            a = diags([np.ones(M - 1), -2 * np.ones(M) - hh**2 / Lm**2, np.ones(M - 1)], [-1, 0, 1]).tolil()
            a[0, :] = 0; a[0, 0] = 1; a[-1, :] = 0; a[-1, -1] = 1
            b = np.zeros(M); b[0] = ni**2 / Nm * (np.exp(V / VT) - 1)
            dn = spsolve(a.tocsc(), b)
            tot += q * A_ * Dm * (-(dn[1] - dn[0]) / hh)
        I_num.append(tot)
    I_num = np.array(I_num)
    I_sh = Is * (np.exp(Vs / VT) - 1)
    k = list(np.round(Vs, 2)).index(0.6)
    p.compare("Forward current at 0.6 V (numerical diffusion vs Shockley)", I_sh[k], I_num[k], "A", tol=3)
    slope = np.polyfit(Vs[3:], np.log10(I_num[3:]), 1)[0]
    p.compare("Ideality factor from the I–V slope", 1.0, 1 / (slope * VT * np.log(10)), "", tol=2)
    p.metric("Saturation current I_s", Is, "A")
    fig, ax = p.fig(2, 2, w=11, h=7)
    xm = x * 1e4
    ax[0][0].plot(xm, psi, color=C_MEAS); style_axes(ax[0][0], None, "ψ (V)", "Electrostatic potential", legend=False)
    ax[0][1].plot(xm, E / 1e3, color=C_MEAS); style_axes(ax[0][1], None, "E (kV/cm)", "Electric field", legend=False)
    ax[1][0].semilogy(xm, n, color=COLORS[0], label="electrons"); ax[1][0].semilogy(xm, pp, color=COLORS[1], label="holes")
    for a_ in (ax[0][0], ax[0][1], ax[1][0]):
        a_.set_xlim(-1, 1)
    style_axes(ax[1][0], "x (µm)", "cm⁻³", "Carrier densities")
    ax[1][1].semilogy(Vs, I_sh, "--", color=C_PRED, label="Shockley"); ax[1][1].semilogy(Vs, I_num, "o", color=C_MEAS, label="diffusion solver")
    style_axes(ax[1][1], "V (V)", "I (A)", "Forward I–V")
    p.save(fig, "junction", "Self-consistent potential, field and carriers, and the resulting diode law.")
    p.csv("equilibrium", x_cm=x[::4], psi_V=psi[::4], E_V_per_cm=E[::4], n=n[::4], p=pp[::4])
    p.discuss("""The self-consistent Poisson solution gives the built-in potential exactly (it must: equilibrium Fermi-level flatness), and
the depletion width (≈ 0.33 µm) and peak field (≈ 47 kV/cm) agree with the depletion approximation within the ambiguity of
where a 'depletion edge' is in a smooth numerical profile — the real carrier profile has Debye-length tails that the
abrupt-edge approximation ignores. Solving the minority-carrier diffusion equations in the neutral regions reproduces
the Shockley law with ideality 1: at low-to-moderate forward bias the diode current is diffusion of injected minority
carriers. Real diodes deviate (n ≈ 1.5–2) because of recombination inside the depletion region and high-injection effects —
both omitted from this model.""")
