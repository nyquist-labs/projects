from eelab import *
from eelab.web import node, page, attach
import scipy.sparse as sp
import scipy.sparse.linalg as spla

META = dict(
    id="SL-202", title="PCB trace width calculator (IPC-2221) vs a thermal model", level="E",
    tools="HTML/JS calculator (IPC-2221 width/current, resistance, drop, loss) + Node harness; own 2-D finite-volume heat-conduction model of a trace in an FR-4 board",
    summary="Current and allowed temperature rise in, trace width out, per IPC-2221 — plus resistance, voltage drop and dissipation. The formula's "
            "temperature rise is then checked against a 2-D thermal simulation of the trace in a board cooled by still air.",
    problem="How wide must a trace be for 3 A, and how much should you trust the 1950s-era curve fit that everyone uses?",
    theory=r"""IPC-2221 fits NBS measurements as $I = k\,ΔT^{0.44}A^{0.725}$ (A in mil², k = 0.048 outer, 0.024 inner). Physically, a long trace dissipates $I^2ρ/(wt)$ per metre and the
heat spreads through the FR-4 to both board surfaces, where still air removes ~10 W/m²K. Because the *board*, not the trace, does most of the cooling,
I expect (i) the outer-layer formula to be of the right order (within ~±40 %) for a typical 1.6 mm board, and (ii) the inner-layer rule (half the current)
to be strongly conservative, because a buried trace spreads heat through the same board with only a thin extra FR-4 resistance.""",
    method="""Model (clearly a model, not a measurement): 60 mm × 1.6 mm FR-4 cross-section (k∥ = 0.8, k⊥ = 0.3 W/mK), 1 oz trace on top (outer) or at mid-depth (inner) as a
high-conductivity strip, still-air convection + radiation h = 10 W/m²K on both faces, infinitely long trace, copper resistivity rising 0.393 %/°C (iterated).
For I = 0.5–10 A, trace width from calc.js for ΔT = 10 °C, then the model's temperature rise.""",
    data="Simulation.",
)

BODY = """<div class="card"><div class="row"><label style="flex:1">Current (A)<input id="i" type="number" value="3" step="any"></label>
<label style="flex:1">Temperature rise (°C)<input id="dt" type="number" value="10" step="any"></label><label style="flex:1">Copper (oz/ft²)<select id="oz"><option>0.5</option><option selected>1</option><option>2</option><option>3</option></select></label>
<label style="flex:1">Trace length (mm)<input id="len" type="number" value="50"></label></div>
<table id="t" style="margin-top:8px"></table><p class="muted">IPC-2221 is a curve fit to old measurements; IPC-2152 (not free) refines it. Inner-layer values here are the conservative 2221 rule.</p></div>"""

JS = r"""const $=id=>document.getElementById(id);
function upd(){const I=+$('i').value,dT=+$('dt').value,oz=+$('oz').value,L=+$('len').value,e=width(I,dT,oz,true),n=width(I,dT,oz,false);
const R=resistance(e.mm,L,oz,20+dT),Rn=resistance(n.mm,L,oz,20+dT);$('t').innerHTML=`<tr><th></th><th class="n">outer layer</th><th class="n">inner layer</th></tr>
<tr><td>Minimum width</td><td class="n big">${e.mm.toFixed(3)} mm</td><td class="n big">${n.mm.toFixed(3)} mm</td></tr>
<tr><td>… in mil</td><td class="n">${e.mil.toFixed(1)}</td><td class="n">${n.mil.toFixed(1)}</td></tr>
<tr><td>Resistance (at ${20+dT} °C)</td><td class="n">${(R*1000).toFixed(2)} mΩ</td><td class="n">${(Rn*1000).toFixed(2)} mΩ</td></tr>
<tr><td>Voltage drop</td><td class="n">${(I*R*1000).toFixed(1)} mV</td><td class="n">${(I*Rn*1000).toFixed(1)} mV</td></tr>
<tr><td>Power loss</td><td class="n">${(I*I*R*1000).toFixed(1)} mW</td><td class="n">${(I*I*Rn*1000).toFixed(1)} mW</td></tr>`;}
document.querySelectorAll('input,select').forEach(e=>e.oninput=upd);upd();"""


