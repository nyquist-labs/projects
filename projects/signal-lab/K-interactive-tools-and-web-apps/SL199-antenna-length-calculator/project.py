from eelab import *
from eelab.nec import solve
from eelab.web import node, page, attach

META = dict(
    id="SL-199", title="Antenna length calculator — and when the 0.95 rule is right", level="E",
    tools="HTML/JS calculator (dipole, monopole, 5/8 λ, loop, 3-element Yagi, coax stub) + Node harness; method-of-moments solver (PWS-Galerkin) for the resonant length vs wire thickness",
    summary="Frequency in, dimensions out for common antennas. The classic 'multiply λ/2 by 0.95' shortening rule is then tested with a "
            "method-of-moments simulation of dipoles of different wire thickness to show where it holds.",
    problem="Every ham knows '468 / f(MHz) feet'. Where does the 0.95 come from, and does it depend on the wire?",
    theory=r"""A half-wave dipole resonates (X_in = 0) slightly shorter than λ/2 because of end effects and the finite wire radius a. Thin-wire theory (Hallén) gives a
shortening that grows with thickness through $Ω = 2\ln(L/a)$: very thin wires resonate near 0.49 λ, typical wire antennas (a/λ ≈ 10⁻⁴–10⁻³) near 0.47–0.48 λ,
fat elements shorter still. The 0.95 rule (0.475 λ) should therefore be accurate to ~1–2 % for ordinary wire and err for very thin/fat conductors.
At resonance R_in ≈ 70 Ω (less than the 73 Ω of the exactly-λ/2 dipole).""",
    method="""calc.js outputs checked against closed-form values. MoM: centre-fed dipole, 41 segments (fewer for fat wires so that each segment is ≥ 4 radii long — the thin-wire kernel's validity limit; a first run ignoring this gave a nonsensical 0.483 λ for the fattest wire), radius a/λ = 10⁻⁵ … 10⁻², length swept 0.44–0.50 λ; resonant length from the X_in = 0
crossing; compared with the 0.95 rule. Example: 2 m band (146 MHz) with 2 mm wire.""",
    data="Simulation (own MoM solver, validated in SL-128/SL-135).",
)

BODY = """<div class="card"><div class="row"><label style="flex:1">Frequency (MHz)<input id="f" type="number" value="146" step="any"></label>
<label style="flex:1">End-effect factor k<input id="k" type="number" value="0.95" step="0.005"></label><label style="flex:1">Coax velocity factor<input id="vf" type="number" value="0.66" step="0.01"></label></div>
<p>Wavelength λ = <span class="big" id="lam"></span></p><table id="t"></table>
<p class="muted">k ≈ 0.95 suits ordinary wire (diameter ~1/2000 λ). Thicker elements need smaller k — see this project's README for the simulation.</p></div>"""

JS = r"""const $=id=>document.getElementById(id);const u=m=>m>=1?m.toFixed(3)+' m':(m*100).toFixed(1)+' cm';
function upd(){const f=+$('f').value*1e6,k=+$('k').value,d=dipole(f,k),y=yagi3(f);$('lam').textContent=u(wavelength(f));
$('t').innerHTML=[["Half-wave dipole — total",u(d.total)],["Half-wave dipole — each leg",u(d.leg)],["Quarter-wave monopole / ground plane",u(monopole(f,k).height)],
["5/8-λ vertical",u(fiveEighths(f,k).height)],["Full-wave loop circumference",u(loop(f).circumference)],["Yagi reflector / driven / director",`${u(y.reflector)} / ${u(y.driven)} / ${u(y.director)}`],
["Yagi element spacing",u(y.spacing)],["λ/4 coax stub (VF "+$('vf').value+")",u(coaxStub(f,+$('vf').value).quarterWave)]].map(r=>`<tr><td>${r[0]}</td><td class="n">${r[1]}</td></tr>`).join('');}
document.querySelectorAll('input').forEach(e=>e.oninput=upd);upd();"""


