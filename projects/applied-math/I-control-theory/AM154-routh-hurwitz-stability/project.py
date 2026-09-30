from eelab import *
from fractions import Fraction
from scipy import signal

META = dict(
    id="AM-154", title="Routh–Hurwitz: stability without finding the roots", level="M",
    tools="Own Routh array (exact rational arithmetic, with the ε rule for a zero pivot and the auxiliary-polynomial rule for a zero row), Hurwitz determinants, comparison with numerically computed roots on thousands of random polynomials, critical-gain prediction checked by simulation",
    summary="Count right-half-plane roots from the signs in the first column of the Routh array, verify against computed roots for 5000 random "
            "polynomials, handle the two special cases, and use the array to predict the gain and frequency at which a feedback loop starts to oscillate.",
    problem="Is this characteristic polynomial stable — and for which range of a gain K — without solving it?",
    theory=r"""The number of sign changes in the first column of the Routh array equals the number of roots with positive real part. A zero pivot is replaced by ε → 0⁺; an all-zero row signals roots symmetric about the origin (e.g. a pair on the jω axis) and is replaced by the
derivative of the auxiliary polynomial from the row above. Equivalent: all Hurwitz determinants positive. For $s^3+3s^2+2s+K$ the array gives stability for $0<K<6$; at K = 6 the auxiliary polynomial $3s^2+6$ gives oscillation at $ω=\sqrt2$ rad/s.""",
    method="""5000 polynomials of degree 2–8 built from random roots (kept away from the imaginary axis), floating-point Routh array vs numpy.roots. Special cases in exact arithmetic: s⁵+2s⁴+2s³+4s²+11s+10 (zero pivot; 2 RHP roots) and s⁵+7s⁴+6s³+42s²+8s+56
(zero row; roots ±j√2, ±j2). Critical gain by root sweep and oscillation period from a simulated step response at K = 6.""",
)


def routh(coeffs, exact=False):
    """Return (first column, number of sign changes, zero_row_flag)."""
    F = Fraction if exact else float
    c = [F(x) for x in coeffs]; n = len(c) - 1
    rows = [c[0::2], c[1::2] + [F(0)] * (len(c[0::2]) - len(c[1::2]))]
    eps = Fraction(1, 10 ** 12) if exact else 1e-9
    zero_row = False
    for i in range(2, n + 1):
        a, b = rows[i - 2], rows[i - 1]
        if all(x == 0 for x in b):                               # auxiliary polynomial from row a (degree n − (i − 2))
            zero_row = True; deg = n - (i - 2)
            b = [a[k] * (deg - 2 * k) for k in range(len(a))]; rows[i - 1] = b
        if b[0] == 0:
            b = [eps] + list(b[1:]); rows[i - 1] = b
        new = [(b[0] * a[k + 1] - a[0] * b[k + 1]) / b[0] for k in range(len(a) - 1)] + [F(0)]
        rows.append(new)
    col = [r[0] for r in rows[: n + 1]]
    sgn = [1 if x > 0 else -1 for x in col if x != 0]
    return col, sum(1 for u, v in zip(sgn, sgn[1:]) if u != v), zero_row


def hurwitz_stable(c):
    n = len(c) - 1; c = np.array(c, float) / c[0]; Hm = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            k = 2 * (j + 1) - (i + 1)
            if 0 <= k <= n:
                Hm[i, j] = c[k]
    return all(np.linalg.det(Hm[:k, :k]) > 0 for k in range(1, n + 1))


