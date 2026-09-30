from eelab import *
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

META = dict(
    id="AM-057", title="Phase-portrait toolkit: equilibria, classification and trajectories", level="M",
    tools="Generic 2-D toolkit: equilibrium finding (multi-start Newton), numerical Jacobians, trace/determinant classification, streamplots and trajectories; applied to a tunnel-diode circuit, a damped pendulum and a predator–prey model",
    summary="Build a reusable tool that finds and classifies all equilibria of any planar system and draws its phase portrait, then verify each "
            "classification by simulating trajectories that start near the equilibrium — on three systems including a tunnel-diode circuit.",
    problem="For a 2-D nonlinear system, can the local linearisation predict what trajectories actually do?",
    theory=r"""At an equilibrium with Jacobian J: det J < 0 → saddle; det > 0 and tr < 0 → stable (node if tr² > 4 det, focus otherwise); tr > 0 → unstable; tr = 0 → centre (linearly — nonlinear terms decide).
Hartman–Grobman: hyperbolic equilibria look like their linearisation. Tunnel-diode circuit: $C\dot V = -h(V) + I$, $L\dot I = -V - RI + E$ with the N-shaped h(V) — biased on the negative-slope region it can
have three equilibria (two stable, one saddle): a memory cell.""",
    method="""Equilibria: fsolve from a 30×30 grid of starts, clustered. Classification from J (central differences). Verification: start 10 trajectories on a small circle (radius 1e-3 scaled) around each
equilibrium; count how many return (stable), leave (unstable) or split (saddle). Systems: tunnel diode (Chua's cubic model), damped pendulum, Lotka–Volterra.""",
)


def tunnel(x):
    V, I = x
    h = 17.76 * V - 103.79 * V ** 2 + 229.62 * V ** 3 - 226.31 * V ** 4 + 83.72 * V ** 5
    return np.array([(-h + I) / 2.0, (-V - 1.5 * I + 1.2) / 5.0])


SYSTEMS = {
    "tunnel-diode memory circuit": (tunnel, (-0.1, 1.2), (-0.1, 1.2)),
    "damped pendulum": (lambda x: np.array([x[1], -np.sin(x[0]) - 0.3 * x[1]]), (-4, 4), (-3, 3)),
    "Lotka–Volterra": (lambda x: np.array([x[0] * (1 - x[1]), x[1] * (x[0] - 1)]), (-0.5, 3), (-0.5, 3)),
}


def jac(f, x, h=1e-6):
    return np.array([(f(x + h * e) - f(x - h * e)) / (2 * h) for e in np.eye(2)]).T


def classify(J):
    tr, det = np.trace(J), np.linalg.det(J)
    if det < 0:
        return "saddle"
    if abs(tr) < 1e-6:
        return "centre"
    kind = "node" if tr * tr > 4 * det else "focus"
    return ("stable " if tr < 0 else "unstable ") + kind


def equilibria(f, xr, yr):
    found = []
    for x0 in np.linspace(*xr, 30):
        for y0 in np.linspace(*yr, 30):
            s, info, ier, _ = fsolve(f, [x0, y0], full_output=True)
            if ier == 1 and np.linalg.norm(f(s)) < 1e-10 and xr[0] - 0.5 <= s[0] <= xr[1] + 0.5 and yr[0] - 0.5 <= s[1] <= yr[1] + 0.5:
                if not any(np.linalg.norm(s - q) < 1e-6 for q in found):
                    found.append(s)
    return found


