from eelab import *
from eelab.circuit import Circuit, e_series
from scipy import signal

META = dict(
    id="SL-005", title="Butterworth vs Chebyshev (4th order)", level="M",
    tools="SciPy analog prototypes + eelab mini-SPICE (cascaded Sallen-Key)",
    summary="Two 4th-order 1 kHz low-pass filters built as cascaded Sallen-Key stages: measure "
            "passband ripple and stop-band attenuation to show flatness vs steepness.",
    problem="Butterworth promises a maximally flat passband; Chebyshev trades 1 dB of ripple for a "
            "steeper roll-off. How big is that trade in dB at 2 kHz, and does it survive E24 parts?",
    theory=r"""Poles come from the prototypes: Butterworth poles lie on a circle
($s_k = \omega_c e^{j\pi(2k+n-1)/2n}$), Chebyshev poles on an ellipse determined by the ripple ε
($\varepsilon^2=10^{R_p/10}-1$). Pairing conjugate poles gives biquads with
$\omega_{0}=|s_k|$, $Q=|s_k|/(2|\mathrm{Re}\,s_k|)$ — each built as a unity-gain Sallen-Key stage.
Predicted attenuation at 2 kHz: Butterworth $10\log(1+2^{8}) = 24.1$ dB; Chebyshev
$10\log(1+\varepsilon^2T_4^2(2))$ with $T_4(2)=97$.""",
    method="""scipy.signal.butter / cheby1 give analog poles → (f₀, Q) per stage → components
(R = 10 kΩ, C1 = 2Q/(ω₀R), C2 = 1/(2Qω₀R)) rounded to E24 → two cascaded op-amp stages simulated
in AC. Measured: passband ripple (max − min gain below 1 kHz), −3 dB point, attenuation at 2 kHz and 5 kHz.""",
)


def stages(z, pz, k):
    ps = [x for x in pz if x.imag > 0]
    return [(abs(x) / (2 * pi), abs(x) / (2 * abs(x.real))) for x in ps]


def build(stg, R=10e3):
    ck = Circuit("cascade")
    ck.V("in", "n0", "0", ac=1)
    parts = []
    for i, (f0, Q) in enumerate(stg):
        w0 = 2 * pi * f0
        C1, C2 = e_series(2 * Q / (w0 * R)), e_series(1 / (2 * Q * w0 * R))
        parts.append((C1, C2))
        a, b, o = f"a{i}", f"b{i}", f"n{i+1}"
        ck.R(f"1_{i}", f"n{i}", a, R); ck.R(f"2_{i}", a, b, R)
        ck.C(f"1_{i}", a, o, C1); ck.C(f"2_{i}", b, "0", C2)
        ck.OPAMP(f"U{i}", b, o, o)
    return ck, parts, f"n{len(stg)}"


def run(p):
    wc = 2 * pi * 1000
    f = np.logspace(2, 4, 800)
    res = {}
    fig, ax = p.fig()
    for i, (name, proto) in enumerate([("Butterworth", signal.butter(4, wc, analog=True, output="zpk")),
                                       ("Chebyshev 1 dB", signal.cheby1(4, 1, wc, analog=True, output="zpk"))]):
        stg = stages(*proto)
        ck, parts, out = build(stg)
        H = ck.ac(f).v(out)
        _, Hp = signal.freqs_zpk(*proto, worN=2 * pi * f)
        Hp = Hp / abs(Hp[0]) if name.startswith("Butter") else Hp / abs(Hp[0]) * 10**(-1/20) / 10**(-1/20)
        g, gp = db(H), db(Hp) - db(Hp[0]) + (0 if name.startswith("Butter") else 0)
        pb = f <= 1000
        ripple_m = g[pb].max() - g[pb].min()
        ripple_p = gp[pb].max() - gp[pb].min()
        a2m, a2p = -np.interp(2000, f, g - g[0]), -np.interp(2000, f, gp - gp[0])
        a5m, a5p = -np.interp(5000, f, g - g[0]), -np.interp(5000, f, gp - gp[0])
        if name.startswith("Butter"):
            p.compare(f"{name}: gain at passband edge 1 kHz", np.interp(1000, f, gp - gp[0]),
                      np.interp(1000, f, g - g[0]), "dB", kind="abs")
            p.compare(f"{name}: max deviation below 500 Hz", 0.0, np.max(np.abs((g - g[0])[f <= 500])), "dB", kind="abs")
        else:
            p.compare(f"{name}: passband ripple (0–1 kHz)", ripple_p, ripple_m, "dB", kind="abs")
        p.compare(f"{name}: attenuation at 2 kHz", a2p, a2m, "dB", kind="abs")
        p.compare(f"{name}: attenuation at 5 kHz", a5p, a5m, "dB", kind="abs")
        for j, (st, pc) in enumerate(zip(stg, parts)):
            p.metric(f"{name} stage {j+1}", f"f₀={st[0]:.1f} Hz, Q={st[1]:.3f}, C1={pc[0]*1e9:.3g} nF, C2={pc[1]*1e9:.3g} nF")
        ax.semilogx(f, g - g[0], color=COLORS[i], label=f"{name} (simulated, E24)")
        ax.semilogx(f, gp - gp[0], "--", color=COLORS[i], lw=1, label=f"{name} (ideal prototype)")
        res[name] = (a2m, ripple_m)
        p.csv(name.split()[0].lower(), freq_hz=f, gain_db=g)
    ax.set_ylim(-60, 3)
    style_axes(ax, "frequency (Hz)", "gain re DC (dB)", "4th-order low-pass: flat Butterworth vs steep Chebyshev")
    p.save(fig, "compare", "Chebyshev buys ~12 dB more attenuation at 2 kHz for 1 dB of passband ripple.")
    fig, ax = p.fig()
    ax.plot(f, db(ck.ac(f).v(out)) - db(ck.ac(f[:1]).v(out))[0], color=COLORS[1])
    ax.set_xlim(100, 1200); ax.set_ylim(-4, 1.5)
    style_axes(ax, "frequency (Hz)", "gain (dB)", "Chebyshev passband detail (equiripple)", legend=False)
    p.save(fig, "cheby_passband", "Zoom on the Chebyshev passband showing the 1 dB equiripple.")
    p.discuss(f"""Chebyshev gives {res['Chebyshev 1 dB'][0] - res['Butterworth'][0]:.1f} dB more attenuation at
2 kHz than Butterworth, the price being {res['Chebyshev 1 dB'][1]:.2f} dB of passband ripple. Rounding the
capacitors to E24 shifts each stage's f₀ and Q by up to a few percent; the Chebyshev filter is far
more sensitive to this because its second stage has Q ≈ 3.6, so the ripple deviates more from the
ideal 1 dB than the Butterworth's flatness does.""")
