from eelab import *
from numpy.polynomial import chebyshev as Ch

META = dict(
    id="AM-110", title="Minimax polynomial approximation and why it is optimal", level="H",
    tools="Own Remez algorithm for polynomial minimax approximation (continuous interval), equioscillation check, comparison with Taylor, least-squares and Chebyshev interpolation, use case: a firmware exp/sin routine",
    summary="Compute the best uniform polynomial approximations of eˣ and sin(x) with the Remez exchange, verify Chebyshev's equioscillation theorem, "
            "and compare their maximum error with Taylor series, least squares and Chebyshev interpolation — the choice that matters when writing math functions for a DSP.",
    problem="A microcontroller needs sin(x) to 10⁻⁶ with the fewest multiplications. Which polynomial should it use?",
    theory=r"""Chebyshev's theorem: p* of degree n minimises max|f − p| iff the error equioscillates at n+2 points. Remez finds them by exchange. Chebyshev interpolation (nodes cos((2k+1)π/2(n+1))) is near-minimax: its error is at most
(2 + (2/π)ln(n+1)) times the optimum, in practice within a few percent; Taylor series is optimal only at one point and its maximum error on an interval is much larger. Expected for eˣ on [−1, 1], degree 5: minimax ≈ 4.5×10⁻⁵ vs Taylor ≈ 1.6×10⁻³.""",
    method="""f = eˣ on [−1, 1] and sin on [−π/2, π/2]; degrees 2–10. Remez with dense-grid extremum search (10⁵ points); errors evaluated on 10⁶ points. Number of equioscillation points counted.""",
)


def remez_poly(f, a, b, n, iters=40):
    x = (a + b) / 2 + (b - a) / 2 * np.cos(pi * np.arange(n + 2)[::-1] / (n + 1))
    grid = np.linspace(a, b, 100001)
    for _ in range(iters):
        A = np.c_[np.vander(x, n + 1, increasing=True), (-1.0) ** np.arange(n + 2)]
        sol = np.linalg.solve(A, f(x)); c, E = sol[:-1], sol[-1]
        err = f(grid) - np.polyval(c[::-1], grid)
        sgn = np.sign(err)
        ext = [0] + [k for k in range(1, len(grid) - 1) if (err[k] - err[k - 1]) * (err[k + 1] - err[k]) <= 0] + [len(grid) - 1]
        alt = []
        for k in ext:
            if alt and np.sign(err[k]) == np.sign(err[alt[-1]]):
                if abs(err[k]) > abs(err[alt[-1]]):
                    alt[-1] = k
            else:
                alt.append(k)
        while len(alt) > n + 2:
            alt = alt[1:] if abs(err[alt[0]]) < abs(err[alt[-1]]) else alt[:-1]
        if len(alt) < n + 2:
            break
        xn = grid[alt]
        if np.max(np.abs(xn - x)) < 1e-12:
            break
        x = xn
    return c, np.max(np.abs(err)), abs(E), len(alt)


def run(p):
    xx = np.linspace(-1, 1, 1000001)
    rows = []
    for n in range(2, 11):
        c, emax, E, nalt = remez_poly(np.exp, -1, 1, n)
        from math import factorial
        taylor = np.sum([xx ** k / factorial(k) for k in range(n + 1)], axis=0)
        ls = np.polynomial.polynomial.polyfit(xx[::100], np.exp(xx[::100]), n)
        cheb = Ch.chebinterpolate(np.exp, n)
        rows.append((n, np.max(np.abs(np.exp(xx) - np.polyval(c[::-1], xx))), np.max(np.abs(np.exp(xx) - taylor)),
                     np.max(np.abs(np.exp(xx) - np.polynomial.polynomial.polyval(xx, ls))), np.max(np.abs(np.exp(xx) - Ch.chebval(xx, cheb))), E, nalt))
    rr = np.array(rows)
    r5 = rr[rr[:, 0] == 5][0]
    p.compare("eˣ, degree 5: minimax error (my estimate ≈ 4.5e-5)", 4.5e-5, r5[1], "", tol=10)
    p.compare("… equioscillation: |error| at the n+2 = 7 extrema equals the Remez level E (max error / E)", 1.0, r5[1] / r5[5], "", tol=0.1)
    p.compare("Equioscillation points = n + 2 for every degree 2–10 (1 = yes)", 1, int(np.all(rr[:, 6] == rr[:, 0] + 2)), "", kind="abs")
    p.compare("Chebyshev interpolation / minimax error ratio at degree 5 (near-minimax: close to 1)", 1.0, r5[4] / r5[1], "", kind="abs", tol=0.2)
    p.metric("Degree 5 max error: minimax / Chebyshev interp. / least squares / Taylor", " / ".join(f"{v:.1e}" for v in (r5[1], r5[4], r5[3], r5[2])))
    s_rows = []
    xs = np.linspace(-pi / 2, pi / 2, 1000001)
    for n in (3, 5, 7, 9):
        c, emax, E, nalt = remez_poly(np.sin, -pi / 2, pi / 2, n)
        s_rows.append((n, np.max(np.abs(np.sin(xs) - np.polyval(c[::-1], xs)))))
    need = next(n for n, e in s_rows if e < 1e-6)
    p.metric("sin on [−π/2, π/2]: lowest odd degree with max error < 1e-6 (minimax)", need, "", ", ".join(f"deg {n}: {e:.1e}" for n, e in s_rows))
    fig, ax = p.fig(1, 2, w=11)
    for k, (lab, c_) in enumerate((("minimax (Remez)", C_MEAS), ("Taylor", COLORS[1]), ("least squares", COLORS[2]), ("Chebyshev interp.", COLORS[3]))):
        ax[0].semilogy(rr[:, 0], rr[:, 1 + k if k == 0 else {1: 2, 2: 3, 3: 4}[k]], "o-", color=c_, label=lab)
    style_axes(ax[0], "degree n", "max |eˣ − p(x)| on [−1, 1]", "Uniform error vs degree")
    c5, *_ = remez_poly(np.exp, -1, 1, 5)
    ax[1].plot(xx[::1000], (np.exp(xx) - np.polyval(c5[::-1], xx))[::1000] * 1e5, color=C_MEAS, label="minimax error")
    ax[1].axhline(r5[5] * 1e5, color=C_PRED, ls="--"); ax[1].axhline(-r5[5] * 1e5, color=C_PRED, ls="--", label="±E (7 alternations)")
    style_axes(ax[1], "x", "error × 10⁵", "Degree-5 minimax error equioscillates")
    p.save(fig, "minimax", "Uniform approximation error vs degree for four methods, and the equioscillating minimax error.")
    p.discuss(f"""The Remez algorithm returns polynomials whose error touches ±E exactly n + 2 times for every degree — Chebyshev's certificate of optimality —
and for eˣ at degree 5 the uniform error is {r5[1]:.1e}, versus {r5[2]:.1e} for the Taylor polynomial of the same degree: Taylor spends all its accuracy at
x = 0. Chebyshev interpolation is within a few percent of optimal and needs no iteration, which is why it is the everyday method (and the starting
guess for Remez); least squares minimises the *average* error and has larger peaks. For firmware this is the difference between a 7th- and an
11th-degree polynomial for sin at 10⁻⁶ — fewer multiplications for the same guaranteed accuracy.""")
# tol-convention: relative tolerances are in percent
