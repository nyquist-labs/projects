from eelab import *
from scipy.integrate import solve_ivp

META = dict(
    id="SL-168", title="Ball and beam: a nonlinear, open-loop-unstable plant", level="H",
    tools="Nonlinear rolling-ball model (SciPy ODE), cascaded PD control (inner beam angle, outer ball position), linearised predictions",
    summary="Balance a ball on a tilting beam with a cascaded controller designed on the linearised double-integrator model, and "
            "compare the nonlinear response (including servo-rate limits) with the linear predictions.",
    problem="A rolling ball accelerates with the beam angle — a double integrator. How does cascaded control handle it, and when "
            "does the nonlinearity bite?",
    theory=r"""Solid ball rolling without slipping: $\ddot r=\frac{5}{7}(r\dot\theta^2-g\sin\theta)$ ≈ −(5g/7)θ for small angles. The outer PD loop commands θ_ref =
−(k_p e + k_d ė)/(5g/7) giving closed-loop poles s² + k_d s + k_p = 0; with k_p = 4, k_d = 3.2 (ζ = 0.8, ω_n = 2 rad/s) the 2 % settling time ≈ 4/(ζω_n) = 2.5 s
and overshoot 1.5 %, if the inner (servo) loop is much faster.""",
    method="""Beam angle driven by a servo modelled as a first-order lag (τ = 50 ms) with angle limit ±15° and rate limit 60°/s. Steps of 0.1 m and 0.8 m in ball position (0.8 m demands ~26° of tilt, beyond the 15° limit).""",
)


def run(p):
    g = 9.81; kg = 5 * g / 7; kp, kd = 4.0, 3.2; tau = 0.05
    def f(t, s, ref, lim):
        r, rd, th, _ = s
        th_ref = -(kp * (ref - r) - kd * rd) / kg          # tilt needed: r̈ ≈ −kg·θ
        th_cmd = np.clip(th_ref, -np.radians(15), np.radians(15)) if lim else th_ref
        thd = (th_cmd - th) / tau
        if lim:
            thd = np.clip(thd, -np.radians(60), np.radians(60))
        rdd = 5 / 7 * (r * thd**2 - g * np.sin(th))
        return [rd, rdd, thd, 0]
    res = {}
    for ref in (0.1, 0.8):
        for lim in (False, True):
            sol = solve_ivp(f, (0, 8), [0, 0, 0, 0], args=(ref, lim), max_step=0.005, dense_output=True)
            t = np.linspace(0, 8, 1601); y = sol.sol(t)[0]
            res[(ref, lim)] = (t, y)
    from eelab.control import step_info
    i1 = step_info(*res[(0.1, False)], 0.1)
    p.compare("Small step (0.1 m), no limits: overshoot (ζ = 0.8)", 100 * np.exp(-pi * 0.8 / np.sqrt(1 - 0.64)), i1["overshoot"], "%", kind="abs")
    p.compare("Small step: 2 % settling time 4/(ζω_n)", 2.5, i1["settle"], "s", tol=25)
    i4 = step_info(*res[(0.8, True)], 0.8); i4n = step_info(*res[(0.8, False)], 0.8)
    p.metric("0.8 m step: settling time, ideal servo / limited servo", f"{i4n['settle']:.2f} s / {i4['settle']:.2f} s")
    p.metric("0.8 m step with limits: overshoot", i4["overshoot"], "%", "PD has no integrator, so saturation slows but does not wind up")
    fig, ax = p.fig()
    for i, (key, lab) in enumerate(((((0.1, False)), "0.1 m, ideal servo"), (((0.8, False)), "0.8 m, ideal servo"), (((0.8, True)), "0.8 m, ±15°, 60°/s servo"))):
        t, y = res[key]
        ax.plot(t, y / key[0], color=COLORS[i], label=lab)
    ax.axhline(1, color="gray", ls=":")
    style_axes(ax, "time (s)", "position / target", "Ball and beam: linear design meets actuator limits")
    p.save(fig, "ball_beam", "Small moves behave like the linear design; big moves saturate the beam angle and overshoot.")
    p.discuss("""For small moves the nonlinear plant behaves like the linear double integrator and the overshoot matches the ζ = 0.8 design; the 4/(ζω_n) settling estimate is
conservative (it bounds the envelope, and ζ = 0.8 is well damped). An 0.8 m move asks for ~26° of tilt; the 15° limit caps the ball's acceleration, so the move takes longer than the
linear design promises (with a PD outer loop there is no integrator to wind up, so it does not overshoot — add integral action and it would).
The linear prediction is only valid while the actuator stays inside its limits. Saturation-aware
designs (reference shaping, anti-windup, MPC — AM-168) exist precisely for this.""")