def run(p):
    r = p.rng; bad = hbad = 0; N = 5000
    for _ in range(N):
        deg = int(r.integers(2, 9)); roots = []
        while len(roots) < deg:
            re = r.uniform(0.1, 3) * r.choice([-1, -1, 1])
            if deg - len(roots) >= 2 and r.random() < 0.6:
                im = r.uniform(0.1, 4); roots += [complex(re, im), complex(re, -im)]
            else:
                roots.append(re)
        c = np.real(np.poly(roots))
        true = int(np.sum(np.real(np.roots(c)) > 0))
        bad += routh(c)[1] != true
        hbad += hurwitz_stable(c) != (true == 0)
    p.compare(f"Routh sign changes vs number of RHP roots from numpy.roots ({N} random polynomials, degree 2–8): mismatches", 0, bad, "", kind="abs")
    p.compare("Hurwitz determinant test disagrees with the roots (same polynomials)", 0, hbad, "", kind="abs")
    c1 = [1, 2, 2, 4, 11, 10]
    p.compare("Zero pivot (ε rule): RHP roots of s⁵+2s⁴+2s³+4s²+11s+10", int(np.sum(np.real(np.roots(c1)) > 1e-9)), routh(c1, exact=True)[1], "", kind="abs")
    c2 = [1, 7, 6, 42, 8, 56]; col, ch, zr = routh(c2, exact=True)
    p.compare("Zero row detected for s⁵+7s⁴+6s³+42s²+8s+56 (1 = yes)", 1, int(zr), "", kind="abs")
    p.compare("… and no sign changes (no RHP roots; the roots of the auxiliary polynomial sit on the jω axis)", 0, ch, "", kind="abs")
    aux = np.roots([7, 0, 42, 0, 56])
    p.compare("Auxiliary polynomial 7s⁴+42s²+56: largest root magnitude (±j2)", 2.0, float(np.max(np.abs(aux))), "rad/s", tol=1e-6)
    lo, hi = 0.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if np.max(np.real(np.roots([1, 3, 2, mid]))) < 0 else (lo, mid)
    p.compare("s³+3s²+2s+K: critical gain from the Routh array (K = 6) vs root sweep", 6.0, lo, "", tol=1e-6)
    p.compare("Routh array says stable at K = 5.9 and unstable at K = 6.1 (sign changes 0 and 2)", 2, routh([1, 3, 2, 5.9])[1] * 10 + routh([1, 3, 2, 6.1])[1], "", kind="abs")
    t = np.linspace(0, 80, 40001); _, y, _ = signal.lsim(([6.0], [1, 3, 2, 6.0]), np.ones_like(t), t)
    e = y - 1; zc = t[1:][(e[:-1] < 0) & (e[1:] >= 0)]
    per = np.mean(np.diff(zc[2:]))
    p.compare("K = 6: period of the sustained oscillation = 2π/√2", 2 * pi / np.sqrt(2), per, "s", tol=0.5)
    pk = [np.max(np.abs(e[(t > a) & (t < a + 10)])) for a in (20, 60)]
    p.compare("K = 6: oscillation neither grows nor decays (amplitude ratio late/early)", 1.0, pk[1] / pk[0], "", tol=1)
    p.section("Routh array for s³ + 3s² + 2s + K", "| row | | |\n|---|---|---|\n| s³ | 1 | 2 |\n| s² | 3 | K |\n| s¹ | (6 − K)/3 | |\n| s⁰ | K | |\n\nStable iff 6 − K > 0 and K > 0.")
    Ks = np.linspace(0, 12, 200)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(Ks, [np.max(np.real(np.roots([1, 3, 2, k]))) for k in Ks], color=C_MEAS); ax[0].axhline(0, color="gray", lw=.6); ax[0].axvline(6, color=C_PRED, ls="--", label="Routh: K = 6")
    style_axes(ax[0], "gain K", "largest real part of the roots", "Stability boundary")
    for k, c in ((3, COLORS[2]), (6, C_MEAS), (7, COLORS[1])):
        tt = np.linspace(0, 30, 6000); ax[1].plot(tt, signal.lsim(([k], [1, 3, 2, k]), np.ones_like(tt), tt)[1], color=c, label=f"K = {k}")
    ax[1].set_ylim(-1, 3)
    style_axes(ax[1], "time (s)", "step response", "Below, at and above the critical gain")
    p.save(fig, "routh", "Largest real part of the closed-loop poles versus gain, and step responses around the Routh stability limit.")
    p.discuss("""The array's sign changes matched the true count of right-half-plane roots for all 5000 random polynomials, and the Hurwitz determinants agreed —
two views of the same test. The special cases behave as the textbook says when done in exact arithmetic: the ε rule recovers the two unstable
roots behind a zero pivot, and a zero row flags purely imaginary root pairs, located by the auxiliary polynomial. The real value of the method is
parametric: a symbolic gain K in the array gives the stability range 0 < K < 6 and the oscillation frequency √2 rad/s at the limit directly, both
confirmed by a root sweep and by a simulated response that neither grows nor decays at K = 6. Floating-point Routh arrays are fragile near zero
pivots — for plain yes/no questions on numeric polynomials, computing the roots is now cheaper; Routh remains the tool for design inequalities.""")
# tol-convention: relative tolerances are in percent
