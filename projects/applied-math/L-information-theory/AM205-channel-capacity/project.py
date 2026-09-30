from eelab import *
from eelab.info import blahut_arimoto, mutual_info, h2
from scipy.optimize import minimize

META = dict(
    id="AM-205", title="Channel capacity: the Blahut–Arimoto algorithm", level="H",
    tools="Own Blahut–Arimoto iteration with certified upper/lower bounds, closed-form capacities (BSC, BEC, Z-channel, symmetric channels), brute-force maximisation of the mutual information as an independent check, a channel estimated from simulated noisy 4-PAM with a hard-decision receiver",
    summary="Compute the capacity of any discrete memoryless channel by the alternating-maximisation algorithm of Blahut and Arimoto, verify it against every "
            "channel with a closed form and against direct numerical optimisation, and show that the capacity-achieving input need not be uniform.",
    problem="A channel is a table of transition probabilities. What is the most information per use it can carry, and which input distribution achieves it?",
    theory=r"""$C=\max_{p(x)}I(X;Y)$. BSC(ε): $1-H_2(ε)$; BEC(ε): $1-ε$; symmetric channels: uniform input, $C=\log_2|Y|-H(\text{row})$. Z-channel (1 → 0 with probability ε, 0 always correct): $C=\log_2\left(1+(1-ε)ε^{ε/(1-ε)}\right)$, achieved with
$P(X=1)=\frac{1}{(1-ε)\left(1+2^{H_2(ε)/(1-ε)}\right)}$, less than ½. Blahut–Arimoto alternates between the output distribution and the input distribution; at every step $\log_2\sum_xp(x)2^{D_x}\le C\le\max_xD_x$ with $D_x=D(W_x\|p_Y)$, so the gap certifies convergence.""",
    method="""Closed-form channels at several ε; 200 random channels (2–6 inputs, 2–8 outputs) against SciPy optimisation of I(X;Y) over the simplex (softmax parametrisation, 5 random starts). 4-PAM with Gaussian noise at 6 dB and 12 dB: transition matrix of the hard-decision
channel estimated from 10⁶ symbols, its capacity and optimal input.""",
)


