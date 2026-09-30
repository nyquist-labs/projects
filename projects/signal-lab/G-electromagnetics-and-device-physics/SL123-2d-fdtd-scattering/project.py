from eelab import *

META = dict(
    id="SL-123", title="2-D FDTD: diffraction through a slit", level="H",
    tools="2-D TMz Yee FDTD with PML-style absorbing sponge (NumPy)",
    summary="Send a plane wave through a slit in a perfectly conducting wall and measure the far-field diffraction "
            "pattern; compare null angles with sin θ = mλ/a and the intensity profile with the single-slit sinc².",
    problem="Why does a wave spread out after a narrow opening? Solve Maxwell's equations on a grid and check against "
            "Fraunhofer diffraction.",
    theory=r"""Single slit of width a illuminated by a plane wave: far-field intensity $I(\theta)\propto\mathrm{sinc}^2\!\left(\frac{a\sin\theta}{\lambda}\right)$, first nulls at
$\sin\theta=\pm\lambda/a$. With a = 3λ: nulls at ±19.5°, second nulls at ±41.8°.""",
    method="""TMz Yee grid, λ = 20 cells, Courant 0.5, 500×600 cells, conducting wall (E_z = 0) with a 60-cell (3λ) opening, continuous-wave line source
with a soft ramp, graded conductivity sponge at the edges. After steady state, time-averaged |E_z|² sampled on a semicircle of radius 12λ
behind the slit.""",
)


def run(p):
    nx, ny = 500, 600
    lam = 20.0
    S = 0.5
    Ez = np.zeros((nx, ny)); Hx = np.zeros((nx, ny)); Hy = np.zeros((nx, ny))
    sig = np.zeros((nx, ny)); w = 40
    for i in range(w):
        s_ = 0.5 * ((w - i) / w) ** 3
        sig[i, :] = np.maximum(sig[i, :], s_); sig[-1 - i, :] = np.maximum(sig[-1 - i, :], s_)
        sig[:, i] = np.maximum(sig[:, i], s_); sig[:, -1 - i] = np.maximum(sig[:, -1 - i], s_)
    ca = (1 - sig) / (1 + sig); cb = S / (1 + sig)
    wall = 150; a = int(3 * lam)
    mask = np.ones((nx, ny)); mask[wall, :] = 0; mask[wall, ny // 2 - a // 2: ny // 2 + a // 2] = 1
    acc = np.zeros((nx, ny)); nsteps = 1600
    for n in range(nsteps):
        Hx[:, :-1] -= S * (Ez[:, 1:] - Ez[:, :-1])
        Hy[:-1, :] += S * (Ez[1:, :] - Ez[:-1, :])
        curl = np.zeros_like(Ez)
        curl[1:, 1:] = (Hy[1:, 1:] - Hy[:-1, 1:]) - (Hx[1:, 1:] - Hx[1:, :-1])
        Ez = ca * Ez + cb * curl
        Ez[60, 50:-50] += np.sin(2 * pi * n * S / lam) * min(1, n / 200)
        Ez *= mask
        if n > nsteps - int(4 * lam / S):
            acc += Ez**2
    R = 12 * lam
    th = np.radians(np.linspace(-70, 70, 281))
    xs = wall + R * np.cos(th); ys = ny / 2 + R * np.sin(th)
    I = np.array([acc[int(round(x)), int(round(y))] for x, y in zip(xs, ys)])
    I /= I.max()
    thd = np.degrees(th)
    pred = np.sinc(3 * np.sin(th)) ** 2
    sm = np.convolve(I, np.ones(5) / 5, "same")
    k0 = np.argmax(sm)
    right = k0
    while right + 1 < len(sm) and sm[right + 1] <= sm[right]:
        right += 1
    left = k0
    while left - 1 >= 0 and sm[left - 1] <= sm[left]:
        left -= 1
    null = (thd[right] - thd[left]) / 2
    p.compare("First diffraction null angle (sin θ = λ/a)", np.degrees(np.arcsin(1 / 3)), null, "°", tol=10)
    fwhm_m = np.sum(sm > 0.5) * (thd[1] - thd[0])
    fwhm_p = np.sum(pred > 0.5) * (thd[1] - thd[0])
    p.compare("Main-lobe full width at half maximum", fwhm_p, fwhm_m, "°", tol=15)
    fig, ax = p.fig(1, 2, w=11)
    im = ax[0].imshow(np.sqrt(acc).T, origin="lower", cmap="magma", aspect="equal")
    ax[0].plot(xs, ys, "--", color="white", lw=.8); ax[0].axvline(wall, color="cyan", lw=1)
    ax[0].set_title("time-averaged |E_z| (slit a = 3λ)", loc="left"); ax[0].axis("off")
    ax[1].plot(thd, I, color=C_MEAS, label="FDTD (r = 12λ)")
    ax[1].plot(thd, pred, "--", color=C_PRED, label="sinc²(a sinθ/λ)")
    style_axes(ax[1], "angle (°)", "normalised intensity", "Diffraction pattern")
    p.save(fig, "slit", "The field fans out behind the slit with nulls where Fraunhofer theory puts them.")
    p.csv("pattern", theta_deg=thd, intensity=I, fraunhofer=pred)
    p.discuss("""The main lobe and first nulls land near the Fraunhofer prediction. Differences are expected: the observation circle at
12λ is not fully in the far field (a²/λ = 9λ, so we are just past the Fraunhofer distance), the sponge boundaries are not
perfectly absorbing, and a thin PEC wall with a 3λ slit also supports edge-diffracted waves the scalar sinc² ignores. The
2-D simulation is the same Yee algorithm as SL-122 extended by one dimension.""")
