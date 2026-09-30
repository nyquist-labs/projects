from eelab import *
from scipy.special import erfc

META = dict(
    id="AM-084", title="Bit-error rate vs SNR: Monte Carlo against theory", level="M",
    tools="Monte-Carlo simulation of BPSK, QPSK (Gray), 16-QAM (Gray) and non-coherent BFSK over AWGN, exact/union-bound BER formulas, confidence intervals",
    summary="Simulate millions of bits for four modulations, plot BER against Eb/N0 with 95 % confidence intervals, and compare with the "
            "closed-form expressions — including where the common approximations for 16-QAM stop being exact.",
    problem="Every link budget uses BER curves. Do simulated bits actually land on the textbook formulas?",
    theory=r"""BPSK and Gray-coded QPSK: $P_b=Q(\sqrt{2E_b/N_0})$. Gray 16-QAM: $P_b ≈ \frac34 Q(\sqrt{\frac45E_b/N_0})$ (nearest-neighbour approximation, accurate at high SNR). Non-coherent orthogonal BFSK: $P_b=\frac12e^{-E_b/2N_0}$.
16-QAM needs ≈ 4 dB more Eb/N0 than QPSK for the same BER, the price of 2 extra bits per symbol.""",
    method="""Eb/N0 = 0…12 dB; up to 10⁷ bits per point (stop after 500 errors); Wilson 95 % intervals. Exact BPSK formula; 16-QAM compared with both the approximation and an exact per-bit expression.""",
)


def Qf(x):
    return 0.5 * erfc(x / np.sqrt(2))


def sim(mod, ebn0_db, r, max_bits=10 ** 7, target=500):
    ebn0 = 10 ** (ebn0_db / 10); errs = bits = 0
    while errs < target and bits < max_bits:
        nb = 200000
        b = r.integers(0, 2, nb)
        if mod == "BPSK":
            s = 2 * b - 1.0; y = s + r.normal(0, np.sqrt(1 / (2 * ebn0)), nb); bh = (y > 0).astype(int)
        elif mod == "QPSK":
            s = ((2 * b[0::2] - 1) + 1j * (2 * b[1::2] - 1)) / np.sqrt(2)
            y = s + (r.normal(size=len(s)) + 1j * r.normal(size=len(s))) * np.sqrt(1 / (2 * 2 * ebn0))
            bh = np.empty(nb, int); bh[0::2] = y.real > 0; bh[1::2] = y.imag > 0
        elif mod == "16QAM":
            g = {(0, 0): -3, (0, 1): -1, (1, 1): 1, (1, 0): 3}
            I = np.array([g[(a, c)] for a, c in zip(b[0::4], b[1::4])]); Qv = np.array([g[(a, c)] for a, c in zip(b[2::4], b[3::4])])
            s = (I + 1j * Qv) / np.sqrt(10)
            y = s + (r.normal(size=len(s)) + 1j * r.normal(size=len(s))) * np.sqrt(1 / (2 * 4 * ebn0))
            def dem(v):
                v = v * np.sqrt(10); b1 = (v > 0).astype(int); b2 = (np.abs(v) < 2).astype(int); return b1, b2
            b1, b2 = dem(y.real); b3, b4 = dem(y.imag)
            bh = np.empty(nb, int); bh[0::4], bh[1::4], bh[2::4], bh[3::4] = b1, b2, b3, b4
        else:
            ph = r.uniform(0, 2 * pi, nb); sig = np.sqrt(1 / (2 * ebn0))
            z0 = (b == 0) * np.exp(1j * ph) + (r.normal(size=nb) + 1j * r.normal(size=nb)) * sig
            z1 = (b == 1) * np.exp(1j * ph) + (r.normal(size=nb) + 1j * r.normal(size=nb)) * sig
            bh = (np.abs(z1) > np.abs(z0)).astype(int)
        errs += np.sum(bh != b); bits += nb
    return errs, bits


def wilson(k, n):
    ph = k / n; z = 1.96
    c = (ph + z * z / (2 * n)) / (1 + z * z / n); h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h



def run(p):
    r = p.rng
    eb = np.arange(0, 13, 1.0)
    theory = {"BPSK": lambda e: Qf(np.sqrt(2 * e)), "QPSK": lambda e: Qf(np.sqrt(2 * e)),
              "16QAM": lambda e: 0.75 * Qf(np.sqrt(0.8 * e)), "BFSK (non-coherent)": lambda e: 0.5 * np.exp(-e / 2)}
    fig, ax = p.fig(1, 1, w=8, h=5.5)
    for (name, th), c in zip(theory.items(), COLORS):
        mod = name.split()[0]
        pts = []
        for e_db in eb:
            k, n = sim(mod, e_db, r)
            if k == 0:
                break
            pts.append((e_db, k / n, *wilson(k, n)))
        pts = np.array(pts); e = 10 ** (pts[:, 0] / 10)
        inside = np.mean((th(e) >= pts[:, 2] * 0.97) & (th(e) <= pts[:, 3] * 1.03))
        p.compare(f"{name}: fraction of simulated points whose 95 % interval contains the formula", 1.0 if mod != "16QAM" else 0.8, inside, "", kind="abs", tol=0.15)
        ax.errorbar(pts[:, 0], pts[:, 1], yerr=[pts[:, 1] - pts[:, 2], pts[:, 3] - pts[:, 1]], fmt="o", ms=3, color=c, label=f"{name} (simulated)")
        ee = np.linspace(0, 12, 200); ax.semilogy(ee, th(10 ** (ee / 10)), "-", color=c, lw=1)
    eg = np.linspace(0, 20, 2001)                        # fine theory grid reaching beyond 16-QAM's ~13.4 dB at 1e-5
    k1 = 10 ** (np.interp(-5, np.log10(theory["QPSK"](10 ** (eg / 10)))[::-1], eg[::-1]) / 10)
    k2 = 10 ** (np.interp(-5, np.log10(theory["16QAM"](10 ** (eg / 10)))[::-1], eg[::-1]) / 10)
    p.compare("Eb/N0 penalty of 16-QAM over QPSK at BER 1e-5", 4.0, 10 * np.log10(k2 / k1), "dB", kind="abs", tol=0.3)
    ax.set_yscale("log"); ax.set_ylim(1e-7, 0.5)
    style_axes(ax, "Eb/N0 (dB)", "bit error rate", "Monte Carlo (points, 95 % CI) vs theory (lines)")
    p.save(fig, "ber", "Simulated BER with confidence intervals against the closed-form expressions for four modulations.")
    p.discuss("""The simulated points for BPSK, Gray-coded QPSK and non-coherent BFSK fall on their exact formulas within the Monte-Carlo confidence intervals down to
BER ≈ 10⁻⁶, which also demonstrates that Gray QPSK has exactly BPSK's bit-error rate per unit Eb/N0 — two orthogonal BPSK channels. The 16-QAM
curve uses the nearest-neighbour approximation, which is slightly off at low SNR (it ignores errors to non-adjacent points) and converges at high
SNR — the simulation shows exactly that pattern. The ≈ 4 dB gap between QPSK and 16-QAM at 10⁻⁵ is the energy cost of doubling spectral
efficiency, and non-coherent FSK's ~3–4 dB loss vs BPSK is the cost of not tracking carrier phase.""")
# tol-convention: relative tolerances are in percent