def run(p):
    r = p.rng
    for e in (0.01, 0.11, 0.3):
        W = np.array([[1 - e, e], [e, 1 - e]]); C, px, gap, it = blahut_arimoto(W)
        p.compare(f"BSC(ε = {e}): capacity 1 − H₂(ε)", 1 - h2(e), C, "bit", tol=1e-6)
    W = np.array([[0.75, 0.25, 0.0], [0.0, 0.25, 0.75]]); C, _, _, _ = blahut_arimoto(W)
    p.compare("BEC(0.25): capacity 1 − ε", 0.75, C, "bit", tol=1e-6)
    e = 0.3; W = np.array([[1, 0], [e, 1 - e]]); C, px, gap, it = blahut_arimoto(W)
    Cz = np.log2(1 + (1 - e) * e ** (e / (1 - e))); p1 = 1 / ((1 - e) * (1 + 2 ** (h2(e) / (1 - e))))
    p.compare("Z-channel (ε = 0.3): capacity log₂(1 + (1−ε)ε^{ε/(1−ε)})", Cz, C, "bit", tol=1e-6)
    p.compare("Z-channel: optimal P(X = 1) (not ½)", p1, px[1], "", tol=1e-4)
    p.metric("Z-channel: mutual information with a uniform input", mutual_info(np.array([0.5, 0.5]), W), "bit", f"vs capacity {C:.4f} — the loss from not optimising the input")
    sym = np.array([[0.7, 0.2, 0.1], [0.1, 0.7, 0.2], [0.2, 0.1, 0.7]]); Cs, ps, _, _ = blahut_arimoto(sym)
    p.compare("Symmetric 3-ary channel: log₂3 − H(row)", np.log2(3) - (-np.sum(sym[0] * np.log2(sym[0]))), Cs, "bit", tol=1e-6)
    worst = 0.0; worst_gap = 0.0; its = []
    for _ in range(200):
        nx, ny = int(r.integers(2, 7)), int(r.integers(2, 9)); Wr = r.dirichlet(np.ones(ny) * 0.5, nx)
        C, px, gap, it = blahut_arimoto(Wr); its.append(it); worst_gap = max(worst_gap, gap)
        best = 0.0
        for _ in range(5):
            res = minimize(lambda z: -mutual_info(np.exp(z) / np.exp(z).sum(), Wr), r.normal(size=nx), method="Nelder-Mead", options=dict(maxiter=4000, xatol=1e-10, fatol=1e-13))
            best = max(best, -res.fun)
        worst = max(worst, best - C)
    p.compare("200 random channels: best mutual information found by direct optimisation minus Blahut–Arimoto capacity (never positive)", 0.0, worst, "bit", kind="abs", tol=1e-7)
    p.compare("Certified bound gap (upper − lower) at termination, worst channel", 0.0, worst_gap, "bit", kind="abs", tol=1e-10)
    p.metric("Blahut–Arimoto iterations: median / max", f"{int(np.median(its))} / {int(np.max(its))}")
    rows = []
    for snr in (6, 12):
        lv = np.array([-3, -1, 1, 3.0]); sig = np.sqrt(np.mean(lv ** 2) / 10 ** (snr / 10))
        x = r.integers(0, 4, 1_000_000); y = lv[x] + sig * r.normal(size=x.size); yh = np.clip(np.round((y + 3) / 2), 0, 3).astype(int)
        Wp = np.zeros((4, 4)); np.add.at(Wp, (x, yh), 1); Wp /= Wp.sum(1, keepdims=True)
        C, px, _, _ = blahut_arimoto(Wp); rows.append((snr, C, px, mutual_info(np.full(4, 0.25), Wp)))
    p.metric("Hard-decision 4-PAM: capacity at 6 / 12 dB", f"{rows[0][1]:.3f} / {rows[1][1]:.3f} bit/symbol", "", "out of 2")
    p.metric("… optimal input at 6 dB (outer, inner, inner, outer levels)", ", ".join(f"{v:.3f}" for v in rows[0][2]), "", f"uniform input gives {rows[0][3]:.3f} bit — the outer levels, which are more reliable, are used more")
    fig, ax = p.fig(1, 2, w=11)
    es = np.linspace(0.001, 0.5, 100)
    ax[0].plot(es, 1 - h2(es), color=C_MEAS, label="BSC"); ax[0].plot(es, 1 - es, color=C_PRED, label="BEC")
    ax[0].plot(es, [blahut_arimoto(np.array([[1, 0], [q, 1 - q]]))[0] for q in es], color=COLORS[2], label="Z-channel")
    style_axes(ax[0], "crossover / erasure probability ε", "capacity (bit/use)", "Three binary channels")
    ax[1].plot(es, [blahut_arimoto(np.array([[1, 0], [q, 1 - q]]))[1][1] for q in es], color=COLORS[2], label="Z-channel optimal P(X=1)"); ax[1].axhline(0.5, color="gray", ls=":")
    style_axes(ax[1], "ε", "optimal P(X = 1)", "The optimal input is not always uniform")
    p.save(fig, "capacity", "Capacities of three binary channels and the optimal input distribution of the Z-channel.")
    p.discuss(f"""Blahut–Arimoto reproduces every closed-form capacity — BSC, BEC, symmetric and Z-channels — to 10⁻⁶ or better, and on 200 random channels no
direct optimisation found more mutual information than it certified (the upper and lower bounds met to {worst_gap:.0e}). The Z-channel shows why an
algorithm is needed at all: its best input sends '1' only {p1 * 100:.1f} % of the time at ε = 0.3, because every 1 risks being received as 0 while 0s are
safe. The same effect appears in a hard-decision 4-PAM receiver at 6 dB, where the optimal input favours the outer, less confusable levels. For
symmetric channels the uniform input is optimal and capacity is a formula; for everything else it is an optimisation with a guaranteed stopping
certificate.""")
# tol-convention: relative tolerances are in percent
