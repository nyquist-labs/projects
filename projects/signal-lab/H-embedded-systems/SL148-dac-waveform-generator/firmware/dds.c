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
