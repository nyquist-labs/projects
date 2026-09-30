#include "hal_sim.h"
enum { SLEEP, SAMPLE, TX, BUTTON, NSTATE };
static const double I_uA[NSTATE] = {2.0, 1500.0, 12000.0, 1500.0};
static double charge[NSTATE], tin[NSTATE];
static void spend(int s, double us) { charge[s] += I_uA[s] * us; tin[s] += us; sim_us += (uint64_t)us; }
int main(void) {
    log_pins = 0;
    const double T_end = 30.0 * 86400e6;
    double next_sample = 60e6, next_button = -log(rnd01()) * 86400e6 / 20;
    int samples = 0;
    while (sim_us < T_end) {
        double t = (double)sim_us;
        double nxt = next_sample < next_button ? next_sample : next_button;
        if (nxt > T_end) nxt = T_end;
        spend(SLEEP, nxt - t);
        if (nxt == next_sample) {
            spend(SAMPLE, 5000); samples++;
            if (samples % 10 == 0) spend(TX, 20000);
            next_sample += 60e6;
        } else if (nxt == next_button) {
            spend(BUTTON, 50000); next_button += -log(rnd01()) * 86400e6 / 20;
        } else break;
    }
    double T = (double)sim_us, Q = 0;
    for (int s = 0; s < NSTATE; s++) { Q += charge[s]; printf("S %d %f %f\n", s, tin[s] / T, charge[s] / T); }
    printf("RES avg_uA %f\n", Q / T);
    return 0;
}
