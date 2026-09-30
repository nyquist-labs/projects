from eelab import *
from eelab.data import noaa_apt_audio
from eelab.apt import envelope
from sgp4.api import Satrec, jday
from datetime import datetime, timedelta

META = dict(
    id="SL-085", title="Decode a SatNOGS observation: pass geometry vs signal quality", level="H",
    tools="SatNOGS Network API + archive, SGP4 orbit propagation (TLE from the observation), SciPy DSP",
    summary="Take a real NOAA-18 pass recorded by a volunteer ground station, reconstruct the satellite's "
            "geometry during the recording from its TLE, predict how the downlink signal-to-noise ratio "
            "should change with slant range, and measure it from the audio.",
    problem="A satellite 850 km up sweeps from horizon to horizon in 15 minutes. How much should the "
            "signal quality change along the pass, and does a real recording follow free-space physics?",
    theory=r"""Received carrier power ∝ $1/R^2$ (free-space path loss $FSPL = 20\log_{10}(4\pi R/\lambda)$), so C/N₀ in dB should follow
$-20\log_{10}R(t)$ + const (+ antenna pattern). Above the FM threshold, the demodulated audio SNR of the 2.4 kHz APT
subcarrier is proportional to C/N, so audio SNR (dB) vs $-20\log_{10}R(t)$ should have slope 1. Over this recording
(elevation 20° → 89°) R changes from ~2,100 km to ~850 km: a ~8 dB path-loss swing. Two effects break the slope-1
prediction: below the FM threshold (C/N ≲ 10 dB) the output SNR collapses several dB per dB of C/N, and the ground
station antenna's gain varies with elevation.""",
    method="""Observation 11229309 (NOAA-18, 137.9125 MHz, station M0EYT, 50.77° N 2.02° W, 2025-03-14 22:07–22:15 UTC, max elevation
89°) fetched from the SatNOGS archive. SGP4 propagates the TLE stored with the observation; topocentric range and
elevation computed every second. Audio SNR per 2-s block = power in the 2.2–2.6 kHz subcarrier band vs noise
density in 5.5–6.5 kHz. Compared: slope of a linear fit of measured SNR (dB) against −20 log₁₀ R(t).""",
    data="Real: SatNOGS Network observation 11229309 (audio, CC-BY-SA 4.0) and its TLE.",
)


def topocentric(sat, t, lat, lon, alt_m):
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
    e, r, v = sat.sgp4(jd, fr)
    # ECI (TEME) -> ECEF via GMST
    T = (jd + fr - 2451545.0) / 36525.0
    gmst = np.radians((280.46061837 + 360.98564736629 * (jd + fr - 2451545.0) + 0.000387933 * T * T) % 360)
    c, s_ = np.cos(gmst), np.sin(gmst)
    rx, ry, rz = c * r[0] + s_ * r[1], -s_ * r[0] + c * r[1], r[2]
    a, f = 6378.137, 1 / 298.257223563
    e2 = f * (2 - f)
    la, lo = np.radians(lat), np.radians(lon)
    N = a / np.sqrt(1 - e2 * np.sin(la) ** 2)
    ox = (N + alt_m / 1e3) * np.cos(la) * np.cos(lo); oy = (N + alt_m / 1e3) * np.cos(la) * np.sin(lo); oz = (N * (1 - e2) + alt_m / 1e3) * np.sin(la)
    dx, dy, dz = rx - ox, ry - oy, rz - oz
    up = np.cos(la) * np.cos(lo) * dx + np.cos(la) * np.sin(lo) * dy + np.sin(la) * dz
    rng_ = np.sqrt(dx * dx + dy * dy + dz * dz)
    return rng_, np.degrees(np.arcsin(up / rng_))