def resonant(a_lam):
    Ls = np.linspace(0.44, 0.50, 13)
    X, R = [], []
    nseg = int(min(41, 0.47 / (4 * a_lam))) | 1          # thin-wire kernel needs segments ≳ 4 radii long
    for L in Ls:
        _, Z = solve([(0.0, L, True)], lam=1.0, nseg=nseg, radius=a_lam)
        X.append(Z.imag); R.append(Z.real)
    X, R = np.array(X), np.array(R)
    i = np.flatnonzero(np.diff(np.sign(X)))[0]
    Lr = Ls[i] - X[i] * (Ls[i + 1] - Ls[i]) / (X[i + 1] - X[i])
    return Lr, np.interp(Lr, Ls, R), Ls, X


def run(p):
    p.write("web/index.html", page("Antenna length calculator", "Frequency to dimensions for common antennas.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "calculation library (tested)")
    js = p.dir / "web" / "calc.js"
    f = 146e6; lam = 299792458 / f
    d, m, y = node(js, [["dipole", [f]], ["monopole", [f]], ["yagi3", [f]]])
    p.compare("146 MHz dipole total length (0.95·λ/2)", 0.95 * lam / 2, d["total"], "m", tol=1e-07)
    p.compare("Classic '468/f(MHz) ft' formula vs 0.95·λ/2 (same rule in feet)", 468 / 146 * 0.3048, d["total"], "m", tol=0.5)
    radii = np.logspace(-5, -2, 7)
    res = [resonant(a) for a in radii]
    Lr = np.array([r[0] for r in res]); Rr = np.array([r[1] for r in res])
    a_ex = 1e-3 / lam
    Lex, Rex, _, _ = resonant(a_ex)
    p.compare("2 mm wire at 146 MHz: MoM resonant length vs 0.95 rule", 0.475, Lex, "λ", tol=2)
    p.compare("Resistance at resonance (≈ 70 Ω)", 70, Rex, "Ω", tol=5)
    p.metric("Resonant length for very thin wire (a/λ = 10⁻⁵)", Lr[0], "λ")
    p.metric("Resonant length for fat element (a/λ = 10⁻²)", Lr[-1], "λ")
    fine = np.logspace(-5, -2, 60); Lf = np.interp(np.log(fine), np.log(radii), Lr); ok = np.abs(Lf / 0.475 - 1) < 0.01
    p.metric("a/λ range where the 0.95 rule is within ±1 % (interpolated)", f"{fine[ok].min():.1e} – {fine[ok].max():.1e}", "")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].semilogx(radii, Lr, "o-", color=C_MEAS, label="MoM resonant length")
    ax[0].axhline(0.475, ls="--", color=C_PRED, label="0.95 × λ/2 rule"); ax[0].axhline(0.5, ls=":", color="gray", label="λ/2")
    ax[0].axvline(a_ex, color=COLORS[7], lw=1); ax[0].text(a_ex * 1.1, 0.455, "2 mm wire\n@146 MHz", fontsize=8)
    style_axes(ax[0], "wire radius a/λ", "resonant length (λ)", "Fatter wires resonate shorter")
    _, _, Ls, X = resonant(a_ex)
    ax[1].plot(Ls, X, "o-", color=C_MEAS); ax[1].axhline(0, color="gray", lw=.8)
    style_axes(ax[1], "dipole length (λ)", "input reactance X (Ω)", "Finding resonance (2 mm wire)", legend=False)
    p.save(fig, "resonance", "Resonant dipole length vs wire thickness from the MoM solver, against the 0.95 rule.")
    p.csv("resonance", a_over_lambda=radii, resonant_length_lambda=Lr, R_at_resonance=Rr)
    p.discuss(f"""The calculator reproduces the '468/f' rule (they are the same number in different units). The MoM sweep shows why the rule works for ordinary wire:
at a/λ ≈ 5×10⁻⁴ (2 mm wire on 2 m) the dipole resonates at {Lex:.3f} λ, close to 0.475 λ. It is not a constant, though — very thin wires resonate
near {Lr[0]:.3f} λ and fat elements (tubing on HF/VHF Yagis, a/λ ≈ 10⁻²) much shorter at {Lr[-1]:.3f} λ, which is why the tool exposes k and warns
about thickness. Real antennas also shorten with insulation (dielectric loading) and height above ground, so the practical recipe remains: cut
long, measure the SWR minimum, trim.""")
# tol-convention: relative tolerances are in percent
