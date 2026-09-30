from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-053", title="Coupled LC oscillators: normal modes and beating", level="H",
    tools="Eigenvalue analysis of two magnetically coupled LC tanks, MNA transient simulation with a coupled-inductor element, spectral peak and beat-period measurement",
    summary="Couple two identical LC tanks through mutual inductance, predict the split normal-mode frequencies ω0/√(1±k) and the energy "
            "beating between the tanks, and verify both in simulation for coupling coefficients from 0.02 to 0.3.",
    problem="Two identical resonators placed near each other stop having one resonance. Why two — and how does energy slosh between them?",
    theory=r"""With L1 = L2 = L, mutual M = kL: $L\ddot q_1 + M\ddot q_2 + q_1/C = 0$ (and symmetric). Normal modes q1 = ±q2 have $ω_\pm = ω_0/\sqrt{1\pm k}$. Starting with energy only in tank 1, the
envelope beats at $Δω = ω_- - ω_+$: energy fully transfers to tank 2 after $T_{transfer}=π/Δω ≈ π/(kω_0)$. This is the physics of double-tuned IF transformers and wireless power transfer.""",
    method="""L = 10 µH, C = 100 nF (f0 = 159 kHz), k = 0.02, 0.05, 0.1, 0.2, 0.3. Tank 1 capacitor precharged to 1 V; transient 500 µs; mode frequencies from the FFT peaks of v1, transfer time from the first
minimum of tank-1 energy.""",
)


def run(p):
    L, Cc = 10e-6, 100e-9
    w0 = 1 / np.sqrt(L * Cc); f0 = w0 / (2 * pi)
    rows = []
    for k in (0.02, 0.05, 0.1, 0.2, 0.3):
        ck = Circuit("coupled")
        ck.L("1", "a", "0", L); ck.C("1", "a", "0", Cc); ck.L("2", "b", "0", L); ck.C("2", "b", "0", Cc); ck.K("1", "2", k)
        ck.R("big1", "a", "0", 1e9); ck.R("big2", "b", "0", 1e9)
        Tsim = max(500e-6, 8 / (f0 * k))                 # record long enough to resolve the splitting ≈ k·f0 several times over
        tr = ck.tran(Tsim, 2e-8, method="trap", ic={"a": 1.0, "b": 0.0, "I(1)": 0.0, "I(2)": 0.0})
        t, v1, v2 = tr.t, tr.v("a"), tr.v("b")
        V = np.abs(np.fft.rfft(v1 * np.hanning(len(v1)), 1 << 22)); f = np.fft.rfftfreq(1 << 22, t[1] - t[0])
        from scipy.signal import find_peaks
        pk, _ = find_peaks(V, height=V.max() * 0.3)
        fm = np.sort(f[pk])[:2]
        env1 = np.convolve(v1 ** 2, np.ones(200) / 200, "same")
        wp, wm = w0 / np.sqrt(1 + k), w0 / np.sqrt(1 - k)
        Ttr = pi / (wm - wp)
        seg = (t > 0.3 * Ttr) & (t < 1.7 * Ttr)
        t_min = t[seg][np.argmin(env1[seg])]
        rows.append((k, wp / (2 * pi), wm / (2 * pi), fm, Ttr, t_min))
    for k, fp, fmm, fm, Ttr, tm in rows:
        p.compare(f"k = {k}: lower mode ω0/√(1+k)", fp, fm[0], "Hz", tol=0.3)
        p.compare(f"k = {k}: upper mode ω0/√(1−k)", fmm, fm[1], "Hz", tol=0.3)
    for k, fp, fmm, fm, Ttr, tm in rows[:3]:
        p.compare(f"k = {k}: time for energy to move to tank 2 = π/(ω− − ω+)", Ttr, tm, "s", tol=3)
    ck = Circuit("coupled"); k = 0.05
    ck.L("1", "a", "0", L); ck.C("1", "a", "0", Cc); ck.L("2", "b", "0", L); ck.C("2", "b", "0", Cc); ck.K("1", "2", k); ck.R("big1", "a", "0", 1e9); ck.R("big2", "b", "0", 1e9)
    tr = ck.tran(300e-6, 2e-8, method="trap", ic={"a": 1.0, "b": 0.0, "I(1)": 0.0, "I(2)": 0.0})
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(tr.t * 1e6, tr.v("a"), color=C_MEAS, lw=.5, label="tank 1"); ax[0].plot(tr.t * 1e6, tr.v("b"), color=C_PRED, lw=.5, alpha=.8, label="tank 2")
    style_axes(ax[0], "t (µs)", "V", "k = 0.05: energy beats between the tanks")
    kk = np.linspace(0.005, 0.4, 100)
    ax[1].plot(kk, f0 / np.sqrt(1 + kk) / 1e3, color=C_PRED, ls="--", label="ω0/√(1±k)"); ax[1].plot(kk, f0 / np.sqrt(1 - kk) / 1e3, color=C_PRED, ls="--")
    for k, fp, fmm, fm, *_ in rows:
        ax[1].plot([k, k], fm / 1e3, "o", color=C_MEAS)
    style_axes(ax[1], "coupling k", "mode frequency (kHz)", "Mode splitting")
    p.save(fig, "coupled", "Beating between two coupled tanks and the normal-mode splitting vs coupling coefficient.")
    p.discuss("""The simulated spectra show two peaks at exactly ω0/√(1±k) for every coupling, and energy placed in one tank migrates completely to the other
after π/(ω− − ω+) — the beat of the two normal modes, just as with coupled pendulums. Stronger coupling transfers energy faster and splits the
modes further. This is the design lever of double-tuned transformers (k ≈ 1/Q gives the flattest band-pass) and of resonant wireless power
transfer, where the frequency splitting at strong coupling is a well-known nuisance: the single-frequency driver ends up between two modes.""")
# tol-convention: relative tolerances are in percent
