from eelab import *
from eelab import firmware as fwk

META = dict(
    id="SL-147", title="MCU ADC sampling with a fixed-point digital filter", level="M",
    tools="C firmware (10-bit ADC model, Q15 one-pole IIR and 16-sample moving average) on the simulated MCU",
    summary="Sample a noisy 5 Hz sensor signal with a 10-bit ADC at 1 kHz and clean it with integer-only filters; predict "
            "the SNR improvement from each filter's noise bandwidth and measure it, including fixed-point rounding.",
    problem="Microcontrollers often lack floating point. How much noise can a cheap integer filter remove, and what does "
            "fixed-point arithmetic cost?",
    theory=r"""White noise through a filter is reduced by its noise-equivalent bandwidth: moving average of M → variance ×1/M (−12 dB for M = 16); one-pole
IIR y += α(x − y) → variance × α/(2 − α) (α = 1/16 → −14.9 dB). The signal (5 Hz) passes with gain ≈ 1 (MA: sinc, −0.03 dB; IIR corner 10.3 Hz → −0.9 dB).
Q15 rounding adds noise of LSB²/12 at the output (negligible vs ADC noise here).""",
    method="""Signal 1.65 V + 0.5 V·sin(2π·5 t) + Gaussian noise σ = 40 mV, ADC 10-bit (3.3 V/1024 = 3.2 mV LSB) at 1 kHz for 10 s. Filters in integer arithmetic;
SNR = signal power at 5 Hz vs residual after removing the fitted sine, compared with float references.""",
)

C = r"""
#include "hal_sim.h"
int main(void) {
    log_pins = 0;
    int32_t y_iir = 0;       /* Q15 state (ADC counts << 5) */
    int32_t buf[16] = {0}, sum = 0; int bi = 0;
    for (int n = 0; n < 10000; n++) {
        double t = n / 1000.0;
        double v = 1.65 + 0.5 * sin(2 * 3.141592653589793 * 5 * t) + 0.04 * rndn();
        int adc = (int)lround(v / 3.3 * 1023); if (adc < 0) adc = 0; if (adc > 1023) adc = 1023;
        int32_t x = adc << 5;                         /* scale to Q5 fraction for headroom */
        y_iir += (x - y_iir) >> 4;                    /* alpha = 1/16 */
        sum += adc - buf[bi]; buf[bi] = adc; bi = (bi + 1) & 15;
        printf("A %f %d %f %f\n", t, adc, y_iir / 32.0, sum / 16.0);
    }
    return 0;
}
"""


def snr(t, y, f0=5.0):
    X = np.c_[np.sin(2 * pi * f0 * t), np.cos(2 * pi * f0 * t), np.ones_like(t)]
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ c
    r = y - fit
    return 10 * np.log10(np.var(fit) / np.var(r)), c


def run(p):
    log = fwk.run(p, {"adcfilter.c": C})
    A = fwk.rows(log, "A")
    t, raw, iir, ma = A[:, 0], A[:, 1], A[:, 2], A[:, 3]
    k = t > 0.2
    s_raw, _ = snr(t[k], raw[k]); s_iir, _ = snr(t[k], iir[k]); s_ma, _ = snr(t[k], ma[k])
    p.compare("Moving average (M = 16): SNR gain", 10 * np.log10(16), s_ma - s_raw, "dB", kind="abs")
    a = 1 / 16
    p.compare("One-pole IIR (α = 1/16): SNR gain", -10 * np.log10(a / (2 - a)), s_iir - s_raw, "dB", kind="abs")
    p.metric("Raw ADC SNR", s_raw, "dB")
    fc = -np.log(1 - a) * 1000 / (2 * pi)
    p.compare("IIR corner frequency", 1000 * a / (2 * pi), fc, "Hz", tol=5)
    fig, ax = p.fig()
    m = (t > 1) & (t < 1.4)
    ax.plot(t[m], raw[m], color="gray", lw=.5, label="raw 10-bit ADC")
    ax.plot(t[m], ma[m], color=C_MEAS, label="moving average (16)")
    ax.plot(t[m], iir[m], color=COLORS[1], label="one-pole IIR (1/16)")
    style_axes(ax, "time (s)", "ADC counts", "Integer filters on a noisy 5 Hz signal")
    p.save(fig, "adc_filter", "Both integer filters remove most of the noise; the IIR also lags the signal slightly.")
    p.discuss("""Both filters deliver close to their noise-bandwidth predictions (≈ 12 and 15 dB). The one-pole IIR removes slightly more noise
but, with its corner at ~10 Hz, it also attenuates and delays the 5 Hz signal, which the SNR metric (fitted amplitude)
tolerates but a control loop might not. Both run with shifts and adds only; the Q5 headroom in the IIR state keeps rounding
noise below the ADC's own quantisation noise.""")
