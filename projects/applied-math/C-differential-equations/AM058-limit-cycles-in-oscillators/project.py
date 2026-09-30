from eelab import *
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

META = dict(
    id="AM-058", title="What sets an oscillator's amplitude?", level="H",
    tools="Wien-bridge oscillator with a tanh-limited amplifier (state-space ODE), describing-function prediction of amplitude, sensitivity to excess gain",
    summary="Model a Wien-bridge oscillator whose amplifier saturates smoothly, predict the steady amplitude with a describing function (the "
            "amplitude at which the effective gain falls to exactly 3), and verify with simulation as the small-signal excess gain is varied.",
    problem="Linear theory says an oscillator's amplitude grows forever or dies. Real ones settle — where, and why there?",
    theory=r"""A Wien bridge needs amplifier gain exactly 3 at f0 = 1/(2πRC). With $v_o = V_s\tanh(Kv_i/V_s)$ the effective (describing-function) gain for a sinusoid of amplitude a at the input is
$N(a)=\frac{2}{π a}\int_0^π V_s\tanh\!\big(\tfrac{Ka}{V_s}\sin θ\big)\sin θ\,dθ$, decreasing from K. The steady amplitude solves N(a) = 3; output amplitude ≈ 3a. More excess gain (K − 3) → larger amplitude and more
distortion. The frequency stays at f0 to first order.""",
    method="""R = 10 kΩ, C = 10 nF (f0 = 1.59 kHz), V_s = 5 V; K from 3.05 to 6. States: the two capacitor voltages; simulate 200 periods from a 1 mV kick; amplitude and frequency from the last 20 periods;
THD from the FFT.""",
)


def N(a, K, Vs=5.0):
    th = np.linspace(0, pi, 2001)
    return 2 / (pi * a) * np.trapezoid(Vs * np.tanh(K * a / Vs * np.sin(th)) * np.sin(th), th)


def simulate(K, R=10e3, C=10e-9, Vs=5.0):
    # series RC (R, C) from output to node v+; parallel RC (R, C) from v+ to ground; amplifier output = Vs·tanh(K v+/Vs)
    def f(t, y):
        vs_, vp = y                     # voltage across series C, node voltage v+
        vo = Vs * np.tanh(K * vp / Vs)
        i = (vo - vs_ - vp) / R          # current through series branch
        return [i / C, (i - vp / R) / C]
    f0 = 1 / (2 * pi * R * C)
    T = 200 / f0
    s = solve_ivp(f, (0, T), [0, 1e-3], rtol=1e-8, atol=1e-11, max_step=1 / f0 / 100, dense_output=True)
    t = np.linspace(T - 20 / f0, T, 20000); vp = s.sol(t)[1]; vo = Vs * np.tanh(K * vp / Vs)
    up = np.flatnonzero((vp[:-1] < 0) & (vp[1:] >= 0))
    freq = 1 / np.mean(np.diff(t[up]))
    X = np.abs(np.fft.rfft(vo * np.hanning(len(vo)))); fr = np.fft.rfftfreq(len(vo), t[1] - t[0])
    k1 = np.argmax(X); harm = [np.max(X[max(0, int(k1 * h) - 3): int(k1 * h) + 4]) for h in (2, 3, 4, 5)]
    thd = np.sqrt(np.sum(np.square(harm))) / X[k1]
    return vp.max(), vo.max(), freq, thd


def run(p):
    rows = []
    for K in (3.05, 3.2, 3.5, 4.0, 5.0, 6.0):
        a_pred = brentq(lambda a: N(a, K) - 3, 1e-4, 10)
        ap, ao, fq, thd = simulate(K)
        rows.append((K, a_pred, ap, fq, thd, ao))
    for K, apred, ap, fq, thd, ao in rows:
        if K in (3.05, 3.5, 5.0):
            p.compare(f"K = {K}: steady input amplitude, describing function N(a) = 3", apred, ap, "V", tol=5)
    p.compare("Oscillation frequency (K = 3.2) = 1/(2πRC)", 1 / (2 * pi * 10e3 * 10e-9), rows[1][3], "Hz", tol=1)
    p.metric("THD of the output: K = 3.05 / 4 / 6", f"{rows[0][4] * 100:.2f} / {rows[3][4] * 100:.1f} / {rows[5][4] * 100:.1f} %")
    fig, ax = p.fig(1, 2, w=11)
    aa = np.linspace(0.01, 4, 300)
    for K, c in ((3.2, COLORS[0]), (4.0, COLORS[1]), (6.0, COLORS[2])):
        ax[0].plot(aa, [N(a, K) for a in aa], color=c, label=f"N(a), K = {K}")
    ax[0].axhline(3, color="black", ls="--", label="required gain 3")
    style_axes(ax[0], "input amplitude a (V)", "effective gain", "Describing function: amplitude where N(a) = 3")
    r = np.array(rows)
    ax[1].plot(r[:, 0], r[:, 1], "--", color=C_PRED, label="prediction"); ax[1].plot(r[:, 0], r[:, 2], "o", color=C_MEAS, label="simulation")
    style_axes(ax[1], "small-signal gain K", "steady amplitude at v+ (V)", "More excess gain → larger (and dirtier) oscillation")
    p.save(fig, "limit_cycle", "Describing functions of the tanh amplifier and predicted vs simulated oscillation amplitude.")
    p.discuss("""The oscillation settles exactly where the describing function says: at the input amplitude that compresses the amplifier's effective gain from K
down to the 3 the Wien bridge needs, so the loop gain is precisely one. With barely any excess gain (K = 3.05) the amplitude is small and the tanh
is almost linear — very low distortion, but slow start-up and fragile against component drift; with K = 6 the amplitude grows and the output
becomes visibly clipped (several percent THD). This is why precision sine oscillators use a slow amplitude-control loop (a lamp, thermistor or
JFET) to hold the gain just above 3, rather than relying on hard saturation.""")
# tol-convention: relative tolerances are in percent
