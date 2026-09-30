from eelab import *

META = dict(
    id="SL-130", title="Eddy-current loss in solid vs laminated cores", level="H",
    tools="1-D magnetic diffusion in a conducting sheet (finite differences, complex phasors), classical loss formula",
    summary="Compute the eddy-current loss in a steel core sheet driven by an AC field, compare with the low-frequency "
            "formula P = σω²B²t²/24, and show why transformer cores are laminated.",
    problem="A solid iron core in a transformer gets hot. How much does slicing it into thin laminations help, and why?",
    theory=r"""For a sheet of thickness t in a uniform AC field of peak B (thin-sheet limit, t ≪ δ): induced E grows linearly from the
mid-plane, giving loss per volume $P_v=\frac{\sigma\omega^2B^2t^2}{24}$ (average over a cycle, B peak). Loss ∝ t², so N laminations of
thickness t/N reduce it N²-fold. When t ≳ δ the field no longer penetrates (skin effect) and the formula overestimates.""",
    method="""Electrical steel σ = 2×10⁶ S/m, μ_r = 1,000, B surface amplitude 1.0 T, 50 Hz (δ ≈ 0.5 mm). 1-D diffusion $\partial^2H/\partial x^2=j\omega\mu\sigma H$
solved for thickness 0.1–5 mm; loss = ∫|J|²/(2σ) dx per unit area. Fixed flux comparison: solid 5 mm vs 10 × 0.5 mm and 50 × 0.1 mm.""",
)


def sheet_loss(t, f, sig=2e6, mur=1000, B0=1.0, N=401):
    mu = 4e-7 * pi * mur; w = 2 * pi * f
    x = np.linspace(-t / 2, t / 2, N); h = x[1] - x[0]
    A = np.zeros((N, N), complex); b = np.zeros(N, complex)
    for i in range(1, N - 1):
        A[i, i - 1] = A[i, i + 1] = 1 / h**2; A[i, i] = -2 / h**2 - 1j * w * mu * sig
    A[0, 0] = A[-1, -1] = 1; b[0] = b[-1] = B0 / mu
    H = np.linalg.solve(A, b)
    J = np.gradient(H, h)
    Pv = np.trapezoid(np.abs(J) ** 2 / (2 * sig), x) / t
    Bavg = np.abs(np.mean(mu * H))
    return Pv, Bavg


def run(p):
    sig, mur, f = 2e6, 1000, 50.0
    ts = np.array([0.1, 0.2, 0.35, 0.5, 1.0, 2.0, 5.0]) * 1e-3
    rows = []
    for t in ts:
        Pv, Bavg = sheet_loss(t, f)
        pred = sig * (2 * pi * f) ** 2 * Bavg**2 * t**2 / 24
        rows.append((t, Pv, pred, Bavg))
    t_, P_, pr_, B_ = map(np.array, zip(*rows))
    for t in (0.1e-3, 0.35e-3):
        k = np.argmin(abs(t_ - t))
        p.compare(f"Loss density, {t*1e3:.2f} mm sheet (thin-sheet formula)", pr_[k], P_[k], "W/m³", tol=3)
    k5 = np.argmin(abs(t_ - 5e-3))
    p.metric("5 mm sheet: FD loss / thin-sheet formula", P_[k5] / pr_[k5], "", "formula overestimates once t > δ")
    delta = np.sqrt(2 / (2 * pi * f * 4e-7 * pi * mur * sig))
    p.metric("Skin depth in the steel at 50 Hz", delta, "m")
    Ps, _ = sheet_loss(0.5e-3, f)
    Pt, _ = sheet_loss(0.05e-3, f)
    p.compare("Loss reduction from 10× thinner laminations at equal B (∝ t²)", 100, Ps / Pt, "×", tol=5)
    fig, ax = p.fig()
    ax.loglog(t_ * 1e3, pr_, "--", color=C_PRED, label="σω²B²t²/24")
    ax.loglog(t_ * 1e3, P_, "o", color=C_MEAS, ms=7, label="finite-difference diffusion")
    ax.axvline(delta * 1e3, color="gray", ls=":", label="skin depth δ")
    style_axes(ax, "sheet thickness (mm)", "eddy loss (W/m³)", "Why cores are laminated (50 Hz, 1 T)")
    p.save(fig, "eddy", "Loss grows as t² until the sheet is thicker than a skin depth.")
    p.csv("loss", thickness_m=t_, loss_fd=P_, loss_formula=pr_, B_avg=B_)
    p.discuss("""For sheets well below the 0.5 mm skin depth the numerical loss matches σω²B²t²/24, and the t² law means ten 0.5 mm laminations
dissipate one-hundredth of a 5 mm solid sheet's eddy loss… per unit volume, at the same flux. Once t exceeds δ the field no
longer penetrates the middle of the sheet, the formula overestimates the loss and — worse for a transformer — the core's
interior stops carrying flux. Standard 50 Hz electrical steel is therefore rolled to 0.27–0.35 mm.""")
