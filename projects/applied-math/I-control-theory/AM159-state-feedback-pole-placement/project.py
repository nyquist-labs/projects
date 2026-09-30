from eelab import *
from scipy import signal
from scipy.linalg import expm

META = dict(
    id="AM-159", title="State-feedback pole placement with Ackermann's formula", level="H",
    tools="Own Ackermann implementation (controllability matrix, matrix polynomial), comparison with scipy.signal.place_poles, controllability rank test, conditioning study versus system order, servo example with settling-time and control-effort predictions",
    summary="Place closed-loop poles anywhere with u = −Kx using Ackermann's formula, verify against an independent algorithm, show what happens "
            "for an uncontrollable system, measure how the accuracy of pole placement collapses with system order, and quantify the price of fast poles in actuator effort.",
    problem="If every state is measured, feedback can put the poles anywhere. How — and what stops us from making the system arbitrarily fast?",
    theory=r"""For a controllable pair (A, b): $K=[0\;\dots\;0\;1]\;\mathcal C^{-1}\,φ(A)$ with $\mathcal C=[b\;Ab\;\dots\;A^{n-1}b]$ and φ the desired characteristic polynomial. If rank 𝒞 < n some modes cannot be moved. The formula inverts 𝒞, whose condition number
grows with n — accurate for small systems, poor beyond n ≈ 10; orthogonal-transformation methods (Kautsky–Nichols–Van Dooren, used by SciPy) avoid that inversion, and I expected them to stay accurate. For a double-integrator servo with poles at $ω_n$, ζ: settling time ≈ 4/(ζω_n),
and the gains — hence the peak actuator effort for a step — scale with $ω_n^2$.""",
    method="""200 random controllable systems (n = 2…6): eigenvalues of A − bK vs requested. Random systems n = 2…14 for the conditioning study (median pole error of 20 systems each). Uncontrollable example with a decoupled mode.
Servo ẍ = u: ω_n = 2, 4, 8 rad/s, ζ = 0.7; step response via matrix exponential.""",
)


def ackermann(A, b, poles):
    n = A.shape[0]
    C = np.hstack([np.linalg.matrix_power(A, k) @ b for k in range(n)])
    c = np.real(np.poly(poles)); phi = sum(c[k] * np.linalg.matrix_power(A, n - k) for k in range(n + 1))
    e = np.zeros((1, n)); e[0, -1] = 1
    return e @ np.linalg.solve(C, phi), C


def pole_err(A, b, K, poles):
    got = np.linalg.eigvals(A - b @ K); err = 0
    got = list(got)
    for q in poles:
        i = int(np.argmin([abs(g - q) for g in got])); err = max(err, abs(got[i] - q) / max(1, abs(q))); got.pop(i)
    return err


def rand_poles(n, r):
    ps = []
    while len(ps) < n:
        if n - len(ps) >= 2 and r.random() < 0.5:
            re, im = -r.uniform(0.5, 3), r.uniform(0.5, 3); ps += [complex(re, im), complex(re, -im)]
        else:
            ps.append(-r.uniform(0.5, 4))
    return np.array(ps)


