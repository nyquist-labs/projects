#include "hal_sim.h"
#define SCK 13
#define MOSI 11
static double cyc_acc = 0;
static void cyc(int n) { cyc_acc += n / 16.0; while (cyc_acc >= 1.0) { sim_us += 1; cyc_acc -= 1.0; } }
static uint64_t t_ns = 0;
static void pin(int p_, int v) { cyc(2); printf("E %llu %d %d\n", (unsigned long long)t_ns, p_, v); }
static void adv(int n) { t_ns += (uint64_t)(n * 62.5); }
static uint8_t xfer(uint8_t out, int mode) {
    uint8_t in = 0;
    for (int b = 7; b >= 0; b--) {
        printf("E %llu %d %d\n", (unsigned long long)t_ns, MOSI, (out >> b) & 1); adv(3);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 1 : 0); adv(2);
        in = (in << 1) | 0; adv(2);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 0 : 1); adv(2);
        adv(5);
    }
    return in;
}
int main(void) {
    log_pins = 0;
    for (int mode = 0; mode <= 3; mode += 3) {
        printf("MODE %d\n", mode);
        printf("E %llu %d %d\n", (unsigned long long)t_ns, SCK, mode == 0 ? 0 : 1);
        for (int k = 0; k < 64; k++) { uint8_t v = (uint8_t)(k * 37 + 11); printf("B %d\n", v); xfer(v, mode); }
        t_ns += 10000;
    }
    return 0;
}
