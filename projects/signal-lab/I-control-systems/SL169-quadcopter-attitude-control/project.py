from eelab import *
from eelab.control import zoh

META = dict(
    id="SL-169", title="Quadcopter attitude: cascaded rate and angle loops", level="H",
    tools="Rigid-body roll/pitch/yaw model with motor lag, cascaded P-angle / PI-rate controllers at 1 kHz, bandwidth analysis",
    summary="Stabilise roll, pitch and yaw of a 1 kg quadrotor with the standard cascade (fast inner rate loop, slower outer angle "
            "loop); predict each loop's bandwidth and verify the step responses and the need for bandwidth separation.",
    problem="Every drone flight controller uses cascaded loops. Why, and how far apart must the inner and outer bandwidths be?",
    theory=r"""Per axis: J·ω̇ = τ, motors respond with τ_m = 20 ms. Inner rate loop (P gain k_r on ω): crossover ≈ k_r/J (below 1/τ_m). Outer angle loop (P gain k_a) sees
the inner loop as ≈ unity up to its bandwidth, so ω_outer ≈ k_a; stable and well damped if ω_outer ≲ ω_inner/4.""",
    method="""J = (0.01, 0.01, 0.02) kg·m², rate loop crossover 30 rad/s (k_r = 0.3 roll/pitch, 0.6 yaw) with small integral, angle loop k_a = 6 rad/s, 1 kHz discrete control.
10° step on each axis; a second run with k_a = 20 (poor separation).""",
)


def simulate(J, kr, ka, ki=0.0, T=2.0, dt=1e-3, tm=0.02):
    th = w = tau = I = 0.0; out = []
    for n in range(int(T / dt)):
        ref = np.radians(10)
        w_ref = ka * (ref - th)
        e = w_ref - w; I += e * dt
        tau_cmd = kr * e + ki * I
        tau += (tau_cmd - tau) * dt / tm
        w += tau / J * dt; th += w * dt
        out.append(th)
    return np.arange(1, len(out) + 1) * dt, np.degrees(np.array(out))


def run(p):
    from eelab.control import step_info
    Js = {"roll": 0.01, "pitch": 0.01, "yaw": 0.02}
    fig, ax = p.fig(1, 2, w=11)
    for i, (ax_nm, J) in enumerate(Js.items()):
        kr = 30 * J
        t, y = simulate(J, kr, 6.0, ki=0.5 * kr)
        info = step_info(t, y, 10.0)
        p.compare(f"{ax_nm}: angle-loop rise time ≈ 2.2/k_a (k_a = 6 rad/s)", 2.2 / 6, info["rise"], "s", tol=20)
        p.metric(f"{ax_nm}: overshoot", info["overshoot"], "%")
        ax[0].plot(t, y, color=COLORS[i], label=ax_nm)
    style_axes(ax[0], "time (s)", "angle (°)", "10° steps, k_a = 6 rad/s, rate loop 30 rad/s")
    for i, ka in enumerate((6, 12, 20)):
        t, y = simulate(0.01, 0.3, ka, ki=0.15)
        info = step_info(t, y, 10.0)
        ax[1].plot(t, y, color=COLORS[i], label=f"k_a = {ka} (ratio {30/ka:.1f})")
        if ka == 20:
            p.metric("Overshoot with poor separation (k_a = 20, inner/outer = 1.5)", info["overshoot"], "%")
    style_axes(ax[1], "time (s)", "roll (°)", "Why the inner loop must be faster")
    p.save(fig, "attitude", "With 5× separation the angle loop behaves as designed; pushing the outer loop toward the inner one causes ringing.")
    p.discuss("""With the inner rate loop at 30 rad/s and the outer angle loop at 6 rad/s, each axis responds without overshoot at roughly the designed outer
bandwidth — about 25 % faster than the first-order 2.2/k_a estimate, because the rate loop's integral term adds drive while the
error is large, and yaw — with twice the inertia — behaves the same because its rate gain was scaled by J. Raising the
outer gain toward the inner bandwidth produces overshoot and ringing: the outer loop starts seeing the inner loop's lag and the motor
time constant. Flight-controller tuning guides encode the same rule — tune rate loops first, then keep the angle loop several times slower.""")
