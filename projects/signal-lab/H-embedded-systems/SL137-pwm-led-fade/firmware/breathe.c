#include "hal_sim.h"
#define LED 13
static uint8_t gamma8[256];
int main(void) {
    for (int i = 0; i < 256; i++) gamma8[i] = (uint8_t)lround(pow(i / 255.0, 2.2) * 255.0);
    const uint32_t tick_us = 4;                 /* 256 ticks × 3.9 µs ≈ 1 kHz */
    uint64_t t_end = 4000000;
    int idx = 0, dir = 1;
    uint64_t next_step = 0;
    const uint64_t step_us = 1000000 / 256;      /* 256 steps up + 256 down = 2 s */
    while (sim_us < t_end) {
        uint8_t duty = gamma8[idx];
        for (int c = 0; c < 256; c++) {          /* one PWM period */
            digitalWrite(LED, c < duty);
            delay_us(tick_us);
        }
        if (sim_us >= next_step) {
            next_step += step_us * 4;            /* ~one PWM period per step x 4 */
            idx += dir;
            if (idx == 255 || idx == 0) dir = -dir;
        }
    }
    RES("pwm_period_us", "%u", 256 * tick_us);
    return 0;
}
