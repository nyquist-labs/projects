from eelab import *
from scipy import signal
from scipy.special import erfc

META = dict(
    id="SL-093", title="RTTY (45.45 Bd, 170 Hz FSK) decoder", level="M",
    tools="Non-coherent FSK filter-bank demodulator, Baudot (ITA2) decoding, Monte Carlo BER",
    summary="Decode amateur radioteletype: two tone filters, envelope comparison, start/stop-bit framing and "
            "ITA2 letters/figures shifting; measure bit and character error rates vs E_b/N₀ against the "
            "non-coherent FSK formula.",
    problem="RTTY has carried text over shortwave since the 1930s. How close does a simple two-filter receiver come "
            "to the theoretical error rate of non-coherent FSK?",
    theory=r"""Orthogonal non-coherent binary FSK: $P_b=\tfrac12e^{-E_b/2N_0}$. 170 Hz shift at 45.45 Bd (22 ms bits) gives tones spaced
7.5 × the bit rate — comfortably orthogonal. Each character = 1 start + 5 data + 1.5 stop bits; a character is wrong if
any of its 5 data bits is (plus framing), so CER ≈ $1-(1-P_b)^5$.""",
    method="""Text 'RYRYRY CQ CQ DE ABC123 THE QUICK BROWN FOX 73' in ITA2 (with LTRS/FIGS shifts), mark 2125 Hz / space 2295 Hz, 8 kS/s. Noise
set by E_b/N₀. Demodulator: two 2nd-order band-pass filters (70 Hz wide) → envelopes → difference → matched
(integrate over bit) → sample at bit centres located by the start-bit edge.""",
    data="Synthetic RTTY signal with known text.",
)

LTRS = {c: i for i, c in enumerate("\0E\nA SIU\rDRJNFCKTZLWHYPQOBG\x1fMXV\x1b")}
FIGS = {c: i for i, c in enumerate("\x003\n- '87\r$4',!:(5\")2#6019?&\x1f./;\x1b")}
LTRS_R = {v: k for k, v in LTRS.items()}; FIGS_R = {v: k for k, v in FIGS.items()}


def encode(text):
    codes, mode = [], "L"
    for ch in text:
        if ch in LTRS and ch not in "\x1f\x1b":
            if mode != "L": codes.append(31); mode = "L"
            codes.append(LTRS[ch])
        elif ch in FIGS:
            if mode != "F": codes.append(27); mode = "F"
            codes.append(FIGS[ch])
    return codes


def decode_codes(codes):
    out, mode = "", "L"
    for c in codes:
        if c == 31: mode = "L"
        elif c == 27: mode = "F"
        else: out += (LTRS_R if mode == "L" else FIGS_R).get(c, "?")
    return out


def run(p):
    fs, baud = 8000, 45.45
    spb = fs / baud
    text = "RYRYRY CQ CQ DE ABC123 THE QUICK BROWN FOX 73"
    codes = encode(text)
    bits = []
    for c in codes:
        bits += [0] + [(c >> k) & 1 for k in range(5)] + [1, 1]  # 1 start, 5 data (LSB first), 2 stop (1.5 → 2 for simplicity)
    bits = [1] * 10 + bits + [1] * 10
    level = np.repeat(bits, int(round(spb)))
    t = np.arange(len(level)) / fs
    f = np.where(level == 1, 2125.0, 2295.0)
    s = np.cos(2 * pi * np.cumsum(f) / fs)
    def demod(x):
        outs = []
        for fc in (2125, 2295):
            b, a = signal.butter(2, [fc - 35, fc + 35], "bandpass", fs=fs)
            outs.append(np.abs(signal.hilbert(signal.lfilter(b, a, x))))
        d = outs[0] - outs[1]
        k = int(round(spb)); d = np.convolve(d, np.ones(k) / k, "same")   # integrate over one bit (centred)
        return d
    n = int(round(spb))
    ref = np.repeat(2 * np.array(bits) - 1.0, n)
    dcl = demod(s)
    lag = int(np.argmax(np.correlate(dcl[:len(ref)], ref[:len(ref)], "full")) - (len(ref) - 1))
    p.metric("Receiver filter group delay (measured by correlation)", lag / fs * 1e3, "ms")
    def frame(d):
        rx, i = [], 0
        while i < len(d) - 8 * n:
            if d[i] < 0 and d[max(i - 1, 0)] >= 0:
                c0 = i + n // 2                                  # centre of the start bit
                data = [1 if d[c0 + (k + 1) * n] > 0 else 0 for k in range(5)]
                rx.append(sum(b << k for k, b in enumerate(data)))
                i = c0 + 6 * n + n // 2
            else:
                i += 1
        return rx
    clean = decode_codes(frame(dcl))
    p.compare("Clean decode character errors", 0, sum(a != b for a, b in zip(clean, text)) + abs(len(clean) - len(text)), "", kind="abs")
    ebs = np.arange(4, 17, 2)
    ber, pred = [], []
    lag = max(lag, 0)
    for eb in ebs:
        errs = tot = 0
        for rep in range(6):
            Eb = np.sum(s**2) / fs / len(bits)          # joules per bit (sample energy × Ts)
            N0 = Eb / 10 ** (eb / 10)
            x = s + p.rng.normal(0, np.sqrt(N0 * fs / 2), len(s))
            d = demod(x)
            n = int(round(spb))
            centres = np.arange(len(bits)) * n + n // 2 + lag
            dec = (d[centres] > 0).astype(int)
            errs += np.sum(dec != np.array(bits)); tot += len(bits)
        ber.append(errs / tot); pred.append(0.5 * np.exp(-10 ** (eb / 10) / 2))
    ber, pred = np.array(ber), np.array(pred)
    e_meas = np.interp(-3, np.log10(np.maximum(ber[::-1], 1e-6)), ebs[::-1])
    e_pred = 2 * np.log(0.5 / 1e-3) ; e_pred = 10 * np.log10(e_pred)
    p.compare("E_b/N₀ for BER 10⁻³ (non-coherent FSK: ½e^(−Eb/2N0))", e_pred, e_meas, "dB", kind="abs")
    fig, ax = p.fig()
    ax.semilogy(ebs, np.maximum(ber, 1e-5), "o-", color=C_MEAS, label="measured (bit-synchronous)")
    ax.semilogy(ebs, pred, "--", color=C_PRED, label="½·exp(−Eb/2N0)")
    ax.set_ylim(1e-5, 0.5)
    style_axes(ax, "Eb/N0 (dB)", "BER", "RTTY two-filter receiver vs theory")
    p.save(fig, "ber", "The simple filter-bank receiver runs a couple of dB behind the optimum non-coherent detector.")
    p.section("Decoded text (clean signal)", f"`{clean}`")
    p.csv("ber", ebn0_db=ebs, ber=ber, theory=pred)
    p.discuss("""The decoder reproduces the transmitted text exactly, including the letters/figures shifts ITA2 needs for digits. In noise
it follows the non-coherent FSK curve shifted by ~1–3 dB: the 70 Hz-wide analog-style filters are wider than the
~45 Hz matched bandwidth and their group delay smears adjacent bits (inter-symbol interference). A matched-filter
(correlator) receiver would close most of that gap.""")
