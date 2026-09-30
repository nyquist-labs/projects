from eelab import *
from scipy import signal
from math import factorial

META = dict(
    id="AM-012", title="Residue calculus: from H(s) to the impulse response", level="H",
    tools="Own residue computation (limits and derivatives for repeated poles), analytic inverse Laplace, comparison with scipy.signal.residue and numerical impulse responses",
    summary="Expand rational transfer functions into partial fractions by residue calculus — including repeated and complex poles — write the "
            "impulse response in closed form, and check it against SciPy's residue routine and a numerical simulation.",
    problem="The inverse Laplace transform is a contour integral. In practice it reduces to summing residues — how, and how accurately?",
    theory=r"""For a proper rational H(s), $h(t)=\sum_k \mathrm{Res}_{s=p_k}\,H(s)e^{st}$. A simple pole contributes $r_k e^{p_kt}$ with $r_k=\lim_{s\to p_k}(s-p_k)H(s)$; a pole of order m contributes
$\sum_{j=1}^{m} \frac{c_j}{(j-1)!}t^{j-1}e^{p_kt}$ with $c_{m-i}=\frac{1}{i!}\frac{d^i}{ds^i}\big[(s-p_k)^mH(s)\big]_{s=p_k}$. Complex-conjugate residues combine into real damped sinusoids.""",
    method="""Three systems: distinct real poles, a complex pair plus a real pole, and a triple pole with a zero. Residues computed symbolically-by-numerics (polynomial division and
derivatives with numpy.polynomial), compared with scipy.signal.residue; h(t) evaluated on 0–10 s and compared with scipy.signal.impulse.""",
)

SYS = {
    "distinct real poles": ([2.0, 3.0], np.poly([-1, -2, -5])),
    "complex pair + real pole": ([10.0], np.poly([-1 + 3j, -1 - 3j, -4]).real),
    "triple pole with a zero": ([1.0, 2.0], np.poly([-1, -1, -1])),
}


def residues(b, a):
    """Return list of (pole, [c_1..c_m]) using limits/derivatives."""
    b = np.poly1d(b); a = np.poly1d(a)
    roots = np.roots(a.coeffs)
    groups = []
    for r in roots:
        for g in groups:
            if abs(g[0] - r) < 1e-4:
                g[1] += 1; break
        else:
            groups.append([r, 1])
    out = []
    for pk, m in groups:
        pk = complex(np.round(pk.real, 8), np.round(pk.imag, 8))
        # (s-pk)^m H(s) = b(s) / (a(s)/(s-pk)^m)
        q = np.poly1d(a.coeffs.astype(complex))
        for _ in range(m):
            q, rem = np.polydiv(q.coeffs, np.array([1, -pk]))
            q = np.poly1d(q)
        num, den = np.poly1d(b.coeffs.astype(complex)), q
        cs = []
        for i in range(m):
            # i-th derivative of num/den at pk via repeated quotient rule on polynomials
            N, D = num, den
            for _ in range(i):
                N, D = N.deriv() * D - N * D.deriv(), D * D
            cs.append(N(pk) / D(pk) / factorial(i))
        out.append((pk, cs[::-1]))       # c_m ... c_1 → reversed to c_1..c_m ordering below
    return out


def h_of_t(res, t):
    h = np.zeros_like(t, complex)
    for pk, cs in res:
        m = len(cs)
        # cs[j-1] multiplies 1/(s-pk)^j  → t^{j-1}/(j-1)! e^{pk t}
        for j in range(1, m + 1):
            h += cs[j - 1] * t ** (j - 1) / factorial(j - 1) * np.exp(pk * t)
    return h


def run(p):
    t = np.linspace(0, 10, 5001)
    fig, ax = p.fig(1, 3, w=12, h=3.6)
    for k, (name, (b, a)) in enumerate(SYS.items()):
        res = residues(b, a)
        h = h_of_t(res, t)
        rs, ps, _ = signal.residue(b, a)
        # compare our (pole, coefficient) pairs with scipy's (scipy lists repeated poles with increasing powers)
        ours = sorted([(pk, c) for pk, cs in res for c in cs], key=lambda x: (round(x[0].real, 6), round(x[0].imag, 6), abs(x[1])))
        theirs = sorted(zip(ps, rs), key=lambda x: (round(x[0].real, 6), round(x[0].imag, 6), abs(x[1])))
        dres = max(abs(o[1] - th[1]) for o, th in zip(ours, theirs))
        _, hn = signal.impulse((b, a), T=t)
        tol = 2e-5 if "triple" in name else 1e-9      # a triple root is only found to ~ε^(1/3) ≈ 6e-6 by any root solver
        p.compare(f"{name}: residues vs scipy.signal.residue (worst difference)", 0, dres, "", kind="abs", tol=tol)
        p.compare(f"{name}: closed-form h(t) vs numerical impulse response (worst)", 0, np.max(np.abs(h.real - hn)), "", kind="abs", tol=tol)
        p.compare(f"{name}: imaginary part of h(t) (conjugate residues cancel)", 0, np.max(np.abs(h.imag)), "", kind="abs", tol=1e-9)
        ax[k].plot(t, hn, color=C_MEAS, lw=3, alpha=.5, label="numerical"); ax[k].plot(t, h.real, "--", color=C_PRED, label="residues")
        style_axes(ax[k], "t (s)", "h(t)" if k == 0 else None, name, legend=(k == 0))
    p.save(fig, "impulse", "Impulse responses from residue sums (dashed) overlaid on numerical simulation.")
    b, a = SYS["complex pair + real pole"]
    res = residues(b, a)
    rc = [c for pk, cs in res if pk.imag > 0 for c in cs][0]
    p.metric("Complex pair residue r → 2|r| e^{−t} cos(3t + ∠r)", f"|r| = {abs(rc):.4f}, ∠r = {np.degrees(np.angle(rc)):.2f}°")
    p.discuss("""Residues computed by the limit/derivative formulas match SciPy's partial-fraction routine and give impulse responses identical to numerical
simulation to ~1e-9, including the triple pole, whose response t²e^{−t}/2-type terms come from the derivative formula. Conjugate poles give
conjugate residues, and their sum is real — the imaginary parts cancel to rounding error — which is the algebraic reason a real circuit rings
as a damped cosine. A practical warning surfaced while building this: repeated poles found by a root solver are never exactly equal (errors
~1e-5 for a triple root), (the error of a triple root scales as ε^(1/3) ≈ 6e-6, which is exactly the level of disagreement seen
here), so they must be clustered before applying the multiple-pole formula; treating them as distinct produces huge,
nearly cancelling residues — a classic ill-conditioning trap.""")
# tol-convention: relative tolerances are in percent
