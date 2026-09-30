from eelab import *

META = dict(
    id="AM-202", title="Distributed vs lumped: exactly when the lumped model fails", level="M",
    tools="Exact transmission-line input impedance, single- and multi-section LC ladder models (ABCD matrices), error versus electrical length, convergence of n-section ladders, the quarter-wave resonance versus the lumped LC resonance, the λ/10 rule of thumb quantified",
    summary="Compare a transmission line with its lumped-element approximations frequency by frequency: map how the error grows with electrical length, "
            "show that n-section ladders converge as 1/n², and pin down the classic failure — a single LC section puts the open line's first resonance 36 % too low.",
    problem="'Treat it as a lumped circuit if it is shorter than λ/10' — how wrong is the lumped model at λ/10, at λ/4, and how many sections fix it?",
    theory=r"""Line of length ℓ, $Z_0=\sqrt{L'/C'}$, phase constant β: $Z_{in}=Z_0\frac{Z_L+jZ_0\tanβℓ}{Z_0+jZ_L\tanβℓ}$. A symmetric π section (series $L'ℓ/n$, half the shunt capacitance at each end) reproduces the line's ABCD matrix with errors of third order in its electrical length βℓ/n, so the impedance error
of one section grows as $(βℓ)^3$ and that of n sections as $(βℓ)^3/n^2$. Open-circuited line: first resonance (Z_in → 0) at ℓ = λ/4, $f=v/(4ℓ)$. One π section resonates when its series L meets the far half-capacitance: $f=\frac{\sqrt2\,v}{2πℓ}$ = 0.90 of the true value;
putting all the capacitance at the far end (an L section) gives $v/(2πℓ)$, a factor 2/π = 0.64 low. With n sections the lowest mode approaches v/(4ℓ) with a 1/n² error.""",
    method="""Z₀ = 50 Ω, v = 2×10⁸ m/s, ℓ = 1 m, load 100 Ω and open circuit; electrical length swept 0.001 to 0.5 λ. Symmetric π sections. Error = |Z_lumped − Z_exact|/|Z_exact|. Resonances found by root finding on Im Z_in.""",
)


def abcd_line(beta_l, Z0):
    return np.array([[np.cos(beta_l), 1j * Z0 * np.sin(beta_l)], [1j * np.sin(beta_l) / Z0, np.cos(beta_l)]])


def abcd_ladder(w, Lt, Ct, n):
    L, C = Lt / n, Ct / n; M = np.eye(2, dtype=complex)
    for _ in range(n):
        Y = 1j * w * C / 2; Z = 1j * w * L
        M = M @ np.array([[1, 0], [Y, 1]]) @ np.array([[1, Z], [0, 1]]) @ np.array([[1, 0], [Y, 1]])
    return M


def zin(M, ZL):
    return (M[0, 0] * ZL + M[0, 1]) / (M[1, 0] * ZL + M[1, 1]) if np.isfinite(ZL) else M[0, 0] / M[1, 0]


