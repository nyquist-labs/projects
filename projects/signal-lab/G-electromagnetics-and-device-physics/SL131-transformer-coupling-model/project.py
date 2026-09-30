from eelab import *
from eelab.circuit import Circuit

META = dict(
    id="SL-131", title="Transformer coupling: coefficient k and leakage inductance", level="M",
    tools="eelab mini-SPICE with mutual inductance (AC analysis), open/short-circuit tests",
    summary="Characterise a two-winding transformer by the classic open- and short-circuit tests in simulation and "
            "recover the coupling coefficient and leakage inductance; show how k sets voltage ratio and regulation.",
    problem="Real transformers leak flux. How do you measure the coupling coefficient, and what does leakage do to the "
            "output voltage under load?",
    theory=r"""Coupled inductors L₁, L₂, M = k√(L₁L₂). Open-circuit voltage ratio $V_2/V_1 = M/L_1 = k\sqrt{L_2/L_1}$. Primary inductance with secondary
shorted: $L_{sc}=L_1(1-k^2)$ (the leakage). So $k=\sqrt{1-L_{sc}/L_{oc}}$. Under load the leakage reactance ωL_sc causes a voltage drop that grows
with load current.""",
    method="""L₁ = 10 mH, L₂ = 2.5 mH (n = 0.5), winding resistances 0.5 Ω / 0.15 Ω, k ∈ {0.9, 0.98, 0.998}. AC analysis at 1 kHz: input impedance with secondary
open and shorted; voltage ratio; load regulation from open circuit to 10 Ω.""",
)


def build(k, load=None):
    ck = Circuit("xfmr")
    ck.V("s", "in", "0", ac=1)
    ck.R("w1", "in", "a", 0.5); ck.L("p", "a", "0", 10e-3)
    ck.L("s", "b", "0", 2.5e-3); ck.R("w2", "b", "out", 0.15)
    ck.K("p", "s", k)
    ck.R("L", "out", "0", 1e9 if load is None else load)
    return ck


def run(p):
    f = np.array([1000.0]); w = 2 * pi * 1000
    rows = []
    for k in (0.9, 0.98, 0.998):
        oc = build(k).ac(f); Zoc = 1 / (-oc.i("s")[0]) - 0.5
        sc = build(k, 1e-6).ac(f); Zsc = 1 / (-sc.i("s")[0]) - 0.5
        Loc, Lsc = np.imag(Zoc) / w, np.imag(Zsc) / w
        k_meas = np.sqrt(1 - Lsc / Loc)
        p.compare(f"k = {k}: recovered from open/short tests", k, k_meas, "", tol=0.5)
        p.compare(f"k = {k}: leakage L₁(1−k²)", 10e-3 * (1 - k * k), Lsc, "H", tol=3)
        ratio = np.abs(oc.v("out")[0] / oc.v("a")[0])
        p.compare(f"k = {k}: open-circuit ratio k√(L₂/L₁)", k * 0.5, ratio, "", tol=0.5)
        v_load = np.abs(build(k, 10.0).ac(f).v("out")[0])
        reg = (np.abs(oc.v("out")[0]) - v_load) / v_load * 100
        rows.append((k, k_meas, Lsc, ratio, reg))
        p.metric(f"k = {k}: load regulation (open → 10 Ω)", reg, "%")
    fig, ax = p.fig()
    ks = [r[0] for r in rows]
    ax.semilogy(ks, [r[4] for r in rows], "o-", color=C_MEAS, label="regulation (sim)")
    ax.semilogy(ks, [r[2] / 10e-3 * 100 for r in rows], "s--", color=C_PRED, label="leakage L_sc / L₁ (%)")
    style_axes(ax, "coupling coefficient k", "%", "Tighter coupling → less leakage → better regulation")
    p.save(fig, "coupling", "Regulation is dominated by leakage reactance (plus winding resistance).")
    p.discuss("""The open/short-circuit method recovers k and the leakage inductance exactly as a lab technician would, which confirms the
coupled-inductor model. Leakage L₁(1 − k²) is the key design number: at k = 0.9 it is 19 % of the magnetising inductance and
the output sags badly under load; at k = 0.998 (interleaved windings on a closed core) it is 0.4 % and regulation is set by
winding resistance. Flyback converters (SL-029) show the flip side: leakage energy must be clamped every cycle.""")
