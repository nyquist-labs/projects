"""eelab.data — download-once cache for the real public datasets used by projects.

Raw downloads go to ./data_cache/ (git-ignored). Each project saves the small slice it
actually analyses into its own data/ folder, so results are inspectable without
re-downloading.
"""
from __future__ import annotations

import hashlib
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from .core import ROOT

CACHE = ROOT / "data_cache"
UA = {"User-Agent": "nyquist-labs-projects/1.0 (educational research; python urllib)"}
try:
    import certifi, ssl
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:          # pragma: no cover
    _SSL = None


def fetch(url: str, name: str | None = None, sub="misc", timeout=300) -> Path:
    d = CACHE / sub
    d.mkdir(parents=True, exist_ok=True)
    name = name or Path(urllib.parse.urlparse(url).path).name or hashlib.md5(url.encode()).hexdigest()
    path = d / name
    if not path.exists() or path.stat().st_size == 0:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
            data = r.read()
        path.write_bytes(data)
    return path


# ------------------------------------------------------------------ PhysioNet
def physionet(db: str, record: str, sampfrom=0, sampto=None, channels=None, ann=None):
    """Read a WFDB record (+ optional annotation) from PhysioNet, cached as .npz."""
    key = f"{db.replace('/', '_')}_{record}_{sampfrom}_{sampto}_{channels}_{ann}"
    path = CACHE / "physionet" / (hashlib.md5(key.encode()).hexdigest() + ".npz")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        z = np.load(path, allow_pickle=True)
        out = {k: (z[k].item() if z[k].dtype == object and z[k].shape == () else z[k]) for k in z}
        out["fs"] = float(out["fs"])
        return out
    import wfdb
    rec = wfdb.rdrecord(record, pn_dir=db, sampfrom=sampfrom, sampto=sampto, channels=channels)
    out = dict(signal=rec.p_signal.astype(np.float32), fs=float(rec.fs),
               names=np.array(rec.sig_name), units=np.array(rec.units))
    if ann:
        a = wfdb.rdann(record, ann, pn_dir=db, sampfrom=sampfrom, sampto=sampto)
        out["ann_sample"] = np.asarray(a.sample) - sampfrom
        out["ann_symbol"] = np.array(a.symbol)
        out["ann_aux"] = np.array([s or "" for s in (a.aux_note or [""] * len(a.sample))])
    np.savez_compressed(path, **out)
    return out


def read_edf(path):
    """Minimal EDF/EDF+ reader -> dict(signals={label: array}, fs={label: Hz}, annotations=[...])."""
    raw = Path(path).read_bytes()
    h = raw[:256].decode("latin-1")
    nrec = int(h[236:244])
    dur = float(h[244:252])
    ns = int(h[252:256])
    hh = raw[256:256 + ns * 256].decode("latin-1")

    def field(off, width):
        base = off * ns
        return [hh[base + i * width: base + (i + 1) * width].strip() for i in range(ns)]

    labels = field(0, 16)
    pmin = np.array(field(104, 8), float); pmax = np.array(field(112, 8), float)
    dmin = np.array(field(120, 8), float); dmax = np.array(field(128, 8), float)
    # sample counts sit after label(16) transducer(80) dim(8) pmin pmax dmin dmax prefilter(80)
    off = ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
    nsamp = [int(hh[off + i * 8: off + (i + 1) * 8]) for i in range(ns)]
    data = np.frombuffer(raw[256 + ns * 256:], dtype="<i2")
    rec_len = sum(nsamp)
    nrec = min(nrec, len(data) // rec_len) if nrec > 0 else len(data) // rec_len
    data = data[: nrec * rec_len].reshape(nrec, rec_len)
    sig, fs, anns = {}, {}, []
    pos = 0
    for i, lab in enumerate(labels):
        chunk = data[:, pos:pos + nsamp[i]].ravel()
        pos += nsamp[i]
        if lab == "EDF Annotations":
            txt = chunk.tobytes().decode("latin-1")
            for tal in txt.split("\x00"):
                parts = tal.split("\x14")          # "+onset[\x15dur]\x14text1\x14text2…\x14"
                if len(parts) >= 2:
                    onset_dur = parts[0].split("\x15")
                    for text in parts[1:]:
                        if text:
                            try:
                                anns.append((float(onset_dur[0]),
                                             float(onset_dur[1]) if len(onset_dur) > 1 and onset_dur[1] else 0.0, text))
                            except ValueError:
                                pass
            continue
        gain = (pmax[i] - pmin[i]) / (dmax[i] - dmin[i])
        sig[lab] = ((chunk - dmin[i]) * gain + pmin[i]).astype(np.float32)
        fs[lab] = nsamp[i] / dur
    return dict(signals=sig, fs=fs, annotations=anns)


def physionet_edf(path_in_db: str):
    """e.g. 'eegmmidb/1.0.0/S001/S001R02.edf'"""
    p = fetch("https://physionet.org/files/" + path_in_db, path_in_db.replace("/", "_"),
              sub="physionet")
    return read_edf(p)


def physionet_file(path_in_db: str):
    return fetch("https://physionet.org/files/" + path_in_db, path_in_db.replace("/", "_"),
                 sub="physionet")


# ------------------------------------------------------------------ radio data
def wspr(sql: str):
    """Query the public wspr.live ClickHouse mirror of the WSPRnet spot database."""
    import pandas as pd
    key = hashlib.md5(sql.encode()).hexdigest()
    path = CACHE / "wspr" / f"{key}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        url = "https://db1.wspr.live/?query=" + urllib.parse.quote(sql + " FORMAT CSVWithNames")
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=300, context=_SSL) as r:
            path.write_bytes(r.read())
    return pd.read_csv(path)


