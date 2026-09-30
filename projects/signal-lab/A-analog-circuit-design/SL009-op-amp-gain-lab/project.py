from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-009", title="Op-amp gain lab", level="E",
    tools="eelab mini-SPICE (op-amp macromodel A₀ = 2×10⁵, GBW = 1 MHz)",
    summary="Verify inverting and non-inverting gain equations for six configurations, and the "
            "gain-bandwidth trade-off that the ideal equations leave out.",
    problem="Do −R_f/R_in and 1 + R_f/R_g hold for a real op-amp, and what bandwidth do you get "
            "at each gain?",
    theory=r"""Ideal: inverting $A=-R_f/R_{in}$, non-inverting $A=1+R_f/R_g$. With open-loop gain $A_0$ and
feedback factor $\beta$ the closed-loop gain is $A_{ideal}/(1+1/(A_0\beta))$ and — for a single-pole
op-amp — the closed-loop bandwidth is $f_{-3dB}= \mathrm{GBW}\cdot\beta$, where $1/\beta$ is the *noise
gain* ($1+R_f/R_{in}$ for **both** configurations).""",
    method="""R_in = R_g = 1 kΩ, R_f ∈ {1 k, 10 k, 100 k} for inverting, R_f ∈ {1 k, 10 k, 100 k} for non-inverting.
AC analysis 10 Hz–10 MHz: measured gain at 100 Hz and −3 dB bandwidth.""",
)


def run(p):
    f = np.logspace(1, 7, 600)
    fig, ax = p.fig()
    rows = []
    for i, Rf in enumerate([1e3, 10e3, 100e3]):
        for mode in ("inv", "noninv"):
            ck = Circuit(f"{mode} {Rf}")
            ck.V("in", "in", "0", ac=1)
            if mode == "inv":
                ck.R("in", "in", "m", 1e3); ck.R("f", "m", "out", Rf)
                ck.OPAMP("U1", "0", "m", "out")
                A_ideal = -Rf / 1e3
            else:
                ck.R("g", "m", "0", 1e3); ck.R("f", "m", "out", Rf)
                ck.OPAMP("U1", "in", "m", "out")
                A_ideal = 1 + Rf / 1e3
            ng = 1 + Rf / 1e3
            H = ck.ac(f).v("out")
            G = abs(np.interp(100, f, np.abs(H)))
            bw = find_crossing(f, db(H), db(abs(H[0])) - 3.0103)
            lab = f"{'inverting' if mode == 'inv' else 'non-inverting'} A={A_ideal:+.0f}"
            p.compare(f"{lab}: |gain|", abs(A_ideal), G, "", tol=0.5)
            p.compare(f"{lab}: bandwidth (GBW/noise gain)", 1e6 / ng, bw, "Hz", tol=10)
            rows.append((lab, abs(A_ideal), G, bw))
            ax.loglog(f, np.abs(H), color=COLORS[i], ls="-" if mode == "inv" else "--",
                      label=lab)
    ax.loglog(f, 1e6 / f, ":", color="gray", label="GBW line (1 MHz / f)")
    ax.set_ylim(0.1, 300)
    style_axes(ax, "frequency (Hz)", "|gain|", "Closed-loop responses: gain × bandwidth ≈ constant")
    p.save(fig, "gain_bandwidth", "Each configuration rides down the same 1 MHz gain-bandwidth line.")
    p.discuss("""Gains agree with the ideal equations to ~0.05 % at A = 100 because A₀β = 2×10⁵/101 ≈ 2000 still
dwarfs 1. Bandwidth follows GBW × β with the noise gain, which is why the inverting A = −1 stage has
only 500 kHz while the non-inverting A = +2 stage also has 500 kHz: both have noise gain 2. The small
bandwidth deviations come from the output resistance (50 Ω) and the second-order effect of the
feedback network loading the macromodel's output.""")
