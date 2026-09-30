from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-019", title="Class-A vs Class-B vs Class-AB output stages", level="M",
    tools="eelab mini-SPICE transient, FFT THD, supply-power integration",
    summary="Compare efficiency and crossover distortion of three emitter-follower output stages "
            "driving 8 Ω, against the textbook 25 % and π/4 limits.",
    problem="Why do audio amplifiers use class AB? Quantify efficiency and distortion of class A, B "
            "and AB at the same output power.",
    theory=r"""Class A (resistor-biased emitter follower, quiescent current ≥ peak load current): efficiency
$\eta = P_L/P_{supply}$ is at most 25 % and scales as $(\hat V/V_{CC})^2$.
Class B (complementary pair, no bias): $\eta=\frac{\pi}{4}\frac{\hat V}{V_{CC}}$, max 78.5 %, but each transistor
conducts only when $|v_{in}|>V_{BE}\approx0.6$ V → crossover distortion.
Class AB: two diodes pre-bias the bases by ~2V_BE so one device is always on → distortion
collapses, efficiency ≈ class B.""",
    method="""±15 V rails, 8 Ω load, 1 kHz drive. Class A: NPN follower with a 1.9 A constant-current sink (≈ 57 W
standby). Class B: complementary NPN/PNP. Class AB: same pair with two biasing diodes fed by 40 mA
current sources (enough to supply the ≈ 20 mA peak base current at full output). Amplitudes 2–12 V; efficiency from ∫v·i of both supplies, THD from FFT.""",
)

Q = dict(Is=1e-13, BF=80, VAF=100)


def build(kind, amp):
    ck = Circuit(kind)
    ck.V("p", "vp", "0", dc=15); ck.V("n", "vn", "0", dc=-15)
    ck.V("in", "in", "0", wave=lambda t: amp * np.sin(2 * pi * 1000 * t))
    if kind == "A":
        ck.Q("1", "vp", "in", "out", pol="npn", **Q)
        ck.I("sink", "out", "vn", dc=1.9)
    else:
        if kind == "B":
            bn, bp = "in", "in"
        else:
            bn, bp = "bn", "bp"
            ck.I("b1", "vp", "bn", dc=40e-3); ck.I("b2", "bp", "vn", dc=40e-3)
            ck.D("1", "bn", "in", Is=1e-13, N=1.0); ck.D("2", "in", "bp", Is=1e-13, N=1.0)
        ck.Q("n", "vp", bn, "out", pol="npn", **Q)
        ck.Q("p", "vn", bp, "out", pol="pnp", **Q)
    ck.R("L", "out", "0", 8)
    return ck


def thd(x, fs, f0=1000):
    X = np.abs(np.fft.rfft(x))
    fr = np.fft.rfftfreq(len(x), 1 / fs)
    h = [X[np.argmin(abs(fr - k * f0))] for k in range(1, 10)]
    return np.sqrt(np.sum(np.square(h[1:]))) / h[0] * 100


def run(p):
    fs = 500e3
    amps = [2, 4, 6, 8, 10, 12]
    res = {k: [] for k in "ABC"}
    for kind, key in (("A", "A"), ("B", "B"), ("AB", "C")):
        for a in amps:
            ck = build(kind, a + (0.0 if kind != "A" else 0.7))
            tr = ck.tran(3e-3, 1 / fs)
            m = tr.t >= 1e-3
            vo = tr.v("out")[m][:-1]
            ip = -tr.i("p")[m][:-1]; inn = tr.i("n")[m][:-1]
            Psup = np.mean(15 * ip) + np.mean(15 * inn)
            PL = np.mean(vo**2) / 8
            vhat = np.sqrt(2 * np.mean(vo**2))
            res[key].append((a, vhat, PL / Psup * 100, thd(vo, fs)))
            if a == 8:
                if kind == "B":
                    wB = (tr.t[m][:-1], vo)
    for key, lab in (("A", "class A"), ("B", "class B"), ("C", "class AB")):
        a, vh, eta, th = map(np.array, zip(*res[key]))
        i = -1
        if key == "A":
            pred = (vh[i]**2 / 16) / (2 * 15 * 1.9) * 100
        else:
            pred = pi / 4 * vh[i] / 15 * 100
        p.compare(f"{lab}: efficiency at V̂ ≈ {vh[i]:.1f} V", pred, eta[i], "%", kind="abs")
        p.metric(f"{lab}: THD at 2 V drive", th[0], "%")
        p.metric(f"{lab}: THD at 12 V drive", th[-1], "%")
    fig, ax = p.fig(1, 2)
    for i, (key, lab) in enumerate((("A", "class A"), ("B", "class B"), ("C", "class AB"))):
        a, vh, eta, th = map(np.array, zip(*res[key]))
        ax[0].plot(vh, eta, "o-", color=COLORS[i], label=lab)
        ax[1].semilogy(vh, th, "o-", color=COLORS[i], label=lab)
    vv = np.linspace(1, 13, 50)
    ax[0].plot(vv, pi / 4 * vv / 15 * 100, "--", color=C_PRED, lw=1, label="π/4·V̂/V_CC")
    ax[0].plot(vv, vv**2 / 16 / 57 * 100, ":", color=C_PRED, lw=1, label="class A theory")
    style_axes(ax[0], "output amplitude (V)", "efficiency (%)", "Efficiency")
    style_axes(ax[1], "output amplitude (V)", "THD (%)", "Distortion")
    p.save(fig, "efficiency_thd", "Class B is efficient but distorted; AB keeps the efficiency and removes crossover distortion.")
    t, vo = wB
    fig, ax = p.fig()
    ax.plot(t[:1000] * 1e3, vo[:1000], color=COLORS[1], label="class B output")
    ax.plot(t[:1000] * 1e3, 8 * np.sin(2 * pi * 1000 * t[:1000]), "--", color="gray", lw=1, label="input")
    style_axes(ax, "time (ms)", "V", "Crossover distortion: the dead zone around 0 V")
    p.save(fig, "crossover", "Class B output is flat while |v_in| < V_BE.")
    import pandas as pd
    rows = [(k, *r) for k in res for r in res[k]]
    p.csv_df("sweep", pd.DataFrame(rows, columns=["class", "drive_v", "vout_peak_v", "efficiency_pct", "thd_pct"]))
    p.discuss("""Class B's efficiency tracks π/4·V̂/V_CC, slightly lower because the output never reaches the rail
and because of the V_BE loss. Its THD is large at low amplitude — the fixed 1.2 V dead zone is a bigger
fraction of a small signal — which is exactly the wrong way round for music, most of which is quiet.
The class-A stage has almost no distortion but burns 57 W at idle to deliver a few watts. Class AB
removes the dead zone with two diode drops of bias and keeps most of class-B's efficiency — the few
points it loses against π/4·V̂/V_CC are the 2 × 40 mA bias-network current drawn from ±15 V
(2.4 W), which the textbook formula ignores.""")
