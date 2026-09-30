from eelab import *
from eelab.data import wspr

META = dict(
    id="SL-089", title="24-hour HF propagation on one path (WSPR network data)", level="M",
    tools="wspr.live public ClickHouse API (WSPRnet spot database), NumPy/solar geometry",
    summary="Follow the signal-to-noise ratio of beacon transmissions between Western Europe and the eastern "
            "USA on 20 m and 40 m through a full day, and relate the openings to the Sun's position at "
            "the path midpoint.",
    problem="Why does a shortwave band 'open' and 'close' through the day? Measure it on real spots instead of "
            "listening to one receiver.",
    theory=r"""HF skywave needs the ionosphere's F-layer to refract the signal (frequency below the MUF) while the D-layer, which
absorbs lower frequencies, is weak. Prediction: 20 m (14 MHz) is open when the path midpoint is sunlit (MUF high,
F2 layer ionised by sunlight); 40 m (7 MHz) is best when the midpoint is dark (D-layer absorption gone). So the
fraction of spots in daylight at the midpoint should be high for 20 m and low for 40 m.""",
    method="""Spots from 2026-09-01 to 2026-09-14 whose transmitter lies in western Europe (lat 43–56°, lon −10…+10°) and receiver in the
eastern USA (lat 30–46°, lon −85…−68°), bands 20 m and 40 m. Per hour (UTC): spot count and median SNR. Solar elevation
at the path midpoint (≈ 50° N, 38° W) computed from the date/hour.""",
    data="Real: WSPRnet spots via the public wspr.live database (CC0-style open data).",
)


def solar_elev(lat, lon, day_of_year, hour_utc):
    decl = -23.44 * np.cos(np.radians(360 / 365 * (day_of_year + 10)))
    ha = (hour_utc - 12) * 15 + lon
    la, de, h = np.radians(lat), np.radians(decl), np.radians(ha)
    return np.degrees(np.arcsin(np.sin(la) * np.sin(de) + np.cos(la) * np.cos(de) * np.cos(h)))


def run(p):
    sql = """SELECT band, toHour(time) AS hr, count() AS n, median(snr) AS snr
FROM wspr.rx
WHERE time >= '2026-09-01' AND time < '2026-09-15' AND band IN (7, 14)
  AND tx_lat BETWEEN 43 AND 56 AND tx_lon BETWEEN -10 AND 10
  AND rx_lat BETWEEN 30 AND 46 AND rx_lon BETWEEN -85 AND -68
GROUP BY band, hr ORDER BY band, hr"""
    df = wspr(sql)
    hours = np.arange(24)
    el = np.array([solar_elev(50, -38, 250, h + 0.5) for h in hours])
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    for i, (band, name) in enumerate(((14, "20 m"), (7, "40 m"))):
        d = df[df.band == band].set_index("hr").reindex(hours).fillna(0)
        n = d["n"].values
        day_frac = n[el > 0].sum() / max(n.sum(), 1)
        pred = 0.8 if band == 14 else 0.2
        p.compare(f"{name}: fraction of spots with the path midpoint sunlit", pred, day_frac, "", kind="abs",
                  note="expectation: 20 m daytime, 40 m night-time band")
        p.metric(f"{name}: total spots on the path (2 weeks)", n.sum())
        ax[0].bar(hours + (i - 0.5) * 0.4, n, 0.4, color=COLORS[i], label=name)
        snr = d["snr"].values.astype(float).copy(); snr[n == 0] = np.nan
        ax[1].plot(hours, snr, "o-", color=COLORS[i], label=name)
    ax2 = ax[0].twinx() if False else None
    style_axes(ax[0], None, "spots per UTC hour", "Europe → eastern USA, 1–14 Sep 2026")
    ax[1].fill_between(hours, -35, np.where(el > 0, 5, -35), color="#f5d76e", alpha=.25, step="mid", label="midpoint sunlit")
    ax[1].set_ylim(-32, 5)
    style_axes(ax[1], "hour (UTC)", "median SNR (dB, 2.5 kHz)", None)
    p.save(fig, "propagation", "20 m carries the daylight openings; 40 m takes over when the path is dark.")
    p.csv_df("hourly_spots", df)
    p.section("Query used", "```sql\n" + sql + "\n```")
    p.discuss("""The split between bands follows ionospheric physics: 20 m spots cluster when the mid-Atlantic path point is sunlit and
the F2-layer MUF is high, while 40 m is predominantly a night-time band because daytime D-layer absorption (∝ 1/f²)
kills 7 MHz over long paths. The measured fractions are not the 0.8/0.2 I guessed exactly — spot counts also depend
on when people run stations on each side of the Atlantic (evening in Europe is afternoon in the USA), a human bias the
physics prediction ignores. The median SNR per hour is the cleaner signal-quality measure.""")
