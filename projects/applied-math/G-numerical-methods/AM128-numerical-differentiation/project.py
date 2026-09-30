from eelab import *
from scipy import signal

META = dict(
    id="AM-128", title="Numerical differentiation: step size, round-off and noise", level="M",
    tools="Forward/central differences, the truncation–round-off trade-off and optimal step, the complex-step derivative, Richardson extrapolation, group delay from noisy measured phase with smoothing",
    summary="Differentiate a circuit's phase response numerically, find the optimal step where truncation and round-off errors balance, show the complex-step "
            "method's immunity to cancellation, and quantify the noise amplification that makes group delay from measured phase so hard.",
    problem="Group delay is a derivative of measured phase. Why is it always noisy — and how small should the frequency step be?",
    theory=r"""Central difference error ≈ h²f‴/6 + ε|f|/h ⇒ optimal h ~ (3ε|f|/|f‴|)^{1/3} ≈ ε^{1/3} (≈ 6×10⁻⁶ relative), best error ~ ε^{2/3}. Forward difference: h ~ ε^{1/2}, error ~ ε^{1/2}. Complex step $f'(x)≈\mathrm{Im}f(x+ih)/h$ has no subtraction, so h can be 10⁻²⁰⁰ and the result is exact to
machine precision (for analytic f). Measured phase noise σ_φ gives group-delay noise σ_φ√2/(Δω) (central): halving the step doubles the noise.""",
    method="""f(ω) = phase of a 4th-order Bessel low-pass; exact derivative from the pole formula. Steps h = 10⁻¹⁴…10⁻¹ (relative). Complex-step on the phase via log H. Measured-phase case: σ_φ = 0.1°, steps 0.1–10 % of the band; smoothing by
fitting a local quadratic.""",
)


