from eelab import *

META = dict(
    id="AM-006", title="Nyquist plot generator with encirclement counting", level="M",
    tools="Contour mapping of L(jω), numerical winding number (argument principle), Routh–Hurwitz for the prediction, closed-loop pole computation",
    summary="Map the imaginary axis through L(s) = K/((s+1)(s+2)(s+3)), count encirclements of −1 with a winding-number algorithm, and find the "
            "gain at which the closed loop goes unstable — predicted beforehand with the Routh–Hurwitz criterion.",
    problem="Nyquist's criterion turns a question about roots into a question about a curve. Can a program count the encirclements reliably?",
    theory=r"""Argument principle: as s traverses the Nyquist contour, 1+L(s) winds around 0 (equivalently L around −1) N = Z − P times, Z = closed-loop RHP poles, P = open-loop RHP poles
(here 0). Characteristic polynomial $s^3+6s^2+11s+6+K$: Routh gives stability for 6·11 > 6+K, i.e. **K < 60**; at K = 60 the loop crosses −1 at ω = √11 = 3.317 rad/s.""",
    method="""L(jω) on ω ∈ [−10⁴, 10⁴] (log-dense near 0) plus the vanishing arc; winding number = total change of arg(1+L)/2π, computed from unwrapped phase. K swept 1–200; closed-loop
poles from numpy.roots for comparison; critical K and crossing frequency by bisection on the winding count.""",
)


def winding(K):
    w = np.concatenate([-np.logspace(4, -4, 20000), [0], np.logspace(-4, 4, 20000)])
    s = 1j * w
    F = 1 + K / ((s + 1) * (s + 2) * (s + 3))
    ph = np.unwrap(np.angle(F))
    return -round((ph[-1] - ph[0]) / (2 * pi))      # clockwise encirclements (contour traversed upward)


def rhp(K):
    return int(np.sum(np.roots([1, 6, 11, 6 + K]).real > 0))


def run(p):
    Ks = np.array([k for k in range(1, 201) if k != 60])      # K = 60 itself is marginal: poles exactly on the jω axis
    N = np.array([winding(K) for K in Ks]); Z = np.array([rhp(K) for K in Ks])
    p.compare("Gains where the encirclement count ≠ number of RHP closed-loop poles (K = 1…200 except the marginal K = 60)", 0, int(np.sum(N != Z)), "", kind="abs")
    lo, hi = 1.0, 200.0
    for _ in range(50):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if winding(mid) == 0 else (lo, mid)
    p.compare("Critical gain from Nyquist (bisection on the winding number) vs Routh", 60.0, (lo + hi) / 2, "", tol=0.01)
    w = np.linspace(0.1, 10, 200001); L = 60 / ((1j * w + 1) * (1j * w + 2) * (1j * w + 3))
    wc = w[np.argmin(np.abs(L.imag) + (L.real > 0) * 10)]
    p.compare("Phase-crossover frequency at K = 60 (= √11)", np.sqrt(11), wc, "rad/s", tol=0.1)
    p.compare("Gain margin at K = 10 (predicted 60/10)", 20 * np.log10(6), -db(10 / ((1j * np.sqrt(11) + 1) * (1j * np.sqrt(11) + 2) * (1j * np.sqrt(11) + 3))), "dB", kind="abs", tol=1e-6)
    fig, ax = p.fig(1, 2, w=11)
    wf = np.logspace(-3, 3, 4000)
    for K, c in ((10, COLORS[0]), (60, COLORS[1]), (120, COLORS[2])):
        Lp = K / ((1j * wf + 1) * (1j * wf + 2) * (1j * wf + 3))
        ax[0].plot(Lp.real, Lp.imag, color=c, label=f"K = {K}"); ax[0].plot(Lp.real, -Lp.imag, color=c, ls=":")
    ax[0].plot(-1, 0, "k+", ms=12, mew=2); ax[0].set_xlim(-3, 11); ax[0].set_ylim(-8, 8)
    style_axes(ax[0], "Re L(jω)", "Im L(jω)", "Nyquist plots: K = 60 passes through −1")
    ax[1].step(Ks, N, where="mid", color=C_MEAS, label="encirclements N (Nyquist)"); ax[1].plot(Ks, Z, "--", color=C_PRED, label="RHP closed-loop poles Z (roots)")
    ax[1].axvline(60, color="gray", ls=":")
    style_axes(ax[1], "gain K", "count", "N = Z for every gain")
    p.save(fig, "nyquist", "Nyquist curves around the critical gain, and encirclement count vs RHP pole count.")
    p.discuss("""The winding-number count equals the number of right-half-plane closed-loop poles at every tested gain, and the transition sits at K = 60 —
exactly the Routh–Hurwitz prediction — with the curve crossing −1 at √11 rad/s. The practical subtleties are numerical: the contour must be dense
where L(jω) changes phase quickly and must include negative frequencies (the mirror image), otherwise half an encirclement goes missing. With
open-loop poles on the jω axis the contour would also need an indentation; this example avoids that deliberately and the method section says so.""")
# tol-convention: relative tolerances are in percent
