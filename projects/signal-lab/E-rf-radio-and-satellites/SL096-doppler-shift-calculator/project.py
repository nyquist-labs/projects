from eelab import *
from eelab.data import celestrak_tle, orbit_tools
from datetime import datetime, timedelta, timezone

META = dict(
    id="SL-096", title="Satellite Doppler shift through a pass", level="M",
    tools="SGP4 with a live CelesTrak TLE, analytic circular-orbit Doppler model",
    summary="Compute the Doppler curve of the ISS's 437.8 MHz downlink over a ground station from SGP4 range-rate, "
            "and check the maximum shift and the steepest slope against a closed-form flat-geometry model.",
    problem="A satellite at 7.7 km/s shifts a UHF signal by kilohertz. How big is the shift, how fast does it "
            "change at closest approach, and can a simple formula predict both?",
    theory=r"""$\Delta f = -f_0\,\dot R/c$. Maximum when the satellite is near the horizon: $|\dot R|_{max}\approx v\cos\theta_h$ with
$\cos\theta_h = R_E/(R_E+h)$ (line of sight tangent to the Earth), so $\Delta f_{max}\approx f_0 v R_E/[c(R_E+h)]$. At closest
approach the slope is steepest: $|d\Delta f/dt|_{max}=\frac{f_0v^2}{c\,R_{min}}$ (straight-line pass approximation).""",
    method="""ISS TLE from CelesTrak (fetched at run time), ground station at 51.48° N, 0.0° E. Next pass with max elevation > 30° found by 10-s
search; range-rate and Doppler at 1-s resolution; orbital speed v and minimum range R_min taken from SGP4 for the
analytic formulas.""",
    data="Real: current ISS two-line elements from CelesTrak (propagated with SGP4).",
)


def run(p):
    Satrec, topo = orbit_tools()
    name, l1, l2 = celestrak_tle(25544)
    sat = Satrec.twoline2rv(l1, l2)
    lat, lon = 51.48, 0.0
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=sat.jdsatepoch + sat.jdsatepochF - 2451544.5)
    t = epoch.replace(tzinfo=None)
    best = None
    for k in range(0, 2 * 86400, 10):
        tt = t + timedelta(seconds=k)
        r, el, az, rr, pos = topo(sat, tt, lat, lon)
        if el > 30:
            best = tt; break
    if best is None:
        raise RuntimeError("no pass found")
    ts, R, E, RR = [], [], [], []
    start = best - timedelta(minutes=8)
    for k in range(0, 16 * 60):
        tt = start + timedelta(seconds=k)
        r, el, az, rr, pos = topo(sat, tt, lat, lon)
        ts.append(k); R.append(r); E.append(el); RR.append(rr)
    ts, R, E, RR = map(np.array, (ts, R, E, RR))
    vis = E > 0
    f0, c = 437.8e6, 299792.458
    dop = -f0 * RR / c
    RE = 6378.137
    h = np.linalg.norm(topo(sat, best, lat, lon)[4]) - RE
    v = np.sqrt(398600.4418 / (RE + h))
    pred_max = f0 * v * RE / (c * (RE + h))
    p.compare("Max Doppler shift at horizon", pred_max, np.max(np.abs(dop[vis])), "Hz", tol=10)
    slope = np.max(np.abs(np.gradient(dop, ts)))
    p.compare("Steepest Doppler slope at closest approach", f0 * v**2 / (c * R[vis].min()), slope, "Hz/s", tol=15)
    p.metric("Pass start (UTC)", start.isoformat() + "Z", "", f"max elevation {E.max():.1f}°")
    p.metric("TLE used", f"{l1[18:32]} (epoch day)")
    fig, ax = p.fig(2, 1, h=6, sharex=True)
    ax[0].plot(ts[vis] / 60, E[vis], color=COLORS[2])
    style_axes(ax[0], None, "elevation (°)", f"ISS pass over 51.5° N ({best:%Y-%m-%d %H:%M} UTC)", legend=False)
    ax[1].plot(ts[vis] / 60, dop[vis] / 1e3, color=C_MEAS, label="SGP4 range-rate × f₀/c")
    ax[1].axhline(pred_max / 1e3, color=C_PRED, ls="--", lw=1, label="analytic ±Δf_max"); ax[1].axhline(-pred_max / 1e3, color=C_PRED, ls="--", lw=1)
    style_axes(ax[1], "minutes", "Doppler at 437.8 MHz (kHz)")
    p.save(fig, "doppler", "The S-shaped Doppler curve: largest near the horizon, steepest at closest approach.")
    p.csv("pass", t_s=ts, range_km=R, elevation_deg=E, range_rate_km_s=RR, doppler_hz=dop)
    p.discuss("""The analytic horizon formula predicts the ±10 kHz extremes within a few percent — the residual is because the pass does not
start exactly at the horizon-tangent geometry and the orbit is slightly eccentric. The closest-approach slope formula
assumes a straight-line pass and a stationary observer; Earth rotation and the curved track change it by a few percent.
In practice a receiver must retune by ~10 kHz over a pass and by up to ~100 Hz/s near culmination, which is why SatNOGS
stations drive their radios from exactly this kind of SGP4 prediction.""")
