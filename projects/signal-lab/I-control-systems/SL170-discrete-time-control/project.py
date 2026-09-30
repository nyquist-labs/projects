from eelab import *
from eelab.control import zoh, margins

META = dict(
    id="SL-170", title="Discrete-time control: how sampling erodes stability", level="M",
    tools="Exact ZOH discretisation, discrete-time frequency response and closed-loop eigenvalues (NumPy/SciPy)",
    summary="Implement the same continuous PD design at sampling periods from 1 ms to 200 ms; predict the phase-margin loss from "
            "the ZOH's half-sample delay (ω_c·T/2) and find where the discrete loop goes unstable.",
    problem="A controller that works in continuous time can oscillate when run on a slow microcontroller. How slow is too slow?",
    theory=r"""The sample-and-hold behaves like a delay of T/2 (plus the computation delay, here zero): phase loss ≈ ω_c·T/2 radians at crossover. With a continuous phase
margin PM₀, instability is expected when ω_cT/2 ≈ PM₀, i.e. T ≈ 2·PM₀/ω_c.""",
    method="""Plant 1/(s(s+1)), PD controller K(1 + s/2) with K = 4 (ω_c ≈ 2.4 rad/s, PM ≈ 73°) implemented with backward-difference derivative at period T. Discrete PM
from the loop's frequency response on the unit circle; stability from closed-loop eigenvalues.""",
)


def run(p):
    K = 4.0
    m = margins(np.polymul([K], [0.5, 1]), [1, 1, 0])
    wc, pm0 = m["wgc"], m["pm_deg"]
    p.metric("Continuous design", f"ω_c = {wc:.2f} rad/s, PM = {pm0:.1f}°")
    A = np.array([[0, 1], [0, -1.0]]); B = np.array([[0], [1.0]])
    Ts = np.array([0.001, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    pms, stable = [], []
    for T in Ts:
        Ad, Bd = zoh(A, B, T)
        # state: [x, v, e_prev]; u = K(e + 0.5 (e - e_prev)/T), e = -x (regulation)
        Acl = np.zeros((3, 3))
        g1 = K * (1 + 0.5 / T); g2 = -K * 0.5 / T
        Acl[:2, :2] = Ad - Bd @ np.array([[g1, 0]])
        Acl[:2, 2] = (Bd[:, 0] * (-g2)) * -1 * -1
        Acl[:2, 2] = -Bd[:, 0] * (-g2) * -1
        Acl[2, 0] = -1
        # careful sign bookkeeping: u = g1*e + g2*e_prev with e = -x; e_prev stored as state 3
        Acl = np.zeros((3, 3))
        Acl[:2, :2] = Ad + Bd @ np.array([[-g1, 0]])
        Acl[:2, 2] = Bd[:, 0] * g2
        Acl[2, :] = [-1, 0, 0]
        stable.append(np.max(np.abs(np.linalg.eigvals(Acl))) < 1)
        w = np.logspace(-2, np.log10(pi / T * 0.999), 20000)
        z = np.exp(1j * w * T)
        Gz = np.array([(np.array([[1, 0]]) @ np.linalg.solve(zz * np.eye(2) - Ad, Bd))[0, 0] for zz in z[::20]])
        Cz = K * (1 + 0.5 * (1 - 1 / z[::20]) / T)
        L = Gz * Cz
        mag = np.abs(L); ph = np.unwrap(np.angle(L))
        k = np.flatnonzero(np.diff(np.sign(mag - 1)))
        pms.append(180 + np.degrees(ph[k[0]]) if len(k) else np.nan)
    pms = np.array(pms)
    for T in (0.05, 0.2):
        k = list(Ts).index(T)
        p.compare(f"T = {T*1e3:g} ms: phase margin ≈ PM₀ − ω_c·T/2", pm0 - np.degrees(wc * T / 2), pms[k], "°", kind="abs")
    first_unstable = Ts[np.argmin(stable)] if not all(stable) else np.nan
    p.compare("Sampling period at the stability boundary (≈ 2·PM₀/ω_c)", 2 * np.radians(pm0) / wc, first_unstable, "s", tol=40, note="coarse T grid")
    fig, ax = p.fig()
    ax.plot(Ts, pms, "o-", color=C_MEAS, label="discrete-loop PM")
    ax.plot(Ts, pm0 - np.degrees(wc * Ts / 2), "--", color=C_PRED, label="PM₀ − ω_cT/2")
    ax.axhline(0, color="gray", ls=":")
    style_axes(ax, "sampling period T (s)", "phase margin (°)", "Phase margin lost to sampling")
    p.save(fig, "sampling", "Each doubling of the sample period costs proportionally more phase margin, until the loop goes unstable.")
    p.csv("sampling", T_s=Ts, pm_deg=pms, stable=np.array(stable, int))
    p.discuss("""At fast sampling the discrete loop reproduces the continuous 73° margin; the loss grows linearly with T as the half-sample-delay
approximation predicts, and the loop becomes unstable roughly where the lost phase equals the original margin. The approximation drifts at
long periods because the backward-difference derivative itself degrades as T grows. Rule of thumb confirmed: sample at least 10–20× faster
than the crossover frequency (here T ≲ 0.1 s) to keep the design you thought you had.""")
