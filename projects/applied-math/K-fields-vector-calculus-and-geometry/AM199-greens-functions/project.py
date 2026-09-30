from eelab import *
from eelab.poisson import solve, EPS0
from scipy.sparse import diags
from scipy.signal import fftconvolve

META = dict(
    id="AM-199", title="Green's functions: solving field problems by superposition", level="H",
    tools="1-D Green's function of −u″ = f and its exact agreement with the inverse of the finite-difference matrix, 2-D free-space Green's function −ln r/2π applied by FFT convolution, method of images for a charge above a ground plane, reciprocity in an inhomogeneous region",
    summary="Treat the response to a point source as the fundamental object: build solutions by superposing Green's functions, show that the discrete Green's "
            "function of a finite-difference operator is simply its inverse matrix, verify the method of images against a direct solve, and demonstrate reciprocity where no formula exists.",
    problem="A potential problem with an arbitrary source seems to need a new solve for every source. Why does knowing the response to a single point charge solve all of them?",
    theory=r"""If $LG(x,s)=δ(x-s)$ with the boundary conditions built in, then $u(x)=\int G(x,s)f(s)ds$ solves $Lu=f$. For $-u''$ on [0, 1] with u(0) = u(1) = 0: $G=x(1-s)$ for x ≤ s, $s(1-x)$ otherwise. In 2-D free space $-\nabla^2G=δ$ gives $G=-\frac{1}{2π}\ln r$,
so a line charge λ produces $V=-\frac{λ}{2πε}\ln r$. A grounded plane is replaced by an image charge −λ at the mirror point, giving the surface charge $σ(x)=-\frac{λd}{π(x^2+d^2)}$ whose total is −λ. For a self-adjoint operator G(x, s) = G(s, x) (reciprocity), even
with an arbitrary permittivity distribution.""",
    method="""1-D: N = 99 interior nodes; the inverse of the FD matrix vs G at the nodes; solutions for smooth and point loads. 2-D: uniform charged disc potential by FFT convolution with the discretised Green's function vs the analytic disc potential. Images: line charge
5 mm above a grounded plane in a 200 × 100 mm box, 0.25 mm grid. Reciprocity: two point charges in a region with an irregular dielectric blob.""",
)