def thermal_rise(I, w_mm, external=True, oz=1.0, Wb=60e-3, H=1.6e-3, h=10.0):
    dx, dy = 0.1e-3, 0.05e-3
    nx, ny = int(Wb / dx), int(round(H / dy))
    x = (np.arange(nx) + 0.5) * dx - Wb / 2
    kx = np.full((ny, nx), 0.8); ky = np.full((ny, nx), 0.3)
    row = 0 if external else ny // 2
    t = oz * 35e-6
    on = np.abs(x) <= w_mm * 1e-3 / 2
    kx[row, on] = (390 * t + 0.8 * (dy - t)) / dy          # copper strip lumped into one cell row
    ky[row, on] = 1 / ((t / 390 + (dy - t) / 0.3) / dy)
    idx = lambda j, i: j * nx + i
    N = nx * ny
    rows, cols, vals = [], [], []
    diag = np.zeros(N)
    def link(a, b, g):
        rows.extend([a, b]); cols.extend([b, a]); vals.extend([-g, -g]); diag[a] += g; diag[b] += g
    for j in range(ny):
        for i in range(nx - 1):
            kf = 2 * kx[j, i] * kx[j, i + 1] / (kx[j, i] + kx[j, i + 1])
            link(idx(j, i), idx(j, i + 1), kf * dy / dx)
    for j in range(ny - 1):
        kf = 2 * ky[j] * ky[j + 1] / (ky[j] + ky[j + 1])
        for i in range(nx):
            link(idx(j, i), idx(j + 1, i), kf[i] * dx / dy)
    for i in range(nx):                                   # convection top (j=0) and bottom (j=ny-1)
        for j in (0, ny - 1):
            g = 1 / (1 / (h * dx) + dy / (2 * ky[j, i] * dx)); diag[idx(j, i)] += g
    A = sp.csr_matrix((vals + list(diag), (rows + list(range(N)), cols + list(range(N)))), shape=(N, N))
    lu = spla.splu(A.tocsc())
    dT = 0.0
    for _ in range(6):                                    # resistivity rises with temperature
        rho = 1.72e-8 * (1 + 0.00393 * dT)
        q = I ** 2 * rho / (w_mm * 1e-3 * t)              # W per metre of trace
        src = np.zeros(N); cells = np.flatnonzero(on); src[[idx(row, i) for i in cells]] = q / len(cells)
        T = lu.solve(src)
        dT = T.reshape(ny, nx)[row, on].mean()
    return dT, T.reshape(ny, nx), x


