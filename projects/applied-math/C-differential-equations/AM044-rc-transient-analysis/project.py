from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="AM-044", title="RC transient: solve the ODE, then check it", level="E",
    tools="Analytic solution of the first-order ODE, MNA transient simulation (trapezoidal), time-constant and energy measurements",
    summary="Solve RC·dv/dt + v = V_in analytically for charging and discharging, predict the 63.2 % and 5τ points and the energy lost in the "
            "resistor, and verify every prediction against a circuit simulation.",
    problem="The RC circuit is the first ODE every EE solves. How exactly do simulation and algebra agree — including the famous 50 % energy loss?",
    theory=r"""$RC\,\dot v+v=V$ with v(0) = 0 gives $v=V(1-e^{-t/τ})$, τ = RC: 63.2 % at t = τ, 99.3 % at 5τ, rise time 10→90 % = τ ln 9 = 2.197τ. Charging a capacitor from a fixed source always
dissipates $\tfrac12CV^2$ in the resistor — exactly as much as is stored — independent of R.""",
    method="""R = 10 kΩ, C = 100 nF (τ = 1 ms), 5 V step, then discharge. Transient with Δt = τ/1000; resistor energy ∫i²R dt integrated numerically; R varied 100 Ω–1 MΩ for the energy test.""",
)


def run(p):
    R, C, V = 10e3, 100e-9, 5.0
    tau = R * C
    ck = Circuit("rc"); ck.V("s", "a", "0", wave=lambda t: V if t < 8 * tau else 0.0); ck.R("r", "a", "b", R); ck.C("c", "b", "0", C)
    tr = ck.tran(16 * tau, tau / 1000, method="trap", ic={"b": 0.0})
    t, v = tr.t, tr.v("b")
    ch = t < 8 * tau
    ana = np.where(ch, V * (1 - np.exp(-t / tau)), V * (1 - np.exp(-8)) * np.exp(-(t - 8 * tau) / tau))
    p.compare("Max |simulation − analytic| over charge and discharge", 0, np.max(np.abs(v - ana)), "V", kind="abs", tol=5e-3)
    p.compare("Time to 63.2 % = τ", tau, find_crossing(t[ch], v[ch], 0.632121 * V, logx=False), "s", tol=0.1)
    t10 = find_crossing(t[ch], v[ch], 0.1 * V, logx=False); t90 = find_crossing(t[ch], v[ch], 0.9 * V, logx=False)
    p.compare("10–90 % rise time = τ·ln 9", tau * np.log(9), t90 - t10, "s", tol=0.1)
    rows = []
    for Rx in (100, 1e3, 1e4, 1e5, 1e6):
        tx = Rx * C
        c2 = Circuit("rc"); c2.V("s", "a", "0", dc=V); c2.R("r", "a", "b", Rx); c2.C("c", "b", "0", C)
        tr2 = c2.tran(12 * tx, tx / 2000, method="trap", ic={"b": 0.0})
        i = (tr2.v("a") - tr2.v("b")) / Rx
        rows.append((Rx, np.trapezoid(i * i * Rx, tr2.t)))
    E = 0.5 * C * V * V
    p.compare("Energy dissipated in R while charging = ½CV² (worst over R = 100 Ω … 1 MΩ)", 0, max(abs(e / E - 1) for _, e in rows), "", kind="abs", tol=0.01)
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(t * 1e3, v, color=C_MEAS, lw=3, alpha=.5, label="simulation"); ax[0].plot(t * 1e3, ana, "--", color=C_PRED, label="analytic")
    style_axes(ax[0], "t (ms)", "v_C (V)", "Charge and discharge, τ = 1 ms")
    ax[1].semilogx([r[0] for r in rows], [r[1] / E for r in rows], "o-", color=C_MEAS, label="measured")
    ax[1].axhline(1, ls="--", color=C_PRED, label="½CV² for every R"); ax[1].set_ylim(0.8, 1.2)
    style_axes(ax[1], "R (Ω)", "E_R / (½CV²)", "Charging always wastes half")
    p.save(fig, "rc", "Simulated vs analytic RC transient, and the resistor's share of the energy for five resistances.")
    p.discuss("""Simulation and the exponential solution agree to a few millivolts — the residual sits entirely at the instant the source switches off, which
falls between two time points of the 1 µs grid (the capacitor then discharges at 5 V/ms, so one step of timing is 5 mV) — and the characteristic times come out exactly: 63.2 % at τ and a 10–90 % rise of
2.197τ. The energy result is the one that surprises people: whatever R is — 100 Ω or 1 MΩ — the resistor dissipates exactly the ½CV² that ends up
stored, because a smaller R means a larger current for a shorter time and the integral ∫i²R dt is independent of R. The only way around the 50 %
loss is not to charge from a stiff voltage source at all (inductive or adiabatic charging), which is the principle behind resonant and
adiabatic logic.""")
# tol-convention: relative tolerances are in percent