def celestrak_tle(catnr: int):
    p = fetch(f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catnr}&FORMAT=TLE",
              f"tle_{catnr}.txt", sub="tle")
    lines = [l.rstrip() for l in p.read_text().splitlines() if l.strip()]
    return lines[0].strip(), lines[1], lines[2]


def satnogs_observation(obs_id: int):
    meta_p = fetch(f"https://network.satnogs.org/api/observations/?id={obs_id}&format=json",
                   f"obs_{obs_id}.json", sub="satnogs")
    meta = json.loads(meta_p.read_text())[0]
    audio_url = meta.get("payload") or meta.get("archive_url")
    audio = fetch(audio_url, f"obs_{obs_id}.ogg", sub="satnogs")
    return meta, audio


def read_audio(path):
    import soundfile as sf
    x, fs = sf.read(str(path), dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, fs


def uci_zip(url, name):
    import zipfile
    p = fetch(url, name, sub="uci")
    return zipfile.ZipFile(p)


def nasa_battery(cell="B0005"):
    """NASA Ames PCoE Li-ion battery aging data (Saha & Goebel 2007). Returns list of cycles."""
    import scipy.io as sio
    import zipfile
    d = CACHE / "nasa"
    mat = d / f"{cell}.mat"
    if not mat.exists():
        z = fetch("https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip", "battery.zip", sub="nasa", timeout=1800)
        with zipfile.ZipFile(z) as outer:
            inner_name = [n for n in outer.namelist() if "FY08Q4" in n][0]
            with outer.open(inner_name) as fh:
                inner = zipfile.ZipFile(io.BytesIO(fh.read()))
                for n in inner.namelist():
                    if n.endswith(".mat"):
                        (d / Path(n).name).write_bytes(inner.read(n))
        z.unlink()
    return sio.loadmat(mat, simplify_cells=True)[cell]["cycle"]


def speech_hello():
    """Public-domain recording of the word 'hello' (Wikimedia Commons, File:En-us-hello.ogg)."""
    p = fetch("https://upload.wikimedia.org/wikipedia/commons/5/52/En-us-hello.ogg", "en_us_hello.ogg", sub="audio")
    return read_audio(p)


def noaa_apt_audio():
    """Real NOAA-18 APT pass recorded by a SatNOGS ground station (observation 11229309, 2025-03-14)."""
    meta, path = satnogs_observation(11229309)
    x, fs = read_audio(path)
    return x, fs, meta


def orbit_tools():
    """Topocentric helper using SGP4 (TEME → ECEF via GMST)."""
    from sgp4.api import Satrec, jday
    def topo(sat, t, lat, lon, alt_m=0.0):
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond * 1e-6)
        e, r, v = sat.sgp4(jd, fr)
        T = (jd + fr - 2451545.0) / 36525.0
        g = np.radians((280.46061837 + 360.98564736629 * (jd + fr - 2451545.0) + 0.000387933 * T * T) % 360)
        c, s_ = np.cos(g), np.sin(g)
        we = 7.2921159e-5
        rx, ry, rz = c * r[0] + s_ * r[1], -s_ * r[0] + c * r[1], r[2]
        vx = c * v[0] + s_ * v[1] + we * ry; vy = -s_ * v[0] + c * v[1] - we * rx; vz = v[2]
        a, f = 6378.137, 1 / 298.257223563
        e2 = f * (2 - f); la, lo = np.radians(lat), np.radians(lon)
        N = a / np.sqrt(1 - e2 * np.sin(la) ** 2)
        ox = (N + alt_m / 1e3) * np.cos(la) * np.cos(lo); oy = (N + alt_m / 1e3) * np.cos(la) * np.sin(lo); oz = (N * (1 - e2) + alt_m / 1e3) * np.sin(la)
        d = np.array([rx - ox, ry - oy, rz - oz])
        rng_ = np.linalg.norm(d)
        up = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
        east = np.array([-np.sin(lo), np.cos(lo), 0]); north = np.cross(up, east)
        el = np.degrees(np.arcsin(d @ up / rng_)); az = np.degrees(np.arctan2(d @ east, d @ north)) % 360
        rr = d @ np.array([vx, vy, vz]) / rng_
        return rng_, el, az, rr, np.array([rx, ry, rz])
    return Satrec, topo


