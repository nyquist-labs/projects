from eelab import *
from eelab.data import wspr

META = dict(
    id="SL-105", title="Spectrum occupancy survey of the WSPR sub-bands", level="M",
    tools="wspr.live database, NumPy statistics (occupancy histograms, hourly load)",
    summary="Measure how the 200 Hz-wide WSPR segment of each amateur band is actually used: frequency occupancy "
            "within the segment, hourly load and the fraction of transmitters on crowded vs quiet slots, from one "
            "day of real reports.",
    problem="Spectrum is shared by thousands of independent users. How evenly do they spread across the available "
            "channel, and how busy is it through the day?",
    theory=r"""If N transmitters pick frequencies uniformly in a 200 Hz segment and each WSPR signal occupies ~6 Hz, the expected fraction
of time-frequency overlap (collisions) for a given transmission is $\approx1-e^{-N\cdot 6/200}$ per 2-minute slot (Poisson). Users
cluster around the segment centre, so the real occupancy histogram is peaked, raising collisions above the uniform
estimate.""",
    method="""Spots on 20 m, 2026-09-10: frequency offset within 14.0970–14.0972 MHz in 5 Hz bins (unique transmitter/slot pairs); per
2-minute slot, each transmitter's frequency = median over all receivers that heard it; fraction of transmitters with
another transmitter within ±6 Hz vs the uniform Poisson estimate.""",
    data="Real: WSPRnet spots via wspr.live.",
)


def run(p):
    q1 = """SELECT intDiv(toUInt32(frequency - 14097000), 5) * 5 AS off, uniqExact(tx_sign, time) AS n
FROM wspr.rx WHERE time >= '2026-09-10' AND time < '2026-09-11' AND band = 14 AND frequency BETWEEN 14097000 AND 14097200
GROUP BY off ORDER BY off"""
    q2 = """SELECT time, count() AS ntx, groupArray(f) AS fr FROM (
  SELECT time, tx_sign, toUInt32(median(frequency) - 14097000) AS f
  FROM wspr.rx WHERE time >= '2026-09-10' AND time < '2026-09-11' AND band = 14 AND frequency BETWEEN 14097000 AND 14097200
  GROUP BY time, tx_sign)
GROUP BY time ORDER BY time"""
    h = wspr(q1); s = wspr(q2)
    ntx = s.ntx.values
    p.metric("2-minute slots observed", len(s))
    p.metric("Mean distinct transmitters per slot (20 m)", ntx.mean())
    occ = h.n.values / h.n.values.sum()
    import ast
    coll = []
    for fr in s.fr:
        f = np.sort(np.array(ast.literal_eval(fr) if isinstance(fr, str) else fr, float))
        if len(f) > 1:
            coll.append(np.mean(np.r_[np.diff(f) < 6, False] | np.r_[False, np.diff(f) < 6]))
    N = ntx.mean()
    p.compare("Fraction of transmissions within 6 Hz of another (uniform-spread Poisson)", 1 - np.exp(-N * 12 / 200), np.mean(coll), "", kind="abs",
              note="±6 Hz window = 12 Hz of 200 Hz")
    ent = -np.sum(occ[occ > 0] * np.log2(occ[occ > 0])) / np.log2(len(occ))
    p.metric("Normalised occupancy entropy (1 = perfectly uniform)", ent)
    t = np.array([np.datetime64(x) for x in s.time])
    hours = (t - t[0]).astype("timedelta64[m]").astype(float) / 60
    fig, ax = p.fig(1, 2)
    ax[0].bar(h.off + 2.5, h.n, 5, color=C_MEAS)
    style_axes(ax[0], "offset above 14.0970 MHz (Hz)", "transmissions per 5 Hz", "Where in the segment?", legend=False)
    ax[1].plot(hours, ntx, color=C_MEAS, lw=.8)
    style_axes(ax[1], "hour (UTC)", "transmitters per 2-min slot", "Load through the day", legend=False)
    p.save(fig, "occupancy", "Users crowd toward the middle of the segment; the load follows the global day.")
    p.csv_df("occupancy_hist", h)
    p.discuss("""Transmitters do not spread uniformly: the histogram is peaked near the segment centre (entropy well below 1), so the
measured near-collision fraction exceeds the uniform Poisson estimate. WSPR survives this because its 1.46 Hz tone
spacing, 110 s coherent integration and Fano-coded decoding separate overlapping signals remarkably well — the
decoders routinely report spots only a few Hz apart.""")
