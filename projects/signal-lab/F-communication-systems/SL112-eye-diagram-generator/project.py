from eelab import *

META = dict(
    id="SL-112", title="Eye diagrams, ISI and raised-cosine pulses", level="M",
    tools="NumPy pulse shaping, band-limited channel, eye-opening measurement",
    summary="Draw eye diagrams for rectangular and root-raised-cosine (α = 0.35) signalling through a band-limited "
            "channel, and measure vertical eye opening and timing margin against the Nyquist ISI criterion.",
    problem="How much bandwidth does a data stream need before its symbols start smearing into each other, and how "
            "does an eye diagram show it?",
    theory=r"""Zero ISI requires the overall pulse to cross zero at every other symbol instant (Nyquist). A raised-cosine spectrum with
roll-off α meets it with bandwidth $(1+\alpha)R_s/2$; split as RRC at transmitter and receiver it also maximises SNR. A
rectangular pulse through a first-order channel with corner $f_c$ loses $e^{-2\pi f_cT}$ of the next symbol into the current
one: vertical eye opening ≈ $1-2e^{-2\pi f_cT}$ (worst case).""",
    method="""Binary ±1 symbols, 16 samples/symbol. (a) rectangular pulses through RC channels with f_c·T = 0.3, 0.5, 1.0; (b) RRC α = 0.35 (span 8)
matched pair, with and without an extra channel. Eye opening = (min of +1 samples − max of −1 samples)/2 at the best sampling
phase; horizontal opening where the vertical opening stays > 0.""",
)


def rrc(alpha, sps, span):
    t = np.arange(-span * sps, span * sps + 1) / sps
    h = np.zeros_like(t)
    for i, tt in enumerate(t):
        if abs(tt) < 1e-9:
            h[i] = 1 - alpha + 4 * alpha / pi
        elif abs(abs(4 * alpha * tt) - 1) < 1e-9:
            h[i] = alpha / np.sqrt(2) * ((1 + 2 / pi) * np.sin(pi / (4 * alpha)) + (1 - 2 / pi) * np.cos(pi / (4 * alpha)))
        else:
            h[i] = (np.sin(pi * tt * (1 - alpha)) + 4 * alpha * tt * np.cos(pi * tt * (1 + alpha))) / (pi * tt * (1 - (4 * alpha * tt) ** 2))
    return h / np.sqrt(np.sum(h**2))


def eye_open(y, sps, sym, skip=20):
    best = (-1, 0)
    for ph in range(sps):
        s = y[skip * sps + ph::sps][: len(sym) - 2 * skip]
        d = sym[skip: skip + len(s)]
        op = (s[d > 0].min() - s[d < 0].max()) / 2
        if op > best[0]:
            best = (op, ph)
    return best


def run(p):
    sps = 16
    sym = 1 - 2 * p.rng.integers(0, 2, 3000).astype(float)
    fig, axs = p.fig(1, 3, w=12, h=3.8)
    for a_, fcT in zip(axs, (0.3, 0.5, 1.0)):
        x = np.repeat(sym, sps)
        a = np.exp(-2 * pi * fcT / sps)
        y = np.zeros_like(x); acc = 0.0
        for n, v in enumerate(x):
            acc = a * acc + (1 - a) * v; y[n] = acc
        op, ph = eye_open(y, sps, sym)
        p.compare(f"Rectangular + RC channel f_c·T = {fcT}: vertical eye opening", 1 - 2 * np.exp(-2 * pi * fcT), op, "", kind="abs")
        seg = y[40 * sps:].reshape(-1, sps)[: 300]
        for k in range(len(seg) - 1):
            a_.plot(np.arange(2 * sps) / sps, np.r_[seg[k], seg[k + 1]], color=C_MEAS, lw=.3, alpha=.4)
        style_axes(a_, "time (symbols)", "amplitude", f"f_c·T = {fcT}", legend=False)
    p.save(fig, "eyes_rect", "A narrower channel closes the eye: more of each symbol leaks into the next.")
    h = rrc(0.35, sps, 8)
    up = np.zeros(len(sym) * sps); up[::sps] = sym
    y = np.convolve(np.convolve(up, h), h)
    d = 2 * 8 * sps
    yy = y[d: d + len(up)]
    op, ph = eye_open(yy / np.max(np.abs(yy)) * 1.0, sps, sym)
    s = yy[ph::sps] / np.median(np.abs(yy[ph::sps]))
    isi = np.max(np.abs(s[40:-40] - sym[40:len(s) - 40]))
    p.compare("RRC × RRC (α = 0.35): peak ISI at the ideal sampling instant", 0, isi, "", kind="abs")
    p.metric("RRC occupied bandwidth (1+α)·R_s/2", (1 + 0.35) / 2, "× R_s")
    fig, ax = p.fig()
    seg = yy.reshape(-1, sps)[50:450]
    for k in range(len(seg) - 1):
        ax.plot(np.arange(2 * sps) / sps, np.r_[seg[k], seg[k + 1]] / np.median(np.abs(yy[ph::sps])), color=C_MEAS, lw=.3, alpha=.4)
    style_axes(ax, "time (symbols)", "amplitude", "Raised-cosine (RRC×RRC, α = 0.35): a wide-open eye", legend=False)
    p.save(fig, "eye_rrc", "All traces pass through ±1 at the sampling instant — zero ISI in only 0.675·R_s of bandwidth.")
    p.discuss("""For the rectangular pulse through an RC channel the measured eye opening follows 1 − 2e^(−2πf_cT) — the worst-case sum of the
single-pole tail — and closes almost completely at f_c·T = 0.3. The matched RRC pair gives a raised-cosine overall
response whose zero crossings land exactly on neighbouring symbol instants, so the eye is wide open (residual ISI only
from truncating the filters to ±8 symbols) while using only 1.35/2 of the symbol rate in bandwidth.""")