def emg_gestures(subject):
    """UCI 'EMG data for gestures' (Lobov et al. 2018): Myo armband, 8 channels, 1 kHz, classes 0–7. Returns list of arrays [t, ch1..8, class]."""
    import zipfile
    z = zipfile.ZipFile(fetch("https://archive.ics.uci.edu/static/public/481/emg+data+for+gestures.zip", "emg_gestures.zip", sub="uci"))
    out = []
    for n in sorted(z.namelist()):
        if n.startswith(f"EMG_data_for_gestures-master/{subject:02d}/") and n.endswith(".txt"):
            rows = [r.split() for r in z.read(n).decode().splitlines()[1:]]
            out.append(np.array([list(map(float, r)) for r in rows if len(r) == 10]))   # a few files have truncated last lines
    return out


def har(split="train", raw=False):
    """UCI HAR (Anguita et al. 2013): smartphone IMU, 30 subjects, 6 activities. Features (561) or raw 9-channel windows (128 × 50 Hz)."""
    import zipfile
    z = zipfile.ZipFile(fetch("https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip", "har.zip", sub="uci"))
    inner = zipfile.ZipFile(io.BytesIO(z.read("UCI HAR Dataset.zip")))
    base = f"UCI HAR Dataset/{split}/"
    rd = lambda n: np.loadtxt(io.BytesIO(inner.read(base + n)))
    y = rd(f"y_{split}.txt").astype(int); subj = rd(f"subject_{split}.txt").astype(int)
    if raw:
        chans = [f"{k}_{a}" for k in ("body_acc", "body_gyro", "total_acc") for a in "xyz"]
        X = np.stack([rd(f"Inertial Signals/{c}_{split}.txt") for c in chans], axis=1)
    else:
        X = rd(f"X_{split}.txt")
    return X, y, subj


def fsdd():
    """Free Spoken Digit Dataset: 3,000 recordings (6 speakers × 10 digits × 50), 8 kHz. Returns list of (digit, speaker, idx, audio)."""
    import zipfile
    import soundfile as sf
    z = zipfile.ZipFile(fetch("https://github.com/Jakobovski/free-spoken-digit-dataset/archive/refs/heads/master.zip", "fsdd.zip", sub="audio"))
    out = []
    for n in z.namelist():
        if n.endswith(".wav") and "/recordings/" in n:
            d, spk, i = Path(n).stem.split("_")
            x, fs = sf.read(io.BytesIO(z.read(n)), dtype="float32")
            out.append((int(d), spk, int(i), x, fs))
    return out


def alice_text():
    """Public-domain English text (Lewis Carroll, 'Alice's Adventures in Wonderland', Project Gutenberg #11),
    body only (licence header/footer stripped). Used as a real-world source for the coding/information-theory projects."""
    t = open(fetch("https://www.gutenberg.org/files/11/11-0.txt", "alice.txt", sub="text"), encoding="utf-8").read()
    a = t.find("*** START"); a = t.find("\n", a) + 1
    b = t.find("*** END")
    return t[a:b].replace("\r\n", "\n").strip()
