#include "hal_sim.h"
static const uint8_t HALF[8] = {0x1, 0x3, 0x2, 0x6, 0x4, 0xC, 0x8, 0x9};   /* A, AB, B, BA', A', A'B', B', B'A */
static int phase = 0;
static void step_out(void) { phase = (phase + 1) & 7; for (int i = 0; i < 4; i++) digitalWrite(2 + i, (HALF[phase] >> i) & 1); }
int main(void) {
    const double alpha = 4000.0, vmax = 2000.0; const long S = 1200;
    long accel_steps = (long)(vmax * vmax / (2 * alpha));
    if (accel_steps > S / 2) accel_steps = S / 2;
    double c = sqrt(2.0 / alpha) * 0.676 * 1e6;   /* Austin's 0.676 correction for the first step */
    double cmin = 1e6 / vmax;
    double cn = c;
    for (long n = 0; n < S; n++) {
        step_out();
        printf("S %ld %llu\n", n, (unsigned long long)sim_us);
        long remaining = S - 1 - n;
        if (remaining < accel_steps) {             /* decelerate */
            long k = remaining + 1;
            cn = cn + 2 * cn / (4 * k - 1);
        } else if (n + 1 < accel_steps) {         /* accelerate */
            cn = cn - 2 * cn / (4 * (n + 1) + 1);
            if (cn < cmin) cn = cmin;
        } else cn = cmin;
        sim_us += (uint64_t)llround(cn);
    }
    return 0;
}
