from eelab import *

META = dict(
    id="AM-047", title="Euler vs RK4 on a circuit ODE: measured orders of accuracy", level="M",
    tools="Own forward Euler, Heun (RK2) and classical RK4 integrators, series-RLC state equations, global error vs step size, cost-per-accuracy analysis",
    summary="Integrate the series RLC state equations with three explicit methods, measure the global error against the exact solution as a "
            "function of step size, confirm the theoretical orders 1, 2 and 4, and compare the work needed to reach a given accuracy.",
    problem="Why does every circuit simulator avoid forward Euler? What does 'fourth order' buy in practice?",
    theory=r"""Global error ∝ h^p with p = 1 (Euler), 2 (Heun), 4 (RK4). For a target error ε the number of function evaluations scales as s·T/h ∝ s·ε^{−1/p} (s = stages per step: 1, 2, 4), so for
ε = 10⁻⁶ RK4 needs orders of magnitude fewer evaluations. Forward Euler on an under-damped oscillator also *adds* energy: its amplification factor |1+hλ| exceeds 1 for small damping.""",
    method="""State x = [v_C, i_L]; R = 20 Ω, L = 10 mH, C = 1 µF, 1 V step, 0–5 ms. h from T/50 to T/10⁵; error = max |v_C − exact|; slopes on log-log axes; evaluations to reach 1e-6.""",
)


def f(x, R=20, L=10e-3, C=1e-6, V=1.0):
    v, i = x
    return np.array([i / C, (V - v - R * i) / L])


def integrate(method, h, T=5e-3):
    n = int(round(T / h)); x = np.zeros(2); out = [x[0]]
    for _ in range(n):
        if method == "Euler":
            x = x + h * f(x)
        elif method == "Heun":
            k1 = f(x); k2 = f(x + h * k1); x = x + h / 2 * (k1 + k2)
        else:
            k1 = f(x); k2 = f(x + h / 2 * k1); k3 = f(x + h / 2 * k2); k4 = f(x + h * k3)
            x = x + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        out.append(x[0])
    return np.linspace(0, n * h, n + 1), np.array(out)


def exact(t, R=20, L=10e-3, C=1e-6):
    a = R / (2 * L); w0 = 1 / np.sqrt(L * C); wd = np.sqrt(w0 ** 2 - a ** 2)
    return 1 - np.exp(-a * t) * (np.cos(wd * t) + a / wd * np.sin(wd * t))


def run(p):
    T = 5e-3
    hs = T / np.array([50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000])
    res = {}
    for m, order, stages in (("Euler", 1, 1), ("Heun", 2, 2), ("RK4", 4, 4)):
        errs = []
        for h in hs:
            t, v = integrate(m, h)
            errs.append(np.max(np.abs(v - exact(t))))
        errs = np.array(errs)
        ok = (errs < 1e-1) & (errs > 1e-12)
        sl = np.polyfit(np.log(hs[ok]), np.log(errs[ok]), 1)[0]
        p.compare(f"{m}: observed order of accuracy", order, sl, "", kind="abs", tol=0.15)
        k = np.flatnonzero(errs < 1e-6)
        evals = stages * T / hs[k[0]] if len(k) else np.nan
        res[m] = (errs, evals)
    p.metric("Function evaluations to reach 1e-6 V: Euler / Heun / RK4", " / ".join(f"{res[m][1]:.0f}" if np.isfinite(res[m][1]) else "> 4e5" for m in res))
    from scipy.signal import find_peaks
    h = T / 400
    t, v = integrate("Euler", h, T=20e-3)
    pk, _ = find_peaks(np.abs(v - 1)); rate = np.polyfit(t[pk], np.log(np.abs(v - 1)[pk]), 1)[0]
    lam = -20 / (2 * 10e-3) + 1j * np.sqrt(1 / (10e-3 * 1e-6) - (20 / (2 * 10e-3)) ** 2)
    p.compare("Euler (h = 12.5 µs): ringing decay rate = ln|1+hλ|/h (true rate −1000 s⁻¹)", np.log(abs(1 + h * lam)) / h, rate, "1/s", tol=5)
    fig, ax = p.fig(1, 2, w=11)
    for (m, (errs, _)), c in zip(res.items(), (COLORS[1], COLORS[2], C_MEAS)):
        ax[0].loglog(hs, errs, "o-", color=c, label=m)
    style_axes(ax[0], "step h (s)", "max error (V)", "Global error vs step size")
    t, v = integrate("Euler", T / 400, T=20e-3); t4, v4 = integrate("RK4", T / 400, T=20e-3)
    ax[1].plot(t * 1e3, exact(t), color="black", lw=3, alpha=.3, label="exact"); ax[1].plot(t * 1e3, v, color=COLORS[1], lw=.8, label="Euler, h = 12.5 µs")
    ax[1].plot(t4 * 1e3, v4, "--", color=C_MEAS, lw=.8, label="RK4, same h")
    style_axes(ax[1], "t (ms)", "v_C (V)", "Same step, very different answers")
    p.save(fig, "orders", "Measured convergence orders of Euler, Heun and RK4 on the RLC equations, and a coarse-step comparison.")
    p.discuss("""The measured slopes reproduce the textbook orders 1, 2 and 4, and translate directly into cost: reaching 1 µV accuracy takes RK4 a few thousand
function evaluations where Euler needs orders of magnitude more. The waveform plot shows the qualitative failure of forward Euler on an oscillator:
with a step that looks reasonable (~50 points per ringing period) the ringing decays at less than half the true rate, exactly as its amplification
factor |1 + hλ| predicts — numerically it has *removed* damping; with a slightly larger step or a lossless tank |1 + hλ| exceeds 1 and it pumps
energy in without bound. (My first guess, that energy grows at this particular step, was wrong: |1 + hλ| = 0.995 here.) SPICE uses implicit trapezoidal and Gear methods not for their order but for stability, which the
next project (AM-048) makes explicit.""")
# tol-convention: relative tolerances are in percent
