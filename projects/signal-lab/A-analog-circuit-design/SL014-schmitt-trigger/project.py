from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-014", title="Schmitt trigger (comparator with hysteresis)", level="E",
    tools="eelab mini-SPICE transient, noisy slow ramp input",
    summary="Feed a slow, noisy ramp into a plain comparator and a Schmitt trigger: predict the "
            "hysteresis thresholds and count false transitions in each.",
    problem="A slowly changing noisy signal makes a comparator chatter as it crosses the threshold. "
            "How much hysteresis stops it, and where exactly do the thresholds land?",
    theory=r"""Inverting Schmitt trigger: input to (−), positive feedback R₁ (to ground) / R₂ (to output) on (+).
With output saturation $\pm V_{sat}$:
$$V_{T\pm}=\pm V_{sat}\frac{R_1}{R_1+R_2}$$
R₁ = 1 kΩ, R₂ = 47 kΩ, V_sat = 12 V → ±250 mV (500 mV window). Noise of amplitude below half the
window cannot cause a second transition.""",
    method="""Input: triangle ±2 V at 10 Hz plus Gaussian noise (σ = 60 mV, 20 kHz bandwidth). Op-amp macromodel with
V_sat = 12 V, GBW 10 MHz, SR 10 V/µs. Compare a plain comparator (no feedback) and the Schmitt trigger;
count output transitions and read the input value at each Schmitt transition.""",
)


def run(p):
    fs, T = 200e3, 0.2
    n = int(fs * T)
    tt = np.arange(n) / fs
    tri = 2 * (2 * np.abs(2 * ((tt * 10) % 1) - 1) - 1)
    noise = p.rng.normal(0, 60e-3, n)
    k = np.ones(10) / 10
    noise = np.convolve(noise, k, "same") * np.sqrt(10)
    vin = tri + noise
    wave = lambda t: np.interp(t, tt, vin)
    out = {}
    for name, fb in (("comparator", False), ("schmitt", True)):
        ck = Circuit(name)
        ck.V("in", "in", "0", wave=wave)
        if fb:
            ck.R("1", "p", "0", 1e3); ck.R("2", "p", "out", 47e3)
        else:
            ck.R("1", "p", "0", 1e3)
        ck.OPAMP("U1", "p", "in", "out", VSAT=12, GBW=10e6, SR=10e6)
        ck.R("L", "out", "0", 10e3)
        if fb:
            p.write("simulation/schmitt.cir", ck.to_spice(), "SPICE netlist")
        tr = ck.tran(T, 1 / fs, uic=True)
        out[name] = tr.v("out")
    t = np.arange(len(out["schmitt"])) / fs
    vin = np.interp(t, tt, vin)
    vth = 12 * 1e3 / 48e3
    s = np.sign(out["schmitt"]); c = np.sign(out["comparator"])
    skip = int(2e-3 * fs)       # ignore the power-up edge from the uninitialised output
    ts_idx = np.where(np.diff(s) != 0)[0]; ts_idx = ts_idx[ts_idx > skip]
    tc_idx = np.where(np.diff(c) != 0)[0]; tc_idx = tc_idx[tc_idx > skip]
    ideal = 4 * T * 10 / 2 * 1  # two crossings per triangle period
    up = [vin[i] for i in ts_idx if s[i + 1] < 0]   # output goes low when input rises past V_T+
    dn = [vin[i] for i in ts_idx if s[i + 1] > 0]
    p.compare("Upper threshold V_T+", vth, np.mean(up), "V", tol=10)
    p.compare("Lower threshold V_T−", -vth, np.mean(dn), "V", tol=10)
    p.compare("Transitions, Schmitt trigger", 2 * T * 10, len(ts_idx), "", note="ideal: 2 per triangle period")
    p.compare("Transitions, plain comparator", 2 * T * 10, len(tc_idx), "")
    fig, ax = p.fig(3, 1, h=7.5, sharex=True)
    m = t < 0.1
    ax[0].plot(t[m] * 1e3, vin[m], color=COLORS[2], lw=.6, label="noisy ramp input")
    ax[0].axhline(vth, color=C_PRED, ls="--", lw=1, label="±V_T (predicted)"); ax[0].axhline(-vth, color=C_PRED, ls="--", lw=1)
    style_axes(ax[0], None, "V_in (V)", "Noisy triangle input")
    ax[1].plot(t[m] * 1e3, out["comparator"][m], color=COLORS[7], lw=.8, label=f"comparator ({len(tc_idx)} transitions)")
    style_axes(ax[1], None, "V_out (V)")
    ax[2].plot(t[m] * 1e3, out["schmitt"][m], color=C_MEAS, lw=1, label=f"Schmitt ({len(ts_idx)} transitions)")
    style_axes(ax[2], "time (ms)", "V_out (V)")
    p.save(fig, "chatter", "The plain comparator chatters at every crossing; hysteresis gives one clean edge.")
    p.csv("waveforms", t_s=t, vin_v=vin, comparator_v=out["comparator"], schmitt_v=out["schmitt"])
    p.discuss("""Measured thresholds are a little outside ±250 mV because the transition is detected at the
sample where the output changes sign: noise pushes the input past the threshold earlier or later, and
finite slew rate adds a few µs of delay. The chatter count is the real result — with σ = 60 mV noise
the comparator produces many transitions per crossing, while the 500 mV window is ≈ 8σ wide so the
Schmitt trigger switches exactly twice per period.""")
