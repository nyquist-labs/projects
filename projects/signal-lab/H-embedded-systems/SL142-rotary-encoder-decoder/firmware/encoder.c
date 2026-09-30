#include "hal_sim.h"
static const int8_t TAB[16] = {0,-1, 1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
int main(int argc, char **argv) {
    double fpoll = atof(argv[1]), rps = atof(argv[2]);
    log_pins = 0;
    const int edges_per_rev = 96;
    double edge_dt = 1.0 / (rps * edges_per_rev);
    /* build edge schedule: forward 3 rev, back 1 rev */
    int nedge = edges_per_rev * 4;
    double t = 0.001; int state = 0, truecount = 0;
    const int seqf[4] = {0, 1, 3, 2};
    int pos = 0;
    double *et = malloc(sizeof(double) * nedge * 4); int *es = malloc(sizeof(int) * nedge * 4); int ne = 0;
    for (int k = 0; k < nedge; k++) {
        int dir = k < edges_per_rev * 3 ? 1 : -1;
        pos = (pos + dir + 4) % 4; truecount += dir;
        int ns = seqf[pos];
        int changed = ns ^ state;             /* one bit */
        for (int b = 0; b < 3; b++) { et[ne] = t + b * 8e-6; es[ne] = (b % 2 == 0) ? ns : state; ne++; }  /* bounce */
        et[ne] = t + 30e-6; es[ne] = ns; ne++;
        state = ns; t += edge_dt; (void)changed;
    }
    double dtp = 1.0 / fpoll; int count = 0, prev = 0, idx = 0, cur = 0;
    for (double tp = 0; tp < t + 0.01; tp += dtp) {
        while (idx < ne && et[idx] <= tp) { cur = es[idx]; idx++; }
        count -= TAB[(prev << 2) | cur]; prev = cur;     /* table sign convention: CW sequence 00→01→11→10 counts up */
    }
    printf("RES count %d\nRES truth %d\n", count, truecount);
    return 0;
}
