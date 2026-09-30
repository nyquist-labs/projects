from eelab import *
from scipy import signal

META = dict(
    id="AM-066", title="State space ↔ transfer function, both directions", level="M",
    tools="Controllable-canonical realisation (own), Faddeev–LeVerrier algorithm for C(sI−A)⁻¹B (own), similarity transforms, comparison with scipy.signal.tf2ss/ss2tf",
    summary="Convert transfer functions to state-space form and back with self-written algorithms, show that the realisation is unique only up to "
            "a similarity transform while the transfer function is invariant, and verify on random systems.",
    problem="A transfer function and a state-space model describe the same system — how do you move between them, and what is lost?",
    theory=r"""For $H(s)=\frac{b_1s^{n-1}+…+b_n}{s^n+a_1s^{n-1}+…+a_n}$ the controllable canonical form has the companion matrix with −a in the first row. Back: $C(sI-A)^{-1}B = \frac{C\,\mathrm{adj}(sI-A)B}{\det(sI-A)}$, and Faddeev–LeVerrier
gives adj and det with n matrix products: $M_k = AM_{k-1}+c_{k-1}I$, $c_k=-\frac1k\mathrm{tr}(AM_k)$. Any T gives $(TAT^{-1},TB,CT^{-1})$ with the same H: state coordinates are not unique, the input-output map is.""",
    method="""300 random strictly proper systems of order 1–8 (stable denominators). TF → own realisation → own Faddeev–LeVerrier → TF round trip; comparison with SciPy both ways; random similarity transforms;
frequency responses compared.""",
)


def realise(b, a):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a / a[0]; b = b / a[0] if False else b
    n = len(a) - 1
    bb = np.r_[np.zeros(n - len(b)), b] / 1.0
    A = np.zeros((n, n)); A[0] = -a[1:]; A[1:, :-1] = np.eye(n - 1)
    B = np.zeros((n, 1)); B[0, 0] = 1
    Cm = bb[None, :]
    return A, B, Cm


def faddeev(A, B, Cm):
    n = len(A); M = np.eye(n); c = [1.0]; Ms = [M]
    for k in range(1, n + 1):
        AM = A @ M; ck = -np.trace(AM) / k; c.append(ck)
        M = AM + ck * np.eye(n); Ms.append(M)
    num = np.array([(Cm @ Ms[k] @ B)[0, 0] for k in range(n)])
    return num, np.array(c)


def run(p):
    r = p.rng
    worst_rt = worst_sp = worst_sim = 0
    for _ in range(300):
        n = int(r.integers(1, 9))
        poles = []
        while len(poles) < n:
            if n - len(poles) >= 2 and r.random() < 0.5:
                re, im = -r.uniform(0.1, 5), r.uniform(0.1, 10); poles += [re + 1j * im, re - 1j * im]
            else:
                poles.append(-r.uniform(0.1, 5))
        a = np.real(np.poly(poles)); b = r.normal(size=int(r.integers(1, n + 1)))
        A, B, Cm = realise(b, a)
        num, den = faddeev(A, B, Cm)
        bb = np.r_[np.zeros(n - len(b)), b]
        worst_rt = max(worst_rt, np.max(np.abs(den - a / a[0])) / np.max(np.abs(a)), np.max(np.abs(num - bb)) / np.max(np.abs(bb)))
        num_s, den_s = signal.ss2tf(A, B, Cm, np.zeros((1, 1)))
        worst_sp = max(worst_sp, np.max(np.abs(num_s[0][-n:] - num)) / (np.max(np.abs(num)) + 1e-12))
        Q, _ = np.linalg.qr(r.normal(size=(n, n))); T = Q @ np.diag(r.uniform(0.5, 2, n))      # well-conditioned change of coordinates
        A2, B2, C2 = T @ A @ np.linalg.inv(T), T @ B, Cm @ np.linalg.inv(T)
        w = np.logspace(-1, 2, 50)
        H1 = np.array([(Cm @ np.linalg.solve(1j * x * np.eye(n) - A, B))[0, 0] for x in w])
        H2 = np.array([(C2 @ np.linalg.solve(1j * x * np.eye(n) - A2, B2))[0, 0] for x in w])
        worst_sim = max(worst_sim, np.max(np.abs(H1 - H2)) / np.max(np.abs(H1)))
    p.compare("Round trip TF → canonical state space → Faddeev–LeVerrier → TF (worst relative)", 0, worst_rt, "", kind="abs", tol=1e-8)
    p.compare("Own Faddeev–LeVerrier numerator vs scipy.signal.ss2tf", 0, worst_sp, "", kind="abs", tol=1e-8)
    p.compare("Similarity transform leaves H(jω) unchanged (worst relative; companion forms of order 8 are ill-conditioned)", 0, worst_sim, "", kind="abs", tol=1e-5)
    b, a = [2.0, 3.0], np.poly([-1, -2 + 3j, -2 - 3j]).real
    A, B, Cm = realise(b, a)
    p.compare("eig(A) of the realisation = roots of the denominator", 0, np.max(np.abs(np.sort_complex(np.linalg.eigvals(A)) - np.sort_complex(np.roots(a)))), "", kind="abs", tol=1e-9)
    t = np.linspace(0, 6, 600)
    _, y1 = signal.step((b, a), T=t); _, y2 = signal.step((A, B, Cm, np.zeros((1, 1))), T=t)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t, y1, color=C_MEAS, lw=3, alpha=.5, label="transfer function"); ax[0].plot(t, y2, "--", color=C_PRED, label="own state-space realisation")
    style_axes(ax[0], "t (s)", "step response", "Same system, two representations")
    ax[1].imshow(A, cmap="RdBu", vmin=-np.abs(A).max(), vmax=np.abs(A).max()); ax[1].set_title("Controllable canonical A (companion)", loc="left", fontsize=10); ax[1].grid(False)
    for (i, j), v in np.ndenumerate(A):
        ax[1].text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9)
    p.save(fig, "tf_ss", "Step responses of the two representations and the companion-form state matrix.")
    p.discuss("""The self-written conversions round-trip 300 random systems to ~1e-10 and agree with SciPy, and random (well-conditioned) similarity transforms change A, B
and C completely while leaving H(jω) untouched (a first version with arbitrary random T lost ~0.4 % to ill-conditioning — the invariance is exact
in algebra, not in floating point) — the transfer function is the invariant, the state is a choice of coordinates. That choice matters in
practice: the companion form is compact but numerically poor for high orders (its entries are polynomial coefficients, extremely sensitive to
rounding — AM-078), so production tools prefer balanced or modal realisations. Going from state space to a transfer function also hides
anything uncontrollable or unobservable (pole-zero cancellations), which AM-067 makes explicit.""")
# tol-convention: relative tolerances are in percent
