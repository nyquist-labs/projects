from eelab import *

META = dict(
    id="AM-048", title="Stiff ODEs: why explicit methods die on switching circuits", level="H",
    tools="Forward Euler, RK4, backward Euler and trapezoidal integrators on a two-time-constant RC network, stability-limit measurement, stiffness ratio analysis",
    summary="Build a circuit with a 1 ms time constant and a 10 ns parasitic one (stiffness ratio 10⁵), find the largest stable step of each "
            "integrator, and compare with the stability-region predictions — explicit methods are limited by the fastest pole even after it has died out.",
    problem="A switching converter has nanosecond parasitics and millisecond dynamics. Why can't a simple integrator just take big steps?",
    theory=r"""For $\dot x = Ax$ with eigenvalues λ_i < 0, forward Euler is stable only if |1 + hλ| ≤ 1 → h ≤ 2/|λ_max|; classical RK4 needs h|λ| ≤ 2.785. Backward Euler and trapezoidal are
A-stable: any h > 0 is stable, so the step can follow the slow dynamics. With |λ_fast| = 10⁸ s⁻¹: predicted h_crit = 20 ns (Euler), 27.85 ns (RK4) — 50,000 steps per millisecond just to stay stable.""",
    method="""Two-section RC ladder: R1 = 1 kΩ, C1 = 1 µF (slow) and R2 = 1 Ω, C2 = 10 nF (fast) — eigenvalues computed from the state matrix. Step input; each method run for a range of h;
'stable' = bounded output within 2× the final value over 5 ms; accuracy of implicit methods at large h.""",
)


def A_matrix():
    R1, C1, R2, C2 = 1e3, 1e-6, 1.0, 10e-9
    A = np.array([[-1 / (R1 * C1) - 1 / (R2 * C1), 1 / (R2 * C1)], [1 / (R2 * C2), -1 / (R2 * C2)]])
    b = np.array([1 / (R1 * C1), 0.0])
    return A, b


def run_method(m, h, T=5e-3):
    A, b = A_matrix(); x = np.zeros(2); n = int(T / h); I = np.eye(2)
    if m == "backward Euler":
        M = np.linalg.inv(I - h * A)
    if m == "trapezoidal":
        M = np.linalg.inv(I - h / 2 * A); N_ = I + h / 2 * A
    out = np.empty(n)
    for k in range(n):
        if m == "forward Euler":
            x = x + h * (A @ x + b)
        elif m == "RK4":
            f = lambda y: A @ y + b
            k1 = f(x); k2 = f(x + h / 2 * k1); k3 = f(x + h / 2 * k2); k4 = f(x + h * k3); x = x + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        elif m == "backward Euler":
            x = M @ (x + h * b)
        else:
            x = M @ (N_ @ x + h * b)
        out[k] = x[1]
        if not np.isfinite(x).all() or abs(x[1]) > 1e6:
            return False, out
    return np.max(np.abs(out)) < 2.0, out


def run(p):
    A, b = A_matrix()
    lam = np.linalg.eigvals(A)
    lf, ls = lam[np.argmax(np.abs(lam))].real, lam[np.argmin(np.abs(lam))].real
    p.metric("Eigenvalues (s⁻¹)", f"{ls:.4g} (slow), {lf:.4g} (fast); stiffness ratio {lf / ls:.3g}")
    crit = {}
    for m, pred in (("forward Euler", 2 / abs(lf)), ("RK4", 2.785 / abs(lf))):
        hs = pred * np.array([0.9, 0.95, 0.98, 1.02, 1.05, 1.1])
        st = [run_method(m, h, T=2e-5)[0] for h in hs]
        crit[m] = hs[np.argmax(~np.array(st))] if not all(st) else np.nan
        p.compare(f"{m}: largest stable step (first unstable step in a fine sweep)", pred, crit[m], "s", tol=5)
    from scipy.linalg import expm
    xT = np.linalg.solve(A, (expm(A * 5e-3) - np.eye(2)) @ b)      # exact state at 5 ms for a unit step
    for m in ("backward Euler", "trapezoidal"):
        ok, out = run_method(m, 50e-6)
        p.compare(f"{m} with h = 50 µs (2500× the explicit limit): v_C2 at 5 ms vs exact", xT[1], out[-1] if ok else np.nan, "V", tol=0.5)
    xs = []
    for m in ("backward Euler", "trapezoidal"):
        ok, out = run_method(m, 1e-9, T=2e-4)
        xs.append(out)
    ok_be, out_be = run_method("backward Euler", 20e-6, T=1e-3)
    ok_tr, out_tr = run_method("trapezoidal", 20e-6, T=1e-3)
    ref = run_method("backward Euler", 1e-8, T=1e-3)[1][::2000]
    fig, ax = p.fig(1, 2, w=11)
    hh = np.logspace(-9, -4, 60)
    ax[0].semilogx(hh, np.abs(1 + hh * lf), color=COLORS[1], label="forward Euler |1+hλ_fast|")
    ax[0].semilogx(hh, np.abs(1 / (1 - hh * lf)), color=C_MEAS, label="backward Euler |1/(1−hλ)|")
    ax[0].semilogx(hh, np.abs((1 + hh * lf / 2) / (1 - hh * lf / 2)), color=COLORS[2], label="trapezoidal")
    ax[0].axhline(1, color="gray", ls=":"); ax[0].set_ylim(0, 3)
    style_axes(ax[0], "step h (s)", "|amplification| of the fast mode", "Stability of the fast (dead) mode")
    t = np.arange(len(out_tr)) * 20e-6
    ax[1].plot(np.arange(len(ref)) * 20e-6 * 1e3, ref, color="black", lw=3, alpha=.3, label="reference (h = 10 ns)")
    ax[1].plot(t * 1e3, out_be, "--", color=C_MEAS, label="backward Euler, h = 20 µs"); ax[1].plot(t * 1e3, out_tr, ":", color=COLORS[2], label="trapezoidal, h = 20 µs")
    style_axes(ax[1], "t (ms)", "v_C2 (V)", "Implicit methods with 1000× larger steps")
    p.save(fig, "stiff", "Amplification of the fast mode vs step size for three methods, and implicit solutions at a step far beyond the explicit limit.")
    p.discuss(f"""The explicit stability limits land exactly where the stability regions predict — {crit['forward Euler'] * 1e9:.1f} ns for forward Euler and
{crit['RK4'] * 1e9:.1f} ns for RK4 — set entirely by a 10 ns parasitic mode that is irrelevant to the answer after its first few nanoseconds. Resolving
5 ms of the slow dynamics would need ~250,000 explicit steps; the A-stable implicit methods follow the same waveform with 20–50 µs steps. The
amplification plot shows a subtlety: trapezoidal's factor for the fast mode tends to −1 as h grows, so it never *damps* fast modes (they ring at the
Nyquist rate), whereas backward Euler kills them — which is why SPICE mixes trapezoidal with Gear/BE and why 'trap ringing' is a known artefact.""")
# tol-convention: relative tolerances are in percent
