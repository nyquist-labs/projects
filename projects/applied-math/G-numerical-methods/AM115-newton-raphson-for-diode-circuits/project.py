from eelab import *
from scipy.special import lambertw

META = dict(
    id="AM-115", title="Newton–Raphson for a diode circuit (what SPICE does inside)", level="H",
    tools="Plain, damped and junction-limited Newton iterations for a resistor–diode circuit, exact solution via the Lambert W function, convergence-order measurement, basin-of-convergence map",
    summary="Solve the nonlinear equation of a diode fed through a resistor with Newton's method, verify quadratic convergence against the exact "
            "Lambert-W solution, show how plain Newton overflows from a poor starting guess, and fix it with SPICE-style voltage limiting.",
    problem="Every DC operating point in SPICE is a Newton solve. Why does it sometimes fail to converge, and what do simulators do about it?",
    theory=r"""f(V_d) = (V_s − V_d)/R − I_s(e^{V_d/nV_T} − 1) = 0. Exact: $I = \frac{nV_T}{R}W\!\left(\frac{I_sR}{nV_T}e^{(V_s+I_sR)/nV_T}\right)-I_s$. Newton converges quadratically near the root (error squares each step), but the exponential makes the tangent from a
large V_d guess land far away, and from V_d ≈ 2 V the next exp overflows. Junction limiting (clamp the change of V_d to ~2nV_T·ln(ΔV/(nV_T)) above V_crit) keeps iterates in range.""",
    method="""V_s = 5 V, R = 1 kΩ, I_s = 1e-14 A, n = 1; starting guesses 0…5 V. Iterations to 1e-12 V; error ratios e_{k+1}/e_k² at the end; plain vs damped (step halving on increasing |f|) vs SPICE pnjlim.""",
)

VT = 0.025852; IS = 1e-14; R = 1e3; VS = 5.0


def f(v):
    return (VS - v) / R - IS * np.expm1(v / VT)


def fp(v):
    return -1 / R - IS / VT * np.exp(v / VT)


def pnjlim(vnew, vold, vcrit=VT * np.log(VT / (np.sqrt(2) * IS))):
    if vnew > vcrit and abs(vnew - vold) > 2 * VT:
        if vold > 0:
            arg = 1 + (vnew - vold) / VT
            vnew = vold + VT * np.log(arg) if arg > 0 else vcrit
        else:
            vnew = VT * np.log(vnew / VT)
    return vnew


def newton(v0, mode, tol=1e-12, maxit=500):
    v = v0; hist = [v]
    for k in range(maxit):
        with np.errstate(over="raise", invalid="raise"):
            try:
                step = -f(v) / fp(v)
            except FloatingPointError:
                return None, hist
        vn = v + step
        if mode == "damped":
            t = 1.0
            with np.errstate(over="ignore", invalid="ignore"):
                while not np.isfinite(f(v + t * step)) or abs(f(v + t * step)) > abs(f(v)):
                    t /= 2
                    if t < 1e-12:
                        break
            vn = v + t * step
        elif mode == "limited":
            vn = pnjlim(vn, v)
        if not np.isfinite(vn):
            return None, hist
        hist.append(vn)
        if abs(vn - v) < tol:
            return vn, hist
        v = vn
    return None, hist


