from eelab import *
from scipy import signal

META = dict(
    id="AM-046", title="Impulse and step response: the derivative relationship", level="M",
    tools="Analytic impulse and step responses of a second-order low-pass, numerical differentiation/integration, simulated narrow-pulse approximation of δ(t)",
    summary="Derive the impulse and step responses of a second-order system, confirm that h(t) = dy_step/dt, and show how a real narrow pulse "
            "approximates the impulse with an error that shrinks in proportion to the pulse width.",
    problem="An ideal impulse cannot be generated. How do engineers measure an impulse response anyway?",
    theory=r"""For $H(s)=\frac{ω_0^2}{s^2+2ζω_0s+ω_0^2}$: $h(t)=\frac{ω_0}{\sqrt{1-ζ^2}}e^{-ζω_0t}\sin ω_dt$ and $y_{step}=1-\frac{e^{-ζω_0t}}{\sqrt{1-ζ^2}}\sin(ω_dt+φ)$, φ = arccos ζ. Since the step is the integral of the
impulse, $h=\dot y_{step}$. A rectangular pulse of width w and area 1 gives $\frac1w[y(t)-y(t-w)]$ ≈ h(t − w/2): the error is O(w²) about the midpoint, O(w) if compared at t.""",
    method="""ω0 = 2π·100 rad/s, ζ = 0.2. Closed forms vs scipy.signal.impulse/step; numerical derivative of the step (central differences); unit-area pulses of widths 0.1–5 ms, their response built exactly as (y_step(t) − y_step(t − w))/w (a first attempt fed a sampled pulse to lsim, whose linear interpolation of the input edges added an O(Δt) error that masked the O(w²) behaviour).""",
)


def run(p):
    w0, z = 2 * pi * 100, 0.2
    wd = w0 * np.sqrt(1 - z * z); phi = np.arccos(z)
    t = np.linspace(0, 0.1, 100001)
    h = w0 / np.sqrt(1 - z * z) * np.exp(-z * w0 * t) * np.sin(wd * t)
    ys = 1 - np.exp(-z * w0 * t) / np.sqrt(1 - z * z) * np.sin(wd * t + phi)
    sys = ([w0 * w0], [1, 2 * z * w0, w0 * w0])
    _, hn = signal.impulse(sys, T=t); _, ysn = signal.step(sys, T=t)
    p.compare("Closed-form impulse response vs numerical (max relative)", 0, np.max(np.abs(h - hn)) / np.max(np.abs(h)), "", kind="abs", tol=1e-6)
    p.compare("Closed-form step response vs numerical", 0, np.max(np.abs(ys - ysn)), "", kind="abs", tol=1e-6)
    dy = np.gradient(ys, t)
    p.compare("h(t) = d y_step / dt (central differences, max relative error)", 0, np.max(np.abs(dy - h)) / np.max(np.abs(h)), "", kind="abs", tol=1e-4)
    rows = []
    for wpulse in (0.1e-3, 0.2e-3, 0.5e-3, 1e-3, 2e-3, 5e-3):
        # exact response to a unit-area pulse of width w by superposition of two steps (avoids lsim's sampled-input edge error)
        yp = (ys - np.interp(t - wpulse, t, ys, left=0)) / wpulse
        hs = np.interp(t - wpulse / 2, t, h, left=0)
        late = t > 0.012                                     # away from the onset, where h has a kink and every approximation is O(w)
        rows.append((wpulse, np.max(np.abs(yp - h)[late]) / h.max(), np.max(np.abs(yp - hs)[late]) / h.max()))
    r = np.array(rows)
    sl1 = np.polyfit(np.log(r[:, 0]), np.log(r[:, 1]), 1)[0]
    sl2 = np.polyfit(np.log(r[:4, 0]), np.log(r[:4, 2]), 1)[0]
    p.compare("Pulse approximation error vs h(t): order in width (≈ 1)", 1.0, sl1, "", kind="abs", tol=0.15)
    p.compare("… vs h(t − w/2): order (≈ 2)", 2.0, sl2, "", kind="abs", tol=0.2)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t * 1e3, h / h.max(), color=C_MEAS, label="h(t) (normalised)"); ax[0].plot(t * 1e3, ys, color=C_PRED, label="step response")
    ax[0].plot(t[::500] * 1e3, dy[::500] / h.max(), "o", ms=3, color=COLORS[2], label="d/dt of step")
    ax[0].set_xlim(0, 40)
    style_axes(ax[0], "t (ms)", None, "Impulse = derivative of step")
    ax[1].loglog(r[:, 0] * 1e3, r[:, 1], "o-", color=C_MEAS, label="vs h(t)"); ax[1].loglog(r[:, 0] * 1e3, r[:, 2], "s-", color=COLORS[1], label="vs h(t − w/2)")
    style_axes(ax[1], "pulse width (ms)", "max error / max h", "A narrow pulse approximates δ(t)")
    p.save(fig, "impulse_step", "Impulse and step responses with the numerical derivative, and the error of approximating δ(t) with finite pulses.")
    p.discuss("""(Errors are measured after 12 ms: at the onset h(t) has a kink, so near t = 0 every finite pulse is only first-order accurate.) The closed forms, numerical LTI solutions and the derivative of the step response all agree, confirming h = dy_step/dt — which is how impulse
responses are usually measured in practice: apply a clean step, differentiate. A real narrow pulse is the other practical route. Its error is
first-order in the pulse width if compared at the same time, but only second-order if one accounts for the half-width delay (the pulse's 'centre
of mass'); a 0.1 ms pulse on a 100 Hz system already reproduces h(t) to 0.01 %. What limits real measurements is amplitude: a pulse narrow enough to
be an impulse carries little energy, so noise, not width, sets the accuracy.""")
# tol-convention: relative tolerances are in percent