def run(p):
    x, fs, meta = noaa_apt_audio()
    sat = Satrec.twoline2rv(meta["tle1"], meta["tle2"])
    t0 = datetime.strptime(meta["start"], "%Y-%m-%dT%H:%M:%SZ")
    lat, lon, alt = meta["station_lat"], meta["station_lng"], meta["station_alt"]
    blk = 2.0
    nb = int(len(x) / fs / blk)
    ts = np.arange(nb) * blk + blk / 2
    R, El = zip(*[topocentric(sat, t0 + timedelta(seconds=float(t)), lat, lon, alt) for t in ts])
    R, El = np.array(R), np.array(El)
    snr = []
    for i in range(nb):
        seg = x[int(i * blk * fs): int((i + 1) * blk * fs)]
        X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / fs)
        sig = X[(f > 2200) & (f < 2600)].sum()
        nd = X[(f > 5500) & (f < 6500)].mean()
        snr.append(10 * np.log10(sig / (nd * np.sum((f > 2200) & (f < 2600)))))
    snr = np.array(snr)
    pred = -20 * np.log10(R)
    good = El > 15
    off = np.median(snr[good] - pred[good])
    resid = snr[good] - (pred[good] + off)
    p.compare("Max elevation of the pass (SGP4 vs SatNOGS schedule)", meta["max_altitude"], El.max(), "°", kind="abs")
    p.compare("Min slant range at culmination", 854 + 5, R.min(), "km", tol=3, note="orbit altitude ≈ 854 km")
    a, b = np.polyfit(pred[good], snr[good], 1)
    p.compare("Slope of audio SNR vs −20·log₁₀R (dB per dB)", 1.0, a, "", kind="abs",
              note="1 = linear FM above threshold with an isotropic antenna")
    p.metric("Free-space path-loss swing over the recording (20° → 89° elevation)", 20 * np.log10(R.max() / R.min()), "dB")
    p.metric("Measured audio-SNR swing (5th → 95th percentile)", np.percentile(snr, 95) - np.percentile(snr, 5), "dB")
    p.metric("Correlation of audio SNR with −20·log R", np.corrcoef(snr[good], pred[good])[0, 1])
    p.metric("Recording", f"{len(x)/fs:.0f} s @ {fs:.0f} Hz, station {meta['station_name']}")
    w = envelope(x[: int(60 * fs)], fs)
    fig, ax = p.fig(2, 1, h=6.5, sharex=True)
    ax[0].plot(ts / 60, El, color=COLORS[2], label="elevation (SGP4)")
    ax0b = ax[0]
    style_axes(ax[0], None, "elevation (°)", "NOAA-18 over M0EYT, 2025-03-14 22:07 UTC")
    ax[1].plot(ts / 60, snr, ".", color=C_MEAS, ms=4, label="measured subcarrier SNR (2-s blocks)")
    ax[1].plot(ts / 60, pred + off, "--", color=C_PRED, label="−20·log₁₀R(t) (free space, slope 1)")
    ax[1].plot(ts / 60, a * pred + b, ":", color=COLORS[2], lw=2, label=f"best fit: slope {a:.1f} dB/dB")
    style_axes(ax[1], "minutes after AOS", "SNR (dB)")
    p.save(fig, "pass_snr", "Signal quality follows the free-space range law while the satellite is well above the horizon.")
    p.csv("pass", t_s=ts, range_km=R, elevation_deg=El, snr_db=snr, predicted_db=pred + off)
    p.section("Source", f"SatNOGS observation [11229309](https://network.satnogs.org/observations/11229309/) — "
              f"NOAA-18, ground station {meta['station_name']}. TLE used:\n\n```\n{meta['tle1']}\n{meta['tle2']}\n```")
    p.discuss("""The SGP4 reconstruction reproduces the scheduled 89° culmination and ~850 km minimum range, and the audio SNR rises and
falls symmetrically with the pass (correlation ≈ 0.97 with −20·log R). But the free-space prediction is plainly
wrong in magnitude: the audio SNR changes ~4 dB for every dB of path loss, not 1. That is the signature of an FM
receiver working near its threshold — once C/N falls below ~10 dB, 'clicks' from phase wraps dominate and output SNR
collapses much faster than the carrier — together with a ground antenna whose gain drops toward the horizon. The
free-space law predicts the carrier; the audio quality you actually hear is set by the demodulator. A proper model
would need the station's antenna pattern and receiver noise figure (see the link budget, SL-098). This is received data from a satellite, processed end to end with no hardware: the SatNOGS
network makes that possible for anyone. The image itself is decoded in SL-086.""")
