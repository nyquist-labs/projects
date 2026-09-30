from eelab import *

META = dict(
    id="SL-128", title="Biot–Savart: coils and the Helmholtz pair", level="M",
    tools="Numerical Biot–Savart integration over discretised wire loops (NumPy)",
    summary="Integrate the Biot–Savart law over discretised loops to map the magnetic field of a single coil and a "
            "Helmholtz pair; verify the on-axis formula and the famous uniformity of coils spaced one radius apart.",
    problem="How do you make a region of uniform magnetic field, and how uniform is it really?",
    theory=r"""On the axis of a loop of radius R carrying I: $B_z(z)=\frac{\mu_0IR^2}{2(R^2+z^2)^{3/2}}$. Two coaxial loops separated by R (Helmholtz)
cancel the second derivative at the midpoint: $B=\left(\frac45\right)^{3/2}\frac{\mu_0I}{R}$ at the centre, and the leading deviation on
axis is $-\frac{144}{125}\left(\frac zR\right)^4$ — under 0.2 % at z = ±0.2R.""",
    method="""R = 5 cm, I = 1 A, 720 segments per loop; field at 2-D grids in the x–z plane by summing μ₀I dl × r/(4π|r|³). Uniformity: region where
|B − B₀|/B₀ < 1 %.""",
)


def loop_field(R, z0, pts, I=1.0, N=720):
    mu0 = 4e-7 * pi
    t = np.linspace(0, 2 * pi, N, endpoint=False)
    src = np.stack([R * np.cos(t), R * np.sin(t), np.full(N, z0)], 1)
    dl = np.stack([-R * np.sin(t), R * np.cos(t), np.zeros(N)], 1) * (2 * pi / N)
    B = np.zeros((len(pts), 3))
    for s, d in zip(src, dl):
        r = pts - s
        rn = np.linalg.norm(r, axis=1)[:, None]
        B += np.cross(d, r) / rn**3
    return mu0 * I / (4 * pi) * B


def run(p):
    R = 0.05; mu0 = 4e-7 * pi
    z = np.linspace(-0.15, 0.15, 121)
    pts = np.stack([np.zeros_like(z), np.zeros_like(z), z], 1)
    Bz = loop_field(R, 0.0, pts)[:, 2]
    th = mu0 * R**2 / (2 * (R**2 + z**2) ** 1.5)
    p.compare("Single loop: B at centre", mu0 / (2 * R), Bz[60], "T", tol=0.1)
    p.compare("Single loop: max on-axis error vs formula", 0, np.max(np.abs(Bz - th) / th.max()), "", kind="abs")
    Bh = loop_field(R, -R / 2, pts)[:, 2] + loop_field(R, R / 2, pts)[:, 2]
    B0 = (4 / 5) ** 1.5 * mu0 / R
    p.compare("Helmholtz pair: B at centre", B0, Bh[60], "T", tol=0.1)
    dev = np.abs(Bh / Bh[60] - 1)
    zr = np.abs(z[dev < 0.01]).max()
    p.metric("On-axis ±1 % uniform region", 2 * zr / R, "× R")
    p.compare("Deviation at z = 0.2R (Taylor: (144/125)(z/R)⁴)", 144 / 125 * 0.2**4, float(np.interp(0.2 * R, z, dev)), "", tol=10)
    xs = np.linspace(-0.1, 0.1, 81); zs = np.linspace(-0.1, 0.1, 81)
    X, Z = np.meshgrid(xs, zs)
    P = np.stack([X.ravel(), np.zeros(X.size), Z.ravel()], 1)
    B = loop_field(R, -R / 2, P, N=360) + loop_field(R, R / 2, P, N=360)
    Bx, Bzz = B[:, 0].reshape(X.shape), B[:, 2].reshape(X.shape)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].streamplot(xs * 100, zs * 100, Bx, Bzz, color=np.log10(np.hypot(Bx, Bzz)), cmap="viridis", density=1.2, linewidth=.8)
    for zc in (-R / 2, R / 2):
        ax[0].plot([-R * 100, R * 100], [zc * 100] * 2, "o", color=C_PRED, ms=6)
    ax[0].set_aspect("equal"); ax[0].set_title("Helmholtz pair field lines (x–z plane)", loc="left", fontsize=10)
    ax[0].set_xlabel("x (cm)"); ax[0].set_ylabel("z (cm)")
    ax[1].plot(z / R, Bz / Bz[60], color=COLORS[1], label="single loop")
    ax[1].plot(z / R, Bh / Bh[60], color=C_MEAS, label="Helmholtz pair")
    ax[1].set_xlim(-1.5, 1.5)
    style_axes(ax[1], "z / R", "B_z / B_z(0)", "On-axis uniformity")
    p.save(fig, "helmholtz", "Spacing the coils one radius apart flattens the field around the centre.")
    p.csv("on_axis", z_m=z, B_single_T=Bz, B_helmholtz_T=Bh, B_single_theory=th)
    p.discuss("""The numerical Biot–Savart integral reproduces the on-axis closed form to 10⁻⁶ relative error with 720 segments, and the
Helmholtz pair's centre field equals (4/5)^{3/2} μ₀I/R. Its flatness is the point: the deviation grows only as (z/R)⁴, so the
field stays within 1 % over a large fraction of the coil radius — which is why Helmholtz coils are the standard for
calibrating magnetometers and cancelling Earth's field in experiments.""")
