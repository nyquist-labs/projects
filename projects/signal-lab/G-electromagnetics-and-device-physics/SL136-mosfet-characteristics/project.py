from eelab import *

META = dict(
    id="SL-136", title="MOSFET I–V families and threshold-voltage extraction", level="H",
    tools="Physics-based long-channel MOSFET model (EKV-style charge interpolation, mobility degradation, CLM) + standard extraction methods",
    summary="Generate I_D–V_GS and I_D–V_DS families from a physics-based model with known parameters, then extract the "
            "threshold voltage by linear extrapolation, constant-current and gm-maximum methods — and see how each "
            "method's answer differs from the true V_T0.",
    problem="Datasheets quote 'the' threshold voltage, but there are several ways to extract it. How do they compare "
            "when the true value is known?",
    theory=r"""Square-law: $I_D=\frac{\mu C_{ox}W}{2L}(V_{GS}-V_T)^2$ (saturation), $I_D=\mu C_{ox}\frac WL(V_{GS}-V_T)V_{DS}$ (linear, small V_DS). Linear-extrapolation (ELR):
extrapolate I_D(V_GS) at small V_DS from its max-slope point → V_T + V_DS/2. Mobility degradation $\mu=\mu_0/(1+\theta(V_{GS}-V_T))$ bends the curve and
biases ELR. Subthreshold slope $S=nV_T\ln10$ ≈ 60n mV/decade.""",
    method="""Model: EKV interpolation $I=I_s[\ln^2(1+e^{(V_P-V_S)/2V_t})-\ln^2(1+e^{(V_P-V_D)/2V_t})]$, V_P = (V_G − V_T0)/n, n = 1.3, θ = 0.2 V⁻¹, λ = 0.05 V⁻¹, V_T0 = 0.7 V,
μC_ox W/L = 200 µA/V². V_GS sweep 0–3 V at V_DS = 50 mV; families at V_GS = 1–3 V. Extractions: ELR, constant current (100 nA·W/L), √I_D in saturation.""",
)


def ekv(vg, vd, vs=0.0, VT0=0.7, n=1.3, beta=200e-6, theta=0.2, lam=0.05):
    Vt = 0.025852
    vp = (vg - VT0) / n
    Is = 2 * n * beta * Vt**2
    f = lambda u: np.log1p(np.exp(np.clip(u, -60, 60))) ** 2
    mob = 1 / (1 + theta * np.maximum(vg - VT0, 0))
    return Is * mob * (f((vp - vs) / (2 * Vt)) - f((vp - vd) / (2 * Vt))) * (1 + lam * vd)


def run(p):
    VT0 = 0.7
    vg = np.linspace(0, 3, 601)
    Id = ekv(vg, 0.05)
    gm = np.gradient(Id, vg)
    k = np.argmax(gm)
    v_elr = vg[k] - Id[k] / gm[k] - 0.05 / 2
    p.compare("Threshold by linear extrapolation (ELR)", VT0, v_elr, "V", kind="abs")
    icc = 100e-9 * 1.0
    v_cc = np.interp(icc, Id, vg)
    p.compare("Threshold by constant current (100 nA × W/L)", VT0, v_cc, "V", kind="abs")
    Idsat = ekv(vg, 3.0)
    sq = np.sqrt(Idsat); g2 = np.gradient(sq, vg); k2 = np.argmax(g2)
    v_sat = vg[k2] - sq[k2] / g2[k2]
    p.compare("Threshold by √I_D extrapolation in saturation", VT0, v_sat, "V", kind="abs")
    sub = (vg > 0.2) & (vg < 0.5)
    S = 1 / np.polyfit(vg[sub], np.log10(Id[sub]), 1)[0]
    p.compare("Subthreshold slope n·V_T·ln10", 1.3 * 0.025852 * np.log(10), S, "V/dec", tol=5)
    vds = np.linspace(0, 3, 301)
    fig, ax = p.fig(1, 2, w=11)
    for i, v in enumerate((1.0, 1.5, 2.0, 2.5, 3.0)):
        ax[0].plot(vds, ekv(v, vds) * 1e3, color=COLORS[i], label=f"V_GS = {v} V")
    ax[0].plot(vds, 0.5 * 200e-6 / 1.3 * np.maximum(vds * 1.3, 0) ** 2 * 0, alpha=0)
    style_axes(ax[0], "V_DS (V)", "I_D (mA)", "Output characteristics")
    ax[1].semilogy(vg, Id, color=C_MEAS, label="I_D at V_DS = 50 mV")
    for v, lab, c in ((v_elr, "ELR", COLORS[1]), (v_cc, "const. current", COLORS[2]), (v_sat, "√I_D sat.", COLORS[3])):
        ax[1].axvline(v, color=c, ls="--", lw=1, label=f"{lab}: {v:.3f} V")
    ax[1].axvline(VT0, color="black", lw=1, label="true V_T0 = 0.700 V")
    style_axes(ax[1], "V_GS (V)", "I_D (A)", "Transfer curve and extracted thresholds")
    p.save(fig, "mosfet", "Three standard extraction methods give three different 'thresholds' for the same device.")
    p.csv("transfer", vgs=vg, id_lin=Id, id_sat=Idsat)
    p.discuss("""With the true V_T0 known, the extraction methods' systematic biases are visible: ELR lands within tens of mV but is pulled by
mobility degradation (θ lowers the maximum-slope point); the constant-current method depends entirely on the arbitrary
current criterion and here sits below V_T0 because the device already conducts 100 nA in weak inversion; the saturation √I_D
method is biased by the body-effect factor n. None is 'wrong' — each defines threshold differently — which is why datasheets
state the method (usually constant current, e.g. I_D = 250 µA) next to V_GS(th).""")
