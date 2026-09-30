from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-006", title="60 Hz twin-T notch filter", level="M",
    tools="eelab mini-SPICE, Monte Carlo over component tolerance",
    summary="Twin-T notch tuned to 60 Hz mains hum: the ideal null is infinitely deep; measure how "
            "deep it really is with 1 % and 5 % parts (200 Monte Carlo builds each).",
    problem="A notch filter should delete 60 Hz hum. How deep is the null in practice, and how "
            "precisely must the six components match?",
    theory=r"""Twin-T: series arm R–R with 2C to ground, parallel arm C–C with R/2 to ground.
$$f_0=\frac1{2\pi RC},\qquad H(s)=\frac{s^2+\omega_0^2}{s^2+4\omega_0 s+\omega_0^2}$$
so the passive notch has Q = 1/4: −3 dB bandwidth = 4f₀ = 240 Hz, and the null is exact only if the
bridge is perfectly balanced. C = 100 nF → R = 26.53 kΩ.""",
    method="""Nominal circuit (buffered load 1 MΩ) swept 1 Hz–10 kHz to find f₀, depth and bandwidth.
Then 200 random builds with uniformly distributed ±1 % and ±5 % R/C errors; the null depth is
measured for each by a fine sweep around 60 Hz.""",
)


def build(R, C, err=None):
    e = np.ones(6) if err is None else err
    ck = Circuit("twin-T")
    ck.V("in", "in", "0", ac=1)
    ck.R("a", "in", "m1", R * e[0]); ck.R("b", "m1", "out", R * e[1]); ck.C("g", "m1", "0", 2 * C * e[2])
    ck.C("a", "in", "m2", C * e[3]); ck.C("b", "m2", "out", C * e[4]); ck.R("g", "m2", "0", R / 2 * e[5])
    ck.R("load", "out", "0", 1e6)
    return ck


def run(p):
    C = 100e-9; f0 = 60.0
    R = 1 / (2 * pi * f0 * C)
    ck = build(R, C)
    p.write("simulation/twin_t.cir", ck.to_spice(), "SPICE netlist")
    f = np.logspace(0, 4, 3000)
    H = ck.ac(f).v("out")
    g = db(H)
    k = np.argmin(g)
    s = 1j * 2 * pi * f; w0 = 2 * pi * f0
    Hth = (s**2 + w0**2) / (s**2 + 4 * w0 * s + w0**2)
    ref = db(H[0])
    lo = find_crossing(f[:k], g[:k], ref - 3.0103); hi = find_crossing(f[k:], g[k:], ref - 3.0103)
    p.compare("Notch frequency", f0, f[k], "Hz", tol=1)
    p.compare("−3 dB bandwidth", 4 * f0, hi - lo, "Hz", tol=5)
    ck_inf = build(R, C); ck_inf.elems = [e for e in ck_inf.elems if e[1] != "load"]
    Hi = db(ck_inf.ac(f).v("out")); ki = np.argmin(Hi)
    bw_inf = find_crossing(f[ki:], Hi[ki:], Hi[0] - 3.0103) - find_crossing(f[:ki], Hi[:ki], Hi[0] - 3.0103)
    p.metric("−3 dB bandwidth with no load", bw_inf, "Hz", "confirms Q = 1/4 when unloaded")
    p.metric("Null depth, nominal parts", g[k] - ref, "dB", "limited only by sweep resolution / 1 MΩ load")
    fz = np.linspace(40, 80, 801)
    depths = {}
    for tol in (0.01, 0.05):
        d = []
        for _ in range(200):
            ckm = build(R, C, 1 + p.rng.uniform(-tol, tol, 6))
            Hm = ckm.ac(fz).v("out")
            d.append(db(np.abs(Hm).min()) - ref)
        depths[tol] = np.array(d)
        p.metric(f"Median null depth, ±{tol*100:.0f} % parts", np.median(d), "dB",
                 f"worst {np.max(d):.1f} dB, best {np.min(d):.1f} dB")
    hum_pred = -20 * np.log10(1)  # placeholder not used
    fig, ax = p.fig()
    ax.semilogx(f, db(Hth), "--", color=C_PRED, label="theory (ideal twin-T)")
    ax.semilogx(f, g, color=C_MEAS, label="simulated, nominal parts")
    ckm = build(R, C, 1 + p.rng.uniform(-0.05, 0.05, 6))
    ax.semilogx(f, db(ckm.ac(f).v("out")), color=COLORS[2], label="one ±5 % build")
    ax.set_ylim(-80, 3)
    style_axes(ax, "frequency (Hz)", "gain (dB)", "Twin-T notch at 60 Hz")
    p.save(fig, "notch", "The null is deep only when the bridge is balanced.")
    fig, ax = p.fig()
    bins = np.linspace(-80, 0, 41)
    ax.hist(depths[0.01], bins, color=COLORS[0], alpha=.8, label="±1 % parts", rwidth=.9)
    ax.hist(depths[0.05], bins, color=COLORS[1], alpha=.7, label="±5 % parts", rwidth=.9)
    style_axes(ax, "null depth (dB)", "builds (of 200)", "Monte Carlo: how deep is the notch really?")
    p.save(fig, "depth_histogram", "Null-depth distribution over 200 random builds.")
    p.csv("montecarlo_depths", tol1pct_db=depths[0.01], tol5pct_db=depths[0.05])
    p.discuss(f"""The bandwidth comes out ~8 % narrower than 4f₀ because the 1 MΩ buffer input loads the
network (the twin-T's output impedance is tens of kΩ): removing the load gives {bw_inf:.1f} Hz, matching
Q = 1/4. With perfect parts the null is limited only by the sweep grid (the 1 MΩ load barely unbalances
it). Real parts are the story: ±1 % tolerance gives a median null of {np.median(depths[0.01]):.0f} dB and
±5 % only {np.median(depths[0.05]):.0f} dB, because any imbalance leaves a residual term in the numerator
so H(jω₀) ≠ 0. Q = 1/4 also means the notch is wide (≈240 Hz) and attenuates 120 Hz harmonics and
nearby wanted signals; practical designs add bootstrapped feedback to raise Q and trimmed parts to
restore depth.""")
