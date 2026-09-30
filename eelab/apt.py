"""NOAA APT decoding helpers shared by SL-085/SL-086."""
import numpy as np
from scipy import signal

WORDS_PER_S = 4160
LINE = 2080
SYNC_A = np.array([-1] * 4 + [1, 1, -1, -1] * 7 + [-1] * 8, float)


def envelope(x, fs):
    """AM-demodulate the 2400 Hz APT subcarrier and resample to 4160 words/s."""
    y = signal.resample_poly(x, 13, 30)          # 48 kHz -> 20.8 kHz (5 samples per word)
    b, a = signal.butter(4, [1200, 3600], "bandpass", fs=20800)
    y = signal.filtfilt(b, a, y)
    env = np.abs(signal.hilbert(y))
    n = len(env) // 5
    return env[: n * 5].reshape(n, 5).mean(axis=1)


def find_syncs(w):
    t = SYNC_A - SYNC_A.mean()
    c = np.correlate(w - np.convolve(w, np.ones(64) / 64, "same"), t, "valid")
    peaks = []
    i = int(np.argmax(c[:LINE]))
    while i + LINE + 50 < len(c):
        lo, hi = i + LINE - 20, i + LINE + 20
        i = lo + int(np.argmax(c[lo:hi]))
        peaks.append(i)
    return np.array(peaks), c


def build_image(w, peaks):
    rows = [w[p: p + LINE] for p in peaks if p + LINE <= len(w)]
    img = np.array(rows)
    lo, hi = np.percentile(img, [1, 99])
    return np.clip((img - lo) / (hi - lo), 0, 1)
