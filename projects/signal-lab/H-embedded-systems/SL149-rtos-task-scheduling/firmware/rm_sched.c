#include "hal_sim.h"
int main(int argc, char **argv) {
    log_pins = 0;
    int n = 4; long Cc[4], T[4];
    for (int i = 0; i < 4; i++) { Cc[i] = atol(argv[1 + 2 * i]) ; T[i] = atol(argv[2 + 2 * i]); }
    long rem[4] = {0}, rel[4] = {0}; long worst[4] = {0}; int miss[4] = {0};
    long H = 40000L * 10;
    for (long t = 0; t < H; t++) {
        for (int i = 0; i < n; i++) if (t % T[i] == 0) { if (rem[i] > 0) miss[i]++; rem[i] = Cc[i]; rel[i] = t; }
        for (int i = 0; i < n; i++) if (rem[i] > 0) { rem[i]--; if (rem[i] == 0) { long r = t + 1 - rel[i]; if (r > worst[i]) worst[i] = r; } break; }
    }
    for (int i = 0; i < n; i++) printf("W %d %ld %d\n", i, worst[i], miss[i]);
    return 0;
}