def run(p):
    r = p.rng; worst = 0; worst_sp = 0
    for _ in range(200):
        n = int(r.integers(2, 7)); A = r.normal(size=(n, n)); b = r.normal(size=(n, 1)); poles = rand_poles(n, r)
        K, _ = ackermann(A, b, poles); worst = max(worst, pole_err(A, b, K, poles))
        Ks = signal.place_poles(A, b, poles).gain_matrix; worst_sp = max(worst_sp, float(np.max(np.abs(K - Ks)) / np.max(np.abs(Ks))))
    p.compare("Ackermann: worst relative pole error over 200 random systems (n = 2…6)", 0.0, worst, "", kind="abs", tol=1e-6)
    p.compare("Ackermann gain vs scipy.signal.place_poles (worst relative difference)", 0.0, worst_sp, "", kind="abs", tol=1e-6)
    A = np.array([[0, 1, 0], [-2, -3, 0], [0, 0, 1.0]]); b = np.array([[0], [1], [0.0]])
    Cu = np.hstack([np.linalg.matrix_power(A, k) @ b for k in range(3)])
    p.compare("Uncontrollable example (unstable mode decoupled from the input): rank of the controllability matrix", 2, int(np.linalg.matrix_rank(Cu)), "", kind="abs")
    Kany = np.array([[5.0, 7.0, 100.0]])
    p.compare("… its unstable eigenvalue +1 survives any feedback gain", 1.0, float(np.max(np.linalg.eigvals(A - b @ Kany).real)), "", tol=1e-6)
    ns = list(range(2, 15)); ea = []; es = []; cond = []; evc = []; sens = []
    for n in ns:
        a_, s_, c_, v_, q_ = [], [], [], [], []
        for _ in range(20):
            A = r.normal(size=(n, n)) / np.sqrt(n); b = r.normal(size=(n, 1)); poles = -np.linspace(0.5, 3, n)
            K, C = ackermann(A, b, poles); a_.append(pole_err(A, b, K, poles)); c_.append(np.linalg.cond(C))
            Ks = signal.place_poles(A, b, poles).gain_matrix
            s_.append(pole_err(A, b, Ks, poles))
            v_.append(np.linalg.cond(np.linalg.eig(A - b @ Ks)[1]))
            dA = r.normal(size=(n, n)) * 1e-8                       # a model error of one part in 10⁸
            q_.append(pole_err(A + dA, b, Ks, np.linalg.eigvals(A - b @ Ks)))
        ea.append(np.median(a_)); es.append(np.median(s_)); cond.append(np.median(c_)); evc.append(np.median(v_)); sens.append(np.median(q_))
    p.compare("Accuracy collapses with order: Ackermann pole error at n = 14 exceeds 1 % (1 = yes)", 1, int(ea[-1] > 1e-2), "", kind="abs")
    p.compare("I expected the orthogonal method (place_poles) to stay accurate at n = 14 (error < 10⁻⁶; 1 = yes)", 1, int(es[-1] < 1e-6), "", kind="abs")
    p.metric("Median pole error, Ackermann, n = 4 / 8 / 12 / 14", " / ".join(f"{ea[ns.index(k)]:.1e}" for k in (4, 8, 12, 14)))
    p.metric("Median pole error, place_poles, n = 4 / 8 / 12 / 14", " / ".join(f"{es[ns.index(k)]:.1e}" for k in (4, 8, 12, 14)))
    p.metric("Condition number of the closed-loop eigenvector matrix, n = 4 / 8 / 14", " / ".join(f"{evc[ns.index(k)]:.1e}" for k in (4, 8, 14)), "", "how much the placed poles move per unit perturbation of A − bK")
    p.metric("Pole shift caused by a 10⁻⁸ perturbation of A, n = 4 / 8 / 14", " / ".join(f"{sens[ns.index(k)]:.1e}" for k in (4, 8, 14)), "", "relative to the pole magnitudes")
    p.metric("Median condition number of the controllability matrix, n = 4 / 14", f"{cond[ns.index(4)]:.1e} / {cond[-1]:.1e}")
    A = np.array([[0, 1.0], [0, 0]]); b = np.array([[0], [1.0]]); rows = []
    t = np.linspace(0, 6, 6001)
    for wn in (2.0, 4.0, 8.0):
        zt = 0.7; poles = [complex(-zt * wn, wn * np.sqrt(1 - zt ** 2)), complex(-zt * wn, -wn * np.sqrt(1 - zt ** 2))]
        K, _ = ackermann(A, b, poles); Acl = A - b @ K
        # step reference r = 1 on position: u = −K(x − [1, 0])
        E = expm(Acl * (t[1] - t[0])); x = np.array([-1.0, 0.0]); xs = []
        for _ in t:
            xs.append(x.copy()); x = E @ x
        xs = np.array(xs); y = xs[:, 0] + 1; u = -(xs @ K.T)[:, 0]
        ts = t[np.flatnonzero(np.abs(y - 1) > 0.02)[-1] + 1]
        rows.append((wn, K[0, 0], K[0, 1], ts, np.max(np.abs(u)), y))
        p.compare(f"ω_n = {wn:g}: gains [ω_n², 2ζω_n]", wn ** 2, K[0, 0], "", tol=1e-6)
    p.compare("Settling time (2 %) at ω_n = 4: ≈ 4/(ζω_n)", 4 / (0.7 * 4), rows[1][3], "s", tol=15)
    p.compare("Peak actuator effort ratio when ω_n doubles (4 → 8): 4×", 4.0, rows[2][4] / rows[1][4], "×", tol=1)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogy(ns, ea, "o-", color=C_PRED, label="Ackermann"); ax[0].semilogy(ns, np.maximum(es, 1e-17), "s-", color=C_MEAS, label="place_poles (KNV)")
    ax[0].semilogy(ns, sens, ":", color="gray", label="pole shift for a 10⁻⁸ model error")
    style_axes(ax[0], "system order n", "median relative pole error", "High-order pole placement is ill-conditioned")
    for wn, _, _, _, _, y in rows:
        ax[1].plot(t, y, label=f"ω_n = {wn:g} rad/s")
    ax[1].set_xlim(0, 4)
    style_axes(ax[1], "time (s)", "position", "Faster poles: same shape, 4× the effort per octave")
    p.save(fig, "ackermann", "Pole-placement accuracy versus system order, and servo step responses for three pole speeds.")
    p.discuss(f"""For small systems Ackermann's formula does exactly what it promises — the closed-loop eigenvalues match the requested ones to round-off and the gain
agrees with SciPy's independent algorithm. Its limits are equally clear. A mode that the input cannot reach (rank-deficient controllability matrix)
stays where it is whatever the gain. And accuracy collapses with order: the median pole error is {ea[ns.index(8)]:.0e} at n = 8 and {ea[-1]:.0e} at n = 14.
Here my prediction was wrong in an instructive way. I expected the orthogonal-transformation method behind place_poles to stay accurate where
Ackermann fails; it does no better ({es[-1]:.0e} at n = 14). The culprit is not the formula but the problem: with a single input the gain is unique,
and the closed-loop matrix that realises fourteen prescribed real poles has an eigenvector condition number of {evc[-1]:.0e} — a model error of one part
in 10⁸ already moves the poles by {sens[-1]:.0e}. No algorithm can deliver poles that the matrix itself does not hold still (a known result: pole
placement is intrinsically ill-conditioned for large single-input systems). Finally, 'place the poles anywhere' ignores the actuator: the servo's
gains are ω_n² and 2ζω_n, so every doubling of speed quadruples the peak control effort. Both limits point the same way — choose poles the plant
and its uncertainty can support, which is the question LQR (AM-160) answers systematically.""")
# tol-convention: relative tolerances are in percent
