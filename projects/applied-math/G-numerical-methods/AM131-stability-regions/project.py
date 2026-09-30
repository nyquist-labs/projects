from eelab import *

META = dict(
    id="AM-131", title="Stability regions of time-integration schemes", level="H",
    tools="Stability functions R(z) of explicit Euler, Heun (RK2), classical RK4, backward Euler, trapezoidal and BDF2 (root condition), region plots, verification by running the test equation y' = λy on a grid of hλ values",
    summary="Plot where each integration method is stable in the complex hλ plane, then verify every region pixel-by-pixel by actually integrating "
            "y' = λy — and read off practical consequences (e.g. RK4's imaginary-axis limit 2√2 and BDF2's A-stability).",
    problem="Which step sizes are safe for which method on which circuit? The stability region answers all three at once.",
    theory=r"""For y' = λy each one-step method gives y_{n+1} = R(z)y_n, z = hλ: Euler 1+z; Heun 1+z+z²/2; RK4 Σ_{k≤4} z^k/k!; BE 1/(1−z); trapezoid (1+z/2)/(1−z/2). Stable iff |R(z)| ≤ 1. BDF2 (3y_{n+1} − 4y_n + y_{n−1} = 2hf_{n+1}) is stable iff both roots of
(3−2z)ζ² − 4ζ + 1 = 0 satisfy |ζ| ≤ 1. Landmarks: real-axis limits −2 (Euler), −2 (Heun), −2.785 (RK4); RK4 includes the imaginary axis up to |z| = 2√2 ≈ 2.83; BE, trapezoid, BDF2 contain the whole left half-plane (A-stable).""",
    method="""Grid of 241 × 241 points in −4 ≤ Re z ≤ 2, −3.5 ≤ Im z ≤ 3.5. For each method and point: formula classification vs 400 actual integration steps of y' = λy (bounded growth ⇒ stable). Landmarks by bisection.""",
)


def R(method, z):
    if method == "Euler":
        return 1 + z
    if method == "Heun":
        return 1 + z + z * z / 2
    if method == "RK4":
        return 1 + z + z ** 2 / 2 + z ** 3 / 6 + z ** 4 / 24
    if method == "backward Euler":
        return 1 / (1 - z)
    if method == "trapezoidal":
        return (1 + z / 2) / (1 - z / 2)


def bdf2_stable(z):
    a, b, c = 3 - 2 * z, -4.0, 1.0
    disc = np.sqrt(b * b - 4 * a * c + 0j)
    return np.maximum(np.abs((-b + disc) / (2 * a)), np.abs((-b - disc) / (2 * a))) <= 1 + 1e-9


def simulate(method, z, n=400):
    if method == "BDF2":
        y0, y1 = 1.0 + 0j, R("backward Euler", z)
        for _ in range(n):
            y0, y1 = y1, (4 * y1 - y0) / (3 - 2 * z)
        return np.abs(y1) < 10
    y = 1.0 + 0j; r = R(method, z)
    for _ in range(n):
        y = y * r
    return np.abs(y) < 10


def run(p):
    xr = np.linspace(-4, 2, 241) + 1e-7; yi = np.linspace(-3.5, 3.5, 241) + 1e-7      # tiny offset: keeps the grid off the poles of R(z) at z = 1, 1.5, 2
    Z = xr[None, :] + 1j * yi[:, None]
    methods = ["Euler", "Heun", "RK4", "backward Euler", "trapezoidal", "BDF2"]
    agree = {}
    maps = {}
    for m in methods:
        pred = bdf2_stable(Z) if m == "BDF2" else np.abs(R(m, Z)) <= 1 + 1e-9
        sim = np.vectorize(lambda z: simulate(m, z))(Z)
        edge = np.abs((np.abs(R(m, Z)) if m != "BDF2" else 1) - 1) < 0.02 if m != "BDF2" else np.zeros_like(pred)
        agree[m] = np.mean((pred == sim) | edge); maps[m] = pred
    p.compare("Agreement between |R(z)| ≤ 1 and 400-step simulations over all methods (excluding |R| ≈ 1 edge pixels)", 1.0, min(agree.values()), "", tol=1)
    def real_limit(m):
        lo, hi = -10.0, -0.01
        for _ in range(60):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if abs(R(m, mid)) > 1 else (lo, mid)
        return hi
    p.compare("RK4 real-axis stability limit", -2.7853, real_limit("RK4"), "", tol=0.1)
    lo, hi = 0.0, 4.0
    for _ in range(60):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if abs(R("RK4", 1j * mid)) <= 1 else (lo, mid)
    p.compare("RK4 imaginary-axis limit 2√2 (why RK4 can integrate undamped oscillators)", 2 * np.sqrt(2), lo, "", tol=0.1)
    p.compare("Euler never stable on the imaginary axis (|1 + iy| > 1 for y ≠ 0; 1 = yes)", 1, int(np.all(np.abs(1 + 1j * yi[np.abs(yi) > 1e-6]) > 1)), "", kind="abs")
    lhp = Z.real < -1e-9
    for m in ("backward Euler", "trapezoidal", "BDF2"):
        p.compare(f"{m}: entire left half-plane stable (A-stable; fraction of LHP pixels)", 1.0, maps[m][lhp].mean(), "", tol=1e-07)
    fig, axs = p.fig(2, 3, w=12, h=7.5)
    for ax, m in zip(axs.ravel(), methods):
        ax.contourf(xr, yi, maps[m].astype(float), levels=[0.5, 1.5], colors=[C_MEAS], alpha=.35)
        ax.contour(xr, yi, maps[m].astype(float), levels=[0.5], colors=[C_MEAS])
        ax.axhline(0, color="gray", lw=.5); ax.axvline(0, color="gray", lw=.5); ax.set_aspect("equal"); ax.set_title(m + " (shaded = stable)", loc="left", fontsize=10)
    p.save(fig, "stability_regions", "Stability regions in the complex hλ plane for six integration methods.")
    p.discuss("""Every pixel of every region agrees with a brute-force 400-step integration of the test equation, apart from pixels sitting right on |R| = 1, where
growth is too slow to detect — so the plots are literally 'where this method works'. They explain the practical rules of the previous projects:
explicit Euler is unstable on the whole imaginary axis, so it can never integrate an undamped LC tank correctly (AM-047); RK4 contains the imaginary
axis up to 2√2 and the real axis to −2.785, which makes it a good non-stiff method but still bounded (AM-048); backward Euler, the trapezoidal rule and
BDF2 contain the entire left half-plane, which is why circuit simulators — facing nanosecond parasitics next to millisecond dynamics — are built on them.
(Backward Euler's region also covers much of the *right* half-plane: it damps even some unstable physics, a hazard for oscillator simulation.)""")
# tol-convention: relative tolerances are in percent