def run(p):
    N = 99; h = 1 / (N + 1); x = np.arange(1, N + 1) * h
    A = diags([-np.ones(N - 1), 2 * np.ones(N), -np.ones(N - 1)], [-1, 0, 1]).toarray() / h ** 2
    G = np.where(x[:, None] <= x[None], x[:, None] * (1 - x[None]), x[None] * (1 - x[:, None]))
    p.compare("1-D: inverse of the finite-difference matrix = h·G(xᵢ, xⱼ) at the nodes (max difference)", 0.0, float(np.max(np.abs(np.linalg.inv(A) - h * G))), "", kind="abs", tol=1e-12)
    f = np.sin(3 * pi * x); u = G @ f * h
    p.compare("1-D: u = ∫G f ds for f = sin 3πx vs exact sin(3πx)/(9π²) (max rel. error)", 0.0, float(np.max(np.abs(u - np.sin(3 * pi * x) / (9 * pi ** 2))) / (1 / (9 * pi ** 2))), "", kind="abs", tol=2e-3)
    s0 = 0.3; up = np.where(x <= s0, x * (1 - s0), s0 * (1 - x))
    p.compare("1-D: response to a unit point load at s = 0.3 is G(x, 0.3) — a tent with peak s(1 − s)", s0 * (1 - s0), float(up.max()), "", tol=1e-9)
    n = 401; L = 0.2; hh = L / (n - 1); c = (np.arange(n) - (n - 1) / 2) * hh; X, Y = np.meshgrid(c, c); R0 = 0.02; rho = 1e-6
    q = np.where(X ** 2 + Y ** 2 <= R0 ** 2, rho, 0.0) * hh * hh
    gx = (np.arange(2 * n - 1) - (n - 1)) * hh; GX, GY = np.meshgrid(gx, gx); rr = np.hypot(GX, GY); rr[n - 1, n - 1] = hh * np.exp(-3 / 2 + pi / 4) / 1.0 * 0.5 * np.sqrt(2) * 0 + hh * 0.2240
    Gk = -np.log(rr) / (2 * pi * EPS0)
    V = fftconvolve(q, Gk, mode="valid")
    lam = rho * pi * R0 ** 2; r_ = np.hypot(X, Y)
    Vex = np.where(r_ <= R0, -lam / (2 * pi * EPS0) * np.log(R0) + rho * (R0 ** 2 - r_ ** 2) / (4 * EPS0), -lam / (2 * pi * EPS0) * np.log(np.maximum(r_, 1e-12)))
    diff = V - Vex; off = diff[n // 2, n // 2]
    p.compare("2-D: disc potential by convolution with −ln r/(2πε₀) vs analytic (max error after removing the arbitrary constant, relative to the potential range)", 0.0, float(np.max(np.abs(diff - off)) / (Vex.max() - Vex.min())), "", kind="abs", tol=2e-3)
    W, H, d = 0.2, 0.1, 5e-3; h2 = 0.25e-3; nx, ny = int(W / h2) + 1, int(H / h2) + 1
    xs = (np.arange(nx) - (nx - 1) / 2) * h2; fixed = np.zeros((ny, nx), bool); fixed[0] = fixed[-1] = fixed[:, 0] = fixed[:, -1] = True
    rho2 = np.zeros((ny, nx)); jq = int(round(d / h2)); rho2[jq, (nx - 1) // 2] = 1e-9 / h2 ** 2
    Vp = solve(fixed, np.zeros((ny, nx)), rho2, h2)
    sig = EPS0 * (0 - Vp[1]) / h2 * -1 * -1
    sig = -EPS0 * (Vp[1] - Vp[0]) / h2
    img = -1e-9 * d / (pi * (xs ** 2 + d ** 2))
    mm = np.abs(xs) < 0.03
    p.compare("Method of images: induced surface charge under the line charge (peak) vs −λ/(πd)", float(img.max() * 0 + img[(nx - 1) // 2]), float(sig[(nx - 1) // 2]), "C/m²", tol=6)
    p.compare("… profile within ±30 mm: worst deviation relative to the peak", 0.0, float(np.max(np.abs(sig[mm] - img[mm])) / abs(img[(nx - 1) // 2])), "", kind="abs", tol=0.06)
    p.compare("Total induced charge on the plane ≈ −λ (the rest lands on the distant box walls)", -1e-9, float(np.sum(sig) * h2), "C/m", tol=6)
    n3 = 201; h3 = 1e-3; c3 = (np.arange(n3) - 100) * h3; X3, Y3 = np.meshgrid(c3, c3)
    eps = 1 + 5 * ((X3 - 0.01) ** 2 / 0.03 ** 2 + (Y3 + 0.005) ** 2 / 0.015 ** 2 < 1) + 3 * (np.abs(X3 + 0.03) < 0.01)
    f3 = np.zeros((n3, n3), bool); f3[0] = f3[-1] = f3[:, 0] = f3[:, -1] = True
    A_, B_ = (100 + 30, 100 - 40), (100 - 25, 100 + 35)
    rA = np.zeros((n3, n3)); rA[A_] = 1e-6; rB = np.zeros((n3, n3)); rB[B_] = 1e-6
    VA = solve(f3, np.zeros((n3, n3)), rA, h3, eps); VB = solve(f3, np.zeros((n3, n3)), rB, h3, eps)
    p.compare("Reciprocity with an irregular dielectric: V at B due to a charge at A = V at A due to the same charge at B", VA[B_], VB[A_], "V", tol=1e-8)
    fig, ax = p.fig(1, 3, w=13, h=3.9)
    for s_, c_ in ((0.2, C_MEAS), (0.5, C_PRED), (0.8, COLORS[2])):
        ax[0].plot(x, np.where(x <= s_, x * (1 - s_), s_ * (1 - x)), color=c_, label=f"G(x, {s_})")
    style_axes(ax[0], "x", "G(x, s)", "1-D Green's functions of −u″")
    ax[1].plot(xs[mm] * 1e3, sig[mm] * 1e9, ".", ms=3, color=C_MEAS, label="finite-difference solve"); ax[1].plot(xs[mm] * 1e3, img[mm] * 1e9, color=C_PRED, label="image charge")
    style_axes(ax[1], "x (mm)", "σ (nC/m² per nC/m)", "Charge induced on a ground plane")
    ax[2].imshow(eps, origin="lower", cmap="Greys", alpha=.4, extent=[-100, 100, -100, 100]); ax[2].contour(c3 * 1e3, c3 * 1e3, VA, 15, colors=[C_MEAS], linewidths=.7)
    ax[2].plot(c3[A_[1]] * 1e3, c3[A_[0]] * 1e3, "o", color=C_MEAS); ax[2].plot(c3[B_[1]] * 1e3, c3[B_[0]] * 1e3, "s", color=C_PRED); ax[2].grid(False)
    ax[2].set_title("Reciprocity test: charge at ○, probe at □", loc="left", fontsize=10)
    p.save(fig, "greens", "1-D Green's functions, induced charge from the method of images, and the inhomogeneous reciprocity test.")
    p.discuss(f"""Green's functions turn 'solve the equation' into 'add up point responses'. In 1-D the inverse of the finite-difference matrix *is* the Green's
function sampled at the nodes, to round-off — so every discrete solve is a Green's-function superposition in disguise. Convolving a charged disc
with −ln r/2πε₀ by FFT reproduces its analytic potential, and the method of images — one fictitious charge — predicts the charge induced on a ground
plane in agreement with a full numerical solve (peak {sig[(nx - 1) // 2] / img[(nx - 1) // 2] * 100:.0f} % of the image result; the total falls slightly short of −λ because the
distant box walls collect some flux). Reciprocity needs no formula: with an arbitrary dielectric blob between them, a charge at A produces
exactly the same potential at B as the same charge at B produces at A, because the discrete operator is symmetric. That symmetry is what makes
Green's functions, mutual capacitances and antenna reciprocity work.""")
# tol-convention: relative tolerances are in percent
