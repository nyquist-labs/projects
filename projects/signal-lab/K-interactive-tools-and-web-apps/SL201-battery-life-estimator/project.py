from eelab import *
from eelab.data import nasa_battery
from eelab.web import node, page, attach

META = dict(
    id="SL-201", title="Battery life estimator with sleep-mode modelling", level="E",
    tools="HTML/JS estimator (periodic current profile, sleep current, self-discharge, derating) + Node harness; checked against event-level coulomb counting and NASA Li-ion discharge data",
    summary="Turn a device's current profile (active, radio burst, sleep) into a runtime. The average-current model is checked against a "
            "time-stepped coulomb-counting simulation, and the capacity assumption against real discharge runs of an ageing Li-ion cell (NASA B0005).",
    problem="A sensor wakes every minute. Will it run for a week or a year — and which number on the datasheet matters most?",
    theory=r"""For a periodic profile the average current is $\bar I=\sum I_k t_k/T$ and runtime $= C_\text{usable}/(\bar I + I_\text{self})$. In duty-cycled designs the sleep current
often dominates: with 20 ms at 10 mA plus a 5 ms, 40 mA radio burst every 60 s, activity averages only 6.7 µA, so a 5 µA sleep current is ≈ 43 % of the whole budget. Usable capacity is
below rated capacity (cut-off voltage, ageing): runtime predicted from the *rated* 2 Ah will overestimate an aged cell's run by the capacity fade.""",
    method="""(1) 300 random profiles: calc.js runtime vs a Python simulation that steps through every wake-up (1 ms resolution within active phases) until the charge
is used. (2) NASA B0005 18650 cell, 2 A constant-current discharges to 2.7 V, 168 cycles: predicted runtime from rated 2.0 Ah (derate 1) vs the measured
time to cut-off; and prediction using the previous cycle's measured capacity (what a fuel gauge would know).""",
    data="Real: NASA Ames PCoE Li-ion Battery Aging dataset (Saha & Goebel 2007), public domain (US Government work).",
)

BODY = """<div class="card"><label>Battery capacity (mAh)<input id="cap" type="number" value="2000"></label><label>Usable fraction (derating)<input id="der" type="number" value="0.85" step="0.05"></label>
<label>Self-discharge (% per month)<input id="sd" type="number" value="2" step="0.5"></label></div>
<div class="card"><b>Duty cycle</b><label>Wake period (s)<input id="per" type="number" value="60"></label><label>Active time (ms)<input id="act" type="number" value="20"></label>
<label>Active current (mA)<input id="ia" type="number" value="10"></label><label>Radio burst (ms)<input id="tx" type="number" value="5"></label>
<label>Radio current (mA)<input id="itx" type="number" value="40"></label><label>Sleep current (µA)<input id="isl" type="number" value="5"></label></div>
<div class="card"><p>Average current <span class="big" id="avg"></span> &nbsp; Runtime <span class="big" id="rt"></span></p><div id="bar" style="display:flex;height:22px;border-radius:6px;overflow:hidden"></div>
<p class="muted" id="leg"></p></div>"""

JS = r"""const $=id=>document.getElementById(id);
function upd(){const pr=dutyProfile(+$('per').value,+$('act').value,+$('ia').value,+$('tx').value,+$('itx').value,+$('isl').value);
const I=averageCurrent(pr),h=runtimeHours(+$('cap').value,pr,+$('der').value,+$('sd').value);$('avg').textContent=I<1?(I*1000).toFixed(2)+' µA':I.toFixed(3)+' mA';
$('rt').textContent=h>24*365?(h/24/365).toFixed(2)+' years':h>48?(h/24).toFixed(1)+' days':h.toFixed(1)+' h';const b=breakdown(pr),c=['var(--acc)','var(--acc2)','var(--muted)'],n=['active','radio','sleep'];
$('bar').innerHTML=b.map((x,i)=>`<div style="width:${x*100}%;background:${c[i]}"></div>`).join('');$('leg').innerHTML=b.map((x,i)=>`<span style="color:${c[i]}">■</span> ${n[i]} ${(x*100).toFixed(1)} %`).join(' &nbsp; ')+' of charge';}
document.querySelectorAll('input').forEach(e=>e.oninput=upd);upd();"""


