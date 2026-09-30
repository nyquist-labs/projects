from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-086", title="Manufacturing yield from component tolerances", level="M",
    tools="Monte-Carlo circuit simulation of a Sallen-Key low-pass with toleranced parts, first-order sensitivity analysis, Gaussian vs uniform tolerance models, yield vs specification",
    summary="Predict the spread of a filter's cutoff frequency from component sensitivities, check it with 5,000 Monte-Carlo circuits, and "
            "compute manufacturing yield against a ±5 % specification for different capacitor grades and tolerance distributions.",
    problem="A design is built from 1 % resistors and 5 % capacitors. What fraction of boards will meet a ±5 % cutoff specification?",
    theory=r"""f0 = 1/(2π√(R1R2C1C2)) so each part has sensitivity −½: $\frac{σ_{f}}{f}≈\frac12\sqrt{σ_{R1}^2+σ_{R2}^2+σ_{C1}^2+σ_{C2}^2}$. With parts spread uniformly over ±t (σ = t/√3): 1 % R and 5 % C give σ_f ≈ 2.1 %; if the parts are Gaussian with
±t = 3σ, σ_f ≈ 1.2 %. Yield for |Δf| < 5 % = 2Φ(5/σ_f) − 1: ≈ 98 % (uniform) vs ≈ 100 %; with 10 % capacitors ≈ 76 %.""",
    method="""Unity-gain Sallen-Key Butterworth low-pass at 1 kHz (R = 10 kΩ, C1 = 22.5 nF, C2 = 11.25 nF). 5,000 circuits per case built in the MNA simulator; −3 dB frequency measured; cases: (1 % R, 5 % C) uniform and
Gaussian, (1 %, 10 %) uniform. Q spread also reported.""",
)


def f3db(R1, R2, C1, C2):
    ck = Circuit("sk"); ck.V("s", "in", "0", ac=1); ck.R("1", "in", "a", R1); ck.R("2", "a", "b", R2); ck.C("1", "a", "out", C1); ck.C("2", "b", "0", C2)
    ck.OPAMP("U", "b", "out", "out", A0=1e6, GBW=1e8)
    f = np.logspace(2.5, 3.5, 400); H = np.abs(ck.ac(f).v("out"))
    return find_crossing(f, db(H) - db(H[0]), -3.0103, falling=True)


def run(p):
    R, C1, C2 = 10e3, 2 * 0.7071 / (2 * pi * 1e3 * 10e3), 1 / (2 * 0.7071 * 2 * pi * 1e3 * 10e3)
    f0 = f3db(R, R, C1, C2)
    p.compare("Nominal −3 dB frequency", 1000, f0, "Hz", tol=1)
    nom = [R, R, C1, C2]; sens = []
    for i in range(4):                                       # sensitivities d ln f₋₃ / d ln x_i measured on the simulated circuit
        up = list(nom); dn = list(nom); up[i] *= 1.01; dn[i] /= 1.01
        sens.append((np.log(f3db(*up)) - np.log(f3db(*dn))) / (2 * np.log(1.01)))
    sens = np.array(sens)
    p.metric("Measured sensitivities S(R1), S(R2), S(C1), S(C2) of the −3 dB frequency", ", ".join(f"{v:+.3f}" for v in sens), "", "f0 alone would give −0.5 each")
    r = p.rng; N = 5000
    res = {}
    for name, tr, tc, dist in (("1 % R, 5 % C, uniform", 0.01, 0.05, "u"), ("1 % R, 5 % C, Gaussian (t = 3σ)", 0.01, 0.05, "g"), ("1 % R, 10 % C, uniform", 0.01, 0.10, "u")):
        draw = (lambda t, n: r.uniform(-t, t, n)) if dist == "u" else (lambda t, n: r.normal(0, t / 3, n))
        fs = []
        a, b, c, d = draw(tr, N), draw(tr, N), draw(tc, N), draw(tc, N)
        for k in range(N):
            fs.append(f3db(R * (1 + a[k]), R * (1 + b[k]), C1 * (1 + c[k]), C2 * (1 + d[k])))
        fs = np.array(fs) / f0 - 1
        sd = tr / np.sqrt(3) if dist == "u" else tr / 3; sc = tc / np.sqrt(3) if dist == "u" else tc / 3
        pred_f0 = 0.5 * np.sqrt(2 * sd ** 2 + 2 * sc ** 2)                 # first model: f0 sensitivity only
        # corrected model: the −3 dB point also moves with Q; Q ∝ √(C1/C2) for equal resistors, so S_C1 = −½ + ½k, S_C2 = −½ − ½k
        pred_full = np.sqrt((sens[0] * sd) ** 2 + (sens[1] * sd) ** 2 + (sens[2] * sc) ** 2 + (sens[3] * sc) ** 2)
        from scipy.stats import norm
        res[name] = (fs, pred_f0, pred_full, 2 * norm.cdf(0.05 / pred_full) - 1)
    for name, (fs, pf0, pfull, pyield) in res.items():
        p.compare(f"{name}: σ of cutoff, first model (f0 sensitivity only)", pf0 * 100, fs.std() * 100, "%", tol=10)
        p.compare(f"{name}: σ of cutoff, corrected model (sensitivities measured on the circuit)", pfull * 100, fs.std() * 100, "%", tol=10)
        p.compare(f"{name}: yield for |Δf| < 5 % (Gaussian approx., corrected σ)", pyield * 100, np.mean(np.abs(fs) < 0.05) * 100, "%", kind="abs", tol=3)
    fig, ax = p.fig(1, 1, w=8, h=4.5)
    for (name, (fs, psd, _, _)), c in zip(res.items(), COLORS):
        ax.hist(fs * 100, bins=70, histtype="step", color=c, lw=1.5, label=name, density=True)
    ax.axvline(-5, color="black", ls=":"); ax.axvline(5, color="black", ls=":", label="±5 % spec")
    style_axes(ax, "cutoff error (%)", "density", "Cutoff spread over 5,000 simulated boards per case")
    p.save(fig, "yield", "Distribution of the simulated cutoff frequency for three tolerance scenarios, with the ±5 % specification.")
    p.discuss(f"""My first sensitivity model — every part enters f0 with exponent −½, so relative variances add with weight ¼ — under-predicted the Monte-Carlo
spread by about 25 % in every scenario. The missing piece: the −3 dB frequency is not f0; it also depends on Q, and Q depends on the capacitor *ratio*, so the two capacitors
have unequal influence (measured sensitivities {sens[2]:+.2f} and {sens[3]:+.2f} instead of −0.5 each). An analytic attempt at that correction
over-shot by 10 %; taking the sensitivities by finite differences on the simulated circuit — the standard practice — makes the linear model
match the Monte-Carlo spread within a few percent. But even the right σ does not give the right yield when parts are uniformly distributed: because one
capacitor dominates (sensitivity −0.89), the cutoff distribution inherits that part's flat-topped shape, and a Gaussian with the same σ
under-estimates yield at ±5 % tolerance and over-estimates it at ±10 %. Yield is a statement about tails, so it needs the Monte-Carlo (or the true
part distribution), not just the variance. The assumed part
distribution matters as much as the tolerance printed on the reel: parts spread uniformly across ±5 % give nearly twice the σ of parts whose ±5 %
is a 3σ limit, and in practice distributions are often truncated or bimodal because tight-tolerance parts were sorted out. Moving from 5 % to
10 % capacitors drops yield to about three quarters — the capacitors, not the resistors, set the yield of this filter.""")
# tol-convention: relative tolerances are in percent
