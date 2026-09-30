#include "hal_sim.h"
static int crc15(const int *b, int n) { int c = 0; for (int i = 0; i < n; i++) { int nx = b[i] ^ ((c >> 14) & 1); c = (c << 1) & 0x7FFF; if (nx) c ^= 0x4599; } return c; }
static int build(int id, const uint8_t *d, int dlc, int *out) {
    int f[200], n = 0;
    f[n++] = 0; for (int i = 10; i >= 0; i--) f[n++] = (id >> i) & 1; f[n++] = 0; f[n++] = 0; f[n++] = 0;
    for (int i = 3; i >= 0; i--) f[n++] = (dlc >> i) & 1;
    for (int k = 0; k < dlc; k++) for (int i = 7; i >= 0; i--) f[n++] = (d[k] >> i) & 1;
    int c = crc15(f, n); for (int i = 14; i >= 0; i--) f[n++] = (c >> i) & 1;
    int m = 0, run = 0, last = -1;
    for (int i = 0; i < n; i++) { out[m++] = f[i]; if (f[i] == last) run++; else { run = 1; last = f[i]; }
        if (run == 5) { out[m++] = !last; last = !last; run = 1; } }
    out[m++] = 1; out[m++] = 1; out[m++] = 1;            /* CRC delim, ACK (recessive here), ACK delim */
    for (int i = 0; i < 7; i++) out[m++] = 1;            /* EOF */
    for (int i = 0; i < 3; i++) out[m++] = 1;            /* interframe space */
    return m;
}
int main(void) {
    log_pins = 0;
    const int NM = 5; int ids[5] = {0x100, 0x200, 0x300, 0x400, 0x500}; double Tms[5] = {5, 10, 10, 20, 50};
    double off[5]; for (int i = 0; i < NM; i++) off[i] = 0.0;         /* critical instant: all released together */
    const double bit_us = 2.0; double t = 0; double next[5]; for (int i = 0; i < NM; i++) next[i] = off[i] * 1000;
    int pend[5] = {0}; double rel[5] = {0}; double worst[5] = {0};
    int frame[300]; int maxlen = 0, minlen = 1000; long arb_contests = 0, arb_ok = 0;
    uint8_t d[8];
    while (t < 2e6) {
        for (int i = 0; i < NM; i++) while (next[i] <= t) { if (!pend[i]) { pend[i] = 1; rel[i] = next[i]; } next[i] += Tms[i] * 1000 + 40 * rnd01(); }  /* small release jitter keeps queues colliding */
        int cand[5], nc = 0; for (int i = 0; i < NM; i++) if (pend[i]) cand[nc++] = i;
        if (!nc) { t += bit_us; continue; }
        /* bit-wise arbitration over the 11 ID bits */
        int alive[5]; for (int k = 0; k < nc; k++) alive[k] = 1;
        for (int b = 10; b >= 0; b--) { int bus = 1; for (int k = 0; k < nc; k++) if (alive[k]) bus &= (ids[cand[k]] >> b) & 1;
            for (int k = 0; k < nc; k++) if (alive[k] && ((ids[cand[k]] >> b) & 1) != bus) alive[k] = 0; }
        int win = -1, lowest = 1 << 20; for (int k = 0; k < nc; k++) { if (alive[k]) win = cand[k]; if (ids[cand[k]] < lowest) lowest = ids[cand[k]]; }
        if (nc > 1) { arb_contests++; if (ids[win] == lowest) arb_ok++; }
        for (int k = 0; k < 8; k++) d[k] = (uint8_t)rnd32();
        int len = build(ids[win], d, 8, frame);
        if (len > maxlen) maxlen = len; if (len < minlen) minlen = len;
        t += len * bit_us;
        double resp = t - rel[win]; if (resp > worst[win]) worst[win] = resp; pend[win] = 0;
    }
    printf("RES maxlen %d\nRES minlen %d\nRES contests %ld\nRES arb_ok %ld\n", maxlen, minlen, arb_contests, arb_ok);
    for (int i = 0; i < NM; i++) printf("W %d %f\n", i, worst[i]);
    return 0;
}