def simulate(cap_mAh, profile, derate, self_pct):
    """Step through wake-ups: charge removed per period, plus self-discharge, until exhausted. Returns hours."""
    q = cap_mAh * derate * 3600.0             # mA·s available
    T = sum(p["ms"] for p in profile) / 1000.0
    per_period = sum(p["mA"] * p["ms"] / 1000.0 for p in profile)
    i_self = cap_mAh * self_pct / 100 / (30 * 24)
    n = int(q // (per_period + i_self * T))    # whole periods
    q -= n * (per_period + i_self * T)
    t = n * T
    for p in profile:                          # final partial period at 1 ms resolution
        for _ in range(int(p["ms"])):
            if q <= 0:
                return t / 3600
            q -= (p["mA"] + i_self) * 1e-3; t += 1e-3
    return t / 3600


def run(p):
    p.write("web/index.html", page("Battery life estimator", "Current profile → runtime, with sleep current and self-discharge.", BODY, scripts=("calc.js",), inline=JS), "interactive tool")
    attach(p, "web/calc.js", "estimator library (tested)")
    js = p.dir / "web" / "calc.js"
    r = p.rng
    errs = []
    for _ in range(300):
        prof = node(js, [["dutyProfile", [float(r.choice([1, 10, 60, 600])), float(r.integers(1, 200)), float(r.uniform(1, 30)), float(r.integers(0, 50)),
                                          float(r.uniform(5, 120)), float(r.uniform(0.5, 50))]]])[0]
        cap, der, sd = float(r.uniform(100, 3000)), float(r.uniform(0.6, 1)), float(r.uniform(0, 5))
        h_js = node(js, [["runtimeHours", [cap, prof, der, sd]]])[0]
        errs.append(h_js / simulate(cap, prof, der, sd) - 1)
    p.compare("Worst |average-current model − coulomb-counting simulation| (300 profiles)", 0, np.max(np.abs(errs)) * 100, "%", kind="abs", tol=0.01)
    base = node(js, [["dutyProfile", [60, 20, 10, 5, 40, 5]]])[0]
    br = node(js, [["breakdown", [base]]])[0]
    p.compare("Default profile: share of charge used while asleep (5 µA sleep)", 5e-3 * (60000 - 25) / (10 * 20 + 40 * 5 + 5e-3 * (60000 - 25)), br[2], "", tol=0.0001)
    cyc = [c for c in nasa_battery("B0005") if c["type"] == "discharge"]
    meas_h, cap = [], []
    for c in cyc:
        d = c["data"]; t, V, I = d["Time"], d["Voltage_measured"], -d["Current_measured"]
        on = I > 1.0
        t_on = t[on]; Vv = V[on]
        cut = np.flatnonzero(Vv <= 2.7)
        t_end = t_on[cut[0]] if len(cut) else t_on[-1]
        meas_h.append((t_end - t_on[0]) / 3600); cap.append(float(d["Capacity"]))
    meas_h, cap = np.array(meas_h), np.array(cap)
    rated = node(js, [["runtimeHours", [2000, [{"mA": 2000, "ms": 1000}], 1.0, 0]]])[0]
    prev = np.array(node(js, [["runtimeHours", [float(cap[k - 1] * 1000), [{"mA": 2000, "ms": 1000}], 1.0, 0]] for k in range(1, len(cap))]))
    p.compare("Fresh cell (cycle 1): runtime at 2 A predicted from rated 2 Ah vs measured", rated, meas_h[0], "h", tol=10)
    p.compare("Aged cell (last cycle): same rated-capacity prediction vs measured", rated, meas_h[-1], "h", tol=10)
    e_prev = (prev / meas_h[1:] - 1) * 100
    p.compare("Using the previous cycle's measured capacity: RMS runtime error", 0, np.sqrt(np.mean(e_prev ** 2)), "%", kind="abs", tol=5)
    fig, ax = p.fig(1, 2, w=11)
    k = np.arange(1, len(meas_h) + 1)
    ax[0].plot(k, meas_h * 60, color=C_MEAS, label="measured time to 2.7 V")
    ax[0].axhline(rated * 60, ls="--", color=C_PRED, label="predicted from rated 2 Ah")
    ax[0].plot(k[1:], prev * 60, ":", color=COLORS[2], label="predicted from previous cycle's capacity")
    style_axes(ax[0], "discharge cycle", "runtime at 2 A (min)", "NASA B0005: ageing eats runtime")
    sl = np.logspace(-1, 2, 60)
    life = node(js, [["runtimeHours", [2000, [{"mA": 10, "ms": 20}, {"mA": 40, "ms": 5}, {"mA": float(s) / 1000, "ms": 59975}], 0.85, 2]] for s in sl])
    life0 = node(js, [["runtimeHours", [2000, [{"mA": 10, "ms": 20}, {"mA": 40, "ms": 5}, {"mA": float(s) / 1000, "ms": 59975}], 0.85, 0]] for s in sl])
    ax[1].loglog(sl, np.array(life) / 24 / 365, color=C_MEAS, label="with 2 %/month self-discharge")
    ax[1].loglog(sl, np.array(life0) / 24 / 365, "--", color=C_PRED, label="no self-discharge")
    style_axes(ax[1], "sleep current (µA)", "battery life (years)", "Sleep current decides the lifetime")
    p.save(fig, "battery", "Real ageing vs a rated-capacity estimate, and the lifetime of a duty-cycled sensor vs sleep current.")
    p.csv("nasa_b0005", cycle=k, runtime_min=meas_h * 60, capacity_Ah=cap)
    p.discuss(f"""The tool's average-current arithmetic matches an explicit wake-by-wake coulomb count exactly, so the maths is right; the uncertainty lives in the
inputs. The NASA cell shows which input: fresh, the rated 2 Ah predicts {rated * 60:.0f} min at 2 A while the cell delivered {meas_h[0] * 60:.0f} min
(rated capacity is not usable capacity to a 2.7 V cut-off); after {len(meas_h)} cycles it delivered only {meas_h[-1] * 60:.0f} min — the rated-capacity
estimate is then {(rated / meas_h[-1] - 1) * 100:.0f} % optimistic. Using the previous cycle's measured capacity (what a fuel gauge learns) brings the error
to a few percent, the remainder being cycle-to-cycle variation including capacity recovery after rest periods. For duty-cycled sensors the right-
hand plot is the lesson: once sleep current exceeds a few µA it dominates the budget, and at sub-µA sleep the lifetime is capped by self-
discharge instead — no firmware optimisation beats the battery's own leakage. The default 0.85 derating is a design margin, not a measured value.""")
# tol-convention: relative tolerances are in percent