def run(p):
    p.write("web/index.html", page("PCB trace width (IPC-2221)", "Minimum trace width for a current and temperature rise, with resistance and loss.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "IPC-2221 library (tested)")
    js = p.dir / "web" / "calc.js"
    w = node(js, [["width", [3, 10, 1, True]], ["width", [3, 10, 1, False]], ["current", [100, 10, 1, True]]])
    A = (3 / (0.048 * 10 ** 0.44)) ** (1 / 0.725)
    p.compare("3 A, ΔT 10 °C, 1 oz outer: width = A/1.378 mil", A / 1.378, w[0]["mil"], "mil", tol=1e-07)
    p.compare("100 mil 1 oz outer at 10 °C rise: current", 0.048 * 10 ** 0.44 * 137.8 ** 0.725, w[2], "A", tol=1e-07)
    p.compare("Inner vs outer width for the same current = 2^(1/0.725)", 2 ** (1 / 0.725), w[1]["mil"] / w[0]["mil"], "×", tol=1e-07)
    R = node(js, [["resistance", [1.0, 1000, 1, 20]]])[0]
    p.compare("1 mm × 1 m, 1 oz trace at 20 °C (≈ 0.49 Ω)", 1.72e-8 / (1e-3 * 35.0012e-6), R, "Ω", tol=0.1)
    Is = np.array([0.5, 1, 2, 3, 5, 7, 10])
    ext, inn = [], []
    for I in Is:
        we = node(js, [["width", [float(I), 10, 1, True]]])[0]["mm"]; wi = node(js, [["width", [float(I), 10, 1, False]]])[0]["mm"]
        ext.append(thermal_rise(I, we, True)[0]); inn.append(thermal_rise(I, wi, False)[0])
    ext, inn = np.array(ext), np.array(inn)
    p.compare("Outer layer: model ΔT at the IPC width, 3 A (IPC says 10 °C)", 10, np.interp(3, Is, ext), "°C", kind="abs", tol=4)
    p.compare("Inner layer: model ΔT at the IPC width, 3 A (IPC says 10 °C)", 10, np.interp(3, Is, inn), "°C", kind="abs", tol=4)
    p.metric("Outer-layer model ΔT range over 0.5–10 A", f"{ext.min():.1f} – {ext.max():.1f}", "°C")
    fig, ax = p.fig(1, 2, w=11)
    ax[0].plot(Is, ext, "o-", color=C_MEAS, label="outer layer (model)"); ax[0].plot(Is, inn, "s-", color=COLORS[1], label="inner layer (model)")
    ax[0].axhline(10, ls="--", color=C_PRED, label="IPC-2221 design rise")
    style_axes(ax[0], "current (A)", "temperature rise at IPC width (°C)", "Is IPC-2221 conservative?")
    dT, T, x = thermal_rise(3, node(js, [["width", [3, 10, 1, True]]])[0]["mm"], True)
    im = ax[1].imshow(T, aspect="auto", extent=[x[0] * 1e3, x[-1] * 1e3, 1.6, 0], cmap="inferno")
    ax[1].set_xlim(-15, 15); fig.colorbar(im, ax=ax[1], label="ΔT (°C)")
    ax[1].set_xlabel("x (mm)"); ax[1].set_ylabel("depth (mm)"); ax[1].set_title("3 A outer trace: heat spreads into the board", loc="left", fontsize=10); ax[1].grid(False)
    p.save(fig, "thermal", "Temperature rise predicted by a 2-D board model at the IPC-2221 width; the board, not the trace, does the cooling.")
    p.csv("model", current_A=Is, dT_outer_C=ext, dT_inner_C=inn)
    p.discuss(f"""The calculator reproduces the IPC-2221 formula exactly (including the 2^(1/0.725) ≈ 2.6× wider inner-layer traces). The thermal model is the
interesting part: for outer-layer traces at the IPC width, it gives {ext.min():.0f}–{ext.max():.0f} °C instead of 10 °C across 0.5–10 A — the right order of magnitude, conservative at low current but
*optimistic* at high current. The reason is visible in the formula: at the IPC width the heat per metre of trace, I²ρ/(wt), still grows as
≈ I^0.62, while the 60 mm-wide board that ultimately sheds it to the air stays the same size; IPC's curve fit implicitly assumes the test boards
of its original measurements. For inner layers the model shows the IPC-2221
rule is far more conservative ({np.interp(3, Is, inn):.1f} °C at 3 A): halving the constant was an arbitrary safety factor, which is exactly what
IPC-2152's later measurements found. Caveats matter here: the model assumes an isolated board in still air, an infinitely long trace (no heat-sinking
into pads and planes) and no neighbouring heat sources; nearby copper planes cool traces a lot, enclosures heat them. Use the tool's numbers as a
starting point and the thermal picture as the reason to add copper pours and vias for high-current paths.""")
# tol-convention: relative tolerances are in percent
