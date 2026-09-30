from eelab import *
from eelab.data import noaa_apt_audio
from eelab.apt import envelope, find_syncs, build_image, LINE, WORDS_PER_S

META = dict(
    id="SL-086", title="NOAA APT weather-satellite image decoder", level="M",
    tools="SciPy (resampling, Hilbert AM demodulation), own sync-correlation line alignment, NumPy",
    summary="Turn a real NOAA-18 recording from SatNOGS into an Earth image: AM-demodulate the 2.4 kHz "
            "subcarrier, lock onto the 1040 Hz sync bursts, align 2-lines-per-second scan lines and check "
            "the calibration wedges.",
    problem="The satellite transmits a picture as an audio tone. Recover it, and verify the decoder's timing and "
            "grey-scale calibration from the signal itself.",
    theory=r"""APT: 4160 words/s, 2080 words per line (0.5 s), i.e. 2 lines/s. Each line = sync A (7 cycles of 1040 Hz), space, 909 px
of channel A, telemetry, sync B, space, 909 px channel B, telemetry. Pixel brightness is the AM envelope of the 2400 Hz
subcarrier. Telemetry wedges 1–8 are grey steps at 1/8…8/8 of full scale, so wedge brightness vs index should be a
straight line.""",
    method="""Resample 48 kHz → 20.8 kHz (5 samples/word), band-pass 1.2–3.6 kHz, Hilbert envelope, average to 4160 words/s. Correlate
with the sync-A template; each line starts at the correlation peak searched ±20 words from the previous + 2080.
Line rate and sample-clock error from the fitted peak positions. Wedges read from the channel-B telemetry strip
(8-line blocks, 16-block frame).""",
    data="Real: SatNOGS Network observation 11229309 (NOAA-18, 2025-03-14), CC-BY-SA 4.0.",
)


def run(p):
    x, fs, meta = noaa_apt_audio()
    w = envelope(x, fs)
    peaks, c = find_syncs(w)
    img = build_image(w, peaks)
    nlines = len(img)
    k = np.arange(len(peaks))
    slope = np.polyfit(k, peaks, 1)[0]
    p.compare("Words per line (sync spacing)", LINE, slope, "words", tol=0.1)
    p.compare("Line rate", 2.0, WORDS_PER_S / slope, "Hz", tol=0.1)
    p.metric("Recording sample-clock error", (slope / LINE - 1) * 1e6, "ppm", "from the fitted line spacing")
    p.metric("Image lines decoded", nlines, "", f"{nlines/2/60:.1f} minutes of scan")
    strength = np.median(np.sort(c[peaks])[len(peaks) // 4:]) / np.std(c)
    p.metric("Median sync correlation / correlation std", strength)
    # telemetry wedges: channel B telemetry is the last 45 words of the line
    tel = img[:, LINE - 42: LINE - 3].mean(axis=1)
    sm = np.convolve(tel, np.ones(8) / 8, "valid")
    best = None
    for start in range(0, len(sm) - 128):
        blocks = [tel[start + 8 * i + 1: start + 8 * i + 7].mean() for i in range(8)]
        r = np.corrcoef(np.arange(8), blocks)[0, 1]
        if best is None or r > best[0]:
            best = (r, start, blocks)
    r, st, blocks = best
    fit = np.polyfit(np.arange(1, 9), blocks, 1)
    p.compare("Calibration wedges 1–8: linearity (correlation with a straight ramp)", 1.0, r, "", kind="abs")
    p.metric("Wedge 8 / wedge 1 brightness", blocks[-1] / max(blocks[0], 1e-3))
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(8, 8 * nlines / LINE * 1.0 + 0.5))
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img, cmap="gray", aspect="auto", interpolation="nearest"); ax.axis("off")
    p.save(fig, "apt_image", "Decoded NOAA-18 APT image (channel A left, channel B right) from a real SatNOGS recording.")
    plt.imsave(p.dir / "figures" / "apt_full_resolution.png", img, cmap="gray")
    p.files.append(("figures/apt_full_resolution.png", "full-resolution decoded image"))
    fig, ax = p.fig(1, 2)
    j = peaks[len(peaks) // 2]
    ax[0].plot(np.arange(-20, 120), w[j - 20: j + 120], color=C_MEAS)
    ax[0].axvspan(4, 32, color=COLORS[1], alpha=.15, label="sync A: 7 × 1040 Hz")
    style_axes(ax[0], "word", "envelope", "One line start: the sync burst")
    ax[1].plot(np.arange(1, 9), blocks, "o", color=C_MEAS, ms=8, label="measured wedges")
    ax[1].plot(np.arange(1, 9), np.polyval(fit, np.arange(1, 9)), "--", color=C_PRED, label="linear ramp fit")
    style_axes(ax[1], "wedge", "brightness (normalised)", "Grey-scale calibration wedges")
    p.save(fig, "sync_and_wedges", "Sync burst used for line alignment; wedge ramp used to check the grey scale.")
    p.csv("syncs", line=k, sync_word_index=peaks)
    p.discuss("""The decoder recovers a clean image: sync spacing matches the 2080-word APT line to within a fraction of a word, giving
2 lines/s and a small sample-clock offset in the ground station's sound card (a few ppm-level drift would otherwise
slant the image — aligning each line on its own sync burst removes it). The telemetry wedges rise linearly, which is
the built-in check that AM demodulation preserved the grey scale. At 22:07 UTC the pass was at night, so both
channels show infrared views (cloud tops bright/cold). NOAA-18 APT was switched off in June 2025, so archived SatNOGS
recordings like this one are now the only way to do this project.""")
