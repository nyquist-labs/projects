#include "hal_sim.h"
#define SERVO 9
int main(void) {
    const double tick_us = 0.5;                  /* 16 MHz / 8 */
    for (int a2 = 0; a2 <= 360; a2++) {
        double angle = a2 * 0.5;
        uint16_t ocr = (uint16_t)lround((1000.0 + angle / 180.0 * 1000.0) / tick_us);
        for (int k = 0; k < 3; k++) {
            uint64_t start = sim_us;
            digitalWrite(SERVO, 1);
            /* simulated time advances in half-microsecond ticks: accumulate in 2x units */
            static uint64_t half_us = 0;
            half_us = 0; (void)half_us;
            sim_us = start + (ocr / 2); if (ocr % 2) { printf("H %d %u\n", a2, ocr); }
            digitalWrite(SERVO, 0);
            sim_us = start + 20000;
        }
        printf("C %f %u\n", angle, ocr);
    }
    return 0;
}
