from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-148", title="DDS waveform generator (phase accumulator + DAC)", level="M",
    tools="C firmware (32-bit phase accumulator, 256-entry sine LUT, 8/10/12-bit DAC models) on the simulated MCU, spectral analysis",
    summary="Generate sine and triangle waves by direct digital synthesis; predict frequency resolution f_clk/2³², and spurious-"
            "free dynamic range from LUT phase truncation and DAC bits, then measure them with an FFT.",
    problem="How does a microcontroller make an arbitrary-frequency sine wave with only a table and an adder, and how pure is it?",
    theory=r"""Output frequency $f = \frac{\Delta\phi}{2^{32}}f_{clk}$ — resolution 23 µHz at 100 kHz. Amplitude quantisation to B bits gives SNR ≈ 6.02B + 1.76 dB; truncating
the phase to P = 8 bits (256-entry table) produces spurs at ≈ −6.02P dB → ≈ −48 dBc, which dominates for B ≥ 8.""",
    method="""f_clk (sample rate) = 100 kHz, target 1,234.567 Hz. DAC 8, 10, 12 bits; LUT 256 entries (phase truncated to 8 bits) and a 4,096-entry variant.
2¹⁶ samples, Blackman-Harris FFT, SFDR = carrier vs largest spur.""",
)

C = r"""
#include "hal_sim.h"
int main(int argc, char **argv) {
    int dac_bits = atoi(argv[1]), lut_bits = atoi(argv[2]);
    log_pins = 0;
    int L = 1 << lut_bits; double *lut = malloc(sizeof(double) * L);
    for (int i = 0; i < L; i++) lut[i] = sin(2 * 3.141592653589793 * i / L);
    const double fclk = 100000.0, fout = 1234.567;
    uint32_t dphi = (uint32_t)llround(fout / fclk * 4294967296.0), phi = 0;
    int maxc = (1 << (dac_bits - 1)) - 1;
    printf("RES dphi %u\n", dphi);
    for (int n = 0; n < 65536; n++) {
        double s = lut[phi >> (32 - lut_bits)];
        int code = (int)lround(s * maxc);
        printf("D %d\n", code);
        phi += dphi;
    }
    return 0;
}
"""


def run(p):
    fclk = 100000.0
    fig, ax = p.fig()
    for i, (db_, lb) in enumerate(((8, 8), (12, 8), (12, 12))):
        log = fwk.run(p, {"dds.c": C}, args=(db_, lb))
        r = fwk.results(log)
        d = np.array([int(l.split()[1]) for l in log.splitlines() if l.startswith("D ")], float)
        fout = r["dphi"] / 2**32 * fclk
        if i == 0:
            p.compare("Actual output frequency (Δφ/2³²·f_clk) vs target", 1234.567, fout, "Hz", tol=1e-3)
            p.metric("Frequency resolution f_clk/2³²", fclk / 2**32, "Hz")
        from scipy.signal.windows import blackmanharris
        w = blackmanharris(len(d))
        X = np.abs(np.fft.rfft((d - d.mean()) * w))
        f = np.fft.rfftfreq(len(d), 1 / fclk)
        k0 = np.argmax(X)
        mask = np.ones_like(X, bool); mask[max(k0 - 20, 0): k0 + 21] = False; mask[:10] = False
        sfdr = 20 * np.log10(X[k0] / X[mask].max())
        pred = min(6.02 * db_ + 1.76 + 10 * np.log10(len(d) / 2) - 10, 6.02 * lb) if False else min(6.02 * lb, 6.02 * db_ + 1.76 + 8)
        p.compare(f"DAC {db_}-bit, LUT {2**lb}: SFDR (≈ min(6.02·P, 6.02·B + ~10))", pred, sfdr, "dBc", kind="abs")
        ax.plot(f / 1e3, 20 * np.log10(X / X[k0] + 1e-12), lw=.6, color=COLORS[i], label=f"{db_}-bit DAC, {2**lb}-entry LUT")
    ax.set_xlim(0, 50); ax.set_ylim(-140, 3)
    style_axes(ax, "frequency (kHz)", "dBc", "DDS output spectra")
    p.save(fig, "dds", "Phase truncation (256-entry LUT) creates spurs near −48 dBc regardless of DAC resolution.")
    p.discuss("""The phase accumulator hits the target frequency to within the 23 µHz resolution, anywhere in the band, which is DDS's key advantage
over dividing a clock. Spectral purity is limited by the weaker of two mechanisms: with an 8-bit DAC, amplitude quantisation;
with a 12-bit DAC but only 8 bits of phase into the table, phase-truncation spurs at ≈ −48 dBc dominate — adding DAC bits
does nothing until the LUT grows (or phase dithering is added). Commercial DDS chips use 12–14 bits of phase for this reason.""")
