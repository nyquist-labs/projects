from eelab import *
from scipy.special import erfc

META = dict(
    id="SL-119", title="Frequency hopping against a narrowband jammer", level="M",
    tools="Monte Carlo slow-FH BFSK link (NumPy), jammer-fraction analysis, repetition coding",
    summary="A link hopping over 50 channels versus a strong jammer parked on 1–10 channels: predict the error rate "
            "from the fraction of hops jammed and show how a simple code turns jammed hops into correctable errors.",
    problem="Bluetooth and military radios hop frequencies. How much protection does hopping give against a jammer, "
            "and why is coding essential?",
    theory=r"""With q channels and J jammed, a hop is jammed with probability ρ = J/q; jammed symbols are essentially random (P ≈ ½), clean ones follow
non-coherent BFSK $\tfrac12e^{-E_b/2N_0}$: $P_b\approx\rho\cdot\tfrac12+(1-\rho)\tfrac12e^{-E_b/2N_0}$. Spreading each bit over 3 hops with
majority voting gives $P\approx3P_b^2-2P_b^3$ when hops are independent.""",
    method="""q = 50 channels, 1 bit per hop (slow hopping, 1 symbol/hop), E_b/N₀ = 12 dB, jammer power 20 dB above the signal on its channels.
J = 0, 1, 2, 5, 10. Uncoded and 3× repetition (each copy on a different random hop). 200,000 bits per point.""",
)


def run(p):
    q, eb = 50, 10 ** (12 / 10)
    Js = [0, 1, 2, 5, 10]
    unc, cod, pu, pc = [], [], [], []
    n = 200000
    for J in Js:
        jammed = set(range(J))
        def send(nbits):
            ch = p.rng.integers(0, q, nbits)
            bits = p.rng.integers(0, 2, nbits)
            # non-coherent BFSK energy detector: tone energies with Rayleigh-distributed noise
            s = np.sqrt(eb)
            e0 = np.abs((bits == 0) * s + (p.rng.normal(size=nbits) + 1j * p.rng.normal(size=nbits)) / np.sqrt(2)) ** 2
            e1 = np.abs((bits == 1) * s + (p.rng.normal(size=nbits) + 1j * p.rng.normal(size=nbits)) / np.sqrt(2)) ** 2
            jm = np.isin(ch, list(jammed))
            jam = 10 * np.sqrt(eb)
            e0[jm] += np.abs(jam * (p.rng.normal(size=jm.sum()) + 1j * p.rng.normal(size=jm.sum())) / np.sqrt(2)) ** 2
            e1[jm] += np.abs(jam * (p.rng.normal(size=jm.sum()) + 1j * p.rng.normal(size=jm.sum())) / np.sqrt(2)) ** 2
            return bits, (e1 > e0).astype(int)
        b, d = send(n)
        pb = np.mean(b != d); unc.append(pb)
        b3, d3 = send(3 * n)
        b3 = b3.reshape(n, 3); d3 = d3.reshape(n, 3)
        # repetition: same info bit in 3 hops -> use the first column as truth and flip copies consistently
        info = b3[:, 0]
        errs = (d3 != b3)
        dec_err = errs.sum(1) >= 2
        cod.append(np.mean(dec_err))
        rho = J / q
        pth = rho * 0.5 + (1 - rho) * 0.5 * np.exp(-eb / 2)
        pu.append(pth); pc.append(3 * pth**2 - 2 * pth**3)
    unc, cod, pu, pc = map(np.array, (unc, cod, pu, pc))
    for J in (1, 5):
        k = Js.index(J)
        p.compare(f"{J} jammed channels: uncoded BER", pu[k], unc[k], "", tol=10)
        p.compare(f"{J} jammed channels: 3× repetition BER", pc[k], cod[k], "", tol=15)
    fig, ax = p.fig()
    rho = np.array(Js) / q
    ax.semilogy(rho * 100, np.maximum(unc, 1e-6), "o", color=COLORS[1], label="uncoded (sim)"); ax.semilogy(rho * 100, pu, "--", color=COLORS[1], lw=1)
    ax.semilogy(rho * 100, np.maximum(cod, 1e-6), "s", color=C_MEAS, label="3× repetition over hops (sim)"); ax.semilogy(rho * 100, pc, "--", color=C_MEAS, lw=1)
    style_axes(ax, "fraction of channels jammed (%)", "BER", "Frequency hopping vs a partial-band jammer (dashed = theory)")
    p.save(fig, "fh", "Hopping limits the jammer to ρ/2 errors; coding across hops squares that down.")
    p.csv("ber", jammed_channels=Js, uncoded=unc, repetition=cod, uncoded_theory=pu, repetition_theory=pc)
    p.discuss("""Without hopping a jammer on our channel would destroy every bit; with hopping it only hits the fraction ρ of hops, and the
BER is ≈ ρ/2 regardless of jammer power — exactly the prediction. That residual error rate is still far too high for data,
which is why every FH system codes across hops: with a 3× repetition code the error rate falls roughly as ρ², and real
systems (Bluetooth, SINCGARS) use stronger codes and interleaving to push it much further.""")
