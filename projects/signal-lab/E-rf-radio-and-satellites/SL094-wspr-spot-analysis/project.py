from eelab import *
from eelab.data import wspr

META = dict(
    id="SL-094", title="Global WSPR spot statistics: distance by band", level="M",
    tools="wspr.live public database queries, NumPy statistics",
    summary="Mine one week of the worldwide WSPR beacon network (millions of real reception reports) for how "
            "far each amateur band reaches, and compare the distance distributions with single-hop skywave "
            "geometry.",
    problem="Which HF bands reach farthest, and does the distance distribution show the ionosphere's single-hop "
            "skip distance?",
    theory=r"""One F-layer hop from height h ≈ 300 km at elevation angle Δ spans ground distance
$D = 2R_E\left[\frac{\pi}{2}-\Delta-\arcsin\!\left(\frac{R_E\cos\Delta}{R_E+h}\right)\right]$ — about 4,000 km at Δ = 0°, i.e. the
maximum single-hop distance. Low bands (160–40 m) at night and high bands in the day both need multi-hop for DX, so
spot-distance histograms should show a shoulder near 4,000 km and a long tail. Low bands are dominated by
short-range (NVIS / ground-wave) spots, so their median distance should be smaller.""",
    method="""All spots 2026-09-01…07 per band (80 m to 10 m): count, median and 90th-percentile distance, and a histogram of distance
in 250 km bins for 20 m (server-side aggregation). The single-hop limit computed from the formula at h = 300 km.""",
    data="Real: WSPRnet spots via wspr.live.",
)


def run(p):
    q1 = """SELECT band, count() AS n, quantile(0.5)(distance) AS d50, quantile(0.9)(distance) AS d90
FROM wspr.rx WHERE time >= '2026-09-01' AND time < '2026-09-08' AND band IN (3, 7, 10, 14, 18, 21, 24, 28)
GROUP BY band ORDER BY band"""
    q2 = """SELECT intDiv(distance, 250) * 250 AS dbin, count() AS n
FROM wspr.rx WHERE time >= '2026-09-01' AND time < '2026-09-08' AND band = 14 AND distance < 20000
GROUP BY dbin ORDER BY dbin"""
    s = wspr(q1); h = wspr(q2)
    RE, hh = 6371.0, 300.0
    Dmax = 2 * RE * (pi / 2 - np.arcsin(RE / (RE + hh)))
    p.metric("Spots analysed (1 week, 80–10 m)", int(s.n.sum()))
    names = {3: "80 m", 7: "40 m", 10: "30 m", 14: "20 m", 18: "17 m", 21: "15 m", 24: "12 m", 28: "10 m"}
    for _, r in s.iterrows():
        p.metric(f"{names[int(r.band)]}: median / 90th-percentile distance", f"{r.d50:.0f} km / {r.d90:.0f} km", "", f"{int(r.n):,} spots")
    d20 = h.dbin.values + 125; n20 = h.n.values
    # knee: steepest drop in the smoothed histogram between 2,000 and 7,000 km
    sm = np.convolve(n20, np.ones(3) / 3, "same")
    sel = (d20 > 2000) & (d20 < 7000)
    knee = d20[sel][np.argmin(np.gradient(np.log(sm[sel] + 1)))]
    p.compare("20 m: steepest fall in spot density (single-hop limit, h = 300 km)", Dmax, knee, "km", tol=35)
    low = s[s.band <= 7].d50.mean(); high = s[s.band >= 14].d50.mean()
    p.compare("Median distance ratio, high bands (≥20 m) / low bands (≤40 m)", 2.0, high / low, "×", kind="abs",
              note="expectation: high bands reach roughly twice as far")
    fig, ax = p.fig(1, 2)
    ax[0].bar([names[int(b)] for b in s.band], s.d50, color=C_MEAS, label="median")
    ax[0].plot([names[int(b)] for b in s.band], s.d90, "o", color=C_PRED, label="90th percentile")
    style_axes(ax[0], "band", "distance (km)", "Reach by band")
    ax[1].semilogy(d20, n20, color=C_MEAS, label="20 m spots")
    ax[1].axvline(Dmax, color=C_PRED, ls="--", label=f"single-hop limit {Dmax:.0f} km")
    style_axes(ax[1], "distance (km)", "spots per 250 km", "20 m distance distribution")
    p.save(fig, "distance_by_band", "Higher bands reach farther; the 20 m histogram falls off beyond one hop.")
    p.csv_df("band_stats", s); p.csv_df("dist_hist_20m", h)
    p.discuss("""Median reach grows with frequency from 80 m to the 20–10 m bands, and the 20 m histogram's steep fall-off sits near the
single-hop limit of ~4,000 km for a 300 km F-layer. Beyond it the density drops by orders of magnitude but never
to zero — multi-hop paths carry signals around the globe. Spot counts are biased by where receivers are (Europe and
North America dominate), so the histogram shape partly reflects station geography, not just the ionosphere.""")