def run(p):
    Z0, v, ell = 50.0, 2e8, 1.0; Lp, Cp = Z0 / v, 1 / (Z0 * v); ZL = 100.0
    el = np.logspace(-3, np.log10(0.5), 300); f = el * v / ell; err = {}
    for n in (1, 2, 4, 8, 16):
        err[n] = np.array([abs(zin(abcd_ladder(2 * pi * fi, Lp * ell, Cp * ell, n), ZL) - zin(abcd_line(2 * pi * e_, Z0), ZL)) / abs(zin(abcd_line(2 * pi * e_, Z0), ZL)) for fi, e_ in zip(f, el)])
    at = lambda n, e_: float(np.interp(e_, el, err[n]))
    p.metric("Single π section, 100 Ω load: impedance error at ℓ = λ/100 / λ/20 / λ/10 / λ/4", " / ".join(f"{at(1, e_) * 100:.2f} %" for e_ in (0.01, 0.05, 0.1, 0.25)))
    m = (el > 0.003) & (el < 0.03)
    p.compare("Error of one π section grows as (βℓ)³: log-log slope at small electrical length (I first expected 2)", 3.0, np.polyfit(np.log(el[m]), np.log(err[1][m]), 1)[0], "", kind="abs", tol=0.1)
    p.compare("n-section ladder: error ∝ 1/n² (ratio 4 → 8 sections at ℓ = 0.2λ)", 4.0, at(4, 0.2) / at(8, 0.2), "×", tol=5)
    p.compare("Rule of thumb λ/10: single-section error there is a few percent (< 10 %; 1 = yes)", 1, int(at(1, 0.1) < 0.10), "", kind="abs")
    from scipy.optimize import brentq
    f_exact = v / (4 * ell)
    res = {}
    for n in (1, 2, 4, 8, 16, 32):
        g = lambda fr: np.imag(zin(abcd_ladder(2 * pi * fr, Lp * ell, Cp * ell, n), np.inf))
        fg = np.linspace(0.3 * f_exact, 1.2 * f_exact, 4000); vals = np.array([g(q) for q in fg])
        k = np.flatnonzero(np.sign(vals[:-1]) != np.sign(vals[1:]))
        k = [q for q in k if abs(vals[q]) < 1e6 and abs(vals[q + 1]) < 1e6]
        res[n] = brentq(g, fg[k[0]], fg[k[0] + 1])
    p.compare("Open line, one π section: first resonance √2·v/(2πℓ) = 0.90 × the quarter-wave frequency", np.sqrt(2) * v / (2 * pi * ell), res[1], "Hz", tol=0.5)
    gL = lambda fr: np.imag(zin(np.array([[1, 1j * 2 * pi * fr * Lp * ell], [0, 1]]) @ np.array([[1, 0], [1j * 2 * pi * fr * Cp * ell, 1]]), np.inf))
    fL = brentq(gL, 0.3 * f_exact, 0.9 * f_exact)
    p.compare("One L section (all capacitance at the far end): resonance v/(2πℓ) = 2/π × the quarter-wave frequency", v / (2 * pi * ell), fL, "Hz", tol=0.5)
    p.metric("Exact quarter-wave resonance / one section / 4 / 32 sections", f"{f_exact / 1e6:.1f} / {res[1] / 1e6:.1f} / {res[4] / 1e6:.2f} / {res[32] / 1e6:.3f} MHz")
    p.compare("Ladder resonance error ∝ 1/n² (ratio of errors, 16 → 32 sections)", 4.0, (f_exact - res[16]) / (f_exact - res[32]), "×", tol=5)
    fig, ax = p.fig(1, 2, w=11)
    for n, c in zip((1, 2, 4, 8, 16), COLORS):
        ax[0].loglog(el, err[n] * 100, color=c, label=f"{n} section{'s' if n > 1 else ''}")
    ax[0].axvline(0.1, color="gray", ls=":", label="λ/10"); ax[0].set_ylim(1e-4, 300)
    style_axes(ax[0], "line length / wavelength", "|Z_in error| (%)", "Lumped ladders vs the exact line (100 Ω load)")
    ns = np.array(sorted(res)); ax[1].loglog(ns, [(f_exact - res[n]) / f_exact * 100 for n in ns], "o-", color=C_MEAS, label="ladder"); ax[1].loglog(ns, ((f_exact - res[1]) / f_exact * 100) / ns ** 2 * 1.0, ":", color="gray", label="∝ 1/n²")
    style_axes(ax[1], "number of LC sections", "error of the first resonance (%)", "Open line: quarter-wave resonance")
    p.save(fig, "lumped", "Input-impedance error of lumped ladder models versus line length, and convergence of the quarter-wave resonance.")
    p.discuss(f"""The lumped model does not fail at a threshold; its error grows smoothly — as (βℓ)³ for a symmetric π section, faster than the (βℓ)² I first
assumed, because splitting the capacitance symmetrically cancels the second-order term. A single π section is within {at(1, 0.01) * 100:.2f} % at λ/100, {at(1, 0.05) * 100:.1f} % at λ/20
and {at(1, 0.1) * 100:.1f} % at λ/10 — which is what the 'λ/10 rule' really buys — and is useless by λ/4 ({at(1, 0.25) * 100:.0f} %). Splitting the line into n sections cuts the error as 1/n², because each
section is itself accurate to second order in its own electrical length. The resonance test shows how much the *arrangement* of the lumps matters: an
open-ended 1 m line resonates at {f_exact / 1e6:.0f} MHz; one π section predicts {res[1] / 1e6:.1f} MHz, but the same inductance and capacitance arranged as an L section predict
{fL / 1e6:.1f} MHz — the 2/π factor between an LC tank and a quarter-wave standing wave. My first prediction used the L-section formula for the π section and
was 30 % off. Even 32 sections leave {(f_exact - res[32]) / f_exact * 100:.3f} % of error. The 'distributed' view is not a correction to the lumped one; the lumped circuit is
its low-frequency limit.""")
# tol-convention: relative tolerances are in percent
