from eelab import *

META = dict(
    id="SL-134", title="RF shielding effectiveness: Schelkunoff vs exact", level="M",
    tools="Exact plane-wave transmission through a conducting slab (ABCD / transmission-line model), Schelkunoff's A + R + B approximation",
    summary="Compute the shielding effectiveness of copper, aluminium and steel foils from 10 kHz to 1 GHz exactly, "
            "compare with Schelkunoff's absorption + reflection + multiple-reflection formula, and find where thin "
            "foils fail.",
    problem="How much does a metal sheet attenuate a radio wave, and why does a thin copper foil shield well at 100 MHz "
            "but poorly at 50 kHz?",
    theory=r"""Plane wave (η₀) through a slab of thickness t with intrinsic impedance $\eta_s=\sqrt{j\omega\mu/\sigma}$ and propagation constant γ = (1+j)/δ.
Schelkunoff: $SE=A+R+B$ with $A=8.686\,t/\delta$, $R=20\log_{10}\frac{|\eta_0|}{4|\eta_s|}$, and a correction B that becomes large and negative
when t ≲ δ (multiple internal reflections). The exact result follows from the slab's transmission-line ABCD matrix.""",
    method="""Copper (σ = 5.8e7, μ_r = 1), aluminium (3.5e7, 1), steel (1e7, μ_r = 200); t = 35 µm (1 oz PCB copper) and 0.5 mm. SE_exact = 20 log|E_inc/E_trans|
from $T=\frac{2\eta_0}{(A\eta_0+B+C\eta_0^2+D\eta_0)}$ with the slab ABCD; A + R + B computed separately.""",
)


def se_exact(f, t, sig, mur):
    w = 2 * pi * f; mu = 4e-7 * pi * mur; eta0 = 376.73
    gam = np.sqrt(1j * w * mu * sig); eta = np.sqrt(1j * w * mu / sig)
    A = np.cosh(gam * t); B = eta * np.sinh(gam * t); C = np.sinh(gam * t) / eta; D = A
    T = 2 * eta0 / (A * eta0 + B + C * eta0**2 + D * eta0)
    return -20 * np.log10(np.abs(T))


def se_schelk(f, t, sig, mur):
    w = 2 * pi * f; mu = 4e-7 * pi * mur; eta0 = 376.73
    delta = np.sqrt(2 / (w * mu * sig)); eta = np.abs(np.sqrt(1j * w * mu / sig))
    A = 8.686 * t / delta
    R = 20 * np.log10(eta0 / (4 * eta))
    g = ((eta0 - eta) / (eta0 + eta)) ** 2
    Bc = 20 * np.log10(np.abs(1 - g * np.exp(-2 * (1 + 1j) * t / delta)))
    return A + R + Bc, A, R, Bc


def run(p):
    f = np.logspace(4, 9, 101)
    fig, ax = p.fig(1, 2, w=11)
    for i, (nm, sig, mur) in enumerate((("copper", 5.8e7, 1), ("aluminium", 3.5e7, 1), ("steel", 1e7, 200))):
        for ls, t in (("-", 35e-6), (":", 0.5e-3)):
            ex = se_exact(f, t, sig, mur)
            sc, A, R, B = se_schelk(f, t, sig, mur)
            if nm == "copper" and t == 35e-6:
                for ff in (1e5, 1e8):
                    k = np.argmin(abs(f - ff))
                    p.compare(f"Copper 35 µm at {ff:.0e} Hz: Schelkunoff A+R+B vs exact", sc[k], ex[k], "dB", kind="abs")
                p.metric("Copper 35 µm: worst |A+R (no B) − exact|", np.max(np.abs(A + R - ex)), "dB", "B correction is essential for thin foils")
            ax[0].semilogx(f, ex, ls, color=COLORS[i], label=f"{nm} {t*1e6:.0f} µm" if ls == "-" else f"{nm} {t*1e3:.1f} mm")
    style_axes(ax[0], "frequency (Hz)", "shielding effectiveness (dB)", "Exact SE for plane waves")
    sc, A, R, B = se_schelk(f, 35e-6, 5.8e7, 1)
    ax[1].semilogx(f, A, color=COLORS[0], label="absorption A"); ax[1].semilogx(f, R, color=COLORS[1], label="reflection R")
    ax[1].semilogx(f, B, color=COLORS[2], label="re-reflection B"); ax[1].semilogx(f, se_exact(f, 35e-6, 5.8e7, 1), "--", color="black", lw=1, label="exact total")
    style_axes(ax[1], "frequency (Hz)", "dB", "Copper 35 µm: Schelkunoff terms")
    p.save(fig, "shielding", "Reflection dominates at low frequency; absorption takes over once the foil is several skin depths thick.")
    p.csv("se_copper_35um", f_hz=f, exact_db=se_exact(f, 35e-6, 5.8e7, 1), A=A, R=R, B=B)
    p.discuss("""With the multiple-reflection correction B included, Schelkunoff's decomposition agrees with the exact slab solution to a
fraction of a dB — it is in fact exact for plane waves once B is computed with complex values. Dropping B (as quick
calculators often do) overestimates thin-foil shielding by tens of dB at low frequency, where the 35 µm copper is thinner
than a skin depth. Plane waves are the easy case: near-field magnetic sources at low frequency are much harder to shield
because R becomes small, which is why steel (high μ) beats copper there.""")
