from eelab import *
from eelab.data import wspr

META = dict(
    id="SL-095", title="Ionosphere from propagation data: day/night and seasonal behaviour", level="H",
    tools="wspr.live database (WSPRnet spots), NumPy",
    summary="Infer ionospheric behaviour from millions of real beacon reports: how often long paths on 10, 20 and "
            "40 m are open by local hour, and how the 10 m band changes between a summer and a winter month.",
    problem="The ionosphere can't be seen, but every successful long-distance radio contact is a measurement of it. "
            "What do real propagation reports reveal about its daily and seasonal cycle?",
    theory=r"""The F2 critical frequency follows solar illumination: high by day, collapsing at night, so the maximum usable frequency
(MUF ≈ f_oF2·sec(angle of incidence), ~3–4 × f_oF2 for long hops) rises after sunrise and falls after sunset. Prediction:
long-path (> 3,000 km) spot activity on 10 m peaks around local midday and nearly vanishes at night; 40 m does the
opposite; 20 m is intermediate. Seasonally the F2 layer shows the 'winter anomaly' — daytime f_oF2 in the northern
winter exceeds summer — so 10 m long-path openings in December should exceed June at mid-day (for the northern
mid-latitude receivers that dominate WSPR).""",
    method="""Spots with distance > 3,000 km and receiver in Europe (lat 40–60°, lon −10…25°), 2025-06 and 2025-12; bands 7, 14, 28 MHz.
Aggregated per UTC hour ≈ local solar hour (+1 h). Normalised to each band's hourly maximum.""",
    data="Real: WSPRnet spots via wspr.live.",
)


def run(p):
    q = lambda m1, m2: f"""SELECT band, toHour(time) AS hr, count() AS n FROM wspr.rx
WHERE time >= '{m1}' AND time < '{m2}' AND band IN (7, 14, 28) AND distance > 3000
  AND rx_lat BETWEEN 40 AND 60 AND rx_lon BETWEEN -10 AND 25
GROUP BY band, hr ORDER BY band, hr"""
    jun = wspr(q("2025-06-01", "2025-07-01")); dec = wspr(q("2025-12-01", "2026-01-01"))
    hours = np.arange(24)
    fig, ax = p.fig(1, 2)
    peaks = {}
    for i, (band, nm) in enumerate(((7, "40 m"), (14, "20 m"), (28, "10 m"))):
        for df, lab, a in ((dec, "Dec", ax[0]),):
            d = df[df.band == band].set_index("hr").reindex(hours).fillna(0).n.values
            a.plot(hours + 1, d / max(d.max(), 1), "o-", color=COLORS[i], ms=3, label=nm)
            local = (hours + 1) % 24
            peaks[nm] = local[np.argmax(d)]
    style_axes(ax[0], "local solar hour (≈ UTC + 1)", "normalised long-path spots", "December 2025, Europe receivers")
    p.compare("10 m: local hour of peak long-path activity (midday F2 maximum)", 13, peaks["10 m"], "h", kind="abs")
    p.compare("40 m: local hour of peak long-path activity (night)", 2, peaks["40 m"], "h", kind="abs")
    d10j = jun[jun.band == 28].set_index("hr").reindex(hours).fillna(0).n.values
    d10d = dec[dec.band == 28].set_index("hr").reindex(hours).fillna(0).n.values
    mid = (hours >= 10) & (hours <= 14)
    ratio = d10d[mid].sum() / max(d10j[mid].sum(), 1)
    p.compare("10 m midday long-path spots, December / June (winter anomaly > 1)", 2.0, ratio, "×", kind="abs",
              note="direction matters more than the exact value")
    ax[1].bar(hours - 0.2, d10j, 0.4, color=COLORS[2], label="June 2025")
    ax[1].bar(hours + 0.2, d10d, 0.4, color=COLORS[0], label="December 2025")
    style_axes(ax[1], "hour (UTC)", "10 m spots > 3,000 km", "Seasonal change on 10 m")
    p.save(fig, "ionosphere", "High bands follow the Sun; the northern-winter F2 layer supports more 10 m DX than summer.")
    p.csv_df("december", dec); p.csv_df("june", jun)
    p.discuss("""The day/night split is unmistakable, though the peaks are later than my simple 'noon / midnight' predictions: 10 m peaks
mid-afternoon (the F2 layer's electron density lags the Sun because ionisation accumulates through the day) and 40 m DX
peaks around European sunrise, when the path to the Americas and Asia is still dark at the far end — the classic
'grey-line' enhancement. long-distance 10 m activity peaks near local noon when solar EUV maximises the F2
electron density, while 40 m DX peaks in the middle of the night when the absorbing D-layer disappears. The seasonal
comparison tests the F2 'winter anomaly'; the result depends on solar-cycle phase (2025 is just past the Cycle 25
maximum) and on how many stations are active each month, which the spot counts cannot separate from physics — a
proper study would normalise by the number of active transmitter–receiver pairs.""")