def run(p):
    w = lambertw(IS * R / VT * np.exp((VS + IS * R) / VT)).real
    I = VT / R * w - IS; vd = VS - I * R
    p.metric("Exact diode voltage from Lambert W", vd, "V")
    x, h = newton(0.6, "plain")
    p.compare("Newton from 0.6 V converges to the Lambert-W solution", vd, x, "V", tol=1e-10)
    e = np.abs(np.array(h) - vd); e = e[e > 1e-15]
    q = e[-1] / e[-2] ** 2 if len(e) > 2 else np.nan
    p.compare("Quadratic convergence: e_{k+1}/e_k² ≈ |f''/2f'| at the root", abs((-IS / VT ** 2 * np.exp(vd / VT)) / (2 * fp(vd))), e[-1] / e[-2] ** 2, "1/V", tol=50)
    starts = np.linspace(0.0, 5.0, 101)
    out = {m: [newton(s, m) for s in starts] for m in ("plain", "damped", "limited")}
    conv = {m: np.array([x is not None and abs(x - vd) < 1e-9 for x, _ in out[m]]) for m in out}
    its = {m: np.array([len(hh) - 1 if x is not None else np.nan for x, hh in out[m]]) for m in out}
    p.compare("Plain Newton: fraction of starts in 0–5 V that converge (my first guess was 0.2 — wrong: it crawls, it does not fail)", 1.0, conv["plain"].mean(), "", kind="abs", tol=1e-9)
    p.compare("Junction-limited Newton converges from every start (fraction)", 1.0, conv["limited"].mean(), "", tol=1e-07)
    _, h5 = newton(5.0, "plain"); _, h0 = newton(0.0, "plain"); _, hl = newton(0.0, "limited")
    p.compare("Plain Newton from 5 V: one V_T per iteration ⇒ ≈ (5 − V_d)/V_T + 6 iterations", (5 - vd) / VT + 6, len(h5) - 1, "", tol=5)
    p.compare("Plain Newton from 0 V: first iterate overshoots to ≈ V_S", VS, h0[1], "V", tol=1)
    p.metric("Iterations from 0 V: plain / junction-limited", f"{len(h0) - 1} / {len(hl) - 1}")
    p.compare("Plain Newton from 20 V: e^(V/V_T) overflows and the iteration dies (1 = fails)", 1, int(newton(20.0, "plain")[0] is None), "", kind="abs")
    p.metric("Median iterations over all starts 0–5 V: plain / damped / limited", f"{np.nanmedian(its['plain']):.0f} / {np.nanmedian(its['damped']):.0f} / {np.nanmedian(its['limited']):.0f}", "", "limiting only helps against overshoot from below; above the root every variant walks down one V_T at a time")
    fig, ax = p.fig(1, 2, w=11)
    for m, c in (("plain", COLORS[1]), ("damped", COLORS[2]), ("limited", C_MEAS)):
        ax[0].plot(starts, np.where(conv[m], its[m], np.nan), "o", ms=3, color=c, label=m)
    style_axes(ax[0], "starting guess V_d (V)", "iterations (missing = failed)", "Basin of convergence")
    _, h1 = newton(0.6, "plain"); _, h2 = newton(3.0, "limited")
    ax[1].semilogy(np.abs(np.array(h1) - vd) + 1e-17, "o-", color=COLORS[1], label="plain from 0.6 V")
    ax[1].semilogy(np.abs(np.array(h2) - vd) + 1e-17, "s-", color=C_MEAS, label="limited from 3.0 V")
    style_axes(ax[1], "iteration", "|V_d − V*| (V)", "Linear phase, then quadratic")
    p.save(fig, "newton_diode", "Which starting points converge for each Newton variant, and the error history.")
    p.discuss(f"""Newton's method solves the diode equation to machine precision and, once close, the error squares at every step (the ratio e_{{k+1}}/e_k² approaches
|f''/2f'|) — the famous quadratic convergence. Far from the root it is not so much fragile as painfully slow — and here my
first expectation was wrong. I predicted that plain Newton would fail from most of the 0–5 V range; in fact it converged from every start, because on
the exponential branch each step moves the iterate down by almost exactly one thermal voltage: {len(h5) - 1} iterations from 5 V. A start at 0 V is
no better — the shallow tangent throws the first iterate to ≈ V_S = 5 V and the same crawl follows ({len(h0) - 1} iterations). Real failure needs an
overflow of e^{{V/V_T}}, which happens from about 18 V. SPICE's junction limiting caps how far the diode voltage may *rise* in one iteration on a
logarithmic scale, which removes the overshoot ({len(hl) - 1} iterations from 0 V) but cannot speed up the descent from above — one reason simulators
start junctions near V_crit instead of at an arbitrary guess. Circuits with many junctions still sometimes defeat it — then simulators fall back on gmin stepping and source stepping (the same
homotopies the repository's own simulator uses).""")
# tol-convention: relative tolerances are in percent
