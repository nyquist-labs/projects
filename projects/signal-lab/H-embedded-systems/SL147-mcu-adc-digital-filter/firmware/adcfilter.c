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
