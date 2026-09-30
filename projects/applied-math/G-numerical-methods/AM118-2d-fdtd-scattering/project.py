from eelab import *

META = dict(
    id="AM-118", title="2-D FDTD: diffraction through a slit", level="H",
    tools="TMz Yee scheme (E_z, H_x, H_y), perfectly conducting screen with a slit, convolutional absorbing layer (graded-conductivity PML-like sponge), far-field angular pattern, single-slit diffraction formula",
    summary="Extend FDTD to two dimensions, send a monochromatic plane wave through a slit in a metal screen, and compare the simulated angular "
            "intensity pattern and the first diffraction minimum with the single-slit prediction.",
    problem="Can a direct simulation of Maxwell's equations reproduce the textbook diffraction pattern — and where does the textbook approximation fail?",
    theory=r"""Fraunhofer single slit of width a: $I(θ)∝\mathrm{sinc}^2\!\left(\frac{a\sinθ}{λ}\right)$, minima at sin θ = mλ/a. For a = 3λ: first minimum at 19.5°. The Fraunhofer formula assumes the observation distance ≫ a²/λ and a scalar, thin screen; FDTD solves the full vector problem, so small
differences are expected near grazing angles. Stability in 2-D: S ≤ 1/√2.""",
    method="""Grid 600 × 400 cells, λ = 20 cells (a = 60 cells), S = 0.5; soft line source generating a plane wave; PEC screen (E_z = 0) with slit; 30-cell graded-σ absorbing border; run to steady state (1600 steps);
time-averaged |E_z|² on an arc of radius 250 cells beyond the slit vs sinc².""",
)


def run(p):
    nx, ny = 600, 400; lam = 20.0; S = 0.5
    Ez = np.zeros((nx, ny)); Hx = np.zeros((nx, ny - 1)); Hy = np.zeros((nx - 1, ny))
    npml = 30
    sig = np.zeros((nx, ny))
    for k in range(npml):
        v = 0.3 * ((npml - k) / npml) ** 3
        sig[k, :] = np.maximum(sig[k, :], v); sig[-1 - k, :] = np.maximum(sig[-1 - k, :], v); sig[:, k] = np.maximum(sig[:, k], v); sig[:, -1 - k] = np.maximum(sig[:, -1 - k], v)
    ca = (1 - sig) / (1 + sig); cb = S / (1 + sig)
    screen_x = 150; a = 60
    pec = np.zeros((nx, ny), bool); pec[screen_x, :] = True; pec[screen_x, ny // 2 - a // 2: ny // 2 + a // 2] = False
    acc = np.zeros((nx, ny)); w = 2 * pi / (lam / S)
    steps = 1600
    for t in range(steps):
        Hx = Hx - S * (Ez[:, 1:] - Ez[:, :-1])
        Hy = Hy + S * (Ez[1:, :] - Ez[:-1, :])
        Ez[1:-1, 1:-1] = ca[1:-1, 1:-1] * Ez[1:-1, 1:-1] + cb[1:-1, 1:-1] * ((Hy[1:, 1:-1] - Hy[:-1, 1:-1]) - (Hx[1:-1, 1:] - Hx[1:-1, :-1]))
        Ez[60, npml:-npml] += np.sin(w * t) * min(1, t / 100)
        Ez[pec] = 0
        if t > steps - 2 * lam / S:
            acc += Ez ** 2
    R = 250
    th = np.deg2rad(np.linspace(-60, 60, 241))
    xs = (screen_x + R * np.cos(th)).astype(int); ys = (ny // 2 + R * np.sin(th)).astype(int)
    ok = (xs < nx - npml) & (ys > npml) & (ys < ny - npml)
    I = acc[xs[ok], ys[ok]]; thd = np.rad2deg(th[ok]); I /= I.max()
    pred = np.sinc(a / lam * np.sin(np.deg2rad(thd))) ** 2
    from scipy.signal import find_peaks
    mins, _ = find_peaks(-I)
    first_min = np.min(np.abs(thd[mins][np.abs(thd[mins]) > 5])) if len(mins) else np.nan
    p.compare("First diffraction minimum angle: arcsin(λ/a) for a = 3λ", np.degrees(np.arcsin(1 / 3)), first_min, "°", kind="abs", tol=2.0)
    central = np.abs(thd) < 12
    p.compare("Central lobe shape: correlation of simulated and sinc² intensity (|θ| < 12°)", 1.0, np.corrcoef(I[central], pred[central])[0, 1], "", tol=2)
    p.metric("Observation radius vs Fraunhofer distance a²/λ", f"{R} cells vs {a * a / lam:.0f} cells", "", "only moderately far-field")
    fig, ax = p.fig(1, 2, w=12, h=4.2)
    im = ax[0].imshow(np.sqrt(acc).T, origin="lower", cmap="magma", extent=[0, nx, 0, ny]); ax[0].axvline(screen_x, color="w", lw=.8)
    ax[0].set_title("Time-averaged |E_z| (slit width 3λ)", loc="left", fontsize=10); ax[0].grid(False)
    ax[1].plot(thd, I, color=C_MEAS, label="FDTD"); ax[1].plot(thd, pred, "--", color=C_PRED, label="Fraunhofer sinc²")
    style_axes(ax[1], "angle θ (°)", "normalised intensity", "Angular pattern at r = 250 cells")
    p.save(fig, "fdtd2d", "Field intensity behind the slit and the angular pattern vs the single-slit formula.")
    p.discuss(f"""The two-dimensional Yee scheme reproduces single-slit diffraction from first principles: the simulated angular intensity has its central lobe shaped
like sinc² and its first minimum at ≈ {first_min:.1f}°, against 19.5° from sin θ = λ/a. Differences in the side lobes are expected and informative: the
observation arc (250 cells) is only about 1.4 Fraunhofer distances away, so the pattern is not yet fully far-field; the screen is a perfect conductor
of finite thickness rather than a scalar aperture, and the wave is polarised along the slit (TM), which changes edge diffraction. The graded
absorbing border is crude — a proper PML would reduce the residual reflections that add ripple.""")
# tol-convention: relative tolerances are in percent