def run(p):
    z, pz, k = signal.bessel(4, 1.0, analog=True, output="zpk", norm="mag")
    H = lambda w: k * np.prod([1j * w - q for q in z]) / np.prod([1j * w - q for q in pz])
    phase = lambda w: np.angle(H(w))
    tau = lambda w: sum(-q.real / (q.real ** 2 + (w - q.imag) ** 2) for q in pz)
    w0 = 0.7; t0 = tau(w0)
    hs = np.logspace(-14, -1, 40)
    fwd = np.array([abs(-(phase(w0 + h) - phase(w0)) / h - t0) for h in hs])
    cen = np.array([abs(-(phase(w0 + h) - phase(w0 - h)) / (2 * h) - t0) for h in hs])
    # complex step on φ(ω) = −Σ arg(jω − p) = −Σ atan2(ω − Im p, −Re p): an analytic real function of ω
    phi_an = lambda wv: -sum(np.arctan((wv - q.imag) / (-q.real)) for q in pz)
    cstep = abs(-np.imag(phi_an(w0 + 1j * 1e-200)) / 1e-200 - t0)
    # error model with the actual derivatives (from the pole formula: second derivative of the phase = −dτ/dω, third = −d²τ/dω²), round-off ε_f ≈ ε·|φ|
    D = lambda q: q.real ** 2 + (w0 - q.imag) ** 2
    f2 = abs(sum(2 * q.real * (w0 - q.imag) / D(q) ** 2 for q in pz))
    f3 = abs(sum(2 * q.real * (D(q) - 4 * (w0 - q.imag) ** 2) / D(q) ** 3 for q in pz))
    ef = np.finfo(float).eps * abs(np.unwrap([0, phase(w0)])[1])
    hc_pred = (3 * ef / f3) ** (1 / 3); ec_pred = 1.5 * ef / hc_pred
    ef_pred = 2 * np.sqrt(ef * f2)
    hbest_c = hs[np.argmin(cen)]
    p.compare("Central difference: log₁₀ of the optimal step, from (3ε_f/|φ‴|)^(1/3)", np.log10(hc_pred), np.log10(hbest_c), "", kind="abs", tol=0.7)
    p.compare("Central difference: log₁₀ of the best error, 1.5·ε_f/h*", np.log10(ec_pred), np.log10(cen.min()), "", kind="abs", tol=1.0)
    p.compare("Forward difference: log₁₀ of the best error, 2√(ε_f·|φ″|)", np.log10(ef_pred), np.log10(fwd.min()), "", kind="abs", tol=1.0)
    p.metric("Generic rule of thumb ε^(2/3) / ε^(1/2) vs the actual best errors", f"{np.finfo(float).eps ** (2 / 3):.1e} / {np.sqrt(np.finfo(float).eps):.1e} vs {cen.min():.1e} / {fwd.min():.1e}", "",
             "the best error on a grid of steps is the luckiest sample — truncation and round-off partly cancel there — so it sits below the envelope estimates")
    p.compare("Complex-step derivative (h = 1e-200): error at machine precision", 0, cstep, "s", kind="abs", tol=1e-14)
    r = p.rng; sphi = np.deg2rad(0.1)
    rows = []
    for dw in (0.001, 0.003, 0.01, 0.03, 0.1):
        wg = np.arange(0.2, 1.2, dw)
        ph = np.array([phase(w) for w in wg]); ph = np.unwrap(ph) + r.normal(0, sphi, len(wg))
        gd = -np.gradient(ph, wg)
        err = gd - np.array([tau(w) for w in wg])
        rows.append((dw, np.std(err[2:-2]), sphi / (np.sqrt(2) * dw)))
    rr = np.array(rows)
    p.compare("Noisy phase (0.1°): group-delay noise = σ_φ/(√2·Δω) (worst ratio over steps)", 1.0, np.max(rr[:, 1] / rr[:, 2]), "", tol=25)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].loglog(hs, fwd, "o-", ms=3, color=COLORS[1], label="forward difference"); ax[0].loglog(hs, cen, "s-", ms=3, color=C_MEAS, label="central difference")
    ax[0].axhline(max(cstep, 1e-17), color=COLORS[2], ls="--", label="complex step")
    style_axes(ax[0], "step h", "|error in group delay| (s)", "Truncation vs round-off")
    ax[1].loglog(rr[:, 0], rr[:, 1], "o", color=C_MEAS, label="measured"); ax[1].loglog(rr[:, 0], rr[:, 2], "--", color=C_PRED, label="σ_φ/(√2Δω)")
    style_axes(ax[1], "frequency step Δω (rad/s)", "group-delay noise (s)", "Differentiating measured phase")
    p.save(fig, "numdiff", "Error vs step for finite differences and the complex step, and noise amplification when differentiating measured phase.")
    p.discuss(f"""The V-shaped error curves are the whole story of numerical differentiation: too large a step and truncation error (∝ h² for central differences)
dominates, too small and cancellation in f(x+h) − f(x−h) leaves only round-off (∝ ε/h). The optimum sits near ε^{{1/3}} for central and ε^{{1/2}} for forward
differences, with best achievable errors ~ε^{{2/3}} and ~ε^{{1/2}} — about 10 and 8 correct digits. That is the generic rule, and my first comparison used
exactly those scales — and missed the forward-difference result by a factor of 20. Putting the actual derivatives |φ″| and |φ‴| of this filter into
the error model improves the estimates but still leaves the measured minima up to a decade *below* them: the model gives the envelope of the error,
whereas the smallest error found on a grid of 40 steps is the lucky one where truncation and round-off happen to cancel. The scaling laws and the
location of the optimum are what the theory really predicts; the last digit of 'best error' is luck. The complex-step trick avoids the subtraction entirely
and gives a derivative correct to machine precision with an absurdly small step, for any analytic function. With *measured* phase the round-off
floor is replaced by measurement noise, and the noise of the derivative grows as 1/Δω exactly as predicted — the reason network analysers
specify a group-delay 'aperture' and why group-delay plots from real data are always smoothed.""")
# tol-convention: relative tolerances are in percent