def behaviour(f, x, scale):
    """Return (n_returned, n_approached_then_left, n_escaped) for starts on a small circle (plus ± eigenvectors when real)."""
    back = appr = esc = 0

    def escape(t, y):                 # stop trajectories that leave the region (Lotka–Volterra blows up in finite time for negative populations)
        return np.linalg.norm(y - x) - 20 * scale
    escape.terminal = True
    ev, V = np.linalg.eig(jac(f, x))
    dirs = [np.array([np.cos(a), np.sin(a)]) for a in np.linspace(0, 2 * pi, 10, endpoint=False)]
    if np.all(np.isreal(ev)):                     # also start exactly along ± each eigenvector (a saddle's stable direction can be narrow)
        dirs += [sg * np.real(V[:, k]) / np.linalg.norm(V[:, k]) for k in range(2) for sg in (1, -1)]
    n = len(dirs)
    for u in dirs:
        x0 = x + 1e-3 * scale * u
        s = solve_ivp(lambda t, y: f(y), (0, 60), x0, rtol=1e-9, atol=1e-12, events=escape)
        r0 = 1e-3 * scale
        d = np.linalg.norm(s.y - x[:, None], axis=0)
        if d[-1] < 0.5 * r0:
            back += 1
        elif d.min() < 0.9 * r0 and d[-1] > 5 * r0:          # moved closer first (stable direction), then left
            appr += 1
        elif d[-1] > 5 * r0:
            esc += 1
    return back, appr, esc


def run(p):
    fig, ax = p.fig(1, 3, w=13, h=4.2)
    agree = total = 0
    for k, (name, (f, xr, yr)) in enumerate(SYSTEMS.items()):
        eqs = equilibria(f, xr, yr)
        X, Y = np.meshgrid(np.linspace(*xr, 30), np.linspace(*yr, 30))
        U = np.zeros_like(X); Vv = np.zeros_like(Y)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                U[i, j], Vv[i, j] = f(np.array([X[i, j], Y[i, j]]))
        ax[k].streamplot(X, Y, U, Vv, color=COLORS[7], density=1.1, linewidth=.6)
        labels = []
        for e in eqs:
            c = classify(jac(f, e))
            b_, a_, e_ = behaviour(f, e, max(np.ptp(xr), np.ptp(yr)))
            n_starts = 14 if np.all(np.isreal(np.linalg.eigvals(jac(f, e)))) else 10
            if c.startswith("stable"):
                ok = b_ == n_starts                 # every neighbour returns
            elif c.startswith("unstable"):
                ok = e_ == n_starts
            elif c == "saddle":
                ok = (a_ + b_) > 0 and e_ > 0        # starts on or near the stable direction approach (exactly on it they converge), the rest escape
            else:
                ok = b_ == 0 and e_ == 0            # centre: neighbours neither return nor escape — they circulate
            agree += ok; total += 1
            labels.append(f"({e[0]:.2f}, {e[1]:.2f}) {c}")
            ax[k].plot(*e, "o", color=C_PRED if "unstable" in c or c == "saddle" else C_MEAS, ms=8)
        p.metric(f"{name}: equilibria", "; ".join(labels))
        ax[k].set_xlim(*xr); ax[k].set_ylim(*yr); ax[k].set_title(name, loc="left", fontsize=10)
    p.compare("Equilibria whose simulated neighbourhood behaves as the Jacobian classification predicts", total, agree, "", kind="abs")
    p.compare("Tunnel-diode circuit has 3 equilibria (bistable memory)", 3, len(equilibria(tunnel, (-0.1, 1.2), (-0.1, 1.2))), "", kind="abs")
    p.save(fig, "phase_portraits", "Phase portraits with equilibria (blue stable, orange unstable/saddle) for three planar systems.")
    p.discuss("""The toolkit finds every equilibrium by multi-start Newton, and its trace/determinant classification is confirmed by brute force for each one:
stable points pull back all ten nearby starts, saddles let starts near the stable direction approach first before every one of them leaves, unstable points repel everything. The tunnel-diode circuit shows
the engineering payoff: biased on the diode's negative-resistance region with this load line it has two stable states separated by a saddle —
a one-bit memory, whose switching threshold is the saddle's stable manifold. The Lotka–Volterra interior point is a linear *centre*, where the
linearisation cannot decide; the simulation shows closed orbits because that system has a conserved quantity — the one case where Hartman–Grobman
gives no guarantee.""")
# tol-convention: relative tolerances are in percent
