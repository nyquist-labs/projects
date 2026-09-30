from eelab import *
from scipy import signal

META = dict(
    id="AM-004", title="Pole-zero plotter and geometric frequency response", level="M",
    tools="Polynomial roots, the vector (geometric) evaluation of |H(jω)|, SciPy LTI step responses, dominant-pole approximation",
    summary="Enter a transfer function, get its pole-zero map, and compute the frequency response two ways — directly and as products of "
            "distances from jω to the zeros over distances to the poles — then test the dominant-pole rule for settling time.",
    problem="A pole-zero map is a complete description of a rational H(s). How do you read the response off the picture?",
    theory=r"""$H(s)=K\frac{\prod(s-z_i)}{\prod(s-p_k)}$ so $|H(jω)|=K\frac{\prod|jω-z_i|}{\prod|jω-p_k|}$ and $∠H=\sum∠(jω-z_i)-\sum∠(jω-p_k)$: the response is geometry. A pole pair much closer to the
axis than the rest dominates the transient: 2 % settling ≈ 4/σ_d where σ_d = −Re of the dominant pole.""",
    method="""Four transfer functions (a 3rd-order low-pass with a far pole, a notch, a band-pass, a non-minimum-phase system). |H| and ∠H evaluated both ways on 2000 frequencies;
step responses with scipy.signal.step; settling time measured to ±2 %.""",
)

SYS = {
    "dominant pair + far pole": ([100.0], np.poly([-1 + 4j, -1 - 4j, -20])),
    "notch": (np.poly([10j, -10j]), np.poly([-2 + 9.8j, -2 - 9.8j])),
    "band-pass": ([4.0, 0], np.poly([-2 + 20j, -2 - 20j])),
    "non-minimum phase": (np.poly([2.0]) * -1, np.poly([-1, -3])),
}


def run(p):
    w = np.logspace(-1, 3, 2000)
    worst_m = worst_p = 0
    for name, (b, a) in SYS.items():
        z, pz, k = signal.tf2zpk(b, a)
        Hd = np.polyval(b, 1j * w) / np.polyval(a, 1j * w)
        mag = abs(k) * np.prod([np.abs(1j * w - zi) for zi in z], axis=0) / np.prod([np.abs(1j * w - pk) for pk in pz], axis=0)
        ph = np.angle(k) + np.sum([np.angle(1j * w - zi) for zi in z], axis=0) - np.sum([np.angle(1j * w - pk) for pk in pz], axis=0)
        worst_m = max(worst_m, np.max(np.abs(mag / np.abs(Hd) - 1)))
        worst_p = max(worst_p, np.max(np.abs(np.angle(np.exp(1j * (ph - np.angle(Hd)))))))
    p.compare("Geometric |H| vs direct evaluation, worst relative error (4 systems)", 0, worst_m, "", kind="abs", tol=1e-9)
    p.compare("Geometric ∠H vs direct, worst error", 0, np.degrees(worst_p), "°", kind="abs", tol=1e-6)
    b, a = SYS["dominant pair + far pole"]
    t, y = signal.step((b, a), T=np.linspace(0, 8, 8001))
    yf = y[-1]
    out = np.flatnonzero(np.abs(y - yf) > 0.02 * yf)
    ts = t[out[-1] + 1]
    p.compare("Settling time (2 %) of the dominant-pair system ≈ 4/σ with σ = 1", 4.0, ts, "s", tol=10)
    b2, a2 = SYS["non-minimum phase"]
    t2, y2 = signal.step((b2, a2), T=np.linspace(0, 6, 6001))
    p.compare("Non-minimum-phase zero: initial step response goes the wrong way (sign of min / final)", -1, np.sign(y2.min() / y2[-1]), "", kind="abs")
    fig, ax = p.fig(2, 4, w=13, h=6)
    for j, (name, (bb, aa)) in enumerate(SYS.items()):
        z, pz, k = signal.tf2zpk(bb, aa)
        ax[0, j].plot(pz.real, pz.imag, "x", color=C_PRED, ms=9, mew=2); ax[0, j].plot(z.real, z.imag, "o", mfc="none", color=C_MEAS, ms=9, mew=2)
        ax[0, j].axvline(0, color="gray", lw=.6); ax[0, j].axhline(0, color="gray", lw=.6); ax[0, j].set_title(name, fontsize=9, loc="left")
        Hd = np.polyval(bb, 1j * w) / np.polyval(aa, 1j * w)
        ax[1, j].semilogx(w, db(Hd), color=C_MEAS); ax[1, j].set_xlabel("ω (rad/s)")
    ax[1, 0].set_ylabel("|H| (dB)"); ax[0, 0].set_ylabel("Im s")
    p.save(fig, "pz_maps", "Pole-zero maps (× poles, ○ zeros) and magnitude responses of the four systems.")
    p.discuss(f"""The geometric evaluation equals direct polynomial evaluation to machine precision, confirming that a pole-zero map plus a gain *is* the transfer
function. The pictures read naturally: the notch's zeros on the jω axis force |H| → 0 at 10 rad/s, the band-pass's poles near ±20j lift the response
there, and the dominant-pair system settles in {ts:.2f} s against the 4/σ = 4 s rule. The rule is an envelope bound — it is when e^(−σt)/√(1−ζ²)
reaches 2 % (3.94 s here) — while the oscillating response last leaves the ±2 % band at an earlier peak, so real settling is somewhat faster;
the far pole at −20 barely matters because its exponential dies 20× faster. The right-half-plane zero produces the characteristic initial undershoot of non-minimum-phase systems, which no
amount of gain can remove and which limits achievable control bandwidth.""")
# tol-convention: relative tolerances are in percent
