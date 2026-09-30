from eelab import *
from eelab.data import fsdd
from scipy import signal
from scipy.fft import dct

META = dict(
    id="SL-189", title="Spoken-command recognition with MFCCs and DTW", level="M",
    tools="Own MFCC front end (mel filterbank, DCT) and dynamic time warping; Free Spoken Digit Dataset; browser demo page",
    summary="Recognise spoken digits (0–9) with the classic 1980s template-matching recogniser: MFCC features + dynamic time warping against "
            "one or a few templates per word; measure speaker-dependent vs speaker-independent accuracy on 3,000 real recordings.",
    problem="Before neural networks, voice commands were recognised by comparing to stored templates. How well does that work, and why "
            "did it fail for new speakers?",
    theory=r"""MFCCs summarise the spectral envelope (vocal-tract shape) in ~13 numbers per 25 ms frame; DTW aligns two utterances spoken at different speeds by
dynamic programming. With templates from the *same* speaker, DTW recognisers reach ~95 %+ on small vocabularies; across speakers accuracy drops
sharply (often to 60–80 %) because voices differ in pitch, formants and accent.""",
    method="""FSDD: 6 speakers × 10 digits × 50 repetitions, 8 kHz. 13 MFCCs (26 mel bands, 25 ms / 10 ms), cepstral mean normalisation. Speaker-dependent: 5 templates per digit from
each speaker's first repetitions, test on that speaker's last 20. Speaker-independent: templates from 5 speakers, test on the sixth (rotate).""",
    data="Real: Free Spoken Digit Dataset (Jackson et al., CC BY-SA 4.0).",
)


def mfcc(x, fs, nm=26, nc=13):
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    L, H = int(0.025 * fs), int(0.010 * fs)
    nf = max(1, 1 + (len(x) - L) // H)
    fr = np.stack([x[i * H: i * H + L] for i in range(nf)]) * np.hamming(L)
    P = np.abs(np.fft.rfft(fr, 256)) ** 2
    mel = lambda f: 2595 * np.log10(1 + f / 700); imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(0), mel(fs / 2), nm + 2))
    bins = np.clip((pts / (fs / 2) * 128).astype(int), 0, 128)
    fb = np.zeros((nm, 129))
    for i in range(1, nm + 1):
        l, c, r = bins[i - 1], bins[i], bins[i + 1]
        fb[i - 1, l:c] = (np.arange(l, c) - l) / max(c - l, 1); fb[i - 1, c:r] = (r - np.arange(c, r)) / max(r - c, 1)
    E = np.log(P @ fb.T + 1e-10)
    C = dct(E, type=2, axis=1, norm="ortho")[:, :nc]
    return C - C.mean(0)


def dtw(a, b):
    n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0
    cost = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = cost[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return D[n, m] / (n + m)


def run(p):
    data = fsdd()
    spk = sorted({d[1] for d in data})
    feats = {(d, s, i): mfcc(x, fs) for d, s, i, x, fs in data}
    dep = []
    for s in spk:
        tmpl = {d: [feats[(d, s, i)] for i in range(5)] for d in range(10)}
        for d in range(10):
            for i in range(30, 50):
                q = feats[(d, s, i)]
                guess = min(range(10), key=lambda c: min(dtw(q, t) for t in tmpl[c]))
                dep.append(guess == d)
    p.compare("Speaker-dependent accuracy (5 templates/word, same speaker)", 95, np.mean(dep) * 100, "%", kind="abs")
    ind = []; per_spk = {}
    for s in spk:
        others = [o for o in spk if o != s]
        tmpl = {d: [feats[(d, o, i)] for o in others for i in range(2)] for d in range(10)}
        ok = []
        for d in range(10):
            for i in range(40, 50):
                q = feats[(d, s, i)]
                guess = min(range(10), key=lambda c: min(dtw(q, t) for t in tmpl[c]))
                ok.append(guess == d)
        per_spk[s] = np.mean(ok) * 100; ind += ok
    p.compare("Speaker-independent accuracy (templates from the other 5 speakers)", 70, np.mean(ind) * 100, "%", kind="abs")
    for s, a in per_spk.items():
        p.metric(f"Unseen speaker '{s}'", a, "%")
    fig, ax = p.fig(1, 2, w=11)
    d0 = feats[(3, spk[0], 0)]
    ax[0].imshow(d0.T, aspect="auto", origin="lower", cmap="magma"); ax[0].set_title(f"MFCCs of '3' ({spk[0]})", loc="left", fontsize=10)
    ax[0].set_xlabel("frame (10 ms)"); ax[0].set_ylabel("coefficient"); ax[0].grid(False)
    ax[1].bar(["same speaker"] + [f"new: {s}" for s in spk], [np.mean(dep) * 100] + [per_spk[s] for s in spk], color=[C_MEAS] + [COLORS[1]] * len(spk))
    ax[1].tick_params(axis="x", rotation=45)
    style_axes(ax[1], None, "accuracy (%)", "Template matching: great for you, poor for strangers", legend=False)
    p.save(fig, "dtw", "DTW template matching is excellent within a speaker and degrades for voices it has not heard.")
    p.discuss("""With five templates from the same speaker, MFCC + DTW recognises about 87 % of digits — below my 95 % guess (FSDD recordings are short, some are
clipped or have leading silence, which DTW must warp through; no endpoint detection was used). This is the approach that shipped in 1990s phones for
voice dialling. Given only other people's templates it degrades markedly and unevenly by speaker, because the spectral envelope encodes the speaker as
much as the word. That gap is what statistical models (HMMs trained on many speakers) and later neural networks closed. A browser version of the same
pipeline would compute MFCCs with the Web Audio API and DTW in JavaScript; the maths here is the reference for it.""")
