#include "hal_sim.h"
int main(void) {
    log_pins = 0;
    const int NEV = 10000; double t_loop_start = 0;
    for (int e = 0; e < NEV; e++) {
        double ev = e * 7919.0 + rnd01() * 5000.0;            /* event time, µs */
        /* main loop timeline around the event: loop iterations with random work 400–600 µs */
        double t = floor(ev / 500.0) * 500.0 - 1000.0; double poll_resp = -1, crit_s = 0, crit_e = 0;
        while (1) {
            double work = 400 + 200 * rnd01();
            double cs = t + work * rnd01(); crit_s = cs; crit_e = cs + 50;
            if (t >= ev && poll_resp < 0) poll_resp = t;           /* the flag is checked at the top of the loop */
            if (t > ev + 2000) break;
            if (crit_s <= ev && ev < crit_e) { printf("M %f\n", crit_e - ev); }
            t += work;
        }
        double isr = 0.75; double lat_irq = isr;
        /* is the event inside a critical section of the iteration containing it? */
        double it0 = floor(ev / 500.0) * 500.0; double cs0 = it0 + 250 * rnd01();
        if (cs0 <= ev && ev < cs0 + 50) lat_irq += cs0 + 50 - ev;
        printf("L %f %f\n", poll_resp - ev, lat_irq);
    }
    return 0;
}
