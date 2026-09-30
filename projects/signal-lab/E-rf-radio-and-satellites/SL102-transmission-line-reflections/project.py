from eelab import *

META = dict(
    id="SL-102", title="Transmission-line reflections, standing waves and VSWR", level="M",
    tools="1-D FDTD solution of the telegrapher's equations (NumPy), bounce-diagram prediction",
    summary="Launch a step and a sine onto a 50 Ω line terminated in 150 Ω, 50 Ω, open and short loads; compare the "
            "time-domain voltage at the source with the bounce-diagram prediction and the standing-wave ratio with "
            "(1+|Γ|)/(1−|Γ|).",
    problem="What really happens when a fast edge hits a mismatched load, and how does that become a standing wave "
            "for a continuous sine?",
    theory=r"""Load reflection $\Gamma_L=\frac{Z_L-Z_0}{Z_L+Z_0}$, source $\Gamma_S=\frac{Z_S-Z_0}{Z_S+Z_0}$. A step $V_s$ launches $V^+=V_s\frac{Z_0}{Z_S+Z_0}$;
after each round trip 2T the source voltage changes by the next bounce term, converging to $V_s\frac{Z_L}{Z_S+Z_L}$.
For a sine, the envelope along the line varies between $|V^+|(1\pm|\Gamma_L|)$: VSWR = $\frac{1+|\Gamma|}{1-|\Gamma|}$.""",
    method="""Lossless line, L′ = 250 nH/m, C′ = 100 pF/m (Z₀ = 50 Ω, v = 2×10⁸ m/s), 1 m long, 400 cells, leapfrog update at Courant number 0.5, resistive source 25 Ω and resistive/open/short loads implemented as boundary conditions. Step
response vs bounce diagram; 1 GHz sine for VSWR.""",
)


def fdtd(ZL, ZS, src, T, nx=400, Lp=250e-9, Cp=100e-12, length=1.0, courant=0.5):
    """Leapfrog FDTD of the telegrapher's equations. V at nodes 0..nx, I at half-cells.
    End nodes carry half a cell of capacitance and a resistive source/load (trapezoidal, unconditionally stable)."""
    dx = length / nx; v = 1 / np.sqrt(Lp * Cp); dt = courant * dx / v
    V = np.zeros(nx + 1); I = np.zeros(nx)
    nt = int(T / dt)
    rec, env = [], np.zeros(nx + 1)
    ch = dt / (Cp * dx); cl = dt / (Lp * dx); cb = 2 * dt / (Cp * dx)
    for n in range(nt):
        t = (n + 1) * dt
        V[1:-1] -= ch * np.diff(I)
        # source node: (C dx/2) dV/dt = (Vs − V)/ZS − I[0]
        V[0] = (V[0] * (1 - cb / (2 * ZS)) + cb * (src(t - dt / 2) / ZS - I[0])) / (1 + cb / (2 * ZS))
        if np.isinf(ZL):
            V[-1] += cb * I[-1]
        elif ZL == 0:
            V[-1] = 0.0
        else:
            V[-1] = (V[-1] * (1 - cb / (2 * ZL)) + cb * I[-1]) / (1 + cb / (2 * ZL))
        I -= cl * np.diff(V)
        rec.append(V[0])
        if t > T * 0.6:
            env = np.maximum(env, np.abs(V))
    return (np.arange(nt) + 1) * dt, np.array(rec), env, dt


def bounce(ZL, ZS, Z0, Vs, t, T):
    gL = 1.0 if ZL == np.inf else (ZL - Z0) / (ZL + Z0)
    gS = (ZS - Z0) / (ZS + Z0)
    v = np.zeros_like(t); Vp = Vs * Z0 / (ZS + Z0)
    v += Vp
    k = 1; term = Vp
    while 2 * k * T < t[-1]:
        # arrival of k-th reflection at the source: adds term*gL*(1+gS)
        v += np.where(t >= 2 * k * T, term * gL * (1 + gS), 0)
        term = term * gL * gS
        k += 1
    return v


def run(p):
    Z0, ZS, Vs = 50.0, 25.0, 1.0
    T = 1.0 / 2e8
    fig, ax = p.fig()
    for i, (ZL, lab) in enumerate(((150.0, "150 Ω"), (50.0, "matched 50 Ω"), (np.inf, "open"), (1e-9, "short"))):
        zl = 0.0 if ZL < 1e-6 else ZL
        t, vs, env, dt = fdtd(zl, ZS, lambda tt: Vs if tt > 0 else 0, 12 * T)
        pred = bounce(zl, ZS, Z0, Vs, t, T)
        final = Vs * (1.0 if zl == np.inf else zl / (ZS + zl))
        p.compare(f"{lab}: settled source voltage", final, vs[-1], "V", kind="abs")
        ax.plot(t * 1e9, vs, color=COLORS[i], label=f"{lab} (FDTD)")
        ax.plot(t * 1e9, pred, "--", color=COLORS[i], lw=1)
        if zl == 150.0:
            p.compare("150 Ω: first-step voltage V⁺ = V_s·Z₀/(Z_S+Z₀)", Vs * Z0 / (ZS + Z0), vs[int(T / dt * 0.5)], "V", tol=1)
            p.compare("150 Ω: voltage after first reflection returns (t = 2T+)", bounce(zl, ZS, Z0, Vs, np.array([2.5 * T]), T)[0], vs[int(2.5 * T / dt)], "V", tol=1)
    style_axes(ax, "time (ns)", "source-end voltage (V)", "Step response: FDTD (solid) vs bounce diagram (dashed)")
    p.save(fig, "bounce", "Every step in the waveform is one round trip of the reflection.")
    f = 1e9
    fig, ax = p.fig()
    for i, ZL in enumerate((150.0, 50.0, 100.0)):
        t, vs, env, dt = fdtd(ZL, 50.0, lambda tt: np.sin(2 * pi * f * tt) * min(1, tt * f / 3), 60 * T)
        x = np.linspace(0, 1, len(env))
        g = abs((ZL - Z0) / (ZL + Z0))
        vswr = env[20:-20].max() / env[20:-20].min()
        p.compare(f"VSWR, Z_L = {ZL:.0f} Ω", (1 + g) / (1 - g), vswr, "", tol=3)
        ax.plot(x, env, color=COLORS[i], label=f"Z_L = {ZL:.0f} Ω (Γ = {g:.2f})")
    style_axes(ax, "position (m)", "|V| envelope (V)", "Standing waves at 1 GHz")
    p.save(fig, "standing_waves", "Matched line: flat envelope. Mismatch: peaks every λ/2 with ratio = VSWR.")
    p.discuss("""The FDTD waveform steps where and by how much the bounce diagram says; the small overshoot on each edge is the numerical
dispersion of the Courant-0.5 leapfrog scheme (a first attempt at Courant number 1 with a lumped source node went unstable
— boundary conditions are the delicate part of FDTD). The final voltage is simply the DC divider V_s·Z_L/(Z_S+Z_L) — the reflections are
how the line 'discovers' the load. For a sine the reflections superpose into a standing wave whose max/min ratio is
the VSWR; a matched load gives a flat envelope. Real lines add loss (the steps round off) and dispersion.""")
