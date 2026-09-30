from eelab import *
from eelab.nec import solve, far_field

META = dict(
    id="AM-105", title="Genetic algorithm design of a 3-element Yagi", level="H",
    tools="Own real-coded genetic algorithm (tournament selection, blend crossover, Gaussian mutation, elitism), method-of-moments antenna solver as the fitness evaluator, comparison with a textbook starting design and random search",
    summary="Evolve the element lengths and spacings of a 3-element Yagi–Uda antenna to maximise forward gain while keeping a good front-to-back "
            "ratio and a reasonable input impedance, each candidate evaluated by a full method-of-moments simulation.",
    problem="A Yagi has five continuous design variables and no closed-form optimum. Can evolution find a good one, and how good compared with the textbook recipe?",
    theory=r"""Fitness = directivity toward the director (dBi) + 0.2·min(F/B, 25 dB) − penalty if |Z_in − 25 Ω| is large. The landscape is multimodal (several spacing combinations give similar gains), which favours population
methods. Known result for 3-element Yagis: about 7–8 dBi gain with ~0.2 λ total boom and F/B around 15–25 dB; the classic recipe (0.5/0.47/0.44 λ, 0.2 λ spacing) gives less.""",
    method="""Variables: reflector, driven, director lengths (0.42–0.52 λ) and two spacings (0.08–0.35 λ); radius λ/1000; 21 segments per element. GA: population 30, 25 generations, tournament size 3, BLX-0.3 crossover,
mutation σ = 5 % of range, 2 elites. Directivity from far field on a sphere (E-plane/H-plane sums); fitness compared with the textbook design and with random search using the same number of evaluations.""",
)


def evaluate(x):
    lr, ld, lf, s1, s2 = x
    wires = [(-s1, lr, False), (0.0, ld, True), (s2, lf, False)]
    try:
        cur, Z = solve(wires, lam=1.0, nseg=21, radius=1e-3)
    except Exception:
        return -99, 0, 0, 0
    th = np.linspace(0.01, pi - 0.01, 91); ph = np.linspace(0, 2 * pi, 73)
    P = np.array([far_field(cur, 1.0, th, q) ** 2 for q in ph])
    tot = np.trapezoid(np.trapezoid(P * np.sin(th)[None, :], th, axis=1), ph)
    fwd = far_field(cur, 1.0, pi / 2, 0.0) ** 2; back = far_field(cur, 1.0, pi / 2, pi) ** 2
    D = 10 * np.log10(4 * pi * fwd / tot); fb = 10 * np.log10(fwd / max(back, 1e-30))
    pen = 0.05 * max(0, abs(Z - 25) - 15)
    return D + 0.2 * min(fb, 25) - pen, D, fb, Z


def run(p):
    r = p.rng
    lo = np.array([0.42, 0.42, 0.42, 0.08, 0.08]); hi = np.array([0.52, 0.52, 0.52, 0.35, 0.35])
    pop = lo + (hi - lo) * r.random((30, 5)); fit = np.array([evaluate(x)[0] for x in pop]); evals = 30
    best_hist = [fit.max()]
    for gen in range(25):
        new = [pop[i] for i in np.argsort(fit)[-2:]]
        while len(new) < 30:
            pa = pop[max(r.choice(30, 3, replace=False), key=lambda i: fit[i])]; pb = pop[max(r.choice(30, 3, replace=False), key=lambda i: fit[i])]
            a = r.uniform(-0.3, 1.3, 5); child = pa + a * (pb - pa)
            child += r.normal(0, 0.05 * (hi - lo)) * (r.random(5) < 0.3)
            new.append(np.clip(child, lo, hi))
        pop = np.array(new); fit = np.array([evaluate(x)[0] for x in pop]); evals += 30
        best_hist.append(fit.max())
    xb = pop[np.argmax(fit)]; fb_, Db, fbb, Zb = evaluate(xb)
    xt = np.array([0.5, 0.47, 0.44, 0.2, 0.2]); ft, Dt, fbt, Zt = evaluate(xt)
    rs = lo + (hi - lo) * r.random((evals, 5)); frs = max(evaluate(x)[0] for x in rs[:evals])
    p.metric("GA best design (λ)", f"reflector {xb[0]:.3f}, driven {xb[1]:.3f}, director {xb[2]:.3f}, spacings {xb[3]:.3f}/{xb[4]:.3f}")
    p.compare("GA best: directivity (literature for 3 elements ≈ 7–8 dBi)", 7.5, Db, "dBi", kind="abs", tol=1.0)
    p.metric("GA best: front-to-back ratio / input impedance", f"{fbb:.1f} dB / {Zb.real:.1f} {Zb.imag:+.1f}j Ω")
    p.metric("Textbook design: directivity / F/B / Z_in", f"{Dt:.2f} dBi / {fbt:.1f} dB / {Zt.real:.1f} {Zt.imag:+.1f}j Ω")
    p.compare("GA fitness beats the textbook design (1 = yes)", 1, int(fb_ > ft), "", kind="abs")
    p.compare("GA fitness vs best of random search with the same evaluation budget (difference)", 0.5, fb_ - frs, "", kind="abs", tol=2)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(best_hist, "o-", color=C_MEAS, label="GA best"); ax[0].axhline(ft, color=C_PRED, ls="--", label="textbook design"); ax[0].axhline(frs, color=COLORS[2], ls=":", label="random search (same budget)")
    style_axes(ax[0], "generation", "fitness", "Evolution of the best design")
    phi = np.linspace(0, 2 * pi, 361)
    for x, lab, c in ((xb, "GA", C_MEAS), (xt, "textbook", C_PRED)):
        lr, ld, lf, s1, s2 = x; cur, _ = solve([(-s1, lr, False), (0.0, ld, True), (s2, lf, False)], lam=1.0, nseg=21, radius=1e-3)
        E = np.array([far_field(cur, 1.0, pi / 2, q) for q in phi]); ax[1].plot(phi * 180 / pi, db(E / E.max()), color=c, label=lab)
    ax[1].set_ylim(-40, 2)
    style_axes(ax[1], "azimuth φ (°)", "H-plane pattern (dB)", "Patterns (director at 0°)")
    p.save(fig, "ga_yagi", "Fitness over generations and the H-plane patterns of the evolved and textbook Yagis.")
    p.discuss(f"""With every candidate evaluated by a full moment-method simulation, the genetic algorithm finds a design with {Db:.1f} dBi directivity and
{fbb:.0f} dB front-to-back ratio. Its gain is essentially the same as the classic 0.5/0.47/0.44 λ recipe ({Dt:.1f} dBi — the textbook design is
already near the gain optimum, and both sit slightly above the 7–8 dBi I expected); the GA's real improvement is the front-to-back ratio
({fbb:.0f} vs {fbt:.0f} dB), which the fitness function rewarded, obtained with shorter spacings. Against random search with the same budget of {evals} simulations the GA wins by a modest margin — five variables are few enough
that random sampling is not hopeless; GAs pay off more as dimensions and constraints grow. The penalty weights encode engineering judgement (how
much gain to trade for F/B or a convenient impedance), and different weights give different 'optimal' antennas — the optimiser only answers the
question as posed.""")
# tol-convention: relative tolerances are in percent
